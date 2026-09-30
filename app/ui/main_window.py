from __future__ import annotations

from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
)

from app.ui.canvas_view import CanvasView
from app.core.project import Project, Point
from app.ui.controllers.project_io_controller import ProjectIOController
from app.ui.controllers.measurement_controller import MeasurementController
from app.ui.controllers.workflow_controller import WorkflowController
from app.ui.controllers.calc_controller import CalcController
from app.ui.widgets.calc_panel import CalcPanel
from app.report import generate_report
from app.i18n import tr, set_language, get_language


class Stage(str, Enum):
    LOAD = "load"
    ALIGNMENT = "alignment"
    CALIBRATION = "calibration"
    MARKING = "marking"
    DONE = "done"


class MainWindow(QMainWindow):
    Stage = Stage

    def __init__(self) -> None:
        super().__init__()

        set_language("pt")

        # self.setWindowTitle(tr("app.title"))
        self.resize(1280, 900)

        self.canvas = CanvasView()
        self.setCentralWidget(self.canvas)

        self.project = Project(name="")
        self._current_project_path: str | None = None
        self._update_window_title()

        self.stage: Stage = Stage.LOAD

        self._calibration_px: float | None = None
        self._m_per_px: float | None = None

        self._w_px: float | None = None
        self._w_m: float | None = None
        self._delta_w_px: float | None = None
        self._delta_w_m: float | None = None

        self._ci_px: dict[int, float] = {}
        self._ci_m: dict[int, float] = {}
        self._current_ci_index: int = 1

        self._total_energy: float | None = None
        self._vehicle_mass_kg: float | None = None
        self._damage_speed_mps: float | None = None
        self._damage_speed_kmh: float | None = None

        self.btn_restart_alignment: QPushButton
        self.btn_restart_calibration: QPushButton
        self.btn_restart_marking: QPushButton

        self.io = ProjectIOController(self)
        self.meas = MeasurementController(self)
        self.workflow = WorkflowController(self)
        self.calc = CalcController(self)

        self._build_menu()
        self._build_dock()
        self._apply_styles()
        self._build_shortcuts()

        self.canvas.calibration_px_measured.connect(
            self.meas.on_calibration_px_measured
        )
        self.canvas.w_px_measured.connect(self.meas.on_w_px_measured)
        self.canvas.w_cleared.connect(self.meas.on_w_cleared)
        self.canvas.ci_measured.connect(self.meas.on_ci_measured)

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
        act_export_report = file_menu.addAction(tr("menu.export_report"))

        lang_menu = m.addMenu(tr("menu.language"))
        act_lang_en = lang_menu.addAction(tr("menu.language.english"))
        act_lang_pt = lang_menu.addAction(tr("menu.language.portuguese"))

        act_new.triggered.connect(self._on_new_project)
        act_save.triggered.connect(self._on_save_project)
        act_load.triggered.connect(self._on_load_project)
        act_export.triggered.connect(self._on_export_png)
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

    def _build_dock(self) -> None:
        dock = QDockWidget(tr("dock.controls"), self)
        self._controls_dock = dock
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)

        # --- Load images ---
        self.load_group = QGroupBox(tr("group.load_images"))
        load_layout = QVBoxLayout(self.load_group)
        self.btn_load_ref = QPushButton(tr("button.load_ref"))
        self.btn_load_dam = QPushButton(tr("button.load_dam"))
        load_layout.addWidget(self.btn_load_ref)
        load_layout.addWidget(self.btn_load_dam)
        dock_layout.addWidget(self.load_group)

        self.lbl_overlay_opacity = QLabel(tr("label.overlay_opacity"))
        dock_layout.addWidget(self.lbl_overlay_opacity)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        dock_layout.addWidget(self.opacity_slider)

        # --- Alignment group ---
        self.align_group = QGroupBox(tr("group.alignment"))
        align_layout = QVBoxLayout(self.align_group)

        self.chk_alignment_mode = QCheckBox(tr("check.alignment_mode"))
        self.chk_lock_alignment = QCheckBox(tr("check.lock_alignment"))
        align_layout.addWidget(self.chk_alignment_mode)
        align_layout.addWidget(self.chk_lock_alignment)

        row_target = QHBoxLayout()
        self.lbl_editable_image = QLabel(tr("label.editable_image"))
        row_target.addWidget(self.lbl_editable_image)

        self.cmb_alignment_target = QComboBox()
        self.cmb_alignment_target.addItem(tr("combo.deformed"), "dam")
        self.cmb_alignment_target.addItem(tr("combo.reference"), "ref")
        self.canvas.set_alignment_target("dam")
        row_target.addWidget(self.cmb_alignment_target)

        align_layout.addLayout(row_target)

        self.btn_reset_alignment = QPushButton(tr("button.reset_selected_transform"))
        align_layout.addWidget(self.btn_reset_alignment)

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

        align_layout.addWidget(self.nudge_box)

        self.rotate_box = QGroupBox(tr("group.rotate"))
        rotate_layout = QHBoxLayout(self.rotate_box)

        self.btn_rotate_minus = QPushButton(tr("button.rotate_minus"))
        self.btn_rotate_plus = QPushButton(tr("button.rotate_plus"))

        rotate_layout.addWidget(self.btn_rotate_minus)
        rotate_layout.addWidget(self.btn_rotate_plus)

        self.lbl_step_deg = QLabel(tr("label.step_deg"))
        rotate_layout.addWidget(self.lbl_step_deg)
        self.spn_rotate_step = QDoubleSpinBox()
        self.spn_rotate_step.setDecimals(2)
        self.spn_rotate_step.setRange(0.01, 360.0)
        self.spn_rotate_step.setSingleStep(0.1)
        self.spn_rotate_step.setValue(1.0)
        rotate_layout.addWidget(self.spn_rotate_step)

        align_layout.addWidget(self.rotate_box)

        self.scale_box = QGroupBox(tr("group.scale"))
        scale_layout = QHBoxLayout(self.scale_box)

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

        scale_layout.addWidget(self.btn_scale_minus)
        scale_layout.addWidget(self.btn_scale_plus)

        self.lbl_step_pct = QLabel(tr("label.step_pct"))
        scale_layout.addWidget(self.lbl_step_pct)
        self.spn_scale_step = QDoubleSpinBox()
        self.spn_scale_step.setDecimals(2)
        self.spn_scale_step.setRange(0.01, 50.0)
        self.spn_scale_step.setSingleStep(0.1)
        self.spn_scale_step.setValue(1.0)
        scale_layout.addWidget(self.spn_scale_step)

        align_layout.addWidget(self.scale_box)

        self.lbl_alignment_shortcuts = QLabel(tr("label.alignment_shortcuts"))
        self.lbl_alignment_shortcuts.setWordWrap(True)
        align_layout.addWidget(self.lbl_alignment_shortcuts)

        self.btn_finish_alignment = QPushButton(tr("button.finish_alignment"))
        align_layout.addWidget(self.btn_finish_alignment)

        dock_layout.addWidget(self.align_group)

        # --- Calibration group ---
        self.cal_group = QGroupBox(tr("group.calibration"))
        cal_layout = QVBoxLayout(self.cal_group)

        self.chk_calibration_mode = QCheckBox(tr("check.calibration_mode"))
        cal_layout.addWidget(self.chk_calibration_mode)

        self.lbl_px_distance = QLabel(tr("label.measured_distance"))
        cal_layout.addWidget(self.lbl_px_distance)

        row_real = QHBoxLayout()
        self.lbl_real_distance_m = QLabel(tr("label.real_distance_m"))
        row_real.addWidget(self.lbl_real_distance_m)
        self.txt_real_m = QLineEdit()
        self.txt_real_m.setPlaceholderText("e.g., 1.0")
        row_real.addWidget(self.txt_real_m)
        cal_layout.addLayout(row_real)

        self.btn_apply_calibration = QPushButton(tr("button.apply_calibration"))
        cal_layout.addWidget(self.btn_apply_calibration)

        self.lbl_m_per_px = QLabel(tr("label.scale_m_per_px"))
        cal_layout.addWidget(self.lbl_m_per_px)

        self.btn_confirm_calibration = QPushButton(tr("button.confirm_calibration"))
        cal_layout.addWidget(self.btn_confirm_calibration)

        dock_layout.addWidget(self.cal_group)

        # --- Marking group ---
        self.mark_group = QGroupBox(tr("group.marking"))
        mark_layout = QVBoxLayout(self.mark_group)

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
        mark_layout.addWidget(self.btn_finish_marking)

        dock_layout.addWidget(self.mark_group)

        # --- Workflow group ---
        self.workflow_group = QGroupBox(tr("group.workflow"))
        workflow_layout = QVBoxLayout(self.workflow_group)

        self.btn_restart_alignment = QPushButton(tr("button.restart_alignment"))
        workflow_layout.addWidget(self.btn_restart_alignment)

        self.btn_restart_calibration = QPushButton(tr("button.restart_calibration"))
        workflow_layout.addWidget(self.btn_restart_calibration)

        self.btn_restart_marking = QPushButton(tr("button.restart_marking"))
        workflow_layout.addWidget(self.btn_restart_marking)

        dock_layout.addWidget(self.workflow_group)

        # --- Calc panel ---
        self.calc_panel = CalcPanel(self)
        dock_layout.addWidget(self.calc_panel)

        # --- Summary ---
        summary_group = QGroupBox(tr("group.summary"))
        self._summary_group = summary_group
        summary_layout = QVBoxLayout(summary_group)
        self.lbl_summary = QLabel(tr("summary.status_default"))
        self.lbl_summary.setWordWrap(True)
        summary_layout.addWidget(self.lbl_summary)
        dock_layout.addWidget(summary_group)

        dock_layout.addStretch(1)

        scroll.setWidget(dock_widget)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.btn_load_ref.clicked.connect(self._on_load_ref)
        self.btn_load_dam.clicked.connect(self._on_load_dam)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        self.chk_alignment_mode.toggled.connect(self._on_alignment_mode_toggled)
        self.chk_lock_alignment.toggled.connect(self._on_lock_alignment_toggled)
        self.btn_reset_alignment.clicked.connect(self._on_reset_alignment)

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
        self.btn_restart_alignment.clicked.connect(self._on_restart_alignment)
        self.btn_restart_calibration.clicked.connect(self._on_restart_calibration)
        self.btn_restart_marking.clicked.connect(self._on_restart_marking)

        self.chk_calibration_mode.toggled.connect(self._on_calibration_mode_toggled)
        self.btn_apply_calibration.clicked.connect(self._on_apply_calibration)
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

        self.load_group.setTitle(tr("group.load_images"))
        self.btn_load_ref.setText(tr("button.load_ref"))
        self.btn_load_dam.setText(tr("button.load_dam"))
        self.lbl_overlay_opacity.setText(tr("label.overlay_opacity"))

        self.align_group.setTitle(tr("group.alignment"))
        self.nudge_box.setTitle(tr("group.nudge"))
        self.rotate_box.setTitle(tr("group.rotate"))
        self.scale_box.setTitle(tr("group.scale"))
        self.chk_alignment_mode.setText(tr("check.alignment_mode"))
        self.chk_lock_alignment.setText(tr("check.lock_alignment"))
        self.lbl_editable_image.setText(tr("label.editable_image"))
        self.cmb_alignment_target.setItemText(0, tr("combo.deformed"))
        self.cmb_alignment_target.setItemText(1, tr("combo.reference"))
        self.btn_reset_alignment.setText(tr("button.reset_selected_transform"))
        self.btn_rotate_minus.setText(tr("button.rotate_minus"))
        self.btn_rotate_plus.setText(tr("button.rotate_plus"))
        self.lbl_step_deg.setText(tr("label.step_deg"))
        self.btn_scale_minus.setText(tr("button.scale_minus"))
        self.btn_scale_plus.setText(tr("button.scale_plus"))
        self.lbl_step_pct.setText(tr("label.step_pct"))
        self.lbl_alignment_shortcuts.setText(tr("label.alignment_shortcuts"))
        self.btn_finish_alignment.setText(tr("button.finish_alignment"))

        self.cal_group.setTitle(tr("group.calibration"))
        self.chk_calibration_mode.setText(tr("check.calibration_mode"))
        self.lbl_real_distance_m.setText(tr("label.real_distance_m"))
        self.btn_apply_calibration.setText(tr("button.apply_calibration"))
        self.btn_confirm_calibration.setText(tr("button.confirm_calibration"))

        self.mark_group.setTitle(tr("group.marking"))
        self.ci_select_box.setTitle(tr("group.select_c"))
        self.chk_set_w_mode.setText(tr("check.set_w_mode"))
        self.btn_generate_slices.setText(tr("button.generate_slices"))
        self.chk_set_guide_mode.setText(tr("check.set_guide_mode"))
        self.lbl_bumper_offset.setText(tr("label.bumper_offset_m"))
        self.chk_measure_ci_mode.setText(tr("check.measure_ci_mode"))
        self._update_ci_label()
        self.btn_finish_marking.setText(tr("button.finish_marking"))
        if not self._ci_m:
            self.lbl_ci_values.setText(tr("label.c_values_default"))

        self.workflow_group.setTitle(tr("group.workflow"))
        self.btn_restart_alignment.setText(tr("button.restart_alignment"))
        self.btn_restart_calibration.setText(tr("button.restart_calibration"))
        self.btn_restart_marking.setText(tr("button.restart_marking"))

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
    def _on_load_ref(self) -> None:
        self.io.load_ref()

    def _on_load_dam(self) -> None:
        self.io.load_dam()

    # ---------------- Opacity ----------------
    def _on_opacity_changed(self, value: int) -> None:
        self.canvas.set_deformed_opacity(value / 100.0)
        self.project.opacity = value / 100.0
        self._refresh_summary()

    # ---------------- Alignment ----------------
    def _on_alignment_mode_toggled(self, checked: bool) -> None:
        self.canvas.set_alignment_mode(checked)

    def _on_lock_alignment_toggled(self, checked: bool) -> None:
        self.canvas.set_alignment_locked(checked)

    def _on_alignment_target_changed(self) -> None:
        target = self.cmb_alignment_target.currentData()
        if target:
            self.canvas.set_alignment_target(target)

    def _on_reset_alignment(self) -> None:
        self.canvas.reset_all_transforms()

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
        self.workflow.finish_alignment()

    def _on_restart_alignment(self) -> None:
        self.workflow.restart_from_alignment()

    def _on_restart_calibration(self) -> None:
        self.workflow.restart_from_calibration()

    def _on_restart_marking(self) -> None:
        self.workflow.restart_from_marking()

        self._current_ci_index = 1
        self._sync_ci_radio_buttons()
        self._update_ci_label()
        self.canvas.set_ci_index(1)

        self.chk_measure_ci_mode.blockSignals(True)
        self.chk_measure_ci_mode.setChecked(False)
        self.chk_measure_ci_mode.blockSignals(False)
        self.canvas.set_measure_ci_mode(False)

    # ---------------- Calibration ----------------
    def _on_calibration_mode_toggled(self, checked: bool) -> None:
        self.canvas.set_calibration_mode(checked)
        if checked:
            self._calibration_px = None
            self.lbl_px_distance.setText(tr("label.measured_distance"))

    def _on_apply_calibration(self) -> None:
        if not self._warn_if_alignment_scales_differ():
            return
        self.meas.apply_calibration()

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
            tr("summary.total_energy_default")
            if self._total_energy is None
            else tr("summary.total_energy_value", value=f"{self._total_energy:.2f}")
        )

        parts.append(
            tr("summary.vehicle_mass_default")
            if self._vehicle_mass_kg is None
            else tr("summary.vehicle_mass_value", value=f"{self._vehicle_mass_kg:.2f}")
        )

        parts.append(
            tr("summary.damage_speed_default")
            if self._damage_speed_kmh is None
            else tr("summary.damage_speed_value", value=f"{self._damage_speed_kmh:.2f}")
        )

        ready = (
            (self._m_per_px is not None) and (self._w_px is not None) and (c_done == 6)
        )
        parts.append(
            tr("summary.status_complete") if ready else tr("summary.status_incomplete")
        )

        self.lbl_summary.setText("\n".join(parts))

    def _warn_if_alignment_scales_differ(self) -> bool:
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
