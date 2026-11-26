from __future__ import annotations

from enum import Enum
import logging
import math
from pathlib import Path

import cv2
from PySide6.QtCore import QSignalBlocker, QSize, Qt
from PySide6.QtGui import QActionGroup, QKeySequence, QShortcut
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
from app.ui.styles import (
    ACTION_STYLES, WORKFLOW_PANEL_STYLES, set_style_property, workflow_step_icon,
)
from app.ui.widgets.calc_panel import CalcPanel
from app.ui.widgets.help_dialog import HelpDialog
from app.report import generate_report
from app.core.number_format import format_display_number
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
        self._auto_alignment_undo_transform: dict[str, float] | None = None
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
        self.canvas.ci_measured.connect(self.meas.on_ci_measured)
        self.canvas.ci_selected.connect(self._on_canvas_ci_selected)
        self.canvas.guide_placed.connect(self._refresh_marking_panel)
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
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("")
        language_menu = menu_bar.addMenu("")
        help_menu = menu_bar.addMenu("")
        self._menu_actions = {
            "menu.file": file_menu.menuAction(),
            "menu.language": language_menu.menuAction(),
            "menu.help": help_menu.menuAction(),
        }
        for key, handler, shortcut in (
            ("menu.new", self._on_new_project, QKeySequence.StandardKey.New),
            ("menu.load_project", self._on_load_project, QKeySequence.StandardKey.Open),
            ("menu.save_project", self._on_save_project, QKeySequence.StandardKey.Save),
        ):
            action = file_menu.addAction("", handler)
            action.setShortcuts(shortcut)
            self._menu_actions[key] = action
        file_menu.addSeparator()
        for key, handler in (
            ("menu.export_overlay", self._on_export_png),
            ("menu.export_current_view", self._on_export_current_view_png),
            ("menu.export_report", self._on_export_report),
        ):
            self._menu_actions[key] = file_menu.addAction("", handler)

        self._language_actions = {}
        languages = QActionGroup(language_menu)
        for code, key in (("en", "menu.language.english"), ("pt", "menu.language.portuguese")):
            action = language_menu.addAction("")
            action.setCheckable(True)
            languages.addAction(action)
            action.triggered.connect(lambda checked, lang=code: self._set_language_and_refresh(lang))
            self._language_actions[code] = action
            self._menu_actions[key] = action

        for topic in ("guide", "methodology", "shortcuts", "about"):
            if topic == "about":
                help_menu.addSeparator()
            key = f"help.{topic}.title"
            action = help_menu.addAction("")
            action.triggered.connect(lambda checked, article=topic: self._show_help(article))
            self._menu_actions[key] = action
        self._retranslate_menus()

    def _retranslate_menus(self) -> None:
        for key, action in self._menu_actions.items():
            action.setText(tr(key))
        self._language_actions[get_language()].setChecked(True)

    def _show_help(self, topic: str) -> None:
        project_shortcuts = {}
        if topic == "shortcuts":
            project_shortcuts = {
                name: self._menu_actions[key].shortcut().toString(QKeySequence.SequenceFormat.NativeText)
                for name, key in (
                    ("new", "menu.new"),
                    ("open", "menu.load_project"),
                    ("save", "menu.save_project"),
                )
            }
        dialog = HelpDialog(topic, self, project_shortcuts)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def _apply_styles(self) -> None:
        self.setStyleSheet(ACTION_STYLES + WORKFLOW_PANEL_STYLES)

    def _build_workflow_progress(self) -> None:
        toolbar = QToolBar(self)
        toolbar.setObjectName("workflowProgressBar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.toggleViewAction().setVisible(False)
        strip = QWidget()
        strip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(strip)
        self._workflow_progress_layout = layout
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)
        self.workflow_step_labels = {}
        for step in ("images", "alignment", "calibration", "measurement", "calculation", "result"):
            label = QPushButton()
            label.setProperty("workflowStep", True)
            label.setIconSize(QSize(16, 16))
            label.clicked.connect(lambda checked=False, target=step: self._view_workflow_step(target))
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.workflow_step_labels[step] = label
            layout.addWidget(label, 1)
        toolbar.addWidget(strip)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def has_energy_result(self) -> bool:
        energy = self._total_energy
        return energy is not None and math.isfinite(energy) and energy > 0

    def has_ees_result(self) -> bool:
        speed = self._damage_speed_kmh
        return self.has_energy_result() and speed is not None and math.isfinite(speed) and speed >= 0

    def _current_workflow_step(self) -> str:
        if (
            self.stage == Stage.DONE
            and self.has_ees_result()
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

        for index, (step, label) in enumerate(self.workflow_step_labels.items()):
            title = tr(f"progress.{step}")
            context = []
            if step == "alignment":
                if current <= index:
                    context.append(tr("progress.optional"))
                elif not self.canvas.has_both_images():
                    context.append(tr("progress.skipped"))
            if step == "alignment" and index < current:
                status = "passed"
            elif step == "result" and result_ready:
                status = "complete"
            elif index < current:
                status = "complete"
            elif index == current:
                status = "current"
            else:
                status = "future"
            active = index == current
            viewing = step == self._viewed_step
            set_style_property(label, "progressStatus", status)
            set_style_property(label, "progressCurrent", active)
            set_style_property(label, "progressViewed", viewing)
            label.setIcon(workflow_step_icon(index + 1, status, active, label.devicePixelRatioF()))
            label.setText(title)
            self._workflow_progress_layout.setStretch(index, label.sizeHint().width())
            context.append(tr(f"progress.status.{status}"))
            if active and status == "complete":
                context.append(tr("progress.status.current"))
            if viewing:
                viewing_key = "progress.viewing_calculation" if step == "calculation" else "progress.viewing"
                context.append(tr(viewing_key))
            label.setToolTip(f"{title} — {' · '.join(context)}")
            label.setAccessibleName(label.toolTip())
            label.setEnabled(index <= current and not blocked)

    def _build_canvas_area(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas, 1)

        self.canvas_view_bar = QWidget()
        self.canvas_view_bar.setObjectName("canvasViewBar")
        self.canvas_view_bar.setMinimumHeight(40)
        self.canvas_view_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar_layout = QHBoxLayout(self.canvas_view_bar)
        bar_layout.setContentsMargins(8, 5, 8, 5)
        bar_layout.setSpacing(8)
        self.lbl_overlay_opacity = QLabel(tr("label.overlay_opacity"))
        self.lbl_overlay_opacity.setObjectName("opacityLabel")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName("opacitySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.setMinimumHeight(22)
        self.lbl_overlay_opacity.setBuddy(self.opacity_slider)
        self.lbl_opacity_percent = QLabel()
        self.lbl_opacity_percent.setObjectName("opacityPercent")
        self.lbl_opacity_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        toggle.setProperty("uiRole", "disclosure")

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
        self.btn_return_to_current_step.setProperty("uiRole", "secondary")
        self.btn_return_to_current_step.clicked.connect(self._return_to_current_step)
        self.btn_return_to_current_step.hide()
        dock_layout.addWidget(self.btn_return_to_current_step)
        self.btn_redo_step = QPushButton(tr("progress.redo"))
        self.btn_redo_step.setProperty("uiRole", "destructive")
        self.btn_redo_step.clicked.connect(self._redo_viewed_step)
        self.btn_redo_step.hide()
        dock_layout.addWidget(self.btn_redo_step)

        # --- Load images ---
        self.load_group = QWidget()
        load_layout = QVBoxLayout(self.load_group)
        load_layout.setContentsMargins(0, 0, 0, 0)
        load_layout.setSpacing(10)
        self._images_title = QLabel()
        self._images_title.setObjectName("imagesTitle")
        load_layout.addWidget(self._images_title)

        self.btn_toggle_image_controls = QToolButton()
        self.btn_toggle_image_controls.setObjectName("imagesDisclosure")
        self._style_disclosure(self.btn_toggle_image_controls)
        self.btn_toggle_image_controls.toggled.connect(self._refresh_image_controls)
        load_layout.addWidget(self.btn_toggle_image_controls)

        self.btn_load_dam = QPushButton()
        self.btn_load_ref = QPushButton()
        self._image_cards = {}
        for key, button in (("deformed", self.btn_load_dam), ("reference", self.btn_load_ref)):
            card = QFrame()
            card.setObjectName("imageLoadCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 11, 12, 11)
            card_layout.setSpacing(8)
            heading = QHBoxLayout()
            heading.setSpacing(6)
            title = QLabel()
            title.setObjectName("imageCardTitle")
            title.setWordWrap(True)
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            status = QLabel()
            status.setObjectName("imageCardStatus")
            heading.addWidget(title, 1)
            heading.addWidget(status, 0, Qt.AlignmentFlag.AlignVCenter)
            card_layout.addLayout(heading)
            description = QLabel()
            description.setObjectName("imageCardDescription")
            description.setWordWrap(True)
            card_layout.addWidget(description)
            button.setProperty("uiRole", "secondary")
            button.setProperty("imageAction", True)
            card_layout.addWidget(button)
            load_layout.addWidget(card)
            self._image_cards[key] = (card, title, description, status, button)
        dock_layout.addWidget(self.load_group)

        self.fine_adjust_group = QGroupBox()
        self.fine_adjust_group.setObjectName("alignmentManualCard")
        fine_layout = QVBoxLayout(self.fine_adjust_group)
        fine_layout.setContentsMargins(12, 11, 12, 11)
        fine_layout.setSpacing(8)
        self.btn_toggle_manual_alignment = QToolButton()
        self.btn_toggle_advanced_alignment = QToolButton()
        self.btn_toggle_advanced_alignment.setObjectName("alignmentPrecisionDisclosure")
        for toggle in (self.btn_toggle_manual_alignment, self.btn_toggle_advanced_alignment):
            self._style_disclosure(toggle)
            toggle.setProperty("panelDisclosure", True)
            toggle.toggled.connect(self._refresh_alignment_sections)
        self.alignment_advanced = QWidget()
        advanced_layout = QGridLayout(self.alignment_advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)

        # --- Alignment group ---
        self.align_group = QGroupBox()
        self.align_group.setObjectName("alignmentPanel")
        self.align_group.setAccessibleName(tr("group.alignment"))
        align_layout = QVBoxLayout(self.align_group)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(10)
        self.lbl_alignment_title = QLabel(tr("group.alignment"))
        self.lbl_alignment_title.setObjectName("alignmentTitle")
        self.lbl_alignment_title.setWordWrap(True)
        self.lbl_alignment_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        align_layout.addWidget(self.lbl_alignment_title)
        self.alignment_card = QFrame()
        self.alignment_card.setObjectName("alignmentCard")
        alignment_card_layout = QVBoxLayout(self.alignment_card)
        alignment_card_layout.setContentsMargins(12, 11, 12, 11)
        alignment_card_layout.setSpacing(8)
        align_layout.addWidget(self.alignment_card)
        self.lbl_alignment_consultation = QLabel()
        self.lbl_alignment_consultation.setWordWrap(True)
        self.lbl_alignment_consultation.hide()
        alignment_card_layout.addWidget(self.lbl_alignment_consultation)

        self.chk_alignment_mode = QCheckBox(tr("check.alignment_mode"))
        self.chk_alignment_mode.setToolTip(tr("check.alignment_mode_hint"))
        self.chk_lock_alignment = QCheckBox(tr("check.lock_alignment"))
        fine_layout.addWidget(self.chk_alignment_mode)
        fine_layout.addWidget(self.chk_lock_alignment)

        self.lbl_editable_image = QLabel(tr("label.editable_image"))
        self.lbl_editable_image.setObjectName("alignmentTargetLabel")
        fine_layout.addWidget(self.lbl_editable_image)

        self.cmb_alignment_target = QComboBox()
        self.cmb_alignment_target.addItem(tr("combo.deformed"), "dam")
        self.cmb_alignment_target.addItem(tr("combo.reference"), "ref")
        self.canvas.set_alignment_target("dam")
        fine_layout.addWidget(self.cmb_alignment_target)

        self.btn_reset_alignment = QPushButton(tr("button.reset_selected_transform"))
        self.btn_reset_alignment.setProperty("uiRole", "destructive")
        self.btn_reset_alignment.setProperty("panelAction", True)
        self.btn_reset_alignment.setAccessibleName(self.btn_reset_alignment.text())
        self.btn_reset_alignment.setToolTip(tr("alignment.reset.tooltip"))
        self.btn_reset_alignment.setFlat(True)

        self.lbl_alignment_method = QLabel(tr("label.alignment_method"))
        self.lbl_alignment_method.setObjectName("alignmentMethodLabel")
        alignment_card_layout.addWidget(self.lbl_alignment_method)
        self.rad_alignment_auto = QRadioButton(tr("alignment.method.auto"))
        self.rad_alignment_rigid = QRadioButton(tr("alignment.method.rigid"))
        self.alignment_method_buttons = QButtonGroup(self)
        self.alignment_method_buttons.setExclusive(True)
        self.alignment_method_buttons.addButton(self.rad_alignment_auto)
        self.alignment_method_buttons.addButton(self.rad_alignment_rigid)
        self.rad_alignment_auto.setChecked(True)
        self.alignment_method_row = AlignmentMethodRow(
            self.rad_alignment_auto, self.rad_alignment_rigid
        )
        alignment_card_layout.addWidget(self.alignment_method_row)

        self.btn_start_alignment = QPushButton(tr("button.start_alignment"))
        self.btn_start_alignment.setProperty("uiRole", "primary")
        self.btn_start_alignment.setProperty("panelAction", True)
        self.btn_start_alignment.setEnabled(False)

        self.lbl_alignment_status_title = QLabel()
        self.lbl_alignment_status_title.setObjectName("alignmentStatusTitle")
        self.lbl_alignment_status_title.setWordWrap(True)
        self.lbl_alignment_status_title.hide()
        alignment_card_layout.addWidget(self.lbl_alignment_status_title)
        self.lbl_rigid_region_instruction = QLabel()
        self.lbl_rigid_region_instruction.setWordWrap(True)
        self.lbl_rigid_region_instruction.setText(
            tr("alignment.status.choose_method")
        )
        alignment_card_layout.addWidget(self.lbl_rigid_region_instruction)

        self.alignment_actions_widget = QWidget()
        rigid_actions = QVBoxLayout(self.alignment_actions_widget)
        rigid_actions.setContentsMargins(0, 0, 0, 0)
        rigid_actions.setSpacing(8)
        self._alignment_decisions = QWidget()
        preview_row = QHBoxLayout(self._alignment_decisions)
        preview_row.setContentsMargins(0, 0, 0, 0)
        preview_row.setSpacing(8)
        rigid_actions.addWidget(self._alignment_decisions)
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
            button.setProperty("alignmentDecision", True)
            preview_row.addWidget(button, 1)
        for button in (self.btn_apply_alignment_suggestion, self.btn_rigid_apply):
            button.setAccessibleName(button.text().replace("\n", " "))
            button.setProperty("uiRole", "primary")
        self.btn_rigid_cancel.setProperty("uiRole", "destructive")
        self.btn_rigid_try_again.setProperty("uiRole", "secondary")
        self.btn_rigid_try_again.setProperty("panelAction", True)
        self.btn_rigid_try_again.hide()
        rigid_actions.addWidget(self.btn_rigid_try_again)
        self.btn_undo_auto_alignment = QPushButton(tr("alignment.undo_auto"))
        self.btn_undo_auto_alignment.setProperty("uiRole", "destructive")
        self.btn_undo_auto_alignment.setProperty("panelAction", True)
        self.btn_undo_auto_alignment.setFlat(True)
        self.btn_undo_auto_alignment.hide()
        self.btn_undo_auto_alignment.clicked.connect(self._undo_auto_alignment)
        rigid_actions.addWidget(self.btn_undo_auto_alignment)
        self.alignment_actions_widget.setVisible(False)
        alignment_card_layout.addWidget(self.alignment_actions_widget)
        alignment_card_layout.addWidget(self.btn_start_alignment)

        self.btn_finish_alignment = QPushButton(tr("button.finish_alignment"))
        self.btn_finish_alignment.setVisible(False)
        self.btn_finish_alignment.setEnabled(False)

        self.nudge_box = QGroupBox(tr("group.nudge"))
        self.nudge_box.setProperty("alignmentSection", True)
        nudge_layout = QVBoxLayout(self.nudge_box)
        nudge_layout.setContentsMargins(0, 5, 0, 0)
        directions = QGridLayout()
        directions.setSpacing(4)

        self.btn_up = QPushButton("↑")
        self.btn_left = QPushButton("←")
        self.btn_right = QPushButton("→")
        self.btn_down = QPushButton("↓")

        for b in (self.btn_up, self.btn_left, self.btn_right, self.btn_down):
            b.setFixedWidth(44)

        directions.addWidget(self.btn_up, 0, 1)
        directions.addWidget(self.btn_left, 1, 0)
        directions.addWidget(self.btn_down, 1, 1)
        directions.addWidget(self.btn_right, 1, 2)
        nudge_layout.addLayout(directions)
        nudge_layout.setAlignment(directions, Qt.AlignmentFlag.AlignHCenter)

        advanced_layout.addWidget(self.nudge_box, 0, 0, 1, 2)

        self.rotate_box = QGroupBox(tr("group.rotate"))
        self.rotate_box.setProperty("alignmentSection", True)
        rotate_layout = QGridLayout(self.rotate_box)
        rotate_layout.setContentsMargins(0, 5, 0, 0)
        rotate_layout.setSpacing(8)

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
        self.scale_box.setProperty("alignmentSection", True)
        scale_layout = QGridLayout(self.scale_box)
        scale_layout.setContentsMargins(0, 5, 0, 0)
        scale_layout.setSpacing(8)

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
            btn.setProperty("uiRole", "secondary")
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
        self.lbl_alignment_shortcuts.setObjectName("alignmentShortcuts")
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
        self._build_calibration_panel()
        dock_layout.addWidget(self.cal_group)

        # --- Marking group ---
        self.mark_group = QGroupBox()
        self.mark_group.setObjectName("measurementPanel")
        mark_layout = QVBoxLayout(self.mark_group)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        mark_layout.setSpacing(10)
        self.lbl_marking_title = QLabel(tr("progress.measurement"))
        self.lbl_marking_title.setObjectName("measurementTitle")
        self.mark_group.setAccessibleName(self.lbl_marking_title.text())
        mark_layout.addWidget(self.lbl_marking_title)

        self.lbl_marking_orientation = QLabel(tr("label.marking_orientation"))
        self.lbl_marking_orientation.setObjectName("measurementOrientation")
        self.lbl_marking_orientation.setWordWrap(True)
        mark_layout.addWidget(self.lbl_marking_orientation)

        self.mark_width_group = QGroupBox()
        self.mark_width_group.setProperty("measurementCard", True)
        width_layout = QVBoxLayout(self.mark_width_group)
        width_layout.setContentsMargins(12, 11, 12, 11)
        width_layout.setSpacing(7)
        self.lbl_width_heading = QLabel(tr("marking.width"))
        self.lbl_width_heading.setProperty("measurementHeading", True)
        self.lbl_width_heading.setWordWrap(True)
        width_layout.addWidget(self.lbl_width_heading)
        self.chk_set_w_mode = QPushButton(tr("marking.mark_width"))
        self.chk_set_w_mode.setProperty("uiRole", "primary")
        self.chk_set_w_mode.setProperty("panelAction", True)
        self.chk_set_w_mode.setCheckable(True)
        self.lbl_w = QLabel(tr("label.w_default"))
        self.lbl_w.setObjectName("measurementWidthValue")
        self.lbl_w.setWordWrap(True)
        width_layout.addWidget(self.lbl_w)
        self.lbl_slice_status = QLabel()
        self.lbl_slice_status.setProperty("measurementStatus", True)
        self.lbl_slice_status.setWordWrap(True)
        width_layout.addWidget(self.lbl_slice_status)
        self.lbl_delta_w = QLabel(tr("label.delta_w_default"))
        self.lbl_delta_w.setWordWrap(True)
        width_layout.addWidget(self.lbl_delta_w)
        self.lbl_width_capture = QLabel(tr("marking.width_capture"))
        self.lbl_width_capture.setWordWrap(True)
        width_layout.addWidget(self.lbl_width_capture)
        width_layout.addWidget(self.chk_set_w_mode)
        mark_layout.addWidget(self.mark_width_group)

        self.btn_toggle_marking_references = QToolButton()
        self.btn_toggle_marking_references.setObjectName("measurementReferencesDisclosure")
        self._style_disclosure(self.btn_toggle_marking_references)
        self.btn_toggle_marking_references.setProperty("panelDisclosure", True)
        self.btn_toggle_marking_references.toggled.connect(self._on_marking_references_toggled)
        self.marking_references = QFrame()
        self.marking_references.setProperty("measurementCard", True)
        references_layout = QVBoxLayout(self.marking_references)
        references_layout.setContentsMargins(12, 11, 12, 11)
        references_layout.setSpacing(7)
        self.chk_set_guide_mode = QCheckBox(tr("check.set_guide_mode"))
        self.chk_set_guide_mode.setToolTip(tr("marking.guide_hint"))
        references_layout.addWidget(self.chk_set_guide_mode)

        # --- Offset travessa do para-choque ---
        self.lbl_bumper_offset = QLabel(tr("label.bumper_offset_m"))
        self.lbl_bumper_offset.setWordWrap(True)
        references_layout.addWidget(self.lbl_bumper_offset)

        self.spn_bumper_offset = QDoubleSpinBox()
        self.spn_bumper_offset.setDecimals(3)
        self.spn_bumper_offset.setRange(0.0, 2.0)
        self.spn_bumper_offset.setSingleStep(0.01)
        self.spn_bumper_offset.setValue(0.0)
        references_layout.addWidget(self.spn_bumper_offset)

        self.mark_ci_group = QGroupBox()
        self.mark_ci_group.setProperty("measurementCard", True)
        ci_layout = QVBoxLayout(self.mark_ci_group)
        ci_layout.setContentsMargins(12, 11, 12, 11)
        ci_layout.setSpacing(7)
        self.lbl_ci_heading = QLabel(tr("marking.crush"))
        self.lbl_ci_heading.setProperty("measurementHeading", True)
        self.lbl_ci_heading.setWordWrap(True)
        ci_layout.addWidget(self.lbl_ci_heading)
        self.lbl_ci_progress = QLabel()
        self.lbl_ci_progress.setProperty("measurementStatus", True)
        self.lbl_ci_progress.setWordWrap(True)
        ci_layout.addWidget(self.lbl_ci_progress)
        self.chk_measure_ci_mode = QCheckBox(tr("check.measure_ci_mode"))
        ci_layout.addWidget(self.chk_measure_ci_mode)
        self.lbl_ci_instruction = QLabel()
        self.lbl_ci_instruction.setWordWrap(True)
        ci_layout.addWidget(self.lbl_ci_instruction)

        self.lbl_ci_index = QLabel(tr("label.current_ci", idx=1))
        ci_layout.addWidget(self.lbl_ci_index)

        self.ci_select_box = QGroupBox()
        self.ci_select_box.setObjectName("measurementCiGrid")
        self.ci_select_box.setAccessibleName(tr("group.select_c"))
        ci_select_layout = QGridLayout(self.ci_select_box)
        ci_select_layout.setContentsMargins(0, 0, 0, 0)
        ci_select_layout.setHorizontalSpacing(8)
        ci_select_layout.setVerticalSpacing(3)

        self.rb_c1 = QRadioButton("C1")
        self.rb_c2 = QRadioButton("C2")
        self.rb_c3 = QRadioButton("C3")
        self.rb_c4 = QRadioButton("C4")
        self.rb_c5 = QRadioButton("C5")
        self.rb_c6 = QRadioButton("C6")

        self.rb_c1.setChecked(True)

        self.ci_value_labels = {}
        for index, radio in enumerate(
            (self.rb_c1, self.rb_c2, self.rb_c3, self.rb_c4, self.rb_c5, self.rb_c6), 1
        ):
            row, column = divmod(index - 1, 3)
            ci_select_layout.setColumnStretch(column, 1)
            ci_select_layout.addWidget(radio, row * 2, column)
            value = QLabel("—")
            value.setProperty("measurementCiValue", True)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ci_select_layout.addWidget(value, row * 2 + 1, column)
            self.ci_value_labels[index] = value

        self.lbl_ci_values = QLabel(tr("measurement.c_values_prefix"))
        self.lbl_ci_values.setWordWrap(True)
        ci_layout.addWidget(self.lbl_ci_values)
        ci_layout.addWidget(self.ci_select_box)
        mark_layout.addWidget(self.mark_ci_group)
        mark_layout.addWidget(self.btn_toggle_marking_references)
        mark_layout.addWidget(self.marking_references)
        self.marking_references.hide()

        self.btn_finish_marking = QPushButton(tr("button.finish_marking"))

        dock_layout.addWidget(self.mark_group)


        # --- Calc panel ---
        self.calc_panel = CalcPanel(self)
        dock_layout.addWidget(self.calc_panel)

        # --- Result panel ---
        self._build_result_panel()
        dock_layout.addWidget(self._summary_group)

        dock_layout.addStretch(1)

        scroll.setWidget(dock_widget)
        dock_content = QWidget()
        dock_content_layout = QVBoxLayout(dock_content)
        dock_content_layout.setContentsMargins(0, 0, 0, 0)
        dock_content_layout.setSpacing(0)
        dock_content_layout.addWidget(scroll, 1)

        self.navigation_footer = QWidget()
        self.navigation_footer.setObjectName("navigationFooter")
        self.navigation_footer.setMinimumHeight(40)
        footer_layout = QVBoxLayout(self.navigation_footer)
        footer_layout.setContentsMargins(8, 5, 8, 5)
        footer_layout.setSpacing(4)
        self.lbl_navigation_hint = QLabel()
        self.lbl_navigation_hint.setObjectName("navigationHint")
        self.lbl_navigation_hint.setWordWrap(True)
        self.lbl_navigation_hint.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        footer_layout.addWidget(self.lbl_navigation_hint)
        self.btn_finish_images = QPushButton(tr("button.finish_images"))
        self.btn_finish_images.clicked.connect(self.workflow.finish_images)
        for button in (
            self.btn_finish_images, self.btn_finish_alignment,
            self.btn_confirm_calibration, self.btn_finish_marking,
        ):
            button.setProperty("uiRole", "primary")
            button.setMinimumHeight(30)
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
        self.rad_alignment_auto.toggled.connect(self._update_alignment_edit_availability)
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
        previous_language = get_language()
        set_language(lang)
        self.calc_panel.retranslate_numeric_fields(previous_language)
        self._retranslate_calibration_distance(previous_language)
        self._retranslate_ui()
        self._refresh_summary()

    def _retranslate_ui(self) -> None:
        self._update_window_title()
        self._retranslate_menus()

        self._controls_dock.setWindowTitle(tr("dock.controls"))
        self.btn_return_to_current_step.setText(tr("progress.return_current"))
        self.btn_redo_step.setText(tr("progress.redo"))
        self._refresh_alignment_consultation()

        self._refresh_image_controls()
        self.btn_finish_images.setText(tr("button.finish_images"))
        self.lbl_overlay_opacity.setText(tr("label.overlay_opacity"))

        self.align_group.setAccessibleName(tr("group.alignment"))
        self.lbl_alignment_title.setText(tr("group.alignment"))
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
        self.btn_rigid_apply.setText(tr("button.rigid_apply"))
        self.btn_rigid_try_again.setText(tr("button.rigid_try_again"))
        self._refresh_alignment_cancel_label()
        self.btn_undo_auto_alignment.setText(tr("alignment.undo_auto"))
        if self._rigid_instruction_key is not None:
            self.lbl_rigid_region_instruction.setText(
                tr(self._rigid_instruction_key)
            )
        elif 0 < len(self._rigid_reference_regions) < 3:
            self.lbl_rigid_region_instruction.setText(tr(
                "alignment.rigid.instruction.reference_progress",
                count=len(self._rigid_reference_regions),
            ))
        else:
            self.lbl_rigid_region_instruction.setText(tr(self._idle_alignment_instruction()))
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

        self._translate_calibration_panel()
        self.btn_confirm_calibration.setText(tr("button.confirm_calibration"))

        self.lbl_marking_title.setText(tr("progress.measurement"))
        self.mark_group.setAccessibleName(self.lbl_marking_title.text())
        self.ci_select_box.setAccessibleName(tr("group.select_c"))
        self.lbl_ci_values.setText(tr("measurement.c_values_prefix"))
        self.lbl_width_capture.setText(tr("marking.width_capture"))
        self.lbl_marking_orientation.setText(tr("label.marking_orientation"))
        self.chk_set_w_mode.setText(tr("marking.mark_width"))
        self.chk_set_guide_mode.setText(tr("check.set_guide_mode"))
        self.chk_set_guide_mode.setToolTip(tr("marking.guide_hint"))
        self.lbl_bumper_offset.setText(tr("label.bumper_offset_m"))
        self.chk_measure_ci_mode.setText(tr("check.measure_ci_mode"))
        self._update_ci_label()
        self.btn_finish_marking.setText(tr("button.finish_marking"))
        self.meas.refresh_w_display()
        self.meas.update_ci_values_label()
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
        self._images_title.setVisible(loading or self._viewed_step == "images")
        self._images_title.setText(tr("group.images"))
        roles = []
        for key, item in (
            ("deformed", self.canvas.ctrl.dam_item), ("reference", self.canvas.ctrl.ref_item)
        ):
            card, title, description, badge, button = self._image_cards[key]
            loaded = item is not None
            if loaded:
                roles.append(tr(f"combo.{key}"))
            image_name = tr(f"images.{key}")
            title.setText(tr("images.reference_optional") if key == "reference" else image_name)
            description.setText(tr(f"images.{key}_help"))
            badge.setText(tr("images.status_loaded" if loaded else "images.status_missing"))
            button.setText(tr("images.replace" if loaded else "images.choose"))
            button.setAccessibleName(tr(
                "images.replace_named" if loaded else "images.choose_named",
                image=image_name.lower(),
            ))
            role = "primary" if loading and key == "deformed" and not loaded else "secondary"
            set_style_property(badge, "imageLoaded", loaded)
            set_style_property(button, "uiRole", role)
            card.setVisible(loading or expanded)
            button.setVisible(loading or expanded)
        if len(roles) == 2:
            status = f"✓ {tr('images.both_loaded')}"
        else:
            status = f"✓ {roles[0]}" if roles else tr("images.none_loaded")
        toggle.setText(f"{'▾' if expanded else '▸'} {status}")
        toggle.setAccessibleName(f"{tr('images.loaded')} — {status}")
        toggle.setToolTip("\n".join([tr("images.toggle_controls"), *roles]))

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
                    x=format_display_number(values["x"]),
                    y=format_display_number(values["y"]),
                    rotation=format_display_number(values["rotation_deg"]),
                    scale=format_display_number(values["scale"], 4),
                ))
        self.lbl_alignment_consultation.setText("\n".join(lines))

    def _on_lock_alignment_toggled(self, checked: bool) -> None:
        self.canvas.set_alignment_locked(checked)
        self._update_alignment_actions_visibility()

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
        manual_visible = self.stage == Stage.ALIGNMENT and self._viewed_step is None
        manual_visible = manual_visible and not self._workflow_navigation_blocked()
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
            content.setVisible(expanded and manual_visible)

    def _idle_alignment_instruction(self) -> str:
        if self.canvas.has_images() and not self.canvas.has_both_images():
            return "alignment.status.single_image"
        return "alignment.status.choose_method"

    def _update_alignment_edit_availability(self) -> None:
        pending = self._workflow_navigation_blocked()
        editable = self.stage == Stage.ALIGNMENT and self._viewed_step is None
        idle = editable and not pending
        both_images = self.canvas.has_both_images()
        applied = self._rigid_instruction_key == "alignment.status.auto_applied"
        failed = self._rigid_instruction_key == "alignment.status.auto_low"
        show_methods = idle and both_images and not applied
        self.lbl_alignment_method.setVisible(show_methods)
        self.alignment_method_row.setVisible(show_methods)
        self.alignment_method_row.setEnabled(show_methods)
        self.btn_start_alignment.setVisible(idle and both_images)
        self.btn_start_alignment.setText(tr(
            "alignment.retry_auto"
            if applied or (failed and self.rad_alignment_auto.isChecked())
            else "button.start_alignment"
        ))
        set_style_property(self.btn_start_alignment, "uiRole", "secondary" if applied else "primary")
        self.btn_toggle_manual_alignment.setVisible(idle)
        self.fine_adjust_group.setEnabled(idle)
        self.fine_adjust_group.setVisible(idle and self.btn_toggle_manual_alignment.isChecked())

        heading = ""
        tone = ""
        if editable and (self._auto_preview_active or self._rigid_preview_active):
            heading = tr("alignment.status.review_title")
        elif editable and applied:
            heading = tr("alignment.status.applied_title")
            tone = "success"
        elif editable and failed:
            heading = tr("alignment.status.inconclusive_title")
            tone = "warning"
        set_style_property(self.lbl_alignment_status_title, "tone", tone)
        self.lbl_alignment_status_title.setText(heading)
        self.lbl_alignment_status_title.setVisible(bool(heading))
        self._update_auto_align_availability()
        for shortcut in self._alignment_shortcuts:
            shortcut.setEnabled(editable and not pending)

    def _on_start_alignment(self) -> None:
        if self._workflow_navigation_blocked():
            return
        if self.rad_alignment_rigid.isChecked() and self._rigid_instruction_key != "alignment.status.auto_applied":
            self._on_start_rigid_region_alignment()
        else:
            self._on_auto_align()

    def _set_rigid_instruction(self, key: str | None) -> None:
        self._rigid_instruction_key = key
        self.lbl_rigid_region_instruction.setText(
            tr(key or self._idle_alignment_instruction())
        )
        self.lbl_rigid_region_instruction.setVisible(True)
        self._update_alignment_edit_availability()

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
        active = None if self._viewed_step is not None else self.stage
        if active == Stage.LOAD and not self.workflow.can_finish_images():
            active = None
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
            (Stage.LOAD, self.btn_finish_images),
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
        undo_available = (
            self.stage == Stage.ALIGNMENT
            and self._auto_alignment_undo_transform is not None
            and not self._workflow_navigation_blocked()
        )
        self.btn_undo_auto_alignment.setVisible(undo_available)
        self.btn_undo_auto_alignment.setEnabled(
            undo_available and not self.chk_lock_alignment.isChecked()
        )
        decisions = (
            self.btn_apply_alignment_suggestion,
            self.btn_rigid_apply,
            self.btn_rigid_cancel,
        )
        self._alignment_decisions.setVisible(any(not button.isHidden() for button in decisions))
        self.alignment_actions_widget.setVisible(
            any(not button.isHidden() for button in (
                *decisions, self.btn_rigid_try_again, self.btn_undo_auto_alignment
            ))
        )
        self._refresh_navigation_footer()
        self._update_alignment_edit_availability()
        self._refresh_workflow_progress()

    def _on_alignment_state_changed(self) -> None:
        if self._rigid_internal_transform_change:
            return
        if self._auto_alignment_undo_transform is not None:
            self._auto_alignment_undo_transform = None
            self._sync_alignment_transforms_to_project()
        if self._rigid_instruction_key == "alignment.status.auto_applied":
            self._set_rigid_instruction(None)
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
        self._auto_alignment_undo_transform = None
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
        self._auto_alignment_undo_transform = None
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
            self._set_rigid_instruction("alignment.rigid.failure")
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
        if restore and baseline is not None:
            self._sync_alignment_transforms_to_project()

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
        self._commit_auto_alignment()

    def _commit_auto_alignment(self, *, offer_undo: bool = False) -> None:
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
        self._auto_alignment_undo_transform = (
            self._auto_preview_baseline_dam_transform if offer_undo else None
        )
        self._invalidate_auto_alignment_suggestion()
        self.cmb_alignment_target.setCurrentIndex(0)
        self.canvas.set_alignment_target("dam")
        self._sync_alignment_transforms_to_project()
        self._refresh_summary()
        self._show_finish_alignment()
        self._set_rigid_instruction("alignment.status.auto_applied")
        logger.info(
            "Automatic alignment preview accepted: "
            "dx=%.3f dy=%.3f rotation=%.4f scale=%.6f",
            hypothesis.dx,
            hypothesis.dy,
            hypothesis.rotation_deg,
            hypothesis.scale,
        )

    def _sync_alignment_transforms_to_project(self) -> None:
        deformed = (
            self._auto_preview_baseline_dam_transform
            if self._auto_preview_active
            else None
        ) or self.canvas.get_deformed_transform()
        for target, values in (
            (self.project.ref_transform, self.canvas.get_reference_transform()),
            (self.project.dam_transform, deformed),
        ):
            target.x = values["x"]
            target.y = values["y"]
            target.scale = values["scale"]
            target.rotation_deg = values["rotation_deg"]

    def _undo_auto_alignment(self) -> None:
        baseline = self._auto_alignment_undo_transform
        if baseline is None or not self.btn_undo_auto_alignment.isEnabled():
            return
        self._auto_alignment_undo_transform = None
        self._set_canvas_alignment_transforms(None, baseline)
        self._sync_alignment_transforms_to_project()
        self._set_rigid_instruction(None)
        self._update_alignment_actions_visibility()
        self._refresh_summary()

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
            self._commit_auto_alignment(offer_undo=True)

            logger.info(
                "Auto-alignment applied: dx=%.3f dy=%.3f rotation=%.4f "
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
        self._auto_alignment_undo_transform = None
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
    def _build_calibration_panel(self) -> None:
        self.cal_group = QGroupBox()
        self.cal_group.setObjectName("calibrationPanel")
        layout = QVBoxLayout(self.cal_group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.lbl_calibration_title = QLabel()
        self.lbl_calibration_title.setObjectName("calibrationTitle")
        layout.addWidget(self.lbl_calibration_title)

        points_card = QFrame()
        distance_card = QFrame()
        self.calibration_scale_card = QFrame()
        for card in (points_card, distance_card, self.calibration_scale_card):
            card.setProperty("calibrationCard", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 11, 12, 11)
            card_layout.setSpacing(7)
            layout.addWidget(card)

        self.lbl_calibration_points_title = QLabel()
        self.lbl_calibration_distance_title = QLabel()
        self.lbl_calibration_scale_title = QLabel()
        for card, title in (
            (points_card, self.lbl_calibration_points_title),
            (distance_card, self.lbl_calibration_distance_title),
            (self.calibration_scale_card, self.lbl_calibration_scale_title),
        ):
            title.setProperty("calibrationHeading", True)
            title.setWordWrap(True)
            card.layout().addWidget(title)

        self.lbl_calibration_points_status = QLabel()
        self.lbl_calibration_points_status.setObjectName("calibrationPointsStatus")
        self.lbl_calibration_points_status.setWordWrap(True)
        points_card.layout().addWidget(self.lbl_calibration_points_status)
        self.chk_calibration_mode = QPushButton()
        self.chk_calibration_mode.setProperty("uiRole", "primary")
        self.chk_calibration_mode.setProperty("panelAction", True)
        self.chk_calibration_mode.setCheckable(True)
        points_card.layout().addWidget(self.chk_calibration_mode)

        self.lbl_px_distance = QLabel()
        self.lbl_px_distance.setWordWrap(True)
        distance_card.layout().addWidget(self.lbl_px_distance)
        self.lbl_real_distance_m = QLabel()
        self.lbl_real_distance_m.setWordWrap(True)
        distance_card.layout().addWidget(self.lbl_real_distance_m)
        self.txt_real_m = QLineEdit()
        self.txt_real_m.setObjectName("calibrationDistanceInput")
        self.lbl_real_distance_m.setBuddy(self.txt_real_m)
        distance_card.layout().addWidget(self.txt_real_m)

        self.lbl_m_per_px = QLabel()
        self.lbl_m_per_px.setObjectName("calibrationScaleValue")
        self.lbl_m_per_px.setWordWrap(True)
        self.calibration_scale_card.layout().addWidget(self.lbl_m_per_px)
        self.lbl_calibration_scale_hint = QLabel()
        self.lbl_calibration_scale_hint.setWordWrap(True)
        self.calibration_scale_card.layout().addWidget(self.lbl_calibration_scale_hint)
        self.btn_confirm_calibration = QPushButton(tr("button.confirm_calibration"))
        self._translate_calibration_panel()

    def _translate_calibration_panel(self) -> None:
        title = tr("progress.calibration")
        self.lbl_calibration_title.setText(title)
        self.cal_group.setAccessibleName(title)
        self.lbl_calibration_points_title.setText(tr("calibration.points_title"))
        self.lbl_calibration_distance_title.setText(tr("calibration.distance_title"))
        self.lbl_real_distance_m.setText(tr("label.real_distance_m"))
        self.txt_real_m.setAccessibleName(self.lbl_real_distance_m.text())
        self.txt_real_m.setPlaceholderText(tr("calibration.distance_example"))
        self.lbl_calibration_scale_hint.setText(tr("calibration.preview_hint"))

    def _retranslate_calibration_distance(self, previous_language: str) -> None:
        if self._calibration_px is None or self._m_per_px is None:
            return
        real_m = self._calibration_px * self._m_per_px
        if self.txt_real_m.text() == format_display_number(real_m, None, language=previous_language):
            with QSignalBlocker(self.txt_real_m):
                self.txt_real_m.setText(format_display_number(real_m, None))

    def _on_calibration_mode_toggled(self, checked: bool) -> None:
        if checked:
            self.canvas.clear_calibration()
            self._calibration_px = None
        self.canvas.set_calibration_mode(checked)
        self._refresh_calibration_panel()

    def _refresh_calibration_panel(self) -> None:
        has_points = self.canvas.cal_p1 is not None and self.canvas.cal_p2 is not None
        capturing = self.chk_calibration_mode.isChecked()
        if capturing:
            action = "calibration.cancel_points"
        else:
            action = "calibration.remark_points" if has_points else "calibration.mark_points"
        self.chk_calibration_mode.setText(tr(action))
        set_style_property(
            self.chk_calibration_mode, "uiRole", "secondary" if has_points or capturing else "primary"
        )
        self.lbl_calibration_points_status.setText(tr(
            "calibration.points_complete" if has_points else "calibration.points_instruction"
        ))
        set_style_property(self.lbl_calibration_points_status, "complete", has_points)
        px_value = (
            f"{format_display_number(self._calibration_px)} px"
            if has_points and self._calibration_px is not None else "—"
        )
        self.lbl_px_distance.setText(tr("calibration.distance_measured", value=px_value))

        editing = self.stage == Stage.CALIBRATION and self._viewed_step is None
        if editing:
            candidate, _ = self.meas.calibration_candidate()
            scale = (
                format_display_number(candidate, 6, significant_digits=True)
                if candidate is not None else None
            )
        elif self._m_per_px is not None:
            scale = format_display_number(self._m_per_px, 6)
        else:
            scale = None
        applied = not editing and scale is not None
        self.lbl_calibration_scale_title.setText(tr(
            "calibration.applied_scale_title" if applied else "calibration.scale_title"
        ))
        self.lbl_m_per_px.setText(f"{scale} m/px" if scale is not None else "—")
        self.lbl_calibration_scale_hint.setVisible(editing and scale is not None)
        set_style_property(self.calibration_scale_card, "hasScale", scale is not None)
        set_style_property(
            self.txt_real_m, "invalidDistance",
            editing and has_points and bool(self.txt_real_m.text().strip()) and scale is None,
        )
        self._refresh_navigation_footer()

    def _on_confirm_calibration(self) -> None:
        self.workflow.confirm_calibration()

    # ---------------- Marking: W ----------------
    def _on_set_w_mode_toggled(self, checked: bool) -> None:
        if checked and self._w_px is not None:
            answer = QMessageBox.question(
                self,
                tr("marking.remark_width"),
                tr("marking.remark_width_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.chk_set_w_mode.setChecked(False)
                return
        if checked:
            self.chk_set_guide_mode.setChecked(False)
            self.chk_measure_ci_mode.setChecked(False)
        self.canvas.set_w_measure_mode(checked)
        self._refresh_marking_panel()

    def _on_bumper_offset_changed(self, value: float) -> None:
        self.canvas.set_crossmember_offset_m(value)
        self._refresh_marking_panel()

    def _on_marking_references_toggled(self, expanded: bool) -> None:
        if not expanded:
            if self.canvas.guide_mode:
                self.workflow.reset_canvas_tools()
            else:
                self.chk_set_guide_mode.setChecked(False)
        self.marking_references.setVisible(expanded)
        self._refresh_marking_panel()

    def _refresh_marking_panel(self) -> None:
        overlay = self.canvas.get_overlay_state()
        has_width = self._w_px is not None
        capturing = self.canvas.set_w_mode
        if capturing:
            action = "marking.cancel_width"
        else:
            action = "marking.remark_width" if has_width else "marking.mark_width"
        self.chk_set_w_mode.setText(tr(action))
        set_style_property(
            self.chk_set_w_mode, "uiRole", "secondary" if has_width or capturing else "primary"
        )
        self.lbl_width_capture.setVisible(capturing)
        positions = len(self.canvas.slice_x)
        measured = sum(i in self._ci_m for i in range(1, 7))
        self.lbl_width_heading.setText(tr("marking.width"))
        self.lbl_ci_heading.setText(tr("marking.crush"))
        self.chk_measure_ci_mode.setEnabled(positions == 6)
        self.chk_set_guide_mode.setEnabled(positions == 6)
        missing = tr("marking.remark_for_positions" if has_width else "marking.no_slices")
        self.lbl_slice_status.setText(
            f"✓ {tr('marking.slice_count', count=positions, intervals=positions - 1)}"
            if positions == 6 else missing
        )
        set_style_property(self.lbl_slice_status, "complete", positions == 6)
        self.lbl_ci_progress.setText(
            f"✓ {tr('marking.ci_complete')}" if measured == 6
            else tr("marking.ci_progress", count=measured)
        )
        set_style_property(self.lbl_ci_progress, "complete", measured == 6)
        instruction = tr("marking.ci_instruction")
        if self.canvas.measure_ci_mode and positions == 6 and measured < 6:
            instruction = tr("marking.ci_mark_current", idx=self._current_ci_index)
        self.lbl_ci_instruction.setText(instruction)
        self.lbl_ci_instruction.setVisible(positions == 6)
        title = tr("marking.references")
        flags = []
        if overlay.get("guide_y") is not None:
            flags.append(tr("marking.guide_configured"))
        if overlay.get("bumper_offset_m"):
            flags.append(tr("marking.offset_configured"))
        toggle = self.btn_toggle_marking_references
        suffix = "\n" + " · ".join(flags) if flags else ""
        toggle.setText(f"{'▾' if toggle.isChecked() else '▸'} {title}{suffix}")
        toggle.setAccessibleName(f"{title}{suffix}".replace("\n", " — "))

    # ---------------- Marking: guide ----------------
    def _on_set_guide_mode_toggled(self, checked: bool) -> None:
        if checked and len(self.canvas.slice_x) != 6:
            QMessageBox.warning(
                self,
                tr("group.marking"),
                tr("marking.remark_for_positions" if self._w_px is not None else "marking.no_slices"),
            )
            self.chk_set_guide_mode.blockSignals(True)
            self.chk_set_guide_mode.setChecked(False)
            self.chk_set_guide_mode.blockSignals(False)
            return
        if checked:
            self.chk_set_w_mode.setChecked(False)
            self.chk_measure_ci_mode.setChecked(False)
        self.canvas.set_guide_mode(checked)

    # ---------------- Marking: Ci ----------------
    def _on_measure_ci_mode_toggled(self, checked: bool) -> None:
        if checked and len(self.canvas.slice_x) != 6:
            QMessageBox.warning(
                self,
                tr("group.marking"),
                tr("marking.remark_for_positions" if self._w_px is not None else "marking.no_slices"),
            )
            self.chk_measure_ci_mode.blockSignals(True)
            self.chk_measure_ci_mode.setChecked(False)
            self.chk_measure_ci_mode.blockSignals(False)
            return
        if checked:
            self.chk_set_w_mode.setChecked(False)
            self.chk_set_guide_mode.setChecked(False)
        self.canvas.set_measure_ci_mode(checked)
        self._refresh_marking_panel()

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
        self._refresh_marking_panel()

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

        self._sync_alignment_transforms_to_project()

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

    def _build_result_panel(self) -> None:
        self._summary_group = QGroupBox()
        self._summary_group.setObjectName("resultPanel")
        layout = QVBoxLayout(self._summary_group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.lbl_result_title = QLabel()
        self.lbl_result_title.setObjectName("resultTitle")
        layout.addWidget(self.lbl_result_title)

        self.lbl_result_ees_heading = QLabel()
        self.lbl_result_energy_heading = QLabel()
        self.lbl_result_measurements_heading = QLabel()
        self.lbl_result_context_heading = QLabel()
        self.lbl_result_ees_kmh = QLabel()
        self.lbl_result_ees_kmh.setObjectName("resultEesValue")
        self.lbl_result_ees_mps = QLabel()
        self.lbl_result_energy = QLabel()
        self.lbl_result_energy.setObjectName("resultEnergyValue")
        self.lbl_summary = QLabel()
        self.lbl_result_context = QLabel()
        self.lbl_result_context.setTextFormat(Qt.TextFormat.PlainText)

        for heading, values in (
            (self.lbl_result_ees_heading, (self.lbl_result_ees_kmh, self.lbl_result_ees_mps)),
            (self.lbl_result_energy_heading, (self.lbl_result_energy,)),
            (self.lbl_result_measurements_heading, (self.lbl_summary,)),
            (self.lbl_result_context_heading, (self.lbl_result_context,)),
        ):
            card = QFrame()
            card.setProperty("resultCard", True)
            if heading is self.lbl_result_ees_heading:
                card.setObjectName("resultEesCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 11, 12, 11)
            card_layout.setSpacing(5)
            heading.setProperty("resultHeading", True)
            for label in (heading, *values):
                label.setWordWrap(True)
                label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                card_layout.addWidget(label)
            layout.addWidget(card)

    def _refresh_summary(self) -> None:
        if self._viewed_step is not None:
            steps = tuple(self.workflow_step_labels)
            if steps.index(self._viewed_step) >= steps.index(self._current_workflow_step()):
                self._viewed_step = None
        self.workflow.apply_stage_gating()
        self.calc_panel.refresh_compute_action()
        self._refresh_marking_panel()
        self._refresh_workflow_progress()
        self._refresh_result_panel()

    def _refresh_result_panel(self) -> None:
        self.lbl_result_title.setText(tr("progress.result"))
        self._summary_group.setAccessibleName(self.lbl_result_title.text())
        self.lbl_result_ees_heading.setText(tr("result.ees_title"))
        self.lbl_result_energy_heading.setText(tr("result.energy_title"))
        self.lbl_result_measurements_heading.setText(tr("progress.measurement"))
        self.lbl_result_context_heading.setText(tr("result.context_title"))
        self.lbl_result_ees_kmh.setText(
            tr("result.ees_kmh", value=format_display_number(self._damage_speed_kmh))
            if self._damage_speed_kmh is not None else "—"
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
            tr("result.ees_mps", value=format_display_number(ees_mps)) if ees_mps is not None else "—"
        )
        self.lbl_result_energy.setText(
            tr("result.energy_j", value=format_display_number(self._total_energy))
            if self._total_energy is not None else "—"
        )
        measurements = [
            tr("summary.scale_not_set")
            if self._m_per_px is None
            else tr("summary.scale_value", value=format_display_number(self._m_per_px, 6))
        ]

        if self._w_px is None:
            measurements.append(tr("summary.w_not_set"))
        else:
            if self._m_per_px is None:
                measurements.append(tr("summary.w_value_px_only", px=format_display_number(self._w_px)))
            else:
                measurements.append(
                    tr(
                        "summary.w_value_full",
                        px=format_display_number(self._w_px),
                        m=format_display_number(self._w_px * self._m_per_px),
                    )
                )

        c_done = sum(1 for i in range(1, 7) if i in self._ci_m)
        measurements.append(tr("summary.c_measures", done=c_done))
        ready = self._m_per_px is not None and self._w_px is not None and c_done == 6
        if not ready:
            measurements.append(tr("summary.status_incomplete"))
        self.lbl_summary.setText("\n".join(measurements))

        context = []
        if self.project.name:
            context.append(tr("summary.project", name=self.project.name))
        if bool(self.project.ref_path) != bool(self.project.dam_path):
            context.append(tr("summary.single_image_active"))
        context.append(
            tr("summary.vehicle_mass_default")
            if self._vehicle_mass_kg is None
            else tr("summary.vehicle_mass_value", value=format_display_number(self._vehicle_mass_kg))
        )

        self.lbl_result_context.setText("\n".join(context))

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
