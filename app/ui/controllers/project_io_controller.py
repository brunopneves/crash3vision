from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from app.core.number_format import format_display_number
from app.core.project import InvalidProjectDataError, Project, UnsupportedCrash3UnitsError
from app.i18n import get_language, tr

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


def _image_path_for_project(image_path: str | None, project_dir: Path) -> str | None:
    if not image_path:
        return image_path

    path = Path(image_path)
    try:
        relative_path = os.path.relpath(path, project_dir)
    except (OSError, ValueError):
        return path.as_posix()
    return Path(relative_path).as_posix()


def _resolve_project_image_path(
    stored_path: str | None, project_dir: Path
) -> str | None:
    if not stored_path:
        return stored_path

    path = Path(stored_path)
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve())


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidProjectDataError("duplicate_key", field=key)
        result[key] = value
    return result


def _read_project_image(path: str) -> QPixmap:
    # Read the file again rather than accepting a copy from the pixmap cache.
    image = QImageReader(path).read()
    pixmap = QPixmap.fromImage(image)
    if pixmap.isNull():
        raise InvalidProjectDataError("image_unavailable", field=path)
    return pixmap


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
        self.host._viewed_step = None

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

        self.host.workflow.reset_canvas_tools()
        self.host.canvas.clear_images()
        self.host._restore_project_opacity()
        self.host.canvas.set_alignment_target("dam")
        self.host._update_auto_align_availability()

        if hasattr(self.host, "cmb_alignment_target"):
            self.host.cmb_alignment_target.blockSignals(True)
            self.host.cmb_alignment_target.setCurrentIndex(0)
            self.host.cmb_alignment_target.blockSignals(False)

        if hasattr(self.host, "calc_panel"):
            self.host.calc_panel.lbl_energy.setText(tr("calc.total_energy_default"))
            self.host.calc_panel.lbl_speed.setText(tr("calc.damage_speed_default"))
            self.host.calc_panel.restore_parameter_fields()

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
        destination = Path(path)
        project_dir = destination.parent
        project_data = self.host.project.to_dict()
        project_data["name"] = destination.stem
        project_data["ref_path"] = _image_path_for_project(
            self.host.project.ref_path, project_dir
        )
        project_data["dam_path"] = _image_path_for_project(
            self.host.project.dam_path, project_dir
        )

        temporary_path = None
        try:
            Project.from_dict(project_data)
            for key in ("ref_path", "dam_path"):
                image_path = _resolve_project_image_path(project_data[key], project_dir)
                if image_path:
                    if Path(image_path) == destination.resolve():
                        raise InvalidProjectDataError("image_is_save_destination", field=image_path)
                    _read_project_image(image_path)
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=project_dir, suffix=".tmp", delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(project_data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None
        except InvalidProjectDataError as error:
            QMessageBox.critical(
                self.host, tr("project.save.dialog_title"),
                tr("project.save.invalid_data", error=tr(f"project.data.{error.reason}", **error.details)),
            )
            return
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.critical(
                self.host, tr("project.save.dialog_title"),
                tr("project.save.failed", error=error),
            )
            return
        finally:
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

        self.host.project.name = destination.stem
        self.host._current_project_path = path
        self.host._update_window_title()
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

        try:
            with open(path, "r", encoding="utf-8") as stream:
                data = json.load(stream, object_pairs_hook=_unique_json_object)
            if not isinstance(data, dict):
                raise ValueError(tr("project.load.invalid_structure"))
            project_dir = Path(path).parent
            for key in ("ref_path", "dam_path"):
                data[key] = _resolve_project_image_path(data.get(key), project_dir)
            project = Project.from_dict(data)
            prepared_images = {
                slot: _read_project_image(image_path)
                for slot, image_path in (("ref", project.ref_path), ("dam", project.dam_path))
                if image_path
            }
            ci_px = {int(k.replace("C", "")): v for k, v in (project.c_px or {}).items()}
            ci_m = {int(k.replace("C", "")): v for k, v in (project.c_m or {}).items()}
        except UnsupportedCrash3UnitsError as e:
            QMessageBox.warning(
                self.host,
                tr("project.load.dialog_title"),
                tr("project.load.unsupported_crash3_units", units=repr(e.units)),
            )
            return
        except InvalidProjectDataError as error:
            QMessageBox.warning(
                self.host, tr("project.load.dialog_title"),
                tr("project.load.invalid_data", error=tr(f"project.data.{error.reason}", **error.details)),
            )
            return
        except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError) as error:
            QMessageBox.warning(
                self.host, tr("project.load.dialog_title"),
                tr("project.load.failed", error=error),
            )
            return

        self.host.project = project
        self.host._update_window_title()
        self.host._current_project_path = path

        self.host._total_energy = self.host.project.total_energy_j
        self.host._vehicle_mass_kg = self.host.project.vehicle_mass_kg
        self.host._damage_speed_mps = self.host.project.damage_speed_mps
        self.host._damage_speed_kmh = self.host.project.damage_speed_kmh

        self.host.canvas.clear_images()
        self.host._restore_project_opacity()
        if "ref" in prepared_images:
            self.host.canvas.load_reference(prepared_images["ref"])
        if "dam" in prepared_images:
            self.host.canvas.load_deformed(prepared_images["dam"])
        self.host._update_auto_align_availability()

        ref_tr = self.host.project.ref_transform
        self.host.canvas.set_reference_transform(
            ref_tr.x, ref_tr.y, ref_tr.scale, ref_tr.rotation_deg
        )

        dam_tr = self.host.project.dam_transform
        self.host.canvas.set_deformed_transform(
            dam_tr.x, dam_tr.y, dam_tr.scale, dam_tr.rotation_deg
        )

        self.host._m_per_px = self.host.project.m_per_px
        if self.host._m_per_px is not None:
            self.host.canvas.apply_scale(self.host._m_per_px)
            self.host.lbl_m_per_px.setText(
                tr("measurement.scale_value", value=format_display_number(self.host._m_per_px, 6))
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
                    value=format_display_number(self.host._calibration_px),
                )
            )

            if self.host._m_per_px is not None:
                real_m = self.host._calibration_px * self.host._m_per_px
                self.host._calibration_distance_language = get_language()
                self.host.txt_real_m.setText(format_display_number(real_m, None))
            else:
                self.host.txt_real_m.setText("")
        else:
            self.host._calibration_px = None
            self.host.lbl_px_distance.setText(tr("label.measured_distance"))
            self.host.txt_real_m.setText("")

        self.host._w_px = self.host.project.w_px
        self.host._w_m = self.host.project.w_m
        self.host._delta_w_px = self.host.project.delta_w_px
        self.host._delta_w_m = self.host.project.delta_w_m
        self.host.meas.refresh_w_display()

        self.host._ci_px.clear()
        self.host._ci_m.clear()

        self.host._ci_px.update(ci_px)
        self.host._ci_m.update(ci_m)

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
        # Older projects could be saved after marking W but before generating slices.
        if (
            not self.host.canvas.slice_x
            and self.host._w_px is not None
            and math.isfinite(self.host._w_px)
            and self.host._w_px > 0
        ):
            self.host.canvas.generate_slices()

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
            self.host.calc_panel.restore_parameter_fields()
            self.host.calc_panel.retranslate_ui()

        self.host.workflow.sync_stage_after_load()
        QMessageBox.information(
            self.host,
            tr("project.load.dialog_title"),
            tr("project.load.loaded", path=path),
        )

    def export_png(self) -> None:
        self._export_png(self.host.canvas.export_scene_png, "project.export_png")

    def export_current_view_png(self) -> None:
        self._export_png(self.host.canvas.export_current_view_png, "project.export_current_view")

    def _export_png(self, export: Callable[[str], None], translation_prefix: str) -> None:
        title = tr(f"{translation_prefix}.dialog_title")
        out_path, _ = QFileDialog.getSaveFileName(
            self.host,
            title,
            "",
            "PNG Image (*.png)",
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".png"):
            out_path += ".png"

        try:
            export(out_path)
        except Exception as error:
            QMessageBox.critical(
                self.host,
                title,
                tr("project.export_png.failed", path=out_path, error=error),
            )
            return

        QMessageBox.information(self.host, title, tr(f"{translation_prefix}.saved", path=out_path))

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
            pixmap = QPixmap(path)
            if pixmap.isNull():
                raise ValueError(tr("project.load.images_failed", error=path))
            self.host.workflow.invalidate_from_alignment(target_stage=self.host.Stage.LOAD)
            self.host.canvas.load_reference(pixmap)
            self.host.project.ref_path = path
            self.host._refresh_summary()

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
            pixmap = QPixmap(path)
            if pixmap.isNull():
                raise ValueError(tr("project.load.images_failed", error=path))
            self.host.workflow.invalidate_from_alignment(target_stage=self.host.Stage.LOAD)
            self.host.canvas.load_deformed(pixmap)
            self.host.canvas.set_deformed_opacity(self.host.project.opacity)
            self.host.project.dam_path = path

            self.host._refresh_summary()

        except Exception as e:
            QMessageBox.critical(
                self.host,
                tr("project.load_dam.error_title"),
                str(e),
            )
