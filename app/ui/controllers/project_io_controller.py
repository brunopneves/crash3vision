from __future__ import annotations

import math
import json
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from app.core.project import Project, UnsupportedCrash3UnitsError
from app.i18n import tr

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


class ProjectIOController:
    def __init__(self, host: "MainWindow") -> None:
        self.host = host

    def new_project(self) -> None:
        name, ok = QInputDialog.getText(
            self.host,
            tr("project.new.dialog_title"),
            tr("project.new.prompt_name"),
        )
        if not ok:
            return

        self.host.project = Project(name=name or "")
        self.host._update_window_title()
        self.host._current_project_path = None
        self.host.stage = self.host.Stage.LOAD  # type: ignore[attr-defined]

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

        self.host._total_energy = None
        self.host._vehicle_mass_kg = None
        self.host._damage_speed_mps = None
        self.host._damage_speed_kmh = None

        self.host.lbl_px_distance.setText(tr("label.measured_distance"))
        self.host.lbl_m_per_px.setText(tr("label.scale_m_per_px"))
        self.host.lbl_w.setText(tr("label.w_default"))
        self.host.lbl_delta_w.setText(tr("label.delta_w_default"))
        if hasattr(self.host, "spn_bumper_offset"):
            self.host.spn_bumper_offset.blockSignals(True)
            self.host.spn_bumper_offset.setValue(0.0)
            self.host.spn_bumper_offset.blockSignals(False)
        self.host.meas.update_ci_values_label()
        self.host._update_ci_label()

        self.host.canvas.clear_images()
        self.host.canvas.set_alignment_target("dam")

        if hasattr(self.host, "cmb_alignment_target"):
            self.host.cmb_alignment_target.blockSignals(True)
            self.host.cmb_alignment_target.setCurrentIndex(0)
            self.host.cmb_alignment_target.blockSignals(False)

        if hasattr(self.host, "calc_panel"):
            self.host.calc_panel.lbl_energy.setText(tr("calc.total_energy_default"))
            self.host.calc_panel.lbl_speed.setText(tr("calc.damage_speed_default"))
            self.host.calc_panel.txt_vehicle_mass.setText("")
            self.host.calc_panel.txt_A.setText("")
            self.host.calc_panel.txt_B.setText("")
            self.host.calc_panel.cmb_class.blockSignals(True)
            self.host.calc_panel.cmb_class.setCurrentIndex(0)
            self.host.calc_panel.cmb_class.blockSignals(False)
            self.host.calc_panel.txt_A.setReadOnly(False)
            self.host.calc_panel.txt_B.setReadOnly(False)
            self.host.calc_panel.txt_alpha_deg.setText("0.0")
            self.host.calc_panel._refresh_ab_source_ui()

        self.host.workflow.apply_stage_gating()
        self.host._refresh_summary()

        QMessageBox.information(
            self.host,
            tr("project.new.dialog_title"),
            tr("project.new.created", name=self.host.project.name),
        )

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self.host,
            tr("project.save.dialog_title"),
            "",
            "Project (*.json)",
        )
        if not path:
            return

        self.host._sync_ui_to_project()
        self.host.project.name = Path(path).stem
        self.host._update_window_title()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.host.project.to_dict(), f, ensure_ascii=False, indent=2)

        self.host._current_project_path = path
        self.host._refresh_summary()
        QMessageBox.information(
            self.host,
            tr("project.save.dialog_title"),
            tr("dialog.saved", path=path),
        )

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.host,
            tr("project.load.dialog_title"),
            "",
            "Project (*.json)",
        )
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            project = Project.from_dict(data)
        except UnsupportedCrash3UnitsError as e:
            QMessageBox.warning(
                self.host,
                tr("project.load.dialog_title"),
                tr("project.load.unsupported_crash3_units", units=repr(e.units)),
            )
            return

        prepared_images = {}
        for slot, image_path in (("ref", project.ref_path), ("dam", project.dam_path)):
            if image_path:
                pixmap = QPixmap(image_path)
                if pixmap.isNull():
                    QMessageBox.warning(
                        self.host,
                        tr("project.load.dialog_title"),
                        tr("project.load.images_failed", error=image_path),
                    )
                    return
                prepared_images[slot] = pixmap

        self.host.project = project
        self.host._update_window_title()
        self.host._current_project_path = path

        self.host._total_energy = self.host.project.total_energy_j
        self.host._vehicle_mass_kg = self.host.project.vehicle_mass_kg
        self.host._damage_speed_mps = self.host.project.damage_speed_mps
        self.host._damage_speed_kmh = self.host.project.damage_speed_kmh

        self.host.canvas.clear_images()
        if "ref" in prepared_images:
            self.host.canvas.load_reference(prepared_images["ref"])
        if "dam" in prepared_images:
            self.host.canvas.load_deformed(prepared_images["dam"])
            self.host.canvas.set_deformed_opacity(self.host.project.opacity)

        ref_tr = self.host.project.ref_transform
        self.host.canvas.set_reference_transform(
            ref_tr.x, ref_tr.y, ref_tr.scale, ref_tr.rotation_deg
        )

        dam_tr = self.host.project.dam_transform
        self.host.canvas.set_deformed_transform(
            dam_tr.x, dam_tr.y, dam_tr.scale, dam_tr.rotation_deg
        )

        self.host.opacity_slider.blockSignals(True)
        self.host.opacity_slider.setValue(int(self.host.project.opacity * 100))
        self.host.opacity_slider.blockSignals(False)

        self.host._m_per_px = self.host.project.m_per_px
        if self.host._m_per_px is not None:
            self.host.canvas.apply_scale(self.host._m_per_px)
            self.host.lbl_m_per_px.setText(
                tr("measurement.scale_value", value=f"{self.host._m_per_px:.6f}")
            )
        else:
            self.host.lbl_m_per_px.setText(tr("label.scale_m_per_px"))

        if (
            self.host.project.cal_p1 is not None
            and self.host.project.cal_p2 is not None
        ):
            x1 = float(self.host.project.cal_p1.x)
            y1 = float(self.host.project.cal_p1.y)
            x2 = float(self.host.project.cal_p2.x)
            y2 = float(self.host.project.cal_p2.y)

            self.host._calibration_px = math.hypot(x2 - x1, y2 - y1)
            self.host.lbl_px_distance.setText(
                tr(
                    "measurement.measured_distance_value",
                    value=f"{self.host._calibration_px:.2f}",
                )
            )

            if self.host._m_per_px is not None:
                real_m = self.host._calibration_px * self.host._m_per_px
                self.host.txt_real_m.setText(f"{real_m:.3f}")
            else:
                self.host.txt_real_m.setText("")
        else:
            self.host._calibration_px = None
            self.host.lbl_px_distance.setText(tr("label.measured_distance"))
            self.host.txt_real_m.setText("")

        self.host._w_px = self.host.project.w_px
        self.host._w_m = self.host.project.w_m

        self.host._delta_w_px = (
            float(self.host._w_px) / 5.0 if self.host._w_px is not None else None
        )
        self.host._delta_w_m = (
            float(self.host._w_m) / 5.0 if self.host._w_m is not None else None
        )

        self.host.project.delta_w_px = self.host._delta_w_px
        self.host.project.delta_w_m = self.host._delta_w_m

        self.host.meas.refresh_w_labels()

        self.host._ci_px.clear()
        self.host._ci_m.clear()

        if self.host.project.c_px:
            for k, v in self.host.project.c_px.items():
                idx = int(k.replace("C", ""))
                self.host._ci_px[idx] = float(v)

        if self.host.project.c_m:
            for k, v in self.host.project.c_m.items():
                idx = int(k.replace("C", ""))
                self.host._ci_m[idx] = float(v)

        self.host._current_ci_index = 1
        if hasattr(self.host, "_sync_ci_radio_buttons"):
            self.host._sync_ci_radio_buttons()
        self.host._update_ci_label()
        self.host.canvas.set_ci_index(1)

        self.host.meas.update_ci_values_label()

        overlay_state = {
            "cal_p1": (
                None
                if self.host.project.cal_p1 is None
                else {"x": self.host.project.cal_p1.x, "y": self.host.project.cal_p1.y}
            ),
            "cal_p2": (
                None
                if self.host.project.cal_p2 is None
                else {"x": self.host.project.cal_p2.x, "y": self.host.project.cal_p2.y}
            ),
            "w_p1": (
                None
                if self.host.project.w_p1 is None
                else {"x": self.host.project.w_p1.x, "y": self.host.project.w_p1.y}
            ),
            "w_p2": (
                None
                if self.host.project.w_p2 is None
                else {"x": self.host.project.w_p2.x, "y": self.host.project.w_p2.y}
            ),
            "slice_x": self.host.project.slice_x,
            "guide_y": self.host.project.guide_y,
            "bumper_offset_m": self.host.project.bumper_offset_m,
            "bumper_offset_px": self.host.project.bumper_offset_px,
            "crossmember_y": self.host.project.crossmember_y,
            "c_points": None,
            "m_per_px": self.host.project.m_per_px,
        }

        if self.host.project.c_points:
            overlay_state["c_points"] = {
                ck: {
                    "ref": {"x": vv["ref"].x, "y": vv["ref"].y},
                    "def": {"x": vv["def"].x, "y": vv["def"].y},
                }
                for ck, vv in self.host.project.c_points.items()
            }

        self.host.canvas.restore_overlay_state(overlay_state)

        if hasattr(self.host, "spn_bumper_offset"):
            self.host.spn_bumper_offset.blockSignals(True)
            self.host.spn_bumper_offset.setValue(
                0.0
                if self.host.project.bumper_offset_m is None
                else float(self.host.project.bumper_offset_m)
            )
            self.host.spn_bumper_offset.blockSignals(False)

        if self.host._m_per_px is not None:
            self.host.canvas.apply_scale(self.host._m_per_px)

        if hasattr(self.host, "cmb_alignment_target"):
            self.host.cmb_alignment_target.blockSignals(True)
            self.host.cmb_alignment_target.setCurrentIndex(0)
            self.host.cmb_alignment_target.blockSignals(False)
            self.host.canvas.set_alignment_target("dam")

        if hasattr(self.host, "calc_panel"):
            if self.host._total_energy is None:
                self.host.calc_panel.lbl_energy.setText(tr("calc.total_energy_default"))
            else:
                self.host.calc_panel.lbl_energy.setText(
                    tr(
                        "calc.total_energy_value",
                        value=f"{self.host._total_energy:.2f}",
                        unit="J",
                    )
                )

            # Restoring inputs must not invalidate the saved calculation results.
            with QSignalBlocker(self.host.calc_panel.txt_A):
                self.host.calc_panel.txt_A.setText(
                    ""
                    if self.host.project.crash3_A is None
                    else f"{self.host.project.crash3_A:.2f}"
                )
            with QSignalBlocker(self.host.calc_panel.txt_B):
                self.host.calc_panel.txt_B.setText(
                    ""
                    if self.host.project.crash3_B is None
                    else f"{self.host.project.crash3_B:.2f}"
                )

            ab_type = self.host.project.ab_source_type
            if ab_type in ("nhtsa_library", "nhtsa_file"):
                self.host.calc_panel.txt_A.setReadOnly(True)
                self.host.calc_panel.txt_B.setReadOnly(True)
            elif ab_type == "generic_class":
                self.host.calc_panel.txt_A.setReadOnly(True)
                self.host.calc_panel.txt_B.setReadOnly(True)
                # Restaurar seleção no combo
                ref = self.host.project.ab_source_ref or ""
                idx = self.host.calc_panel.cmb_class.findData(ref)
                if idx >= 0:
                    self.host.calc_panel.cmb_class.blockSignals(True)
                    self.host.calc_panel.cmb_class.setCurrentIndex(idx)
                    self.host.calc_panel.cmb_class.blockSignals(False)
            else:
                self.host.calc_panel.txt_A.setReadOnly(False)
                self.host.calc_panel.txt_B.setReadOnly(False)

            alpha_deg = self.host.project.crash3_alpha_deg
            with QSignalBlocker(self.host.calc_panel.txt_alpha_deg):
                self.host.calc_panel.txt_alpha_deg.setText(
                    f"{0.0 if alpha_deg is None else alpha_deg:.2f}"
                )

            with QSignalBlocker(self.host.calc_panel.txt_vehicle_mass):
                self.host.calc_panel.txt_vehicle_mass.setText(
                    ""
                    if self.host._vehicle_mass_kg is None
                    else f"{self.host._vehicle_mass_kg:.2f}"
                )

            if self.host._damage_speed_kmh is None:
                self.host.calc_panel.lbl_speed.setText(tr("calc.damage_speed_default"))
            else:
                self.host.calc_panel.lbl_speed.setText(
                    tr(
                        "calc.damage_speed_value",
                        value=f"{self.host._damage_speed_kmh:.2f}",
                        unit="km/h",
                    )
                )

            if hasattr(self.host.calc_panel, "retranslate_ui"):
                self.host.calc_panel.retranslate_ui()

            if hasattr(self.host.calc_panel, "_refresh_ab_source_ui"):
                self.host.calc_panel._refresh_ab_source_ui()

        self.host.workflow.sync_stage_after_load()
        QMessageBox.information(
            self.host,
            tr("project.load.dialog_title"),
            tr("project.load.loaded", path=path),
        )

    def export_png(self) -> None:
        out_path, _ = QFileDialog.getSaveFileName(
            self.host,
            tr("project.export_png.dialog_title"),
            "",
            "PNG Image (*.png)",
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".png"):
            out_path += ".png"

        try:
            self.host.canvas.export_scene_png(out_path)
            QMessageBox.information(
                self.host,
                tr("project.export_png.dialog_title"),
                tr("project.export_png.saved", path=out_path),
            )
        except Exception as e:
            QMessageBox.critical(
                self.host,
                tr("project.export_png.dialog_title"),
                str(e),
            )

    def pick_image_file(self) -> str | None:
        path, _ = QFileDialog.getOpenFileName(
            self.host,
            tr("project.select_image.dialog_title"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        return path or None

    def _confirm_image_replace_reset(self) -> bool:
        p = self.host.project

        has_progress = any(
            [
                p.m_per_px is not None,
                p.w_px is not None,
                bool(p.c_m),
                p.total_energy_j is not None,
                p.damage_speed_kmh is not None,
                p.damage_speed_mps is not None,
            ]
        )

        if not has_progress:
            return True

        answer = QMessageBox.question(
            self.host,
            tr("project.replace_image.dialog_title"),
            tr("project.replace_image.confirm_reset"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def load_ref(self) -> None:
        path = self.pick_image_file()
        if not path:
            return

        if not self._confirm_image_replace_reset():
            return

        try:
            self.host.workflow.invalidate_from_alignment()
            self.host.canvas.load_reference(path)
            self.host.project.ref_path = path

            self.host.workflow.set_stage(self.host.Stage.ALIGNMENT)

        except Exception as e:
            QMessageBox.critical(
                self.host,
                tr("project.load_ref.error_title"),
                str(e),
            )

    def load_dam(self) -> None:
        path = self.pick_image_file()
        if not path:
            return

        if not self._confirm_image_replace_reset():
            return

        try:
            self.host.workflow.invalidate_from_alignment()
            self.host.canvas.load_deformed(path)
            self.host.canvas.set_deformed_opacity(
                self.host.opacity_slider.value() / 100.0
            )
            self.host.project.dam_path = path

            self.host.workflow.set_stage(self.host.Stage.ALIGNMENT)

        except Exception as e:
            QMessageBox.critical(
                self.host,
                tr("project.load_dam.error_title"),
                str(e),
            )
