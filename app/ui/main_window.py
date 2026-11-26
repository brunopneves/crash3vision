from __future__ import annotations

from enum import Enum
import logging
import math
from pathlib import Path

import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QDockWidget,
    QLabel,
    QSlider,
    QMessageBox,
    QFileDialog,
    QCheckBox,
    QGroupBox,
    QLineEdit,
    QScrollArea,
    QComboBox,
    QDoubleSpinBox,
    QRadioButton,
    QButtonGroup,
    QBoxLayout,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QFrame,
)

from app.ui.canvas_view import CanvasView
from app.core.auto_alignment import (
    AlignmentDiagnostics,
    AlignmentHypothesis,
    AutoAlignmentError,
    estimate_auto_alignment,
)
from app.core.rigid_region_alignment import (
    RigidAlignmentResult,
    RigidRegion,
    expand_point_anchor_regions,
    estimate_multiscale_rigid_alignment,
    estimate_rigid_region_alignment,
    suggest_rigid_region_anchors,
)
from app.core.project import Project, Point
from app.ui.controllers.project_io_controller import ProjectIOController
from app.ui.controllers.measurement_controller import MeasurementController
from app.ui.controllers.workflow_controller import WorkflowController
from app.ui.controllers.calc_controller import CalcController
from app.ui.widgets.calc_panel import CalcPanel
from app.report import generate_report
from app.i18n import tr, set_language, get_language


logger = logging.getLogger(__name__)


class Stage(str, Enum):
    LOAD = "load"
    ALIGNMENT = "alignment"
    CALIBRATION = "calibration"
    MARKING = "marking"
    DONE = "done"


class AlignmentMethodRow(QWidget):
    def __init__(self, *buttons: QRadioButton) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._row = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._buttons = buttons
        for button in buttons:
            self._row.addWidget(button)

    def update_direction(self) -> None:
        required = sum(button.sizeHint().width() for button in self._buttons)
        required += self._row.spacing() * (len(self._buttons) - 1)
        self._row.setDirection(
            QBoxLayout.Direction.LeftToRight if self.width() >= required
            else QBoxLayout.Direction.TopToBottom
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_direction()


class MainWindow(QMainWindow):
    Stage = Stage

    def __init__(self) -> None:
        super().__init__()

        set_language("pt")

        # self.setWindowTitle(tr("app.title"))
        self.resize(1280, 900)

        self.canvas = CanvasView()
        self._build_canvas_area()

        self.project = Project(name="")
        self._current_project_path: str | None = None
        self._update_window_title()

        self.stage: Stage = Stage.LOAD
        self._viewed_step: str | None = None

        self._calibration_px: float | None = None
        self._m_per_px: float | None = None

        self._w_px: float | None = None
        self._w_m: float | None = None
        self._delta_w_px: float | None = None
        self._delta_w_m: float | None = None

        self._ci_px: dict[int, float] = {}
        self._ci_m: dict[int, float] = {}
        self._current_ci_index: int = 1

        self._pending_auto_alignment: AlignmentHypothesis | None = None
        self._auto_preview_baseline_dam_transform: dict[str, float] | None = None
        self._auto_preview_active = False
        self._rigid_reference_regions: list[RigidRegion] = []
        self._last_applied_rigid_reference_regions: tuple[RigidRegion, ...] = ()
        self._rigid_deformed_region: RigidRegion | None = None
        self._rigid_alignment_result: RigidAlignmentResult | None = None
        self._rigid_baseline_ref_transform: dict[str, float] | None = None
        self._rigid_baseline_dam_transform: dict[str, float] | None = None
        self._rigid_expansion_attempted = False
        self._rigid_internal_transform_change = False
        self._rigid_preview_active = False
        self._rigid_instruction_key: str | None = None

        self._total_energy: float | None = None
        self._vehicle_mass_kg: float | None = None
        self._damage_speed_mps: float | None = None
        self._damage_speed_kmh: float | None = None

        self.io = ProjectIOController(self)
        self.meas = MeasurementController(self)
        self.workflow = WorkflowController(self)
        self.calc = CalcController(self)

        self._build_menu()
        self._build_workflow_progress()
        self._build_dock()
        self._apply_styles()
        self._build_shortcuts()

        self.canvas.calibration_px_measured.connect(
            self.meas.on_calibration_px_measured
        )
        self.canvas.w_px_measured.connect(self.meas.on_w_px_measured)
        self.canvas.w_cleared.connect(self.meas.on_w_cleared)
        self.canvas.ci_measured.connect(self.meas.on_ci_measured)
        self.canvas.ci_selected.connect(self._on_canvas_ci_selected)
        self.canvas.alignment_state_changed.connect(self._on_alignment_state_changed)
        self.canvas.images_changed.connect(self._on_images_changed)
        self.canvas.rigid_region_selected.connect(self._on_rigid_region_selected)

        self._update_ci_label()
        self._sync_ci_radio_buttons()
        self._refresh_summary()
        self.workflow.apply_stage_gating()

    def _update_window_title(self) -> None:
        project = getattr(self, "project", None)
        project_name = project.name if project and project.name else ""

        if project_name:
            self.setWindowTitle(f"{tr('app.title')} — {project_name}")
        else:
            self.setWindowTitle(tr("app.title"))

    # ---------------- UI builders ----------------
    def _build_menu(self) -> None:
        m = self.menuBar()
        file_menu = m.addMenu(tr("menu.file"))

        act_new = file_menu.addAction(tr("menu.new"))
        act_save = file_menu.addAction(tr("menu.save_project"))
        act_load = file_menu.addAction(tr("menu.load_project"))
        file_menu.addSeparator()
        act_export = file_menu.addAction(tr("menu.export_overlay"))
        act_export_current_view = file_menu.addAction(tr("menu.export_current_view"))
        act_export_report = file_menu.addAction(tr("menu.export_report"))

        lang_menu = m.addMenu(tr("menu.language"))
        act_lang_en = lang_menu.addAction(tr("menu.language.english"))
        act_lang_pt = lang_menu.addAction(tr("menu.language.portuguese"))

        act_new.triggered.connect(self._on_new_project)
        act_save.triggered.connect(self._on_save_project)
        act_load.triggered.connect(self._on_load_project)
        act_export.triggered.connect(self._on_export_png)
        act_export_current_view.triggered.connect(self._on_export_current_view_png)
        act_export_report.triggered.connect(self._on_export_report)

        act_lang_en.triggered.connect(lambda: self._set_language_and_refresh("en"))
        act_lang_pt.triggered.connect(lambda: self._set_language_and_refresh("pt"))

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMenuBar::item {
                padding: 4px 10px;
                margin: 2px;
                border: 1px solid rgba(255,255,255,40);
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: rgba(255,255,255,30);
            }
            QMenu {
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(255,255,255,30);
            }
            """
        )

        bold = QFont()
        bold.setBold(True)
        for lbl in (
            self.lbl_px_distance,
            self.lbl_m_per_px,
            self.lbl_w,
            self.lbl_delta_w,
            self.lbl_ci_values,
        ):
            lbl.setFont(bold)

    def _build_workflow_progress(self) -> None:
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.toggleViewAction().setVisible(False)
        strip = QWidget()
        strip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)
        self.workflow_step_labels = {}
        for step in ("images", "alignment", "calibration", "measurement", "calculation", "result"):
            label = QPushButton()
            label.clicked.connect(lambda checked=False, target=step: self._view_workflow_step(target))
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.workflow_step_labels[step] = label
            layout.addWidget(label, 1)
        toolbar.addWidget(strip)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _current_workflow_step(self) -> str:
        if (
            self.stage == Stage.DONE
            and self._total_energy is not None
            and self._damage_speed_kmh is not None
        ):
            return "result"
        return {
            Stage.LOAD: "images",
            Stage.ALIGNMENT: "alignment",
            Stage.CALIBRATION: "calibration",
            Stage.MARKING: "measurement",
            Stage.DONE: "calculation",
        }[self.stage]

    def _workflow_navigation_blocked(self) -> bool:
        return self._auto_preview_active or self._rigid_baseline_ref_transform is not None

    def _view_workflow_step(self, step: str) -> None:
        steps = tuple(self.workflow_step_labels)
        current = self._current_workflow_step()
        if self._workflow_navigation_blocked() or steps.index(step) > steps.index(current):
            return
        viewed = None if step == current else step
        if viewed != self._viewed_step:
            self.workflow.reset_canvas_tools()
            self._viewed_step = viewed
            self.workflow.apply_stage_gating()
            self._refresh_workflow_progress()

    def _return_to_current_step(self) -> None:
        self._view_workflow_step(self._current_workflow_step())

    def _redo_viewed_step(self) -> None:
        actions = {
            "alignment": self._on_restart_alignment,
            "calibration": self._on_restart_calibration,
            "measurement": self._on_restart_marking,
        }
        step = self._viewed_step
        if step not in actions or self._workflow_navigation_blocked():
            return
        answer = QMessageBox.question(
            self,
            tr("progress.redo"),
            tr(f"progress.redo.{step}"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            actions[step]()

    def _refresh_workflow_progress(self) -> None:
        steps = tuple(self.workflow_step_labels)
        current = steps.index(self._current_workflow_step())
        result_ready = steps[current] == "result"
        blocked = self._workflow_navigation_blocked()

        highlight = "background-color: #245b96; color: white; font-weight: bold;"
        for index, (step, label) in enumerate(self.workflow_step_labels.items()):
            title = tr(f"progress.{step}")
            if step == "alignment":
                if current <= index:
                    title += f" · {tr('progress.optional')}"
                elif not self.canvas.has_both_images():
                    title += f" · {tr('progress.skipped')}"
            if step == "alignment" and index < current:
                status, text, style = "passed", f"→ {title}", "color: #808080;"
            elif step == "result" and result_ready:
                status, text, style = "complete", f"✓ {title}", highlight
            elif index < current:
                status, text, style = "complete", f"✓ {title}", "font-weight: bold;"
            elif index == current:
                status, text, style = "current", title, highlight
            else:
                status, text, style = "future", title, "color: #808080;"
            label.setProperty("progressStatus", status)
            viewing = step == self._viewed_step
            if viewing:
                style += "border: 1px solid #67727a; font-weight: bold;"
                text = f"▸ {text}"
            label.setText(text)
            description = tr(f"progress.status.{status}")
            if viewing:
                description = tr("progress.viewing_calculation" if step == "calculation" else "progress.viewing")
            label.setToolTip(f"{text} — {description}")
            label.setAccessibleName(label.toolTip())
            label.setEnabled(index <= current and not blocked)
            label.setStyleSheet(f"QPushButton {{ border: 1px solid transparent; {style} padding: 3px; border-radius: 3px; }}")

    def _build_canvas_area(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas, 1)

        self.canvas_view_bar = QWidget()
        self.canvas_view_bar.setObjectName("canvasViewBar")
        self.canvas_view_bar.setMinimumHeight(40)
        self.canvas_view_bar.setStyleSheet("""
            QWidget#canvasViewBar { background: palette(window); border-top: 1px solid #b8cddd; }
            QSlider::groove:horizontal { height: 5px; background: #9aafbf; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #3975ab; border-radius: 2px; }
            QSlider::handle:horizontal {
                width: 14px; margin: -5px 0; background: #245b96; border-radius: 7px;
            }
            QSlider::handle:horizontal:disabled { background: #87939d; }
        """)
        bar_layout = QHBoxLayout(self.canvas_view_bar)
        bar_layout.setContentsMargins(8, 3, 8, 3)
        self.lbl_overlay_opacity = QLabel(tr("label.overlay_opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.setMinimumHeight(22)
        self.lbl_opacity_percent = QLabel()
        self.lbl_opacity_percent.setStyleSheet("font-weight: bold;")
        self.lbl_opacity_percent.setMinimumWidth(
            self.lbl_opacity_percent.fontMetrics().horizontalAdvance("100%")
        )
        self._refresh_opacity_percentage()
        bar_layout.addWidget(self.lbl_overlay_opacity)
        bar_layout.addWidget(self.opacity_slider, 1)
        bar_layout.addWidget(self.lbl_opacity_percent)
        layout.addWidget(self.canvas_view_bar)
        self.setCentralWidget(central)

    @staticmethod
    def _style_disclosure(toggle: QToolButton) -> None:
        toggle.setCheckable(True)
        toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toggle.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        toggle.setStyleSheet("""
            QToolButton {
                background: #edf0f2; color: #23313a;
                border: 2px solid #c8cfd4; border-radius: 4px;
                padding: 3px 7px; font-size: 11px;
            }
            QToolButton:hover { background: #e0e5e8; }
            QToolButton:focus { border-color: #245b96; }
            QToolButton:disabled { color: #59636a; background: #f3f4f5; }
        """)

    def _build_dock(self) -> None:
        dock = QDockWidget(tr("dock.controls"), self)
        self._controls_dock = dock
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)

        scroll = QScrollArea()
        self._controls_scroll = scroll
        scroll.setWidgetResizable(True)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(6, 9, 6, 9)
        self.btn_return_to_current_step = QPushButton(tr("progress.return_current"))
        self.btn_return_to_current_step.clicked.connect(self._return_to_current_step)
        self.btn_return_to_current_step.hide()
        dock_layout.addWidget(self.btn_return_to_current_step)
        self.btn_redo_step = QPushButton(tr("progress.redo"))
        self.btn_redo_step.clicked.connect(self._redo_viewed_step)
        self.btn_redo_step.hide()
        dock_layout.addWidget(self.btn_redo_step)

        # --- Load images ---
        self.load_group = QGroupBox(tr("group.load_images"))
        load_layout = QVBoxLayout(self.load_group)
        self.btn_toggle_image_controls = QToolButton()
        self._style_disclosure(self.btn_toggle_image_controls)
        self.btn_toggle_image_controls.toggled.connect(self._refresh_image_controls)
        load_layout.addWidget(self.btn_toggle_image_controls)
        self.btn_load_ref = QPushButton(tr("button.load_ref"))
        self.btn_load_dam = QPushButton(tr("button.load_dam"))
        load_layout.addWidget(self.btn_load_ref)
        load_layout.addWidget(self.btn_load_dam)
        dock_layout.addWidget(self.load_group)

        self.fine_adjust_group = QGroupBox()
        fine_layout = QVBoxLayout(self.fine_adjust_group)
        fine_layout.setContentsMargins(8, 10, 8, 10)
        self.btn_toggle_manual_alignment = QToolButton()
        self.btn_toggle_advanced_alignment = QToolButton()
        for toggle in (self.btn_toggle_manual_alignment, self.btn_toggle_advanced_alignment):
            self._style_disclosure(toggle)
            toggle.toggled.connect(self._refresh_alignment_sections)
        self.alignment_advanced = QWidget()
        advanced_layout = QGridLayout(self.alignment_advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setHorizontalSpacing(3)

        # --- Alignment group ---
        self.align_group = QGroupBox(tr("group.alignment"))
        align_layout = QVBoxLayout(self.align_group)
        self.lbl_alignment_consultation = QLabel()
        self.lbl_alignment_consultation.setWordWrap(True)
        self.lbl_alignment_consultation.hide()
        align_layout.addWidget(self.lbl_alignment_consultation)

        self.chk_alignment_mode = QCheckBox(tr("check.alignment_mode"))
        self.chk_alignment_mode.setToolTip(tr("check.alignment_mode_hint"))
        self.chk_lock_alignment = QCheckBox(tr("check.lock_alignment"))
        fine_layout.addWidget(self.chk_alignment_mode)
        fine_layout.addWidget(self.chk_lock_alignment)

        self.lbl_editable_image = QLabel(tr("label.editable_image"))
        fine_layout.addWidget(self.lbl_editable_image)

        self.cmb_alignment_target = QComboBox()
        self.cmb_alignment_target.addItem(tr("combo.deformed"), "dam")
        self.cmb_alignment_target.addItem(tr("combo.reference"), "ref")
        self.canvas.set_alignment_target("dam")
        fine_layout.addWidget(self.cmb_alignment_target)

        self.btn_reset_alignment = QPushButton(tr("button.reset_selected_transform"))
        self.btn_reset_alignment.setAccessibleName(self.btn_reset_alignment.text())
        self.btn_reset_alignment.setToolTip(tr("alignment.reset.tooltip"))
        self.btn_reset_alignment.setFlat(True)

        self.lbl_alignment_method = QLabel(tr("label.alignment_method"))
        align_layout.addWidget(self.lbl_alignment_method)
        self.rad_alignment_auto = QRadioButton(tr("alignment.method.auto"))
        self.rad_alignment_rigid = QRadioButton(tr("alignment.method.rigid"))
        for radio in (self.rad_alignment_auto, self.rad_alignment_rigid):
            radio.setStyleSheet("QRadioButton { font-size: 10px; }")
        self.alignment_method_buttons = QButtonGroup(self)
        self.alignment_method_buttons.setExclusive(True)
        self.alignment_method_buttons.addButton(self.rad_alignment_auto)
        self.alignment_method_buttons.addButton(self.rad_alignment_rigid)
        self.rad_alignment_auto.setChecked(True)
        self.alignment_method_row = AlignmentMethodRow(
            self.rad_alignment_auto, self.rad_alignment_rigid
        )
        align_layout.addWidget(self.alignment_method_row)

        self.btn_start_alignment = QPushButton(tr("button.start_alignment"))
        self.btn_start_alignment.setEnabled(False)
        align_layout.addWidget(self.btn_start_alignment)

        self.lbl_rigid_region_instruction = QLabel()
        self.lbl_rigid_region_instruction.setWordWrap(True)
        self.lbl_rigid_region_instruction.setText(
            tr("alignment.status.choose_method")
        )
        align_layout.addWidget(self.lbl_rigid_region_instruction)

        self.alignment_actions_widget = QWidget()
        rigid_actions = QVBoxLayout(self.alignment_actions_widget)
        rigid_actions.setContentsMargins(0, 0, 0, 0)
        preview_row = QHBoxLayout()
        rigid_actions.addLayout(preview_row)
        self.btn_rigid_apply = QPushButton(tr("button.rigid_apply"))
        self.btn_rigid_try_again = QPushButton(tr("button.rigid_try_again"))
        self.btn_rigid_cancel = QPushButton(tr("button.rigid_cancel"))

        self.btn_apply_alignment_suggestion = QPushButton(
            tr("button.apply_alignment_suggestion")
        )
        self.btn_apply_alignment_suggestion.setEnabled(False)
        self.btn_apply_alignment_suggestion.setVisible(False)
        for button in (
            self.btn_apply_alignment_suggestion,
            self.btn_rigid_apply,
            self.btn_rigid_cancel,
        ):
            button.setVisible(False)
            preview_row.addWidget(button, 1)
        for button in (self.btn_apply_alignment_suggestion, self.btn_rigid_apply):
            button.setAccessibleName(button.text().replace("\n", " "))
            button.setStyleSheet("""
                QPushButton {
                    background: #245b96; color: white;
                    border: 2px solid #245b96; border-radius: 4px;
                    padding: 4px; font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background: #1b4c80; }
                QPushButton:focus { border-color: #8fc5ff; }
            """)
        self.btn_rigid_cancel.setStyleSheet("""
            QPushButton {
                background: #edf0f2; color: #23313a;
                border: 2px solid #c8cfd4; border-radius: 4px;
                padding: 4px; font-size: 10px;
            }
            QPushButton:hover { background: #e0e5e8; }
            QPushButton:focus { border-color: #245b96; }
        """)
        self.btn_rigid_try_again.hide()
        rigid_actions.addWidget(self.btn_rigid_try_again)
        self.alignment_actions_widget.setVisible(False)
        align_layout.addWidget(self.alignment_actions_widget)

        self.btn_finish_alignment = QPushButton(tr("button.finish_alignment"))
        self.btn_finish_alignment.setVisible(False)
        self.btn_finish_alignment.setEnabled(False)

        self.nudge_box = QGroupBox(tr("group.nudge"))
        nudge_layout = QVBoxLayout(self.nudge_box)
        nudge_layout.setSpacing(2)

        grid_top = QHBoxLayout()
        grid_mid = QHBoxLayout()
        grid_bot = QHBoxLayout()
        grid_top.setSpacing(2)
        grid_mid.setSpacing(2)
        grid_bot.setSpacing(2)

        self.btn_up = QPushButton("↑")
        self.btn_left = QPushButton("←")
        self.btn_right = QPushButton("→")
        self.btn_down = QPushButton("↓")

        for b in (self.btn_up, self.btn_left, self.btn_right, self.btn_down):
            b.setFixedWidth(44)

        grid_top.addStretch(1)
        grid_top.addWidget(self.btn_up)
        grid_top.addStretch(1)

        grid_mid.addWidget(self.btn_left)
        grid_mid.addStretch(1)
        grid_mid.addWidget(self.btn_right)

        grid_bot.addStretch(1)
        grid_bot.addWidget(self.btn_down)
        grid_bot.addStretch(1)

        nudge_layout.addLayout(grid_top)
        nudge_layout.addLayout(grid_mid)
        nudge_layout.addLayout(grid_bot)

        advanced_layout.addWidget(self.nudge_box, 0, 0, 1, 2)

        self.rotate_box = QGroupBox(tr("group.rotate"))
        rotate_layout = QGridLayout(self.rotate_box)

        self.btn_rotate_minus = QPushButton("−")
        self.btn_rotate_plus = QPushButton("+")
        self.btn_rotate_minus.setToolTip(tr("button.rotate_minus"))
        self.btn_rotate_plus.setToolTip(tr("button.rotate_plus"))

        rotate_layout.addWidget(self.btn_rotate_minus, 0, 0)
        rotate_layout.addWidget(self.btn_rotate_plus, 0, 1)

        self.lbl_step_deg = QLabel(tr("label.step_deg"))
        self.lbl_step_deg.setWordWrap(True)
        advanced_layout.addWidget(self.lbl_step_deg, 1, 0)
        self.spn_rotate_step = QDoubleSpinBox()
        self.spn_rotate_step.setDecimals(2)
        self.spn_rotate_step.setRange(0.01, 360.0)
        self.spn_rotate_step.setSingleStep(0.1)
        self.spn_rotate_step.setValue(1.0)
        advanced_layout.addWidget(self.spn_rotate_step, 1, 1)

        fine_layout.addWidget(self.rotate_box)

        self.scale_box = QGroupBox(tr("group.scale"))
        scale_layout = QGridLayout(self.scale_box)

        self.btn_scale_minus = QPushButton(tr("button.scale_minus"))
        self.btn_scale_plus = QPushButton(tr("button.scale_plus"))

        repeat_buttons = [
            self.btn_up,
            self.btn_down,
            self.btn_left,
            self.btn_right,
            self.btn_rotate_minus,
            self.btn_rotate_plus,
            self.btn_scale_minus,
            self.btn_scale_plus,
        ]

        for btn in repeat_buttons:
            btn.setAutoRepeat(True)
            btn.setAutoRepeatDelay(300)
            btn.setAutoRepeatInterval(60)

        scale_layout.addWidget(self.btn_scale_minus, 0, 0)
        scale_layout.addWidget(self.btn_scale_plus, 0, 1)

        self.lbl_step_pct = QLabel(tr("label.step_pct"))
        self.lbl_step_pct.setWordWrap(True)
        advanced_layout.addWidget(self.lbl_step_pct, 2, 0)
        self.spn_scale_step = QDoubleSpinBox()
        self.spn_scale_step.setDecimals(2)
        self.spn_scale_step.setRange(0.01, 50.0)
        self.spn_scale_step.setSingleStep(0.1)
        self.spn_scale_step.setValue(1.0)
        advanced_layout.addWidget(self.spn_scale_step, 2, 1)

        fine_layout.addWidget(self.scale_box)

        self.lbl_alignment_shortcuts = QLabel(tr("label.alignment_shortcuts"))
        self.lbl_alignment_shortcuts.setWordWrap(True)
        fine_layout.addWidget(self.lbl_alignment_shortcuts)
        fine_layout.addWidget(self.btn_toggle_advanced_alignment)
        fine_layout.addWidget(self.alignment_advanced)
        fine_layout.addSpacing(8)
        fine_layout.addWidget(self.btn_reset_alignment)

        align_layout.addWidget(self.btn_toggle_manual_alignment)
        align_layout.addWidget(self.fine_adjust_group)
        dock_layout.addWidget(self.align_group)
        self._refresh_alignment_sections()

        # --- Calibration group ---
        self.cal_group = QGroupBox(tr("group.calibration"))
        cal_layout = QVBoxLayout(self.cal_group)

        self.chk_calibration_mode = QPushButton(tr("calibration.mark_points"))
        self.chk_calibration_mode.setCheckable(True)
        cal_layout.addWidget(self.chk_calibration_mode)

        self.lbl_px_distance = QLabel(tr("label.measured_distance"))
        cal_layout.addWidget(self.lbl_px_distance)

        self.lbl_real_distance_m = QLabel(tr("label.real_distance_m"))
        cal_layout.addWidget(self.lbl_real_distance_m)
        self.txt_real_m = QLineEdit()
        self.txt_real_m.setPlaceholderText("e.g., 1.0")
        cal_layout.addWidget(self.txt_real_m)

        self.lbl_m_per_px = QLabel(tr("label.scale_m_per_px"))
        self.lbl_m_per_px.setWordWrap(True)
        cal_layout.addWidget(self.lbl_m_per_px)

        self.btn_confirm_calibration = QPushButton(tr("button.confirm_calibration"))

        dock_layout.addWidget(self.cal_group)

        # --- Marking group ---
        self.mark_group = QGroupBox(tr("group.marking"))
        mark_layout = QVBoxLayout(self.mark_group)

        self.lbl_marking_orientation = QLabel(tr("label.marking_orientation"))
        self.lbl_marking_orientation.setWordWrap(True)
        mark_layout.addWidget(self.lbl_marking_orientation)

        self.chk_set_w_mode = QCheckBox(tr("check.set_w_mode"))
        mark_layout.addWidget(self.chk_set_w_mode)
        self.lbl_w = QLabel(tr("label.w_default"))
        mark_layout.addWidget(self.lbl_w)

        self.btn_generate_slices = QPushButton(tr("button.generate_slices"))
        mark_layout.addWidget(self.btn_generate_slices)
        self.lbl_delta_w = QLabel(tr("label.delta_w_default"))
        mark_layout.addWidget(self.lbl_delta_w)

        self.chk_set_guide_mode = QCheckBox(tr("check.set_guide_mode"))
        mark_layout.addWidget(self.chk_set_guide_mode)

        # --- Offset travessa do para-choque ---
        self.lbl_bumper_offset = QLabel(tr("label.bumper_offset_m"))
        mark_layout.addWidget(self.lbl_bumper_offset)

        self.spn_bumper_offset = QDoubleSpinBox()
        self.spn_bumper_offset.setDecimals(3)
        self.spn_bumper_offset.setRange(0.0, 2.0)
        self.spn_bumper_offset.setSingleStep(0.01)
        self.spn_bumper_offset.setValue(0.0)
        mark_layout.addWidget(self.spn_bumper_offset)

        self.chk_measure_ci_mode = QCheckBox(tr("check.measure_ci_mode"))
        mark_layout.addWidget(self.chk_measure_ci_mode)

        self.lbl_ci_index = QLabel(tr("label.current_ci", idx=1))
        mark_layout.addWidget(self.lbl_ci_index)

        self.ci_select_box = QGroupBox(tr("group.select_c"))
        ci_select_layout = QVBoxLayout(self.ci_select_box)

        ci_row_1 = QHBoxLayout()
        ci_row_2 = QHBoxLayout()

        self.rb_c1 = QRadioButton("C1")
        self.rb_c2 = QRadioButton("C2")
        self.rb_c3 = QRadioButton("C3")
        self.rb_c4 = QRadioButton("C4")
        self.rb_c5 = QRadioButton("C5")
        self.rb_c6 = QRadioButton("C6")

        self.rb_c1.setChecked(True)

        ci_row_1.addWidget(self.rb_c1)
        ci_row_1.addWidget(self.rb_c2)
        ci_row_1.addWidget(self.rb_c3)

        ci_row_2.addWidget(self.rb_c4)
        ci_row_2.addWidget(self.rb_c5)
        ci_row_2.addWidget(self.rb_c6)

        ci_select_layout.addLayout(ci_row_1)
        ci_select_layout.addLayout(ci_row_2)

        mark_layout.addWidget(self.ci_select_box)

        self.lbl_ci_values = QLabel(tr("label.c_values_default"))
        self.lbl_ci_values.setWordWrap(True)
        mark_layout.addWidget(self.lbl_ci_values)

        self.btn_finish_marking = QPushButton(tr("button.finish_marking"))

        dock_layout.addWidget(self.mark_group)


        # --- Calc panel ---
        self.calc_panel = CalcPanel(self)
        dock_layout.addWidget(self.calc_panel)

        # --- Summary ---
        summary_group = QGroupBox(tr("group.summary"))
        self._summary_group = summary_group
        summary_layout = QVBoxLayout(summary_group)
        self.lbl_result_ees_kmh = QLabel()
        self.lbl_result_ees_kmh.setStyleSheet("font-size: 23px; font-weight: bold;")
        self.lbl_result_ees_mps = QLabel()
        self.lbl_result_energy = QLabel()
        for label in (self.lbl_result_ees_kmh, self.lbl_result_ees_mps, self.lbl_result_energy):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            summary_layout.addWidget(label)
        self.lbl_summary = QLabel(tr("summary.status_default"))
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        summary_layout.addWidget(self.lbl_summary)
        dock_layout.addWidget(summary_group)

        dock_layout.addStretch(1)

        scroll.setWidget(dock_widget)
        dock_content = QWidget()
        dock_content_layout = QVBoxLayout(dock_content)
        dock_content_layout.setContentsMargins(0, 0, 0, 0)
        dock_content_layout.setSpacing(0)
        dock_content_layout.addWidget(scroll, 1)

        self.navigation_footer = QWidget()
        footer_layout = QVBoxLayout(self.navigation_footer)
        footer_layout.setContentsMargins(6, 0, 6, 6)
        footer_layout.setSpacing(4)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        footer_layout.addWidget(separator)
        self.lbl_navigation_hint = QLabel()
        self.lbl_navigation_hint.setWordWrap(True)
        self.lbl_navigation_hint.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        footer_layout.addWidget(self.lbl_navigation_hint)
        self.navigation_footer.setStyleSheet("""
            QPushButton {
                background: #dbe8f5; color: #183c5c;
                border: 2px solid #b8cddd; border-radius: 4px;
                padding: 4px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #ccdff1; }
            QPushButton:focus { border-color: #245b96; }
            QPushButton:disabled {
                background: #edf0f2; color: #53616b; border-color: #c8cfd4;
            }
        """)
        for button in (self.btn_finish_alignment, self.btn_confirm_calibration, self.btn_finish_marking):
            footer_layout.addWidget(button)
        dock_content_layout.addWidget(self.navigation_footer)
        dock.setWidget(dock_content)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.resizeDocks([dock], [370], Qt.Orientation.Horizontal)

        self.btn_load_ref.clicked.connect(self._on_load_ref)
        self.btn_load_dam.clicked.connect(self._on_load_dam)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        self.chk_alignment_mode.toggled.connect(self._on_alignment_mode_toggled)
        self.chk_lock_alignment.toggled.connect(self._on_lock_alignment_toggled)
        self.btn_reset_alignment.clicked.connect(self._on_reset_alignment)
        self.btn_start_alignment.clicked.connect(self._on_start_alignment)
        self.btn_rigid_apply.clicked.connect(self._on_apply_rigid_region_preview)
        self.btn_rigid_try_again.clicked.connect(
            self._on_try_another_rigid_region
        )
        self.btn_rigid_cancel.clicked.connect(self._on_cancel_alignment_preview)
        self.btn_apply_alignment_suggestion.clicked.connect(
            self._on_apply_auto_alignment_suggestion
        )

        self.cmb_alignment_target.currentIndexChanged.connect(
            self._on_alignment_target_changed
        )
        self.btn_rotate_minus.clicked.connect(self._on_rotate_minus)
        self.btn_rotate_plus.clicked.connect(self._on_rotate_plus)
        self.btn_scale_minus.clicked.connect(self._on_scale_minus)
        self.btn_scale_plus.clicked.connect(self._on_scale_plus)

        self.btn_up.clicked.connect(lambda: self.canvas.nudge_selected(0, -1))
        self.btn_down.clicked.connect(lambda: self.canvas.nudge_selected(0, 1))
        self.btn_left.clicked.connect(lambda: self.canvas.nudge_selected(-1, 0))
        self.btn_right.clicked.connect(lambda: self.canvas.nudge_selected(1, 0))

        self.btn_finish_alignment.clicked.connect(self._on_finish_alignment)

        self.chk_calibration_mode.toggled.connect(self._on_calibration_mode_toggled)
        self.txt_real_m.textChanged.connect(self._refresh_calibration_panel)
        self.btn_confirm_calibration.clicked.connect(self._on_confirm_calibration)

        self.chk_set_w_mode.toggled.connect(self._on_set_w_mode_toggled)
        self.btn_generate_slices.clicked.connect(self._on_generate_slices)
        self.chk_set_guide_mode.toggled.connect(self._on_set_guide_mode_toggled)
        self.spn_bumper_offset.valueChanged.connect(self._on_bumper_offset_changed)
        self.chk_measure_ci_mode.toggled.connect(self._on_measure_ci_mode_toggled)

        self.btn_finish_marking.clicked.connect(self._on_finish_marking)

        self.rb_c1.toggled.connect(
            lambda checked: self._on_ci_radio_selected(1, checked)
        )
        self.rb_c2.toggled.connect(
            lambda checked: self._on_ci_radio_selected(2, checked)
        )
        self.rb_c3.toggled.connect(
            lambda checked: self._on_ci_radio_selected(3, checked)
        )
        self.rb_c4.toggled.connect(
            lambda checked: self._on_ci_radio_selected(4, checked)
        )
        self.rb_c5.toggled.connect(
            lambda checked: self._on_ci_radio_selected(5, checked)
        )
        self.rb_c6.toggled.connect(
            lambda checked: self._on_ci_radio_selected(6, checked)
        )

    # ---------------- Language ----------------
    def _set_language_and_refresh(self, lang: str) -> None:
        set_language(lang)
        self._retranslate_ui()
        self._refresh_summary()

    def _retranslate_ui(self) -> None:
        self._update_window_title()
        self.menuBar().clear()
        self._build_menu()

        self._controls_dock.setWindowTitle(tr("dock.controls"))
        self.btn_return_to_current_step.setText(tr("progress.return_current"))
        self.btn_redo_step.setText(tr("progress.redo"))
        self._refresh_alignment_consultation()

        self._refresh_image_controls()
        self.btn_load_ref.setText(tr("button.load_ref"))
        self.btn_load_dam.setText(tr("button.load_dam"))
        self.lbl_overlay_opacity.setText(tr("label.overlay_opacity"))

        self.align_group.setTitle(tr("group.alignment"))
        self._refresh_alignment_sections()
        self.rotate_box.setTitle(tr("group.rotate"))
        self.scale_box.setTitle(tr("group.scale"))
        self.chk_alignment_mode.setText(tr("check.alignment_mode"))
        self.chk_alignment_mode.setToolTip(tr("check.alignment_mode_hint"))
        self.chk_lock_alignment.setText(tr("check.lock_alignment"))
        self.lbl_editable_image.setText(tr("label.editable_image"))
        self.cmb_alignment_target.setItemText(0, tr("combo.deformed"))
        self.cmb_alignment_target.setItemText(1, tr("combo.reference"))
        self.btn_reset_alignment.setText(tr("button.reset_selected_transform"))
        self.btn_reset_alignment.setAccessibleName(self.btn_reset_alignment.text())
        self.btn_reset_alignment.setToolTip(tr("alignment.reset.tooltip"))
        self.lbl_alignment_method.setText(tr("label.alignment_method"))
        self.rad_alignment_auto.setText(tr("alignment.method.auto"))
        self.rad_alignment_rigid.setText(tr("alignment.method.rigid"))
        self.alignment_method_row.update_direction()
        self.btn_start_alignment.setText(tr("button.start_alignment"))
        self.btn_rigid_apply.setText(tr("button.rigid_apply"))
        self.btn_rigid_try_again.setText(tr("button.rigid_try_again"))
        self._refresh_alignment_cancel_label()
        if self._rigid_instruction_key is not None:
            self.lbl_rigid_region_instruction.setText(
                tr(self._rigid_instruction_key)
            )
        else:
            self.lbl_rigid_region_instruction.setText(
                tr("alignment.status.choose_method")
            )
        self.btn_apply_alignment_suggestion.setText(
            tr("button.apply_alignment_suggestion")
        )
        for button in (self.btn_apply_alignment_suggestion, self.btn_rigid_apply):
            button.setAccessibleName(button.text().replace("\n", " "))
        self.btn_rotate_minus.setToolTip(tr("button.rotate_minus"))
        self.btn_rotate_plus.setToolTip(tr("button.rotate_plus"))
        self.lbl_step_deg.setText(tr("label.step_deg"))
        self.nudge_box.setTitle(tr("group.nudge"))
        self.btn_scale_minus.setText(tr("button.scale_minus"))
        self.btn_scale_plus.setText(tr("button.scale_plus"))
        self.lbl_step_pct.setText(tr("label.step_pct"))
        self.lbl_alignment_shortcuts.setText(tr("label.alignment_shortcuts"))
        self.btn_finish_alignment.setText(tr("button.finish_alignment"))

        self.cal_group.setTitle(tr("group.calibration"))
        self.lbl_real_distance_m.setText(tr("label.real_distance_m"))
        self.btn_confirm_calibration.setText(tr("button.confirm_calibration"))

        self.mark_group.setTitle(tr("group.marking"))
        self.ci_select_box.setTitle(tr("group.select_c"))
        self.lbl_marking_orientation.setText(tr("label.marking_orientation"))
        self.chk_set_w_mode.setText(tr("check.set_w_mode"))
        self.btn_generate_slices.setText(tr("button.generate_slices"))
        self.chk_set_guide_mode.setText(tr("check.set_guide_mode"))
        self.lbl_bumper_offset.setText(tr("label.bumper_offset_m"))
        self.chk_measure_ci_mode.setText(tr("check.measure_ci_mode"))
        self._update_ci_label()
        self.btn_finish_marking.setText(tr("button.finish_marking"))
        if not self._ci_m:
            self.lbl_ci_values.setText(tr("label.c_values_default"))


        self._summary_group.setTitle(tr("group.summary"))

        if self._calibration_px is None:
            self.lbl_px_distance.setText(tr("label.measured_distance"))

        if self._m_per_px is None:
            self.lbl_m_per_px.setText(tr("label.scale_m_per_px"))

        if self._w_px is None:
            self.lbl_w.setText(tr("label.w_default"))

        if self._delta_w_px is None:
            self.lbl_delta_w.setText(tr("label.delta_w_default"))

        self.calc_panel.retranslate_ui()

    # ---------------- File operations ----------------
    def _on_new_project(self) -> None:
        self.io.new_project()

    def _on_save_project(self) -> None:
        self.io.save_project()

    def _on_load_project(self) -> None:
        self.io.load_project()

    def _on_export_png(self) -> None:
        self.io.export_png()

    def _on_export_current_view_png(self) -> None:
        self.io.export_current_view_png()

    def _on_export_report(self) -> None:
        self._sync_ui_to_project()

        default_name = f"{Path(self.project.name or 'report').stem}_report.txt"

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dialog.export_report"),
            default_name,
            "Text file (*.txt)" if get_language() == "en" else "Arquivo texto (*.txt)",
        )
        if not path:
            return

        if not path.lower().endswith(".txt"):
            path += ".txt"

        try:
            content = generate_report(self.project)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            QMessageBox.information(
                self,
                tr("dialog.export_report"),
                tr("dialog.saved", path=path),
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("dialog.export_report"),
                str(e),
            )

    # ---------------- Image loading ----------------
    def _refresh_image_controls(self) -> None:
        loading = self.stage == Stage.LOAD
        toggle = self.btn_toggle_image_controls
        if loading:
            toggle.setChecked(False)
        toggle.setVisible(not loading)
        expanded = toggle.isChecked()
        self.load_group.setTitle(tr("group.load_images" if loading else "images.loaded"))
        roles = []
        if self.canvas.ctrl.ref_item is not None:
            roles.append(tr("combo.reference"))
        if self.canvas.ctrl.dam_item is not None:
            roles.append(tr("combo.deformed"))
        if len(roles) == 2:
            status = f"✓ {tr('images.both_loaded')}"
        else:
            status = f"✓ {roles[0]}" if roles else tr("images.none_loaded")
        toggle.setText(f"{'▾' if expanded else '▸'} {status}")
        toggle.setAccessibleName(f"{tr('images.loaded')} — {status}")
        toggle.setToolTip("\n".join([tr("images.toggle_controls"), *roles]))
        self.btn_load_ref.setVisible(loading or expanded)
        self.btn_load_dam.setVisible(loading or expanded)

    def _on_load_ref(self) -> None:
        self.io.load_ref()

    def _on_load_dam(self) -> None:
        self.io.load_dam()

    # ---------------- Opacity ----------------
    def _refresh_opacity_percentage(self) -> None:
        self.lbl_opacity_percent.setText(f"{self.opacity_slider.value()}%")

    def _on_opacity_changed(self, value: int) -> None:
        self._refresh_opacity_percentage()
        self.canvas.set_deformed_opacity(value / 100.0)
        self.project.opacity = value / 100.0
        self._refresh_summary()

    # ---------------- Alignment ----------------
    def _on_alignment_mode_toggled(self, checked: bool) -> None:
        self.canvas.set_alignment_mode(checked)

    def _refresh_alignment_consultation(self) -> None:
        viewing = self._viewed_step == "alignment"
        self.lbl_alignment_consultation.setVisible(viewing)
        if not viewing:
            return
        lines = []
        for item, name, transform in (
            (self.canvas.ctrl.ref_item, "reference", self.canvas.get_reference_transform),
            (self.canvas.ctrl.dam_item, "deformed", self.canvas.get_deformed_transform),
        ):
            if item is not None:
                values = transform()
                lines.append(tr(
                    "progress.transform",
                    image=tr(f"combo.{name}"),
                    x=values["x"], y=values["y"],
                    rotation=values["rotation_deg"], scale=values["scale"],
                ))
        self.lbl_alignment_consultation.setText("\n".join(lines))

    def _on_lock_alignment_toggled(self, checked: bool) -> None:
        self.canvas.set_alignment_locked(checked)

    def _on_alignment_target_changed(self) -> None:
        target = self.cmb_alignment_target.currentData()
        if target:
            self.canvas.set_alignment_target(target)

    def _on_reset_alignment(self) -> None:
        if self.stage != Stage.ALIGNMENT or self._viewed_step is not None or self._workflow_navigation_blocked():
            return
        transforms = (
            self.canvas.get_reference_transform(),
            self.canvas.get_deformed_transform(),
        )
        if not any(
            t["x"] != 0 or t["y"] != 0 or t["scale"] != 1 or t["rotation_deg"] % 360 != 0
            for t in transforms
        ):
            return
        answer = QMessageBox.question(
            self,
            self.btn_reset_alignment.accessibleName(),
            tr("alignment.reset.confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.canvas.reset_all_transforms()

    def _update_auto_align_availability(self) -> None:
        available = self.canvas.has_both_images() and not self._workflow_navigation_blocked()
        self.btn_start_alignment.setEnabled(available)

    def _refresh_alignment_sections(self) -> None:
        manual_open = self.btn_toggle_manual_alignment.isChecked()
        if not manual_open and self.chk_alignment_mode.isChecked():
            self.chk_alignment_mode.setChecked(False)
        for toggle, content, key in (
            (self.btn_toggle_manual_alignment, self.fine_adjust_group, "group.fine_adjustment"),
            (self.btn_toggle_advanced_alignment, self.alignment_advanced, "alignment.advanced"),
        ):
            expanded = toggle.isChecked()
            title = tr(key)
            toggle.setText(f"{'▾' if expanded else '▸'} {title}")
            toggle.setAccessibleName(title)
            content.setVisible(expanded)

    def _update_alignment_edit_availability(self) -> None:
        pending = self._workflow_navigation_blocked()
        editable = self.stage == Stage.ALIGNMENT and self._viewed_step is None
        self.fine_adjust_group.setEnabled(editable and not pending)
        self.alignment_method_row.setEnabled(editable and not pending)
        self._update_auto_align_availability()
        for shortcut in self._alignment_shortcuts:
            shortcut.setEnabled(editable and not pending)

    def _on_start_alignment(self) -> None:
        if self._workflow_navigation_blocked():
            return
        if self.rad_alignment_rigid.isChecked():
            self._on_start_rigid_region_alignment()
        else:
            self._on_auto_align()

    def _set_rigid_instruction(self, key: str | None) -> None:
        self._rigid_instruction_key = key
        self.lbl_rigid_region_instruction.setText(
            tr(key) if key else tr("alignment.status.choose_method")
        )
        self.lbl_rigid_region_instruction.setVisible(True)

    def _show_finish_alignment(self) -> None:
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=False
        )
        self.btn_apply_alignment_suggestion.setVisible(False)
        self.btn_apply_alignment_suggestion.setEnabled(False)
        self._update_alignment_actions_visibility()
        self.lbl_rigid_region_instruction.setVisible(False)
        self._refresh_navigation_footer()

    def _can_finish_alignment(self) -> bool:
        return (
            self.stage == Stage.ALIGNMENT
            and self._viewed_step is None
            and self.canvas.has_images()
            and not self._workflow_navigation_blocked()
        )

    def _refresh_navigation_footer(self) -> None:
        consulting = self._viewed_step is not None
        active = None if consulting else self.stage
        hint = None
        if active == Stage.ALIGNMENT and not self._can_finish_alignment():
            hint = (
                "navigation.resolve_alignment" if self._workflow_navigation_blocked()
                else "navigation.load_image"
            )
        elif active == Stage.CALIBRATION:
            _, hint = self.meas.calibration_candidate()
        elif active == Stage.MARKING:
            hint = self.workflow.marking_block_reason()

        actions = (
            (Stage.ALIGNMENT, self.btn_finish_alignment),
            (Stage.CALIBRATION, self.btn_confirm_calibration),
            (Stage.MARKING, self.btn_finish_marking),
        )
        for stage, button in actions:
            visible = stage == active
            button.setVisible(visible)
            button.setEnabled(visible and hint is None)
        self.lbl_navigation_hint.setText(tr(hint) if hint else "")
        self.lbl_navigation_hint.setVisible(hint is not None)
        self.navigation_footer.setVisible(any(stage == active for stage, _ in actions))

    def _set_rigid_action_visibility(
        self, *, apply: bool, try_again: bool, cancel: bool
    ) -> None:
        self.btn_rigid_apply.setVisible(apply)
        self.btn_rigid_apply.setEnabled(apply)
        self.btn_rigid_try_again.setVisible(try_again)
        self.btn_rigid_try_again.setEnabled(try_again)
        self.btn_rigid_cancel.setVisible(cancel)
        self.btn_rigid_cancel.setEnabled(cancel)
        self._update_alignment_actions_visibility()

    def _refresh_alignment_cancel_label(self) -> None:
        preview = self._auto_preview_active or self._rigid_preview_active
        self.btn_rigid_cancel.setText(tr(
            "alignment.discard_preview" if preview else "button.rigid_cancel"
        ))
        self.btn_rigid_cancel.setAccessibleName(self.btn_rigid_cancel.text().replace("\n", " "))

    def _update_alignment_actions_visibility(self) -> None:
        self._refresh_alignment_cancel_label()
        buttons = (
            self.btn_apply_alignment_suggestion,
            self.btn_rigid_apply,
            self.btn_rigid_try_again,
            self.btn_rigid_cancel,
        )
        self.alignment_actions_widget.setVisible(
            any(not button.isHidden() for button in buttons)
        )
        self._refresh_navigation_footer()
        self._update_alignment_edit_availability()
        self._refresh_workflow_progress()

    def _on_alignment_state_changed(self) -> None:
        if self._rigid_internal_transform_change:
            return
        had_auto_preview = self._auto_preview_active
        self._invalidate_auto_alignment_suggestion()
        if had_auto_preview:
            self._set_rigid_action_visibility(
                apply=False, try_again=False, cancel=False
            )
            self._set_rigid_instruction(None)
        if self._rigid_baseline_ref_transform is not None:
            self._discard_rigid_region_state(restore=False, clear_visuals=True)

    def _on_images_changed(self) -> None:
        self._last_applied_rigid_reference_regions = ()
        self._set_rigid_instruction(None)
        self.workflow.apply_stage_gating()

    def _set_canvas_alignment_transforms(
        self,
        ref_transform: dict[str, float] | None,
        dam_transform: dict[str, float] | None,
    ) -> None:
        self._rigid_internal_transform_change = True
        try:
            if ref_transform is not None:
                self.canvas.set_reference_transform(
                    ref_transform["x"],
                    ref_transform["y"],
                    ref_transform["scale"],
                    ref_transform["rotation_deg"],
                )
            if dam_transform is not None:
                self.canvas.set_deformed_transform(
                    dam_transform["x"],
                    dam_transform["y"],
                    dam_transform["scale"],
                    dam_transform["rotation_deg"],
                )
        finally:
            self._rigid_internal_transform_change = False

    def _discard_rigid_region_state(
        self, *, restore: bool, clear_visuals: bool
    ) -> None:
        if restore:
            self._set_canvas_alignment_transforms(
                self._rigid_baseline_ref_transform,
                self._rigid_baseline_dam_transform,
            )
        self.canvas.set_rigid_region_mode(False)
        if clear_visuals:
            self.canvas.clear_rigid_region_visuals()
        self._rigid_reference_regions = []
        self._rigid_deformed_region = None
        self._rigid_alignment_result = None
        self._rigid_baseline_ref_transform = None
        self._rigid_baseline_dam_transform = None
        self._rigid_expansion_attempted = False
        self._rigid_preview_active = False
        self._set_rigid_instruction(None)
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=False
        )

    def _on_start_rigid_region_alignment(self) -> None:
        if not self.canvas.has_both_images():
            return
        if self.chk_lock_alignment.isChecked():
            QMessageBox.warning(
                self,
                tr("alignment.rigid.title"),
                tr("alignment.auto.locked"),
            )
            return
        self._discard_auto_alignment_preview(restore=True)
        if self._rigid_baseline_ref_transform is not None:
            self._discard_rigid_region_state(restore=True, clear_visuals=True)
        self.canvas.clear_rigid_region_visuals()
        self._last_applied_rigid_reference_regions = ()
        if self.chk_alignment_mode.isChecked():
            self.chk_alignment_mode.setChecked(False)
        self._rigid_baseline_ref_transform = dict(
            self.canvas.get_reference_transform()
        )
        self._rigid_baseline_dam_transform = dict(
            self.canvas.get_deformed_transform()
        )
        self._rigid_reference_regions = []
        self._rigid_deformed_region = None
        self._rigid_alignment_result = None
        self._rigid_preview_active = False
        self._rigid_expansion_attempted = False
        suggestion_regions: tuple[RigidRegion, ...] = ()
        try:
            suggestions = suggest_rigid_region_anchors(
                self.project.ref_path,
                self.project.dam_path,
            )
            suggestion_regions = tuple(
                item.region for item in suggestions.suggestions
            )
            logger.info(
                "Rigid anchor suggestions: ref_keypoints=%d dam_keypoints=%d "
                "suggestions=%s",
                suggestions.reference_keypoints,
                suggestions.deformed_keypoints,
                suggestions.suggestions,
            )
        except (ValueError, cv2.error):
            logger.exception("Could not generate rigid anchor suggestions")
        if suggestion_regions:
            self.canvas.show_rigid_region_suggestions(suggestion_regions)
            self._set_rigid_instruction(
                "alignment.rigid.instruction.suggestions"
            )
        else:
            self._set_rigid_instruction("alignment.rigid.instruction.reference")
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=True
        )
        self.canvas.set_rigid_region_mode(True, "ref")

    def _on_rigid_region_selected(self, target: str, region: object) -> None:
        if not isinstance(region, RigidRegion):
            return
        if target == "ref":
            if len(self._rigid_reference_regions) >= 3:
                return
            self._rigid_reference_regions.append(region)
            count = len(self._rigid_reference_regions)
            if count < 3:
                self._rigid_instruction_key = None
                self.lbl_rigid_region_instruction.setText(
                    tr(
                        "alignment.rigid.instruction.reference_progress",
                        count=count,
                    )
                )
                return
            self._estimate_rigid_region_preview()
        elif target == "dam":
            self._rigid_deformed_region = region
            self._estimate_rigid_region_preview()

    def _estimate_rigid_region_preview(self) -> None:
        reference_regions = tuple(self._rigid_reference_regions)
        if len(reference_regions) != 3:
            return
        ref_path = self.project.ref_path
        dam_path = self.project.dam_path
        if not ref_path or not dam_path:
            return
        result = estimate_rigid_region_alignment(
            ref_path,
            dam_path,
            reference_regions,
            deformed_region=self._rigid_deformed_region,
            reference_transform=self.canvas.get_reference_transform(),
            deformed_transform=self.canvas.get_deformed_transform(),
            expansion_attempted=self._rigid_expansion_attempted,
        )
        structural_regions = reference_regions
        if (
            result.status == "needs_second_region"
            and self._rigid_deformed_region is None
        ):
            self._rigid_expansion_attempted = True
            logger.info(
                "Rigid-region alignment retrying with expanded point ROIs: "
                "initial_reason=%s anchor_matches=%s",
                result.reason,
                result.diagnostics.anchor_matches,
            )
            expanded_regions = expand_point_anchor_regions(reference_regions)
            structural_regions = expanded_regions
            result = estimate_rigid_region_alignment(
                ref_path,
                dam_path,
                expanded_regions,
                reference_transform=self.canvas.get_reference_transform(),
                deformed_transform=self.canvas.get_deformed_transform(),
            )
        if (
            result.status == "needs_second_region"
            and self._rigid_deformed_region is None
        ):
            logger.info(
                "Rigid-region alignment retrying with normalized multiscale "
                "ROIs: expanded_reason=%s anchor_matches=%s",
                result.reason,
                result.diagnostics.anchor_matches,
            )
            result = estimate_multiscale_rigid_alignment(
                ref_path,
                dam_path,
                structural_regions,
                reference_transform=self.canvas.get_reference_transform(),
                deformed_transform=self.canvas.get_deformed_transform(),
            )
        if (
            result.status == "needs_second_region"
            and self._rigid_deformed_region is None
        ):
            logger.info(
                "Rigid-region alignment retrying with structural gradients: "
                "multiscale_reason=%s anchor_matches=%s",
                result.reason,
                result.diagnostics.anchor_matches,
            )
            result = estimate_rigid_region_alignment(
                ref_path,
                dam_path,
                structural_regions,
                reference_transform=self.canvas.get_reference_transform(),
                deformed_transform=self.canvas.get_deformed_transform(),
                expansion_attempted=True,
                structural_fallback=True,
            )
        self._rigid_alignment_result = result
        logger.info(
            "Rigid-region alignment: status=%s reason=%s region=%s "
            "keypoints=%d "
            "matches=%d anchor_keypoints=%s anchor_matches=%s roi_scale=%.2f "
            "expansion_attempted=%s normalized_multiscale=%s scales=%s "
            "structural_fallback=%s candidates=%s",
            result.status,
            result.reason,
            reference_regions,
            result.diagnostics.region_keypoints,
            result.diagnostics.accepted_matches,
            result.diagnostics.anchor_keypoints,
            result.diagnostics.anchor_matches,
            result.diagnostics.roi_scale,
            result.diagnostics.expansion_attempted,
            result.diagnostics.normalized_multiscale,
            result.diagnostics.detection_scales,
            result.diagnostics.structural_fallback,
            result.candidates,
        )
        if result.status == "needs_second_region":
            self._set_rigid_instruction("alignment.rigid.instruction.deformed")
            self._set_rigid_action_visibility(
                apply=False, try_again=True, cancel=True
            )
            self.canvas.set_rigid_region_mode(True, "dam")
            QMessageBox.information(
                self,
                tr("alignment.rigid.title"),
                tr("alignment.rigid.second_region"),
            )
            return
        if result.status != "success" or result.best is None:
            self.canvas.set_rigid_region_mode(False)
            self._set_rigid_action_visibility(
                apply=False, try_again=True, cancel=True
            )
            QMessageBox.warning(
                self,
                tr("alignment.rigid.title"),
                tr("alignment.rigid.failure"),
            )
            return

        candidate = result.best
        self._rigid_internal_transform_change = True
        try:
            self.canvas.apply_deformed_correction(
                candidate.dx,
                candidate.dy,
                candidate.scale,
                candidate.rotation_deg,
            )
        finally:
            self._rigid_internal_transform_change = False
        self._rigid_preview_active = True
        self.canvas.set_rigid_region_mode(False)
        self._set_rigid_instruction("alignment.rigid.instruction.preview")
        self._set_rigid_action_visibility(
            apply=True, try_again=True, cancel=True
        )

    def _on_apply_rigid_region_preview(self) -> None:
        if not self._rigid_preview_active:
            return
        ref_transform = self.canvas.get_reference_transform()
        dam_transform = self.canvas.get_deformed_transform()
        self.project.ref_transform.x = ref_transform["x"]
        self.project.ref_transform.y = ref_transform["y"]
        self.project.ref_transform.scale = ref_transform["scale"]
        self.project.ref_transform.rotation_deg = ref_transform["rotation_deg"]
        self.project.dam_transform.x = dam_transform["x"]
        self.project.dam_transform.y = dam_transform["y"]
        self.project.dam_transform.scale = dam_transform["scale"]
        self.project.dam_transform.rotation_deg = dam_transform["rotation_deg"]
        self._last_applied_rigid_reference_regions = tuple(
            self._rigid_reference_regions
        )
        self._discard_rigid_region_state(restore=False, clear_visuals=True)
        self._refresh_summary()
        self._show_finish_alignment()

    def _on_try_another_rigid_region(self) -> None:
        if self._rigid_baseline_ref_transform is None:
            return
        baseline_ref = dict(self._rigid_baseline_ref_transform)
        baseline_dam = dict(self._rigid_baseline_dam_transform or {})
        self._set_canvas_alignment_transforms(baseline_ref, baseline_dam)
        self.canvas.clear_rigid_region_visuals()
        self._rigid_reference_regions = []
        self._rigid_deformed_region = None
        self._rigid_alignment_result = None
        self._rigid_expansion_attempted = False
        self._rigid_preview_active = False
        self._set_rigid_instruction("alignment.rigid.instruction.reference")
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=True
        )
        self.canvas.set_rigid_region_mode(True, "ref")

    def _on_cancel_rigid_region_alignment(self) -> None:
        self._discard_rigid_region_state(restore=True, clear_visuals=True)

    def _on_cancel_alignment_preview(self) -> None:
        if self._auto_preview_active:
            self._discard_auto_alignment_preview(restore=True)
            self._set_rigid_action_visibility(
                apply=False, try_again=False, cancel=False
            )
            self._set_rigid_instruction(None)
            return
        self._on_cancel_rigid_region_alignment()

    def _invalidate_auto_alignment_suggestion(self) -> None:
        self._pending_auto_alignment = None
        self._auto_preview_baseline_dam_transform = None
        self._auto_preview_active = False
        if hasattr(self, "btn_apply_alignment_suggestion"):
            self.btn_apply_alignment_suggestion.setEnabled(False)
            self.btn_apply_alignment_suggestion.setVisible(False)
            self._update_alignment_actions_visibility()

    def _discard_auto_alignment_preview(self, *, restore: bool) -> None:
        baseline = self._auto_preview_baseline_dam_transform
        if restore and baseline is not None:
            self._set_canvas_alignment_transforms(None, baseline)
        self._invalidate_auto_alignment_suggestion()

    def _preview_auto_alignment(
        self, hypothesis: AlignmentHypothesis
    ) -> None:
        self._discard_auto_alignment_preview(restore=True)
        if self.chk_alignment_mode.isChecked():
            self.chk_alignment_mode.setChecked(False)
        self._auto_preview_baseline_dam_transform = dict(
            self.canvas.get_deformed_transform()
        )
        self._rigid_internal_transform_change = True
        try:
            self.canvas.apply_deformed_correction(
                hypothesis.dx,
                hypothesis.dy,
                hypothesis.scale,
                hypothesis.rotation_deg,
            )
        finally:
            self._rigid_internal_transform_change = False
        self._pending_auto_alignment = hypothesis
        self._auto_preview_active = True
        self.btn_apply_alignment_suggestion.setVisible(True)
        self.btn_apply_alignment_suggestion.setEnabled(True)
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=True
        )
        self._set_rigid_instruction("alignment.status.auto_medium")

    def _on_apply_auto_alignment_suggestion(self) -> None:
        hypothesis = self._pending_auto_alignment
        if hypothesis is None or not self._auto_preview_active:
            return
        if self.chk_lock_alignment.isChecked():
            QMessageBox.warning(
                self,
                tr("alignment.auto.title"),
                tr("alignment.auto.locked"),
            )
            return
        applied = self.canvas.get_deformed_transform()
        self._invalidate_auto_alignment_suggestion()
        self.cmb_alignment_target.setCurrentIndex(0)
        self.canvas.set_alignment_target("dam")
        self.project.dam_transform.x = applied["x"]
        self.project.dam_transform.y = applied["y"]
        self.project.dam_transform.scale = applied["scale"]
        self.project.dam_transform.rotation_deg = applied["rotation_deg"]
        self._refresh_summary()
        self._show_finish_alignment()
        logger.info(
            "Automatic alignment preview accepted: "
            "dx=%.3f dy=%.3f rotation=%.4f scale=%.6f",
            hypothesis.dx,
            hypothesis.dy,
            hypothesis.rotation_deg,
            hypothesis.scale,
        )

    @staticmethod
    def _format_alignment_diagnostics_for_log(
        diagnostics: AlignmentDiagnostics | None,
    ) -> str:
        if diagnostics is None:
            return "diagnostics unavailable"
        return (
            f"keypoints_ref={diagnostics.reference_keypoints} "
            f"keypoints_deformed={diagnostics.deformed_keypoints} "
            f"candidate_matches={diagnostics.candidate_matches} "
            f"accepted_matches={diagnostics.accepted_matches}"
        )

    def _on_auto_align(self) -> None:
        if not self.canvas.has_both_images():
            return
        if self.chk_lock_alignment.isChecked():
            QMessageBox.warning(
                self,
                tr("alignment.auto.title"),
                tr("alignment.auto.locked"),
            )
            return

        if self._rigid_baseline_ref_transform is not None:
            self._discard_rigid_region_state(restore=True, clear_visuals=True)
        self._discard_auto_alignment_preview(restore=True)

        ref_path = self.project.ref_path
        dam_path = self.project.dam_path
        if not ref_path or not dam_path:
            return

        self.btn_start_alignment.setEnabled(False)
        try:
            result = estimate_auto_alignment(
                ref_path,
                dam_path,
                reference_transform=self.canvas.get_reference_transform(),
                deformed_transform=self.canvas.get_deformed_transform(),
            )
            metrics = self._format_alignment_diagnostics_for_log(
                result.diagnostics
            )
            for rank, hypothesis in enumerate(result.hypotheses, start=1):
                logger.info(
                    "Auto-alignment hypothesis %d (model %d): score=%.2f "
                    "inliers=%d ratio=%.3f rmse=%.3f dx=%.3f dy=%.3f "
                    "rotation=%.4f scale=%.6f centroid=(%.3f, %.3f) "
                    "bbox=(%.3f, %.3f, %.3f, %.3f) "
                    "dispersion=(%.3f, %.3f) support_area=%.4f "
                    "edge_fraction=%.3f body_fraction=%.3f",
                    rank,
                    hypothesis.model_index,
                    hypothesis.score,
                    hypothesis.inliers,
                    hypothesis.inlier_ratio,
                    hypothesis.inlier_rmse_px,
                    hypothesis.dx,
                    hypothesis.dy,
                    hypothesis.rotation_deg,
                    hypothesis.scale,
                    hypothesis.centroid_x,
                    hypothesis.centroid_y,
                    hypothesis.bbox_x_min,
                    hypothesis.bbox_y_min,
                    hypothesis.bbox_x_max,
                    hypothesis.bbox_y_max,
                    hypothesis.dispersion_x,
                    hypothesis.dispersion_y,
                    hypothesis.support_area_ratio,
                    hypothesis.edge_fraction,
                    hypothesis.body_fraction,
                )
                refinement = hypothesis.refinement
                if refinement is not None:
                    logger.info(
                        "Auto-alignment rigid refinement for model %d: "
                        "matches=%d rmse_before=%s rmse_after=%s used=%s "
                        "original=(%.3f, %.3f, %.4f, %.6f) "
                        "refined=(%s, %s, %s, %s)",
                        hypothesis.model_index,
                        refinement.rigid_matches,
                        refinement.rmse_before_px,
                        refinement.rmse_after_px,
                        refinement.used_refined,
                        refinement.original_dx,
                        refinement.original_dy,
                        refinement.original_rotation_deg,
                        refinement.original_scale,
                        refinement.refined_dx,
                        refinement.refined_dy,
                        refinement.refined_rotation_deg,
                        refinement.refined_scale,
                    )

            if result.confidence == "medium" and result.best is not None:
                self._preview_auto_alignment(result.best)
                logger.warning(
                    "Auto-alignment preview created: confidence=%s reasons=%s; %s",
                    result.confidence,
                    ",".join(result.confidence_reasons),
                    metrics.replace("\n", "; "),
                )
                return

            selected = result.selected
            if result.confidence != "high" or selected is None:
                self._set_rigid_instruction("alignment.status.auto_low")
                logger.warning(
                    "Auto-alignment not applied: confidence=%s reasons=%s; %s",
                    result.confidence,
                    ",".join(result.confidence_reasons),
                    metrics.replace("\n", "; "),
                )
                return

            self._preview_auto_alignment(selected)

            logger.info(
                "Auto-alignment preview created: dx=%.3f dy=%.3f rotation=%.4f "
                "scale=%.6f; %s",
                selected.dx,
                selected.dy,
                selected.rotation_deg,
                selected.scale,
                metrics.replace("\n", "; "),
            )
        except AutoAlignmentError as error:
            self._set_rigid_instruction("alignment.status.auto_low")
            metrics = self._format_alignment_diagnostics_for_log(
                error.diagnostics
            )
            logger.warning(
                "Auto-alignment rejected (%s): %s",
                error.code,
                metrics.replace("\n", "; "),
            )
            QMessageBox.warning(
                self,
                tr("alignment.auto.title"),
                tr("alignment.auto.failure"),
            )
        except Exception:
            self._set_rigid_instruction("alignment.status.auto_low")
            logger.exception("Auto-alignment failed")
            QMessageBox.warning(
                self,
                tr("alignment.auto.title"),
                tr("alignment.auto.failure"),
            )
        finally:
            self._update_auto_align_availability()
            self._refresh_navigation_footer()

    def _on_rotate_minus(self) -> None:
        step_deg = float(self.spn_rotate_step.value())
        self.canvas.rotate_selected(-step_deg)

    def _on_rotate_plus(self) -> None:
        step_deg = float(self.spn_rotate_step.value())
        self.canvas.rotate_selected(step_deg)

    def _on_scale_minus(self) -> None:
        step_pct = float(self.spn_scale_step.value())
        factor = max(0.001, 1.0 - (step_pct / 100.0))
        self.canvas.scale_selected(factor)

    def _on_scale_plus(self) -> None:
        step_pct = float(self.spn_scale_step.value())
        factor = 1.0 + (step_pct / 100.0)
        self.canvas.scale_selected(factor)

    def _on_finish_alignment(self) -> None:
        if not self._can_finish_alignment():
            return
        self.workflow.finish_alignment()
        if self.stage != Stage.CALIBRATION:
            return
        self.canvas.set_rigid_region_mode(False)
        self.canvas.clear_rigid_region_visuals()
        self._discard_auto_alignment_preview(restore=False)
        self._discard_rigid_region_state(restore=False, clear_visuals=True)
        self._set_rigid_action_visibility(
            apply=False, try_again=False, cancel=False
        )
        self.lbl_rigid_region_instruction.setVisible(False)

    def _on_restart_alignment(self) -> None:
        self.workflow.restart_from_alignment()
        if self.stage == self.Stage.ALIGNMENT:
            self._set_rigid_instruction(None)
            self._refresh_navigation_footer()

    def _on_restart_calibration(self) -> None:
        self.workflow.restart_from_calibration()

    def _on_restart_marking(self) -> None:
        self.workflow.restart_from_marking()

        self._current_ci_index = 1
        self._sync_ci_radio_buttons()
        self._update_ci_label()
        self.canvas.set_ci_index(1)

        self.chk_measure_ci_mode.blockSignals(True)
        self.chk_measure_ci_mode.setChecked(True)
        self.chk_measure_ci_mode.blockSignals(False)
        self.canvas.set_measure_ci_mode(True)

    # ---------------- Calibration ----------------
    def _on_calibration_mode_toggled(self, checked: bool) -> None:
        if checked:
            self.canvas.clear_calibration()
            self._calibration_px = None
        self.canvas.set_calibration_mode(checked)
        self._refresh_calibration_panel()

    def _refresh_calibration_panel(self) -> None:
        has_points = self.canvas.cal_p1 is not None and self.canvas.cal_p2 is not None
        if self.chk_calibration_mode.isChecked():
            action = "calibration.cancel_points"
        else:
            action = "calibration.remark_points" if has_points else "calibration.mark_points"
        self.chk_calibration_mode.setText(tr(action))
        self.lbl_px_distance.setText(
            tr("measurement.measured_distance_value", value=f"{self._calibration_px:.2f}")
            if has_points and self._calibration_px is not None else tr("label.measured_distance")
        )
        if self.stage == Stage.CALIBRATION and self._viewed_step is None:
            candidate, _ = self.meas.calibration_candidate()
            value = f"{candidate:.6g}" if candidate is not None else "—"
            self.lbl_m_per_px.setText(tr("calibration.calculated_scale", value=value))
        elif self._m_per_px is not None:
            self.lbl_m_per_px.setText(tr("measurement.scale_value", value=f"{self._m_per_px:.6f}"))
        else:
            self.lbl_m_per_px.setText(tr("label.scale_m_per_px"))
        self._refresh_navigation_footer()

    def _on_confirm_calibration(self) -> None:
        self.workflow.confirm_calibration()

    # ---------------- Marking: W ----------------
    def _on_set_w_mode_toggled(self, checked: bool) -> None:
        self.canvas.set_w_measure_mode(checked)

    def _on_generate_slices(self) -> None:
        if self._w_px is None:
            QMessageBox.warning(self, tr("group.marking"), tr("warning.set_w_first"))
            return
        self.canvas.generate_slices(n=6)
        self.meas.refresh_w_labels()
        self._refresh_summary()

    def _on_bumper_offset_changed(self, value: float) -> None:
        self.canvas.set_crossmember_offset_m(value)

    # ---------------- Marking: guide ----------------
    def _on_set_guide_mode_toggled(self, checked: bool) -> None:
        if checked and not self.canvas.slice_x:
            QMessageBox.warning(
                self,
                tr("group.marking"),
                tr("warning.generate_slices_first"),
            )
            self.chk_set_guide_mode.blockSignals(True)
            self.chk_set_guide_mode.setChecked(False)
            self.chk_set_guide_mode.blockSignals(False)
            return
        self.canvas.set_guide_mode(checked)

    # ---------------- Marking: Ci ----------------
    def _on_measure_ci_mode_toggled(self, checked: bool) -> None:
        if checked and not self.canvas.slice_x:
            QMessageBox.warning(
                self,
                tr("group.marking"),
                tr("warning.generate_slices_first"),
            )
            self.chk_measure_ci_mode.blockSignals(True)
            self.chk_measure_ci_mode.setChecked(False)
            self.chk_measure_ci_mode.blockSignals(False)
            return
        self.canvas.set_measure_ci_mode(checked)

    def _on_ci_radio_selected(self, idx: int, checked: bool) -> None:
        if not checked:
            return
        self._current_ci_index = idx
        self.canvas.set_ci_index(self._current_ci_index)
        self._update_ci_label()

    def _on_canvas_ci_selected(self, idx: int) -> None:
        self._current_ci_index = idx
        self._sync_ci_radio_buttons()
        self._update_ci_label()

    def _sync_ci_radio_buttons(self) -> None:
        mapping = {
            1: self.rb_c1,
            2: self.rb_c2,
            3: self.rb_c3,
            4: self.rb_c4,
            5: self.rb_c5,
            6: self.rb_c6,
        }

        for idx, rb in mapping.items():
            rb.blockSignals(True)
            rb.setChecked(idx == self._current_ci_index)
            rb.blockSignals(False)

    def _update_ci_label(self) -> None:
        self.lbl_ci_index.setText(tr("label.current_ci", idx=self._current_ci_index))

    def _on_finish_marking(self) -> None:
        self.workflow.finish_marking()

    # ---------------- Project sync + summary ----------------
    def _sync_ui_to_project(self) -> None:
        self.project.opacity = self.opacity_slider.value() / 100.0
        self.project.m_per_px = self._m_per_px

        self.project.w_px = self._w_px
        self.project.w_m = self._w_m
        self.project.delta_w_px = self._delta_w_px
        self.project.delta_w_m = self._delta_w_m

        self.project.c_px = (
            {f"C{i}": self._ci_px[i] for i in self._ci_px} if self._ci_px else None
        )
        self.project.c_m = (
            {f"C{i}": self._ci_m[i] for i in self._ci_m} if self._ci_m else None
        )

        self.project.total_energy_j = self._total_energy
        self.project.vehicle_mass_kg = self._vehicle_mass_kg
        self.project.damage_speed_mps = self._damage_speed_mps
        self.project.damage_speed_kmh = self._damage_speed_kmh

        ref_tr = self.canvas.get_reference_transform()
        self.project.ref_transform.x = ref_tr["x"]
        self.project.ref_transform.y = ref_tr["y"]
        self.project.ref_transform.scale = ref_tr["scale"]
        self.project.ref_transform.rotation_deg = ref_tr["rotation_deg"]

        tr_dam = self.canvas.get_deformed_transform()
        self.project.dam_transform.x = tr_dam["x"]
        self.project.dam_transform.y = tr_dam["y"]
        self.project.dam_transform.scale = tr_dam["scale"]
        self.project.dam_transform.rotation_deg = tr_dam["rotation_deg"]

        st = self.canvas.get_overlay_state()

        def to_point(obj) -> Point | None:
            if not obj:
                return None
            return Point(x=float(obj["x"]), y=float(obj["y"]))

        self.project.cal_p1 = to_point(st.get("cal_p1"))
        self.project.cal_p2 = to_point(st.get("cal_p2"))
        self.project.w_p1 = to_point(st.get("w_p1"))
        self.project.w_p2 = to_point(st.get("w_p2"))
        self.project.slice_x = st.get("slice_x")

        guide_y = st.get("guide_y")
        self.project.guide_y = None if guide_y is None else float(guide_y)
        self.project.bumper_offset_m = st.get("bumper_offset_m")
        self.project.bumper_offset_px = st.get("bumper_offset_px")
        self.project.crossmember_y = st.get("crossmember_y")

        cp = st.get("c_points")
        if isinstance(cp, dict):
            c_points: dict[str, dict[str, Point]] = {}
            for ck, vv in cp.items():
                if not isinstance(vv, dict):
                    continue
                ref = to_point(vv.get("ref"))
                deff = to_point(vv.get("def"))
                if ref and deff:
                    c_points[str(ck)] = {"ref": ref, "def": deff}
            self.project.c_points = c_points if c_points else None
        else:
            self.project.c_points = None

    def _refresh_summary(self) -> None:
        if self._viewed_step is not None:
            steps = tuple(self.workflow_step_labels)
            if steps.index(self._viewed_step) >= steps.index(self._current_workflow_step()):
                self._viewed_step = None
        self.workflow.apply_stage_gating()
        self._refresh_workflow_progress()
        self.lbl_result_ees_kmh.setText(
            tr("result.ees_kmh", value=f"{self._damage_speed_kmh:.2f}")
            if self._damage_speed_kmh is not None else ""
        )
        ees_mps = self._damage_speed_mps
        ees_kmh = self._damage_speed_kmh
        if ees_mps is None or not math.isfinite(ees_mps) or ees_mps < 0:
            ees_mps = (
                ees_kmh / 3.6
                if ees_kmh is not None and math.isfinite(ees_kmh) and ees_kmh >= 0
                else None
            )
        self.lbl_result_ees_mps.setText(
            tr("result.ees_mps", value=f"{ees_mps:.2f}") if ees_mps is not None else "—"
        )
        self.lbl_result_energy.setText(
            tr("result.energy_kj", value=f"{self._total_energy / 1000:.2f}")
            if self._total_energy is not None else ""
        )
        stage_key = f"stage.{self.stage.value}"

        parts = []
        parts.append(tr("summary.project", name=self.project.name))
        parts.append(tr("summary.stage", stage=tr(stage_key)))
        if bool(self.project.ref_path) != bool(self.project.dam_path):
            parts.append(tr("summary.single_image_active"))

        parts.append(
            tr("summary.scale_not_set")
            if self._m_per_px is None
            else tr("summary.scale_value", value=f"{self._m_per_px:.6f}")
        )

        if self._w_px is None:
            parts.append(tr("summary.w_not_set"))
        else:
            if self._m_per_px is None:
                parts.append(tr("summary.w_value_px_only", px=f"{self._w_px:.2f}"))
            else:
                parts.append(
                    tr(
                        "summary.w_value_full",
                        px=f"{self._w_px:.2f}",
                        m=f"{(self._w_px * self._m_per_px):.2f}",
                    )
                )

        c_done = sum(1 for i in range(1, 7) if i in self._ci_m)
        parts.append(tr("summary.c_measures", done=c_done))

        parts.append(
            tr("summary.vehicle_mass_default")
            if self._vehicle_mass_kg is None
            else tr("summary.vehicle_mass_value", value=f"{self._vehicle_mass_kg:.2f}")
        )

        ready = (
            (self._m_per_px is not None) and (self._w_px is not None) and (c_done == 6)
        )
        parts.append(
            tr("summary.status_complete") if ready else tr("summary.status_incomplete")
        )

        self.lbl_summary.setText("\n".join(parts))

    def _warn_if_alignment_scales_differ(self) -> bool:
        if not self.canvas.has_both_images():
            return True
        ref_tr = self.canvas.get_reference_transform()
        dam_tr = self.canvas.get_deformed_transform()

        ref_scale = float(ref_tr.get("scale", 1.0))
        dam_scale = float(dam_tr.get("scale", 1.0))

        smaller = min(ref_scale, dam_scale)
        larger = max(ref_scale, dam_scale)

        if smaller <= 0:
            return True

        ratio = larger / smaller

        if ratio <= 1.02:
            return True

        answer = QMessageBox.question(
            self,
            tr("alignment.warning.title"),
            tr("alignment.warning.scale_mismatch"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _build_shortcuts(self) -> None:
        # Nudge
        self.sc_nudge_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.sc_nudge_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.sc_nudge_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.sc_nudge_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)

        self.sc_nudge_up.activated.connect(lambda: self.canvas.nudge_selected(0, -1))
        self.sc_nudge_down.activated.connect(lambda: self.canvas.nudge_selected(0, 1))
        self.sc_nudge_left.activated.connect(lambda: self.canvas.nudge_selected(-1, 0))
        self.sc_nudge_right.activated.connect(lambda: self.canvas.nudge_selected(1, 0))

        # Rotate
        self.sc_rotate_minus = QShortcut(QKeySequence("Q"), self)
        self.sc_rotate_plus = QShortcut(QKeySequence("E"), self)

        self.sc_rotate_minus.activated.connect(self._on_rotate_minus)
        self.sc_rotate_plus.activated.connect(self._on_rotate_plus)

        # Scale
        self.sc_scale_minus = QShortcut(QKeySequence("Z"), self)
        self.sc_scale_plus = QShortcut(QKeySequence("X"), self)

        self.sc_scale_minus.activated.connect(self._on_scale_minus)
        self.sc_scale_plus.activated.connect(self._on_scale_plus)
        self._alignment_shortcuts = (
            self.sc_nudge_up, self.sc_nudge_down, self.sc_nudge_left, self.sc_nudge_right,
            self.sc_rotate_minus, self.sc_rotate_plus, self.sc_scale_minus, self.sc_scale_plus,
        )
