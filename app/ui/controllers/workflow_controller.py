from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QMessageBox

from app.i18n import tr

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow, Stage


class WorkflowController:
    def __init__(self, host: "MainWindow") -> None:
        self.host = host

    def set_stage(self, stage: "Stage") -> None:
        self.host.stage = stage
        self.apply_stage_gating()
        self.host._refresh_summary()

    def determine_stage_from_project(self):
        Stage = self.host.Stage  # type: ignore[attr-defined]
        p = self.host.project

        has_images = bool(p.ref_path or p.dam_path)
        if not has_images:
            return Stage.LOAD
        if p.m_per_px is None:
            return Stage.ALIGNMENT

        if p.w_px is None:
            return Stage.CALIBRATION

        c_count = 0
        if p.c_m:
            c_count = sum(1 for i in range(1, 7) if f"C{i}" in p.c_m)

        if c_count < 6:
            return Stage.MARKING
        return Stage.DONE

    def sync_stage_after_load(self) -> None:
        stage = self.determine_stage_from_project()
        self.host.canvas.reset_interaction()
        for checkbox in (
            self.host.chk_alignment_mode,
            self.host.chk_calibration_mode,
            self.host.chk_set_w_mode,
            self.host.chk_set_guide_mode,
            self.host.chk_measure_ci_mode,
        ):
            with QSignalBlocker(checkbox):
                checkbox.setChecked(False)
        self.host._current_ci_index = 1
        self.host._sync_ci_radio_buttons()
        self.host._update_ci_label()
        locked = stage != self.host.Stage.ALIGNMENT
        self.host.canvas.set_alignment_locked(locked)
        with QSignalBlocker(self.host.chk_lock_alignment):
            self.host.chk_lock_alignment.setChecked(locked)
        self.set_stage(stage)

    def _enable_restart_buttons(
        self, alignment: bool, calibration: bool, marking: bool
    ) -> None:
        self.host.btn_restart_alignment.setEnabled(alignment)
        self.host.btn_restart_calibration.setEnabled(calibration)
        self.host.btn_restart_marking.setEnabled(marking)

    def apply_stage_gating(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]

        if self.host.stage == Stage.LOAD:
            self.host.align_group.setEnabled(False)
            self.host.cal_group.setEnabled(False)
            self.host.mark_group.setEnabled(False)
            self.host.calc_panel.setEnabled(False)
            self._enable_restart_buttons(False, False, False)
            return

        if self.host.stage == Stage.ALIGNMENT:
            self.host.align_group.setEnabled(True)
            self.host.cal_group.setEnabled(False)
            self.host.mark_group.setEnabled(False)
            self.host.calc_panel.setEnabled(False)
            self._enable_restart_buttons(False, False, False)
            return

        if self.host.stage == Stage.CALIBRATION:
            self.host.align_group.setEnabled(False)
            self.host.cal_group.setEnabled(True)
            self.host.mark_group.setEnabled(False)
            self.host.calc_panel.setEnabled(False)
            self._enable_restart_buttons(True, False, False)
            return

        if self.host.stage == Stage.MARKING:
            self.host.align_group.setEnabled(False)
            self.host.cal_group.setEnabled(False)
            self.host.mark_group.setEnabled(True)
            self.host.calc_panel.setEnabled(False)
            self._enable_restart_buttons(True, True, False)
            return

        if self.host.stage == Stage.DONE:
            self.host.align_group.setEnabled(False)
            self.host.cal_group.setEnabled(False)
            self.host.mark_group.setEnabled(False)
            self.host.calc_panel.setEnabled(True)
            self._enable_restart_buttons(True, True, True)
            return

    def invalidate_energy(self) -> None:
        self.host._total_energy = None
        self.host.project.total_energy_j = None

        if hasattr(self.host, "calc_panel"):
            self.host.calc_panel.lbl_energy.setText(tr("calc.total_energy_default"))

        self.invalidate_speed()

    def invalidate_speed(self) -> None:
        self.host._damage_speed_mps = None
        self.host._damage_speed_kmh = None
        self.host.project.damage_speed_mps = None
        self.host.project.damage_speed_kmh = None

        if hasattr(self.host, "calc_panel"):
            self.host.calc_panel.lbl_speed.setText(tr("calc.damage_speed_default"))

        self.host._refresh_summary()

    def invalidate_from_marking(self) -> None:
        self.host._current_ci_index = 1
        if hasattr(self.host, "_sync_ci_radio_buttons"):
            self.host._sync_ci_radio_buttons()

        self.host.meas.refresh_w_labels()
        self.host.meas.update_ci_values_label()
        self.host._update_ci_label()
        self.host.canvas.set_ci_index(1)

        self.invalidate_energy()

        self.host.canvas.set_w_measure_mode(False)
        self.host.canvas.set_measure_ci_mode(False)

        self.host.chk_set_w_mode.blockSignals(True)
        self.host.chk_set_w_mode.setChecked(False)
        self.host.chk_set_w_mode.blockSignals(False)

        self.host.chk_measure_ci_mode.blockSignals(True)
        self.host.chk_measure_ci_mode.setChecked(False)
        self.host.chk_measure_ci_mode.blockSignals(False)

        self.set_stage(self.host.Stage.MARKING)  # type: ignore[attr-defined]

    def invalidate_from_calibration(self) -> None:
        self.host.canvas.clear_calibration()
        self.host.canvas.clear_markings()

        self.host._calibration_px = None
        self.host._m_per_px = None

        self.host._w_px = None
        self.host._w_m = None
        self.host._delta_w_px = None
        self.host._delta_w_m = None

        self.host._ci_px.clear()
        self.host._ci_m.clear()
        self.host._current_ci_index = 1
        if hasattr(self.host, "_sync_ci_radio_buttons"):
            self.host._sync_ci_radio_buttons()

        self.host.project.m_per_px = None
        self.host.project.cal_p1 = None
        self.host.project.cal_p2 = None

        self.host.project.w_px = None
        self.host.project.w_m = None
        self.host.project.delta_w_px = None
        self.host.project.delta_w_m = None
        self.host.project.w_p1 = None
        self.host.project.w_p2 = None
        self.host.project.slice_x = None

        self.host.project.c_px = None
        self.host.project.c_m = None
        self.host.project.c_points = None

        self.host.lbl_px_distance.setText(tr("label.measured_distance"))
        self.host.lbl_m_per_px.setText(tr("label.scale_m_per_px"))
        self.host.meas.refresh_w_labels()
        self.host.meas.update_ci_values_label()
        self.host._update_ci_label()

        self.host.canvas.set_w_measure_mode(False)
        self.host.canvas.set_guide_mode(False)
        self.host.canvas.set_measure_ci_mode(False)

        self.host.chk_set_w_mode.blockSignals(True)
        self.host.chk_set_w_mode.setChecked(False)
        self.host.chk_set_w_mode.blockSignals(False)

        self.host.chk_set_guide_mode.blockSignals(True)
        self.host.chk_set_guide_mode.setChecked(False)
        self.host.chk_set_guide_mode.blockSignals(False)

        self.host.chk_measure_ci_mode.blockSignals(True)
        self.host.chk_measure_ci_mode.setChecked(False)
        self.host.chk_measure_ci_mode.blockSignals(False)

        self.invalidate_energy()
        self.set_stage(self.host.Stage.CALIBRATION)  # type: ignore[attr-defined]

    def invalidate_from_alignment(self) -> None:
        self.host.canvas.reset_alignment_visual()

        self.host._calibration_px = None
        self.host._m_per_px = None

        self.host._w_px = None
        self.host._w_m = None
        self.host._delta_w_px = None
        self.host._delta_w_m = None

        self.host._ci_px.clear()
        self.host._ci_m.clear()
        self.host._current_ci_index = 1
        if hasattr(self.host, "_sync_ci_radio_buttons"):
            self.host._sync_ci_radio_buttons()

        self.host.project.m_per_px = None
        self.host.project.cal_p1 = None
        self.host.project.cal_p2 = None

        self.host.project.w_px = None
        self.host.project.w_m = None
        self.host.project.delta_w_px = None
        self.host.project.delta_w_m = None
        self.host.project.w_p1 = None
        self.host.project.w_p2 = None
        self.host.project.slice_x = None

        self.host.project.c_px = None
        self.host.project.c_m = None
        self.host.project.c_points = None

        self.host.project.ref_transform.x = 0.0
        self.host.project.ref_transform.y = 0.0
        self.host.project.ref_transform.scale = 1.0
        self.host.project.ref_transform.rotation_deg = 0.0

        self.host.project.dam_transform.x = 0.0
        self.host.project.dam_transform.y = 0.0
        self.host.project.dam_transform.scale = 1.0
        self.host.project.dam_transform.rotation_deg = 0.0

        self.host.lbl_px_distance.setText(tr("label.measured_distance"))
        self.host.lbl_m_per_px.setText(tr("label.scale_m_per_px"))
        self.host.meas.refresh_w_labels()
        self.host.meas.update_ci_values_label()
        self.host._update_ci_label()

        self.host.canvas.set_alignment_locked(False)
        self.host.chk_lock_alignment.setChecked(False)
        self.host.chk_alignment_mode.setChecked(False)
        self.host.canvas.set_alignment_mode(False)

        if hasattr(self.host, "cmb_alignment_target"):
            self.host.cmb_alignment_target.blockSignals(True)
            self.host.cmb_alignment_target.setCurrentIndex(0)
            self.host.cmb_alignment_target.blockSignals(False)
            self.host.canvas.set_alignment_target("dam")

        self.host.canvas.set_w_measure_mode(False)
        self.host.canvas.set_guide_mode(False)
        self.host.canvas.set_measure_ci_mode(False)

        self.host.chk_set_w_mode.blockSignals(True)
        self.host.chk_set_w_mode.setChecked(False)
        self.host.chk_set_w_mode.blockSignals(False)

        self.host.chk_set_guide_mode.blockSignals(True)
        self.host.chk_set_guide_mode.setChecked(False)
        self.host.chk_set_guide_mode.blockSignals(False)

        self.host.chk_measure_ci_mode.blockSignals(True)
        self.host.chk_measure_ci_mode.setChecked(False)
        self.host.chk_measure_ci_mode.blockSignals(False)

        self.invalidate_energy()
        self.set_stage(self.host.Stage.ALIGNMENT)  # type: ignore[attr-defined]

    def restart_from_alignment(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]
        if self.host.stage in (Stage.CALIBRATION, Stage.MARKING, Stage.DONE):
            self.invalidate_from_alignment()

    def restart_from_calibration(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]
        if self.host.stage in (Stage.MARKING, Stage.DONE):
            self.invalidate_from_calibration()

    def restart_from_marking(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]
        if self.host.stage == Stage.DONE:
            self.invalidate_from_marking()

    def finish_alignment(self) -> None:
        Stage = self.host.Stage
        if self.host.stage != Stage.ALIGNMENT:
            return

        has_ref = self.host.project.ref_path is not None
        has_dam = self.host.project.dam_path is not None

        if not (has_ref and has_dam):
            answer = QMessageBox.question(
                self.host,
                tr("alignment.single_image.title"),
                tr("alignment.single_image.confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.host.canvas.set_alignment_mode(False)
        self.host.canvas.set_alignment_locked(True)
        self.host.chk_alignment_mode.setChecked(False)
        self.host.chk_lock_alignment.setChecked(True)

        self.set_stage(Stage.CALIBRATION)

    def confirm_calibration(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]
        if self.host.stage != Stage.CALIBRATION:
            return

        if self.host._m_per_px is None:
            QMessageBox.warning(
                self.host,
                tr("group.calibration"),
                tr("workflow.error.apply_calibration_first"),
            )
            return

        self.host.canvas.set_calibration_mode(False)
        self.host.chk_calibration_mode.setChecked(False)

        self.set_stage(Stage.MARKING)

    def finish_marking(self) -> None:
        Stage = self.host.Stage  # type: ignore[attr-defined]
        if self.host.stage != Stage.MARKING:
            return

        c_done = sum(1 for i in range(1, 7) if i in self.host._ci_m)

        if self.host._w_px is None or self.host._m_per_px is None or c_done != 6:
            QMessageBox.warning(
                self.host,
                tr("group.marking"),
                tr("workflow.error.incomplete_marking"),
            )
            return

        self.set_stage(Stage.DONE)
