from __future__ import annotations

import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QBoxLayout, QDialog, QFileDialog, QGraphicsView, QInputDialog, QMessageBox,
)

from app.core.project import Project
from app.core.rigid_region_alignment import (
    REGION_DEFAULT_HEIGHT_FRACTION,
    REGION_DEFAULT_LENGTH_FRACTION,
    DEFORMED_REGION_MIN_HEIGHT_FRACTION,
    POINT_ROI_HEIGHT_FRACTION,
    POINT_ROI_WIDTH_FRACTION,
    POINT_ROI_EXPANSION_FACTOR,
    RigidAlignmentCandidate,
    RigidAlignmentDiagnostics,
    RigidAlignmentResult,
    RigidAnchorSuggestion,
    RigidAnchorSuggestionResult,
    RigidRegion,
    _candidate_passes_minimums,
    _has_relevant_ambiguity,
    _region_segment_indices,
    _spatial_match_groups,
    _structural_gradient_image,
    corrected_reference_rotation,
    estimate_multiscale_rigid_alignment,
    estimate_rigid_region_alignment,
    expand_point_anchor_regions,
    make_point_anchor_region,
    make_adaptive_deformed_region,
    make_rigid_region,
    region_weights,
    suggest_rigid_region_anchors,
)
from app.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[1]
COMPASS = ROOT / "examples/nhtsa_jeep_compass_2024_m20240300"


class RigidRegionAlignmentTests(unittest.TestCase):
    def test_ab_details_show_only_applicable_source_metadata(self) -> None:
        window = self._window()
        panel = window.calc_panel
        project = window.project
        project.ab_source_type = "manual"
        project.ab_source_snapshot = {"A_n_per_m": 100000, "B_n_per_m2": 1000000}
        panel._refresh_ab_source_ui()
        self.assertTrue(panel.lbl_ab_details.isHidden())
        self.assertIn("Entrada manual", panel.lbl_ab_source.text())

        project.ab_source_type = "generic_class"
        project.ab_source_reference = "Catálogo técnico"
        project.ab_source_snapshot = {
            "class_name": "compact", "A_n_per_m": 100000, "B_n_per_m2": 1000000,
            "test_number": "not-applicable-to-generic",
        }
        panel._refresh_ab_source_ui()
        self.assertIn("compact", panel.lbl_ab_details.text())
        self.assertIn("Catálogo técnico", panel.lbl_ab_details.text())
        self.assertNotIn("not-applicable-to-generic", panel.lbl_ab_details.text())
        self.assertNotIn("100000", panel.lbl_ab_details.text())

        panel.txt_vehicle_mass.setText("1815,00")
        project.ab_source_label = None
        project.ab_source_reference = "M20240300"
        project.ab_source_snapshot = {
            "report_number": "M20240300", "test_number": "N/A",
            "make": "Jeep", "model": "Compass", "test_agency": None,
            "test_configuration": "rigid_frontal_barrier",
            "impact_speed_mps": None, "test_speed_mps": 15.639,
            "rebound_speed_mps": 0.0, "velocity_change_mps": "NaN",
            "speed_basis": "impact", "impact_angle_deg": 0,
            "vehicle_mass_kg": 1815, "c_values_m": [0.34, None, 0.37],
            "A_n_per_m": 100000, "B_n_per_m2": 1000000,
        }
        for source in ("nhtsa_library", "nhtsa_report", "nhtsa_file"):
            project.ab_source_type = source
            before = project.to_dict()
            panel._refresh_ab_source_ui()
            details = panel.lbl_ab_details.text()
            self.assertIn("Jeep Compass", panel.lbl_ab_source.text())
            self.assertEqual(details.count("M20240300"), 1)
            self.assertIn("56,30", details)
            self.assertIn("0,00", details)
            self.assertIn("C3=0,370", details)
            for absent in ("None", "N/A", "NaN", "C2=", "Massa do ensaio", "Ângulo do ensaio", "100000"):
                self.assertNotIn(absent, details)
            self.assertEqual(project.to_dict(), before)

        panel.txt_vehicle_mass.setText("1800")
        window._set_language_and_refresh("en")
        self.assertIn("Test mass (kg): 1815.00", panel.lbl_ab_details.text())
        self.assertIn("Rigid Frontal Barrier", panel.lbl_ab_details.text())
        project.ab_source_snapshot = None
        project.ab_source_reference = None
        panel._refresh_ab_source_ui()
        self.assertTrue(panel.lbl_ab_details.isHidden())
        self.assertEqual(panel.lbl_ab_source.text(), "A/B source: A/B file")

    def test_contextual_calculation_actions_reuse_energy_and_stored_result(self) -> None:
        window = self._window()
        path = str(COMPASS / "crash3vision_reference_project.json")
        with (
            patch.object(QFileDialog, "getOpenFileName", return_value=(path, "")),
            patch.object(QMessageBox, "information"),
        ):
            window.io.load_project()
        panel = window.calc_panel
        window.workflow_step_labels["calculation"].click()
        saved = window.project.to_dict()
        self.assertEqual(panel.btn_compute.text(), "Ver resultado")
        with (
            patch.object(window.calc, "compute_crash3") as energy,
            patch.object(window.calc, "compute_damage_speed") as ees,
        ):
            panel.btn_compute.click()
        energy.assert_not_called()
        ees.assert_not_called()
        self.assertIsNone(window._viewed_step)
        self.assertEqual(window.project.to_dict(), saved)

        window.workflow_step_labels["calculation"].click()
        with (
            patch.object(window.calc, "compute_crash3", side_effect=ValueError("calculation failed")),
            patch.object(QMessageBox, "warning") as warning,
        ):
            self.assertFalse(panel._on_compute())
        warning.assert_called_once()
        self.assertEqual(window.project.total_energy_j, saved["total_energy_j"])
        self.assertEqual(window.project.damage_speed_kmh, saved["damage_speed_kmh"])

        panel.txt_vehicle_mass.setText("1800,5")
        self.assertEqual(panel.btn_compute.text(), "Calcular EES")
        with patch.object(window.calc, "compute_crash3") as energy:
            panel.btn_compute.click()
        energy.assert_not_called()
        self.assertEqual(window.project.total_energy_j, saved["total_energy_j"])
        self.assertEqual(window.project.vehicle_mass_kg, 1800.5)
        self.assertFalse(window._summary_group.isHidden())

        window.workflow_step_labels["calculation"].click()
        panel.txt_alpha_deg.setText("2")
        self.assertEqual(panel.btn_compute.text(), "Calcular energia e EES")
        window._set_language_and_refresh("en")
        self.assertEqual(panel.btn_compute.text(), "Calculate energy and EES")
        with (
            patch.object(window.calc, "compute_crash3", wraps=window.calc.compute_crash3) as energy,
            patch.object(window.calc, "compute_damage_speed", wraps=window.calc.compute_damage_speed) as ees,
        ):
            panel.btn_compute.click()
        energy.assert_called_once()
        ees.assert_called_once_with(1800.5)
        self.assertFalse(window._summary_group.isHidden())
        self.assertEqual(panel.btn_compute.text(), "View result")

        window.workflow_step_labels["calculation"].click()
        panel.txt_vehicle_mass.setText("  ")
        self.assertEqual(panel.btn_compute.text(), "Calculate energy")
        with patch.object(window.calc, "compute_damage_speed") as ees:
            panel.btn_compute.click()
        ees.assert_not_called()
        self.assertGreater(window._total_energy, 0)
        self.assertIsNone(window._damage_speed_kmh)
        self.assertFalse(panel.isHidden())

    def test_contextual_calculation_rejects_invalid_inputs_and_failed_results(self) -> None:
        window = self._window()
        window.workflow.set_stage(window.Stage.DONE)
        panel = window.calc_panel
        panel.txt_A.setText("100000")
        panel.txt_B.setText("1000000")
        with patch.object(QMessageBox, "warning") as warning:
            for invalid in ("NaN", "inf", "-inf", "0", "-1", "invalid"):
                panel.txt_vehicle_mass.setText(invalid)
                with (
                    patch.object(window.calc, "compute_crash3") as energy,
                    patch.object(window.calc, "compute_damage_speed") as ees,
                ):
                    panel.btn_compute.click()
                energy.assert_not_called()
                ees.assert_not_called()
            self.assertEqual(warning.call_count, 6)

        panel.txt_vehicle_mass.setText("1800")
        for field, invalid, valid in (
            (panel.txt_A, "NaN", "100000"),
            (panel.txt_B, "inf", "1000000"),
            (panel.txt_alpha_deg, "NaN", "0"),
            (panel.txt_alpha_deg, "89", "0"),
        ):
            field.setText(invalid)
            with (
                patch.object(QMessageBox, "warning") as warning,
                patch.object(window.calc, "compute_crash3") as energy,
                patch.object(window.calc, "compute_damage_speed") as ees,
            ):
                panel.btn_compute.click()
            warning.assert_called_once()
            energy.assert_not_called()
            ees.assert_not_called()
            field.setText(valid)

        with (
            patch.object(QMessageBox, "warning") as warning,
            patch.object(window.calc, "compute_crash3", return_value={"total_energy_j": float("inf")}),
            patch.object(window.calc, "compute_damage_speed") as ees,
        ):
            panel.btn_compute.click()
        warning.assert_called_once()
        ees.assert_not_called()
        self.assertIsNone(window._total_energy)

        with (
            patch.object(QMessageBox, "warning") as warning,
            patch.object(window.calc, "compute_crash3", return_value={"total_energy_j": 1000.0}),
            patch.object(window.calc, "compute_damage_speed",
                         return_value={"speed_mps": float("nan"), "speed_kmh": float("nan")}),
        ):
            panel.btn_compute.click()
        warning.assert_called_once()
        self.assertEqual(window.project.total_energy_j, 1000.0)
        self.assertIsNone(window.project.damage_speed_kmh)
        self.assertEqual(window._current_workflow_step(), "calculation")
        self.assertEqual(panel.btn_compute.text(), "Calcular EES")

    def test_calculation_layout_keeps_sources_and_actions_available(self) -> None:
        window = self._window()
        source = COMPASS / "crash3vision_reference_project.json"
        with (
            patch.object(QFileDialog, "getOpenFileName", return_value=(str(source), "")),
            patch.object(QMessageBox, "information"),
        ):
            window.io.load_project()
        window.workflow_step_labels["calculation"].click()
        panel = window.calc_panel
        before = window.project.to_dict()
        self.assertIs(panel.cmb_class.parentWidget(), panel.grp_source)
        self.assertIs(panel.txt_vehicle_mass.parentWidget(), panel.grp_params)
        self.assertTrue(panel.details.isHidden())
        window.show()
        for language in ("pt", "en"):
            window._set_language_and_refresh(language)
            panel.btn_toggle_details.setChecked(True)
            QApplication.processEvents()
            self.assertTrue(panel.details.isVisible())
            self.assertTrue(panel.lbl_ab_source.isVisible())
            self.assertAlmostEqual(window._controls_dock.width(), 370, delta=15)
            self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0)
        self.assertEqual(window.project.to_dict(), before)

        panel.cmb_class.setCurrentIndex(1)
        self.assertEqual(window.project.ab_source_type, "generic_class")
        self.assertTrue(panel.txt_A.isReadOnly())
        panel.cmb_class.setCurrentIndex(0)
        self.assertFalse(panel.txt_B.isReadOnly())
        self.assertEqual(window.project.ab_source_type, "manual")
        panel.txt_A.setText("170000")
        panel.txt_B.setText("1800000")
        panel.txt_vehicle_mass.clear()
        panel.btn_compute.click()
        self.assertGreater(window._total_energy, 0)

        def select_compass(_parent, _title, _label, options, *_args):
            return next(item for item in options if "Compass" in item), True

        with patch.object(QInputDialog, "getItem", side_effect=select_compass):
            panel.act_load_ab_library.trigger()
        self.assertEqual(window.project.ab_source_type, "nhtsa_library")
        self.assertIn("M20240300", panel.lbl_ab_details.text())
        with tempfile.TemporaryDirectory() as tmp:
            ab_path = str(Path(tmp) / "coefficients.json")
            with (
                patch.object(QFileDialog, "getSaveFileName", return_value=(ab_path, "")),
                patch.object(QMessageBox, "information"),
            ):
                panel.act_export_ab_file.trigger()
            self.assertTrue(Path(ab_path).is_file())
            with patch.object(QFileDialog, "getOpenFileName", return_value=(ab_path, "")):
                panel.act_import_ab_file.trigger()
        self.assertEqual(window.project.ab_source_type, "nhtsa_file")

        with patch(
            "app.ui.widgets.calc_panel.NhtsaAbDialog.exec",
            return_value=QDialog.DialogCode.Rejected,
        ) as dialog:
            panel.btn_compute_ab_nhtsa.click()
            panel.btn_edit_ab_nhtsa.click()
        self.assertEqual(dialog.call_count, 2)
        self.assertEqual(window.project.ab_source_type, "nhtsa_file")

        def compute_and_accept(dialog):
            dialog._on_compute()
            self.assertIsNotNone(dialog._last_result)
            return QDialog.DialogCode.Accepted

        with (
            patch("app.ui.widgets.calc_panel.NhtsaAbDialog.exec", new=compute_and_accept),
            patch.object(QMessageBox, "warning") as warning,
        ):
            panel.btn_edit_ab_nhtsa.click()
        warning.assert_not_called()
        self.assertEqual(window.project.ab_source_type, "nhtsa_report")
        self.assertGreater(window._total_energy, 0)
        self.assertIsNone(window._damage_speed_kmh)

        panel.txt_vehicle_mass.clear()
        panel.btn_compute.click()
        self.assertGreater(window._total_energy, 0)
        self.assertIsNone(window._damage_speed_kmh)
        with patch("app.ui.widgets.calc_panel.CrushProfileDialog.exec") as profile:
            panel.btn_show_profile.click()
        profile.assert_called_once()
        panel.txt_vehicle_mass.setText("1800")
        self.assertGreater(window._total_energy, 0)
        panel.btn_compute.click()
        self.assertGreater(window._damage_speed_kmh, 0)
        self.assertEqual(window._current_workflow_step(), "result")

    def test_measurement_panel_tracks_steps_and_collapses_guide_safely(self) -> None:
        window = self._window()
        window._m_per_px = 0.005
        window.canvas.apply_scale(0.005)
        window.workflow.set_stage(window.Stage.MARKING)
        window.show()
        QApplication.processEvents()
        self.assertFalse(window.chk_measure_ci_mode.isEnabled())
        self.assertTrue(window.marking_references.isHidden())
        self.assertEqual(window.chk_set_w_mode.property("uiRole"), "primary")
        self.assertEqual(window.lbl_ci_progress.text(), "0 de 6 medidos")
        self.assertTrue(all(label.text() == "—" for label in window.ci_value_labels.values()))

        viewport = window.canvas.viewport()
        center = viewport.rect().center()
        window.chk_set_w_mode.click()
        self.assertTrue(window.lbl_width_capture.isVisible())
        for point in (center + QPoint(150, 0), center - QPoint(150, 0)):
            QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=point)
        self.assertFalse(window.canvas.set_w_mode)
        self.assertFalse(window.chk_set_w_mode.isChecked())
        self.assertTrue(window.canvas.measure_ci_mode)
        self.assertTrue(window.rb_c1.isChecked())
        self.assertIn("Marque C1 com dois cliques", window.lbl_ci_instruction.text())
        self.assertEqual(window.chk_set_w_mode.text(), "Remarcar W")
        width_overlay = window.canvas.get_overlay_state()
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center)
        self.assertEqual(window.canvas.get_overlay_state(), width_overlay)
        self.assertTrue(window.lbl_slice_status.property("complete"))
        self.assertTrue(window.lbl_width_capture.isHidden())
        positions = window.canvas.slice_x
        self.assertEqual(len(positions), 6)
        self.assertTrue(all(
            math.isclose(right - left, window._w_px / 5)
            for left, right in zip(positions, positions[1:])
        ))
        self.assertIn("5 intervalos", window.lbl_slice_status.text())
        self.assertIn("W/5", window.lbl_slice_status.text())
        self.assertEqual(window.lbl_w.text(), f"W: {window._w_m:.3f} m")
        self.assertIn(f"{window._w_px / 5:.2f} px", window.lbl_delta_w.text())
        self.assertIn(f"{window._w_m / 5:.3f} m", window.lbl_delta_w.text())

        window.btn_toggle_marking_references.click()
        window.spn_bumper_offset.setValue(0.1)
        window.chk_set_guide_mode.click()
        self.assertFalse(window.chk_measure_ci_mode.isChecked())
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center)
        self.assertIn("✓ Guia", window.btn_toggle_marking_references.text())
        self.assertIn("✓ Offset", window.btn_toggle_marking_references.text())
        guide_state = window.canvas.get_overlay_state()
        window.btn_toggle_marking_references.click()
        self.assertFalse(window.canvas.guide_mode)
        self.assertIsNone(window.canvas.ctrl.active_tool())
        self.assertEqual(window.canvas.get_overlay_state(), guide_state)

        window.chk_measure_ci_mode.click()
        for count, index in enumerate((4, 1, 2, 3, 5, 6), 1):
            getattr(window, f"rb_c{index}").click()
            self.assertEqual(window._current_ci_index, index)
            x = center.x() - 150 + (index - 1) * 60
            for y in (center.y() - 40, center.y() + 40):
                QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=QPoint(x, y))
            self.assertEqual(window._current_ci_index, min(index + 1, 6))
            self.assertEqual(window.ci_value_labels[index].text(), f"{window._ci_m[index]:.3f}")
            if count < 6:
                self.assertEqual(window.lbl_ci_progress.text(), f"{count} de 6 medidos")
        self.assertEqual(window.stage, window.Stage.MARKING)
        self.assertTrue(window.canvas.measure_ci_mode)
        corrected = window.canvas.c_points[3][1]
        start = window.canvas.mapFromScene(QPointF(*corrected))
        end = start + QPoint(0, 25)
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(viewport, end)
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=end)
        self.assertEqual(window._current_ci_index, 3)
        self.assertEqual(window.canvas.c_points[3][1][0], corrected[0])
        self.assertNotEqual(window.canvas.c_points[3][1][1], corrected[1])
        self.assertIn("✓ C1–C6 medidos", window.lbl_ci_progress.text())
        self.assertTrue(window.btn_finish_marking.isEnabled())
        complete = window.canvas.get_overlay_state()
        window.chk_measure_ci_mode.click()
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center)
        self.assertEqual(window.canvas.get_overlay_state(), complete)
        for language in ("pt", "en"):
            window._set_language_and_refresh(language)
            window.btn_toggle_marking_references.setChecked(True)
            QApplication.processEvents()
            self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0, language)
        self.assertIn("5 intervals", window.lbl_slice_status.text())
        window.btn_finish_marking.click()
        self.assertEqual(window.stage, window.Stage.DONE)
        values = [label.text() for label in window.ci_value_labels.values()]
        window.workflow_step_labels["measurement"].click()
        self.assertFalse(window.chk_set_w_mode.isEnabled())
        self.assertFalse(window.rb_c3.isEnabled())
        self.assertEqual([label.text() for label in window.ci_value_labels.values()], values)
        self.assertEqual(window.canvas.get_overlay_state(), complete)

    def test_w_remarking_preserves_data_until_new_pair_is_complete(self) -> None:
        window = self._window()
        path = str(COMPASS / "crash3vision_reference_project.json")
        with (
            patch.object(QFileDialog, "getOpenFileName", return_value=(path, "")),
            patch.object(QMessageBox, "information"),
        ):
            window.io.load_project()
        window.workflow.restart_from_marking()
        # Exercise the commit boundary with dependent results still present.
        window._total_energy = window.project.total_energy_j = 1000.0
        window._damage_speed_mps = window.project.damage_speed_mps = 2.0
        window._damage_speed_kmh = window.project.damage_speed_kmh = 7.2
        before = window.project.to_dict()
        overlay = window.canvas.get_overlay_state()
        window.show()
        QApplication.processEvents()
        viewport = window.canvas.viewport()
        center = viewport.rect().center()

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            window.chk_set_w_mode.click()
        self.assertFalse(window.canvas.set_w_mode)
        self.assertEqual(window.project.to_dict(), before)
        self.assertEqual(window.canvas.get_overlay_state(), overlay)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.chk_set_w_mode.click()
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center)
        window.chk_set_w_mode.click()
        self.assertFalse(window.canvas.set_w_mode)
        self.assertFalse(window.canvas.measure_ci_mode)
        self.assertEqual(window.project.to_dict(), before)
        self.assertEqual(window.canvas.get_overlay_state(), overlay)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.chk_set_w_mode.click()
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center)
        window.chk_measure_ci_mode.click()
        self.assertTrue(window.canvas.measure_ci_mode)
        self.assertFalse(window.chk_set_w_mode.isChecked())
        self.assertEqual(window.canvas.get_overlay_state(), overlay)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.chk_set_w_mode.click()
        for point in (center, center + QPoint(0, 30)):
            QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=point)
        self.assertTrue(window.canvas.set_w_mode)
        self.assertEqual(window.canvas.get_overlay_state(), overlay)
        self.assertEqual(window.project.to_dict(), before)
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=center + QPoint(90, 0))
        self.assertFalse(window.canvas.set_w_mode)
        self.assertTrue(window.canvas.measure_ci_mode)
        self.assertTrue(window.rb_c1.isChecked())
        self.assertNotEqual(window.project.w_px, before["w_px"])
        self.assertEqual(len(window.canvas.slice_x), 6)
        self.assertAlmostEqual(window.canvas.slice_x[1] - window.canvas.slice_x[0],
                               window.project.w_px / 5)
        self.assertTrue(window.chk_measure_ci_mode.isEnabled())
        self.assertFalse(window.canvas.c_points)
        self.assertFalse(window._ci_m)
        self.assertIsNone(window.project.total_energy_j)
        self.assertIsNone(window.project.damage_speed_kmh)
        self.assertEqual(window.project.m_per_px, before["m_per_px"])
        self.assertEqual(window.canvas.get_overlay_state()["cal_p1"], overlay["cal_p1"])

    def test_legacy_width_without_slices_is_restored_without_losing_crush(self) -> None:
        window = self._window()
        source = COMPASS / "crash3vision_reference_project.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        saved_positions = data.pop("slice_x")
        for key in ("ref_path", "dam_path"):
            data[key] = str(COMPASS / data[key])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy_width.json"
            saved = json.dumps(data)
            path.write_text(saved, encoding="utf-8")
            with (
                patch.object(QFileDialog, "getOpenFileName", return_value=(str(path), "")),
                patch.object(QMessageBox, "information"),
                patch.object(QMessageBox, "warning") as warning,
                patch.object(window.canvas, "generate_slices", wraps=window.canvas.generate_slices) as generate,
            ):
                window.io.load_project()
                warning.assert_not_called()
                window.workflow_step_labels["measurement"].click()
                window.btn_return_to_current_step.click()
                generate.assert_called_once_with()
            self.assertEqual(path.read_text(encoding="utf-8"), saved)
        self.assertEqual(len(window.canvas.slice_x), len(saved_positions))
        for actual, expected in zip(window.canvas.slice_x, saved_positions):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(window.canvas.get_overlay_state()["c_points"], data["c_points"])
        self.assertEqual(window.project.total_energy_j, data["total_energy_j"])
        self.assertEqual(window.project.damage_speed_kmh, data["damage_speed_kmh"])
        window.workflow.restart_from_marking()
        self.assertTrue(window.chk_measure_ci_mode.isEnabled())
        self.assertFalse(window.canvas.measure_ci_mode)

    @staticmethod
    def _mark_calibration_points(window: MainWindow) -> None:
        window.chk_calibration_mode.click()
        viewport = window.canvas.viewport()
        origin = viewport.rect().center()
        for point in (origin, origin + QPoint(50, 0)):
            QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=point)

    def test_calibration_uses_current_points_and_distance_after_warning(self) -> None:
        window = self._window()
        window.show()
        QApplication.processEvents()
        window.canvas.set_reference_transform(0, 0, 1.1, 0)
        window.btn_finish_alignment.click()
        self._mark_calibration_points(window)
        self.assertFalse(window.canvas.calibration_mode)
        self.assertEqual(window.chk_calibration_mode.text(), "Remarcar pontos")
        points = (window.canvas.cal_p1, window.canvas.cal_p2)
        QTest.mouseClick(window.canvas.viewport(), Qt.MouseButton.LeftButton)
        self.assertEqual((window.canvas.cal_p1, window.canvas.cal_p2), points)

        window._m_per_px = window.project.m_per_px = 0.005
        window.txt_real_m.setText("0")
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        window.txt_real_m.setText("0,5")
        first = window.lbl_m_per_px.text()
        window.txt_real_m.setText("0,6")
        self.assertNotEqual(window.lbl_m_per_px.text(), first)
        self.assertTrue(window.btn_confirm_calibration.isEnabled())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as warning:
            window.btn_confirm_calibration.click()
        warning.assert_called_once()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        self.assertEqual(window.project.m_per_px, 0.005)
        self.assertEqual((window.canvas.cal_p1, window.canvas.cal_p2), points)
        self.assertEqual(window.txt_real_m.text(), "0,6")

        window.chk_calibration_mode.click()
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        self.assertIsNone(window.canvas.cal_p1)
        self.assertEqual(window.project.m_per_px, 0.005)
        window.chk_calibration_mode.click()
        self._mark_calibration_points(window)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.btn_confirm_calibration.click()
        self.assertEqual(window.stage, window.Stage.MARKING)
        self.assertAlmostEqual(window.project.m_per_px, 0.6 / window._calibration_px)

    def test_calibration_cards_show_capture_preview_and_applied_scale(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            window.btn_load_dam.click()
        window.btn_finish_images.click()
        window.btn_finish_alignment.click()
        window.show()
        QApplication.processEvents()
        self.assertEqual(window.lbl_calibration_title.text(), "Calibração")
        self.assertEqual(window.chk_calibration_mode.property("uiRole"), "primary")
        self.assertEqual(window.lbl_m_per_px.text(), "—")
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        window.chk_calibration_mode.click()
        viewport = window.canvas.viewport()
        point = viewport.rect().center()
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=point)
        self.assertIsNotNone(window.canvas.cal_p1)
        self.assertIsNone(window.canvas.cal_p2)
        self.assertEqual(window.chk_calibration_mode.text(), "Cancelar marcação")
        self.assertFalse(window.lbl_calibration_points_status.property("complete"))
        QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=point + QPoint(50, 0))
        self.assertTrue(window.lbl_calibration_points_status.property("complete"))
        self.assertTrue(window.lbl_px_distance.text().endswith(" px"))
        self.assertEqual(window.chk_calibration_mode.property("uiRole"), "secondary")
        self.assertEqual(window.chk_calibration_mode.text(), "Remarcar pontos")
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        window.txt_real_m.setText("abc")
        self.assertTrue(window.txt_real_m.property("invalidDistance"))
        self.assertTrue(window.lbl_navigation_hint.isVisible())
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        window.txt_real_m.setText("0,5")
        self.assertFalse(window.txt_real_m.property("invalidDistance"))
        self.assertTrue(window.calibration_scale_card.property("hasScale"))
        self.assertTrue(window.lbl_calibration_scale_hint.isVisible())
        self.assertTrue(window.lbl_m_per_px.text().endswith(" m/px"))
        self.assertIsNone(window.project.m_per_px)
        window.btn_confirm_calibration.click()
        self.assertEqual(window.stage, window.Stage.MARKING)
        before = window.project.to_dict()
        window.workflow_step_labels["calibration"].click()
        self.assertEqual(window.lbl_calibration_scale_title.text(), "Escala aplicada")
        self.assertFalse(window.chk_calibration_mode.isEnabled())
        self.assertFalse(window.txt_real_m.isEnabled())
        self.assertTrue(window.lbl_calibration_scale_hint.isHidden())
        window._set_language_and_refresh("en")
        self.assertEqual(window.lbl_calibration_scale_title.text(), "Applied scale")
        self.assertEqual(window.project.to_dict(), before)

    def test_legacy_project_displays_ees_in_mps_without_changing_stored_results(self) -> None:
        window = self._window()
        source = COMPASS / "crash3vision_reference_project.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data.pop("damage_speed_mps")
        for key in ("ref_path", "dam_path"):
            data[key] = str(COMPASS / data[key])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.json"
            original = json.dumps(data)
            path.write_text(original, encoding="utf-8")
            with (
                patch.object(QFileDialog, "getOpenFileName", return_value=(str(path), "")),
                patch.object(QMessageBox, "information"),
                patch.object(window.calc, "compute_damage_speed") as calculate,
            ):
                window.io.load_project()
            calculate.assert_not_called()
            self.assertEqual(window._current_workflow_step(), "result")
            window.workflow_step_labels["calculation"].click()
            self.assertEqual(window.calc_panel.btn_compute.text(), "Ver resultado")
            window.calc_panel.btn_compute.click()
            self.assertIsNone(window._viewed_step)
            self.assertEqual(window.lbl_result_ees_mps.text(), f"{data['damage_speed_kmh'] / 3.6:.2f} m/s")
            self.assertIsNone(window._damage_speed_mps)
            self.assertIsNone(window.project.damage_speed_mps)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
        window.workflow.invalidate_speed()
        self.assertEqual(window.lbl_result_ees_mps.text(), "—")

    def test_step_consultation_preserves_project_and_disables_tools(self) -> None:
        window = self._window()
        steps = window.workflow_step_labels
        self.assertFalse(steps["calibration"].isEnabled())
        steps["calibration"].click()
        self.assertIsNone(window._viewed_step)
        window.chk_alignment_mode.setChecked(True)
        self.assertTrue(window.canvas.alignment_mode)
        before = window.project.to_dict()
        overlay = window.canvas.get_overlay_state()
        steps["images"].click()
        self.assertEqual(window.stage, window.Stage.ALIGNMENT)
        self.assertEqual(window._viewed_step, "images")
        self.assertTrue(window.align_group.isHidden())
        self.assertFalse(window.btn_load_ref.isEnabled())
        self.assertFalse(window.canvas.alignment_mode)
        self.assertIsNone(window.canvas.ctrl.active_tool())
        self.assertTrue(all(not shortcut.isEnabled() for shortcut in window._alignment_shortcuts))
        self.assertEqual(window.project.to_dict(), before)
        self.assertEqual(window.canvas.get_overlay_state(), overlay)
        window.btn_return_to_current_step.click()
        self.assertIsNone(window._viewed_step)
        self.assertTrue(window.align_group.isEnabled())
        self.assertTrue(all(shortcut.isEnabled() for shortcut in window._alignment_shortcuts))

    def test_result_consultation_and_project_reload_follow_real_progress(self) -> None:
        window = self._window()
        steps = window.workflow_step_labels
        steps["images"].click()
        path = str(COMPASS / "crash3vision_reference_project.json")
        with (
            patch.object(QFileDialog, "getOpenFileName", return_value=(path, "")),
            patch.object(QMessageBox, "information"),
        ):
            window.io.load_project()
        self.assertIsNone(window._viewed_step)
        self.assertEqual(window._current_workflow_step(), "result")
        before = window.project.to_dict()
        overlay = window.canvas.get_overlay_state()
        for step, group in (
            ("alignment", window.align_group),
            ("calibration", window.cal_group),
            ("measurement", window.mark_group),
            ("calculation", window.calc_panel),
        ):
            steps[step].click()
            self.assertEqual(window._viewed_step, step)
            self.assertFalse(group.isHidden())
            self.assertEqual(group.isEnabled(), step == "calculation")
            self.assertIn("#245b96", steps["result"].styleSheet())
            self.assertNotIn("#245b96", steps[step].styleSheet())
            self.assertEqual(window.stage, window.Stage.DONE)
            self.assertEqual(window.project.to_dict(), before)
            self.assertEqual(window.canvas.get_overlay_state(), overlay)
        steps["result"].click()
        self.assertIsNone(window._viewed_step)
        self.assertTrue(window.calc_panel.isHidden())
        self.assertFalse(window._summary_group.isHidden())
        steps["calculation"].click()
        self.assertTrue(window._summary_group.isHidden())
        window.calc_panel.txt_vehicle_mass.setText("2000")
        self.assertFalse(steps["result"].isEnabled())
        self.assertEqual(window._current_workflow_step(), "calculation")
        self.assertIsNone(window._viewed_step)
        self.assertEqual(window._total_energy, before["total_energy_j"])

    def test_redo_confirmation_preserves_or_invalidates_the_expected_data(self) -> None:
        path = str(COMPASS / "crash3vision_reference_project.json")
        for step, target in (
            ("alignment", MainWindow.Stage.ALIGNMENT),
            ("calibration", MainWindow.Stage.CALIBRATION),
            ("measurement", MainWindow.Stage.MARKING),
        ):
            with self.subTest(step=step):
                window = self._window()
                with (
                    patch.object(QFileDialog, "getOpenFileName", return_value=(path, "")),
                    patch.object(QMessageBox, "information"),
                ):
                    window.io.load_project()
                before = window.project.to_dict()
                overlay = window.canvas.get_overlay_state()
                window.workflow_step_labels[step].click()
                self.assertFalse(window.btn_redo_step.isHidden())
                with patch.object(
                    QMessageBox, "question", return_value=QMessageBox.StandardButton.No
                ) as confirm:
                    window.btn_redo_step.click()
                confirm.assert_called_once()
                self.assertEqual(window.stage, window.Stage.DONE)
                self.assertEqual(window._viewed_step, step)
                self.assertEqual(window.project.to_dict(), before)
                self.assertEqual(window.canvas.get_overlay_state(), overlay)
                with patch.object(
                    QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
                ):
                    window.btn_redo_step.click()
                self.assertEqual(window.stage, target)
                self.assertIsNone(window._viewed_step)
                self.assertIsNone(window._total_energy)
                self.assertIsNone(window._damage_speed_kmh)
                if step == "measurement":
                    self.assertEqual(window.canvas.get_overlay_state(), overlay)
                    self.assertEqual(len(window._ci_m), 6)
                else:
                    self.assertIsNone(window._m_per_px)
                    self.assertIsNone(window._w_px)
                    self.assertFalse(window._ci_m)

    def test_image_cards_follow_loading_and_allow_read_only_consultation(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        window.show()
        ref_card, ref_title, ref_help, ref_status, ref_button = window._image_cards["reference"]
        dam_card, dam_title, dam_help, dam_status, dam_button = window._image_cards["deformed"]
        self.assertEqual(window._images_title.text(), "Imagens")
        self.assertLess(
            window.load_group.layout().indexOf(dam_card),
            window.load_group.layout().indexOf(ref_card),
        )
        self.assertEqual(dam_title.text(), "Imagem do veículo danificado")
        self.assertEqual(ref_title.text(), "Imagem de referência (opcional)")
        self.assertEqual(dam_help.text(), "Obrigatória para as medições.")
        self.assertEqual(ref_help.text(), "Usada para comparação e alinhamento.")
        self.assertEqual(ref_status.text(), "Ausente")
        self.assertEqual(dam_status.text(), "Ausente")
        self.assertEqual(dam_button.property("uiRole"), "primary")
        self.assertEqual(ref_button.property("uiRole"), "secondary")
        self.assertTrue(window.btn_finish_images.isHidden())
        self.assertFalse(window.btn_finish_images.isEnabled())

        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            dam_button.click()
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertEqual(window.canvas.ctrl.dam_item.opacity(), 1.0)
        self.assertFalse(window.opacity_slider.isEnabled())
        self.assertTrue(window.btn_toggle_image_controls.isHidden())
        self.assertTrue(window.btn_finish_images.isEnabled())
        self.assertIs(window.btn_finish_images.parentWidget(), window.navigation_footer)
        self.assertTrue(ref_card.isVisible())
        self.assertTrue(dam_card.isVisible())
        self.assertFalse(ref_status.property("imageLoaded"))
        self.assertTrue(dam_status.property("imageLoaded"))
        self.assertEqual(dam_button.property("uiRole"), "secondary")
        self.assertEqual(dam_button.text(), "Substituir imagem")
        self.assertEqual(dam_button.accessibleName(), "Substituir imagem do veículo danificado")

        ref_path = str(COMPASS / "reference_vehicle_frame_000.png")
        with patch.object(window.io, "pick_image_file", return_value=ref_path):
            ref_button.click()
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertTrue(ref_status.property("imageLoaded"))
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            ref_button.click()
        self.assertEqual(window.project.ref_path, dam_path)
        self.assertEqual(window.stage, window.Stage.LOAD)
        with patch.object(window.io, "pick_image_file", return_value=ref_path):
            dam_button.click()
        self.assertEqual(window.project.dam_path, ref_path)
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertFalse(ref_card.isHidden())
        self.assertFalse(dam_card.isHidden())
        window._set_language_and_refresh("en")
        self.assertEqual(window.btn_finish_images.text(), "Continue to alignment")
        window._set_language_and_refresh("pt")
        self.assertEqual(window.btn_finish_images.text(), "Continuar para alinhamento")
        window.btn_finish_images.click()
        self.assertEqual(window.stage, window.Stage.ALIGNMENT)
        self.assertTrue(ref_card.isHidden())
        self.assertTrue(dam_card.isHidden())
        self.assertEqual(window.btn_toggle_image_controls.text(), "▸ ✓ Ambas as imagens")
        before = window.project.to_dict()
        window.workflow_step_labels["images"].click()
        window.btn_toggle_image_controls.click()
        self.assertTrue(window._images_title.isVisible())
        self.assertTrue(ref_card.isVisible())
        self.assertTrue(ref_status.property("imageLoaded"))
        self.assertTrue(dam_status.property("imageLoaded"))
        self.assertFalse(ref_button.isEnabled())
        self.assertFalse(dam_button.isEnabled())
        self.assertTrue(window.btn_finish_images.isHidden())
        self.assertFalse(window.btn_finish_images.isEnabled())
        window.workflow.finish_images()
        self.assertEqual(window._viewed_step, "images")
        window.resize(900, 550)
        window.resizeDocks([window._controls_dock], [350], Qt.Orientation.Horizontal)
        for language, title in (("pt", "Imagens"), ("en", "Images")):
            window._set_language_and_refresh(language)
            QApplication.processEvents()
            self.assertEqual(window._images_title.text(), title)
            self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0)
        self.assertEqual(dam_title.text(), "Damaged vehicle image")
        self.assertEqual(ref_title.text(), "Reference image (optional)")
        self.assertEqual(dam_button.accessibleName(), "Replace damaged vehicle image")
        self.assertEqual(window.project.to_dict(), before)

    def test_reference_only_stays_in_images_until_deformed_is_loaded(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        ref_path = str(COMPASS / "reference_vehicle_frame_000.png")
        with patch.object(window.io, "pick_image_file", return_value=ref_path):
            window.btn_load_ref.click()
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertEqual(window.workflow.determine_stage_from_project(), window.Stage.LOAD)
        self.assertFalse(window.btn_load_dam.isHidden())
        self.assertFalse(window.btn_finish_images.isEnabled())
        window.workflow.finish_images()
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertTrue(window.btn_toggle_image_controls.isHidden())
        self.assertEqual(
            window.workflow_step_labels["images"].property("progressStatus"), "current"
        )
        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            window.btn_load_dam.click()
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertTrue(window.btn_finish_images.isEnabled())
        window.btn_finish_images.click()
        self.assertEqual(window.stage, window.Stage.ALIGNMENT)
        self.assertTrue(window.btn_start_alignment.isEnabled())
        self.assertTrue(window.btn_load_dam.isHidden())

    def test_dock_width_is_stable_and_alignment_methods_adapt(self) -> None:
        window = self._window()
        window.show()
        QApplication.processEvents()
        dock = window._controls_dock
        self.assertAlmostEqual(dock.width(), 370, delta=15)
        width = dock.width()
        row = window.alignment_method_row
        required = (
            window.rad_alignment_auto.sizeHint().width()
            + window.rad_alignment_rigid.sizeHint().width()
            + row.layout().spacing()
        )
        self.assertEqual(
            row.layout().direction(),
            QBoxLayout.Direction.LeftToRight if row.width() >= required
            else QBoxLayout.Direction.TopToBottom,
        )
        window._set_language_and_refresh("en")
        self.assertEqual(window.rad_alignment_auto.text(), "Automatic")
        self.assertEqual(window.btn_toggle_image_controls.text(), "▸ ✓ Both images")
        required = (
            window.rad_alignment_auto.sizeHint().width()
            + window.rad_alignment_rigid.sizeHint().width()
            + row.layout().spacing()
        )
        row.resize(required, row.height())
        self.assertEqual(row.layout().direction(), QBoxLayout.Direction.LeftToRight)
        row.resize(max(window.rad_alignment_auto.sizeHint().width(),
                       window.rad_alignment_rigid.sizeHint().width()), row.height())
        self.assertEqual(row.layout().direction(), QBoxLayout.Direction.TopToBottom)
        for stage in (window.Stage.CALIBRATION, window.Stage.MARKING, window.Stage.DONE):
            window.workflow.set_stage(stage)
            QApplication.processEvents()
            self.assertEqual(dock.width(), width)
        window.resize(900, 650)
        window.resizeDocks([dock], [300], Qt.Orientation.Horizontal)
        QApplication.processEvents()
        self.assertLess(dock.width(), width)

    def test_workflow_progress_tracks_images_and_alignment(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        steps = window.workflow_step_labels
        self.assertEqual(steps["images"].property("progressStatus"), "current")
        self.assertEqual(steps["alignment"].property("progressStatus"), "future")
        self.assertFalse(window.load_group.isHidden())
        self.assertTrue(window.btn_toggle_image_controls.isHidden())
        self.assertFalse(window.btn_load_ref.isHidden())
        self.assertFalse(window.btn_load_dam.isHidden())
        self.assertTrue(window.align_group.isHidden())
        self.assertTrue(window.btn_redo_step.isHidden())

        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            window.io.load_dam()
        self.assertEqual(steps["images"].property("progressStatus"), "current")
        self.assertFalse(steps["alignment"].isEnabled())
        window.btn_finish_images.click()
        self.assertEqual(steps["images"].property("progressStatus"), "complete")
        self.assertEqual(steps["alignment"].property("progressStatus"), "current")
        self.assertIn("opcional", steps["alignment"].text())
        self.assertEqual(window.btn_toggle_image_controls.text(), "▸ ✓ Veículo danificado")
        self.assertTrue(window.btn_load_ref.isHidden())
        self.assertTrue(window.btn_load_dam.isHidden())
        self.assertFalse(window.align_group.isHidden())
        self.assertTrue(window.fine_adjust_group.isHidden())
        self.assertTrue(window.cal_group.isHidden())
        window.btn_finish_alignment.click()
        self.assertIn("pulado", steps["alignment"].text())
        self.assertEqual(steps["calibration"].property("progressStatus"), "current")
        self.assertTrue(window.align_group.isHidden())
        self.assertFalse(window.cal_group.isHidden())
        self.assertTrue(window.btn_redo_step.isHidden())

        self.assertFalse(window.btn_confirm_calibration.isHidden())
        self.assertFalse(window.btn_confirm_calibration.isEnabled())
        self.assertIn("2 pontos", window.lbl_navigation_hint.text())
        window.btn_confirm_calibration.click()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        window.canvas.set_deformed_transform(0, 0, 1.1, 0)
        self._mark_calibration_points(window)
        window.txt_real_m.setText("0.5")
        window.workflow_step_labels["alignment"].click()
        self.assertTrue(window.navigation_footer.isHidden())
        window.workflow.confirm_calibration()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        window.btn_return_to_current_step.click()
        with patch.object(QMessageBox, "question") as warning:
            window.btn_confirm_calibration.click()
        warning.assert_not_called()
        self.assertTrue(window.cal_group.isHidden())
        self.assertFalse(window.mark_group.isHidden())
        self.assertFalse(window.btn_finish_marking.isEnabled())
        self.assertIn("largura W", window.lbl_navigation_hint.text())
        window.meas.on_w_px_measured(600.0)
        self.assertFalse(window.btn_finish_marking.isEnabled())
        self.assertIn("C1–C6", window.lbl_navigation_hint.text())
        for index in range(1, 7):
            window.meas.on_ci_measured(index, 20.0, 0.1)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.chk_set_w_mode.setChecked(True)
        window.workflow.apply_stage_gating()
        self.assertTrue(window.canvas.set_w_mode)
        window.btn_finish_marking.click()
        self.assertTrue(window.mark_group.isHidden())
        self.assertFalse(window.calc_panel.isHidden())
        self.assertTrue(window._summary_group.isHidden())
        self.assertIsNone(window.canvas.ctrl.active_tool())
        self.assertEqual(len(window._ci_m), 6)
        window._sync_ui_to_project()

        ref_path = str(COMPASS / "reference_vehicle_frame_000.png")
        window.btn_toggle_image_controls.click()
        self.assertFalse(window.btn_load_ref.isHidden())
        self.assertFalse(window.btn_load_dam.isHidden())
        with (
            patch.object(window.io, "pick_image_file", return_value=ref_path),
            patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.No
            ) as confirm,
        ):
            window.btn_load_ref.click()
        confirm.assert_called_once()
        self.assertEqual(window.stage, window.Stage.DONE)
        self.assertEqual(len(window._ci_m), 6)
        with (
            patch.object(window.io, "pick_image_file", return_value=ref_path),
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes),
        ):
            window.btn_load_ref.click()
        self.assertTrue(window.calc_panel.isHidden())
        self.assertFalse(window.load_group.isHidden())
        self.assertTrue(window.btn_toggle_image_controls.isHidden())
        self.assertFalse(window.btn_load_ref.isHidden())
        self.assertEqual(window.stage, window.Stage.LOAD)
        self.assertFalse(window._ci_m)
        window.btn_finish_images.click()
        self.assertTrue(window.btn_load_ref.isHidden())
        self.assertEqual(steps["alignment"].property("progressStatus"), "current")
        window.btn_finish_alignment.click()
        self.assertEqual(steps["alignment"].property("progressStatus"), "passed")
        self.assertNotIn("pulado", steps["alignment"].text())

    def test_workflow_progress_loads_results_and_tracks_invalidation(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        path = str(COMPASS / "crash3vision_reference_project.json")
        with (
            patch.object(QFileDialog, "getOpenFileName", return_value=(path, "")),
            patch.object(QMessageBox, "information"),
        ):
            window.io.load_project()
        steps = window.workflow_step_labels
        self.assertTrue(window.calc_panel.isHidden())
        self.assertFalse(window._summary_group.isHidden())
        self.assertTrue(window.mark_group.isHidden())
        self.assertEqual(
            {step: label.property("progressStatus") for step, label in steps.items()},
            dict.fromkeys(steps, "complete") | {"alignment": "passed"},
        )
        self.assertNotIn("✓", steps["alignment"].text())
        self.assertIn("Etapa superada", steps["alignment"].toolTip())

        window.workflow.restart_from_marking()
        self.assertFalse(window.mark_group.isHidden())
        self.assertTrue(window._summary_group.isHidden())
        self.assertTrue(window.btn_redo_step.isHidden())
        self.assertEqual(steps["measurement"].property("progressStatus"), "current")
        window.workflow.finish_marking()
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")
        window.calc_panel.txt_vehicle_mass.clear()
        window.calc_panel.btn_compute.click()
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")
        window.show()
        QApplication.processEvents()
        scrollbar = window._controls_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        window.calc_panel.txt_vehicle_mass.setText("1800")
        window.calc_panel.btn_compute.click()
        QApplication.processEvents()
        self.assertEqual(steps["calculation"].property("progressStatus"), "complete")
        self.assertEqual(steps["result"].property("progressStatus"), "complete")
        self.assertIn("#245b96", steps["result"].styleSheet())
        self.assertEqual(scrollbar.value(), 0)
        self.assertEqual(window.lbl_result_ees_kmh.text(), f"EES {window._damage_speed_kmh:.2f} km/h")
        self.assertEqual(window.lbl_result_ees_mps.text(), f"{window._damage_speed_mps:.2f} m/s")
        self.assertIn(f"{window._total_energy / 1000:.2f} kJ", window.lbl_result_energy.text())
        viewport = window._controls_scroll.viewport()
        for label in (window.lbl_result_ees_kmh, window.lbl_result_ees_mps, window.lbl_result_energy):
            self.assertTrue(label.isVisible())
            origin = viewport.mapFromGlobal(label.mapToGlobal(label.rect().topLeft()))
            bounds = label.rect().translated(origin)
            bounds.setWidth(max(
                label.fontMetrics().horizontalAdvance(line)
                for line in label.text().splitlines()
            ))
            self.assertTrue(viewport.rect().contains(bounds), (label.text(), bounds, viewport.rect()))
        window.workflow.invalidate_speed()
        self.assertTrue(window._summary_group.isHidden())
        self.assertFalse(window.calc_panel.isHidden())
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")

        window.workflow.restart_from_calibration()
        self.assertEqual(steps["calibration"].property("progressStatus"), "current")
        self.assertEqual(steps["measurement"].property("progressStatus"), "future")
        self._mark_calibration_points(window)
        window.txt_real_m.setText("0.5")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.btn_confirm_calibration.click()
        self.assertEqual(steps["calibration"].property("progressStatus"), "complete")
        self.assertEqual(steps["measurement"].property("progressStatus"), "current")

    def test_structural_image_uses_continuous_sobel_magnitude(self) -> None:
        image = np.zeros((120, 160), dtype=np.uint8)
        cv2.rectangle(image, (20, 20), (140, 100), 180, 3)
        cv2.line(image, (30, 90), (130, 35), 255, 2)

        structural = _structural_gradient_image(image)

        self.assertEqual(structural.dtype, np.uint8)
        self.assertEqual(structural.shape, image.shape)
        self.assertGreater(len(np.unique(structural)), 2)

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_region_geometry_is_proportional_to_image(self) -> None:
        first = make_rigid_region(1000, 800, (500.0, 400.0))
        second = make_rigid_region(2000, 1600, (1000.0, 800.0))

        self.assertAlmostEqual(first.length, 1000 * REGION_DEFAULT_LENGTH_FRACTION)
        self.assertAlmostEqual(first.height, 800 * REGION_DEFAULT_HEIGHT_FRACTION)
        self.assertAlmostEqual(second.length, first.length * 2.0)
        self.assertAlmostEqual(second.height, first.height * 2.0)
        self.assertAlmostEqual(first.height / 800.0, 0.09)

    def test_anchor_suggestions_are_distributed_and_advisory(self) -> None:
        ref_path = COMPASS / "reference_vehicle_frame_000.png"
        dam_path = COMPASS / "deformed_vehicle_frame_300.png"

        result = suggest_rigid_region_anchors(ref_path, dam_path)

        self.assertEqual(len(result.suggestions), 3)
        centers = np.array(
            [
                [item.region.center_x / 1440.0, item.region.center_y / 1024.0]
                for item in result.suggestions
            ]
        )
        distances = [
            np.linalg.norm(centers[left] - centers[right])
            for left in range(3)
            for right in range(left + 1, 3)
        ]
        self.assertGreaterEqual(min(distances), 0.20)
        self.assertTrue(all(item.probable_matches > 0 for item in result.suggestions))
        self.assertTrue(all(item.stable_scale_pairs > 1 for item in result.suggestions))
        alignment = estimate_multiscale_rigid_alignment(
            ref_path,
            dam_path,
            expand_point_anchor_regions(
                tuple(item.region for item in result.suggestions)
            ),
        )
        self.assertEqual(alignment.status, "success")

    def test_rigid_start_shows_suggestions_without_selecting_them(self) -> None:
        window = self._window()
        regions = tuple(
            make_point_anchor_region(1440, 1024, center)
            for center in ((430.0, 760.0), (720.0, 380.0), (1010.0, 760.0))
        )
        suggestion_result = RigidAnchorSuggestionResult(
            suggestions=tuple(
                RigidAnchorSuggestion(region, 1.0, 20, 8, 3, 10.0, 0.2)
                for region in regions
            ),
            reference_keypoints=100,
            deformed_keypoints=100,
        )

        with patch(
            "app.ui.main_window.suggest_rigid_region_anchors",
            return_value=suggestion_result,
        ):
            window._on_start_rigid_region_alignment()

        tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
        self.assertEqual(tool._suggestion_regions, list(regions))  # noqa: SLF001
        self.assertEqual(window._rigid_reference_regions, [])
        self.assertIn("Clique para aceitar", window.lbl_rigid_region_instruction.text())
        tool.set_visuals_visible(False)
        self.assertTrue(
            all(
                not visual.isVisible()
                for visuals in tool._suggestion_items  # noqa: SLF001
                for visual in visuals
            )
        )
        tool.set_visuals_visible(True)

    def test_suggestion_can_be_accepted_moved_or_replaced(self) -> None:
        window = self._window()
        tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
        regions = tuple(
            make_point_anchor_region(1440, 1024, center)
            for center in ((430.0, 760.0), (720.0, 380.0), (1010.0, 760.0))
        )
        tool.set_target("ref")
        tool.show_suggestions(regions)

        def event(kind: QEvent.Type) -> QMouseEvent:
            return QMouseEvent(
                kind,
                QPointF(),
                QPointF(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )

        accepted = QPointF(regions[0].center_x, regions[0].center_y)
        tool.mouse_press(window.canvas, accepted, event(QEvent.Type.MouseButtonPress))
        tool.mouse_release(
            window.canvas, accepted, event(QEvent.Type.MouseButtonRelease)
        )
        self.assertEqual(window._rigid_reference_regions[0], regions[0])

        second = tool._suggestion_regions[0]  # noqa: SLF001
        start = QPointF(second.center_x, second.center_y)
        moved = QPointF(second.center_x + 24.0, second.center_y + 18.0)
        tool.mouse_press(window.canvas, start, event(QEvent.Type.MouseButtonPress))
        tool.mouse_release(window.canvas, moved, event(QEvent.Type.MouseButtonRelease))
        self.assertAlmostEqual(window._rigid_reference_regions[1].center_x, moved.x())
        self.assertAlmostEqual(window._rigid_reference_regions[1].center_y, moved.y())

        window._rigid_reference_regions = []
        tool.clear_visuals()
        tool.set_target("ref")
        tool.show_suggestions(regions)
        replacement = QPointF(720.0, 650.0)
        tool.mouse_press(
            window.canvas, replacement, event(QEvent.Type.MouseButtonPress)
        )
        tool.mouse_release(
            window.canvas, replacement, event(QEvent.Type.MouseButtonRelease)
        )
        self.assertAlmostEqual(
            window._rigid_reference_regions[0].center_x, replacement.x()
        )
        self.assertEqual(len(tool._suggestion_regions), 2)  # noqa: SLF001

    def test_region_geometry_is_independent_of_viewport_zoom(self) -> None:
        window = self._window()
        tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
        tool.set_target("ref")
        before = tool._region_at(QPointF(720.0, 700.0), None)  # noqa: SLF001
        window.canvas.scale(3.0, 3.0)
        after = tool._region_at(QPointF(720.0, 700.0), None)  # noqa: SLF001

        self.assertEqual(before, after)

    def test_point_anchor_roi_is_proportional_and_numbered(self) -> None:
        first = make_point_anchor_region(1000, 800, (250.0, 300.0))
        second = make_point_anchor_region(2000, 1600, (500.0, 600.0))
        self.assertTrue(first.point_anchor)
        self.assertAlmostEqual(first.length, 1000 * POINT_ROI_WIDTH_FRACTION)
        self.assertAlmostEqual(first.height, 800 * POINT_ROI_HEIGHT_FRACTION)
        self.assertAlmostEqual(second.length, first.length * 2.0)
        self.assertAlmostEqual(second.height, first.height * 2.0)

        window = self._window()
        tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
        tool.set_target("ref")
        for center in ((450.0, 760.0), (720.0, 730.0), (990.0, 760.0)):
            tool.show_anchor("ref", make_point_anchor_region(1440, 1024, center))
        labels = [
            visuals[2].text()
            for visuals in tool._anchor_items["ref"]  # noqa: SLF001
        ]
        self.assertEqual(labels, ["1", "2", "3"])

    def test_point_anchor_expansion_preserves_centers_and_records_scale(self) -> None:
        anchors = tuple(
            make_point_anchor_region(1000, 800, center)
            for center in ((200.0, 300.0), (500.0, 280.0), (800.0, 300.0))
        )
        expanded = expand_point_anchor_regions(anchors)

        for original, enlarged in zip(anchors, expanded, strict=True):
            self.assertEqual(
                (enlarged.center_x, enlarged.center_y),
                (original.center_x, original.center_y),
            )
            self.assertAlmostEqual(
                enlarged.length,
                original.length * POINT_ROI_EXPANSION_FACTOR,
            )
            self.assertAlmostEqual(
                enlarged.height,
                original.height * POINT_ROI_EXPANSION_FACTOR,
            )
            self.assertAlmostEqual(
                enlarged.roi_scale,
                POINT_ROI_EXPANSION_FACTOR,
            )

    def test_click_and_drag_regions(self) -> None:
        clicked = make_rigid_region(1000, 800, (500.0, 500.0), (501.0, 501.0))
        dragged = make_rigid_region(1000, 800, (300.0, 500.0), (700.0, 600.0))

        self.assertFalse(clicked.directional)
        self.assertEqual(clicked.angle_deg, 0.0)
        self.assertTrue(dragged.directional)
        self.assertAlmostEqual(dragged.angle_deg, math.degrees(math.atan2(100, 400)))
        self.assertGreaterEqual(dragged.length, 1000 * REGION_DEFAULT_LENGTH_FRACTION)

    def test_spatial_weight_is_smooth_and_transversely_stricter(self) -> None:
        region = RigidRegion(500.0, 400.0, 600.0, 120.0)
        points = np.array(
            [[500.0, 400.0], [650.0, 400.0], [500.0, 460.0]], dtype=np.float64
        )
        weights = region_weights(points, region)

        self.assertAlmostEqual(weights[0], 1.0)
        self.assertGreater(weights[1], weights[2])
        self.assertGreater(weights[2], 0.0)

    def test_global_matches_are_grouped_spatially(self) -> None:
        points = np.array(
            [
                [90, 90],
                [100, 90],
                [110, 100],
                [90, 110],
                [100, 100],
                [110, 110],
                [890, 890],
                [900, 890],
                [910, 900],
                [890, 910],
                [900, 900],
                [910, 910],
            ],
            dtype=np.float64,
        )
        groups = _spatial_match_groups(points, 1000, 1000)

        self.assertEqual(len(groups[0]), len(points))
        self.assertTrue(any(set(group) == set(range(6)) for group in groups[1:]))
        self.assertTrue(
            any(set(group) == set(range(6, 12)) for group in groups[1:])
        )

    def test_region_support_is_measured_in_five_longitudinal_segments(self) -> None:
        region = RigidRegion(500.0, 400.0, 500.0, 80.0)
        points = np.array(
            [[275.0, 400.0], [400.0, 400.0], [500.0, 400.0],
             [600.0, 400.0], [725.0, 400.0]],
            dtype=np.float64,
        )

        self.assertEqual(
            list(_region_segment_indices(points, region)),
            [0, 1, 2, 3, 4],
        )

    def test_weak_alternative_is_not_relevant_ambiguity(self) -> None:
        best = self._candidate(inliers=13, score=3.4)
        weak_alternative = self._candidate(
            dx=-15.0,
            inliers=9,
            score=3.1,
        )
        strong_alternative = self._candidate(
            dx=-15.0,
            inliers=10,
            score=3.1,
        )

        self.assertFalse(_has_relevant_ambiguity([best, weak_alternative]))
        self.assertTrue(_has_relevant_ambiguity([best, strong_alternative]))

    def test_objective_candidate_minimums_and_second_region_fallback(self) -> None:
        diagonal = math.hypot(1440, 1024)
        valid = self._candidate(spatial_segments=3)

        self.assertTrue(
            _candidate_passes_minimums(
                valid, diagonal, has_second_region=False
            )
        )
        distributed = self._candidate(
            anchor_matches=(5, 4, 3),
            anchor_inliers=(3, 2, 1),
        )
        concentrated = self._candidate(
            anchor_matches=(12, 0, 0),
            anchor_inliers=(6, 0, 0),
        )
        self.assertTrue(
            _candidate_passes_minimums(
                distributed,
                diagonal,
                has_second_region=False,
                uses_point_anchors=True,
            )
        )
        self.assertFalse(
            _candidate_passes_minimums(
                concentrated,
                diagonal,
                has_second_region=False,
                uses_point_anchors=True,
            )
        )
        for overrides in (
            {"inliers": 5},
            {"inlier_ratio": 0.24},
            {"rmse_px": 2.01},
            {"scale": 0.89},
            {"scale": 1.11},
            {"rotation_deg": 5.01},
            {"spatial_segments": 2},
        ):
            self.assertFalse(
                _candidate_passes_minimums(
                    self._candidate(**overrides),
                    diagonal,
                    has_second_region=False,
                )
            )
        self.assertTrue(
            _candidate_passes_minimums(
                self._candidate(inlier_ratio=0.10, spatial_segments=2),
                diagonal,
                has_second_region=True,
            )
        )

    def test_directional_rotation_preserves_center_and_pixels(self) -> None:
        window = self._window()
        item = window.canvas.ctrl.ref_item
        assert item is not None
        window.canvas.set_reference_transform(13.0, -8.0, 1.02, 5.0)
        center = item.boundingRect().center()
        before_center = item.mapToScene(center)
        before_pixmap = item.pixmap().cacheKey()
        region = RigidRegion(720.0, 700.0, 800.0, 150.0, 10.0, True)
        rotation, correction = corrected_reference_rotation(5.0, region)

        window.canvas.set_reference_transform(13.0, -8.0, 1.02, rotation)

        after_center = item.mapToScene(center)
        self.assertAlmostEqual(rotation, -10.0)
        self.assertAlmostEqual(correction, -15.0)
        self.assertAlmostEqual(after_center.x(), before_center.x())
        self.assertAlmostEqual(after_center.y(), before_center.y())
        self.assertEqual(item.pixmap().cacheKey(), before_pixmap)

    def test_region_guides_matching_and_recovers_similarity(self) -> None:
        rng = np.random.default_rng(20261120)
        reference = rng.integers(0, 256, size=(480, 640), dtype=np.uint8)
        reference = cv2.GaussianBlur(reference, (3, 3), 0)
        rotation = -2.0
        scale = 0.98
        theta = math.radians(rotation)
        expected = np.array(
            [
                [scale * math.cos(theta), -scale * math.sin(theta), 8.0],
                [scale * math.sin(theta), scale * math.cos(theta), 14.0],
            ],
            dtype=np.float64,
        )
        deformed = cv2.warpAffine(
            reference,
            cv2.invertAffineTransform(expected),
            (640, 480),
        )
        region = RigidRegion(320.0, 320.0, 360.0, 130.0)

        with tempfile.TemporaryDirectory() as tmp:
            ref_path = Path(tmp) / "ref.png"
            dam_path = Path(tmp) / "dam.png"
            cv2.imwrite(str(ref_path), reference)
            cv2.imwrite(str(dam_path), deformed)
            result = estimate_rigid_region_alignment(ref_path, dam_path, region)

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.best)
        assert result.best is not None
        self.assertLess(result.diagnostics.region_keypoints, result.diagnostics.reference_keypoints)
        self.assertAlmostEqual(result.best.dx, 8.0, delta=0.8)
        self.assertAlmostEqual(result.best.dy, 14.0, delta=0.8)
        self.assertAlmostEqual(result.best.rotation_deg, rotation, delta=0.15)
        self.assertAlmostEqual(result.best.scale, scale, delta=0.005)

        theta = math.radians(result.best.rotation_deg)
        linear = np.array(
            [
                [
                    result.best.scale * math.cos(theta),
                    -result.best.scale * math.sin(theta),
                ],
                [
                    result.best.scale * math.sin(theta),
                    result.best.scale * math.cos(theta),
                ],
            ]
        )
        self.assertAlmostEqual(float(np.dot(linear[:, 0], linear[:, 1])), 0.0)
        self.assertAlmostEqual(
            float(np.linalg.norm(linear[:, 0])),
            float(np.linalg.norm(linear[:, 1])),
        )

    def test_three_point_anchors_report_independent_contributions(self) -> None:
        reference = cv2.imread(
            str(COMPASS / "reference_vehicle_frame_000.png"),
            cv2.IMREAD_GRAYSCALE,
        )
        anchors = tuple(
            make_point_anchor_region(reference.shape[1], reference.shape[0], center)
            for center in ((430.0, 775.0), (720.0, 735.0), (1010.0, 775.0))
        )
        result = estimate_rigid_region_alignment(
            COMPASS / "reference_vehicle_frame_000.png",
            COMPASS / "deformed_vehicle_frame_300.png",
            anchors,
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.diagnostics.anchor_keypoints), 3)
        self.assertEqual(len(result.diagnostics.anchor_matches), 3)
        self.assertTrue(all(value > 0 for value in result.diagnostics.anchor_matches))
        assert result.best is not None
        self.assertEqual(len(result.best.anchor_inliers), 3)
        self.assertGreaterEqual(
            sum(value > 0 for value in result.best.anchor_inliers),
            2,
        )

    def test_compass_narrow_region_requests_fallback_for_spatial_support(self) -> None:
        result = estimate_rigid_region_alignment(
            COMPASS / "reference_vehicle_frame_000.png",
            COMPASS / "deformed_vehicle_frame_300.png",
            make_rigid_region(1440, 1024, (720.0, 760.0)),
        )

        self.assertEqual(result.status, "needs_second_region")
        self.assertEqual(result.reason, "weak_solution")
        self.assertTrue(result.candidates)

    def test_deformed_fallback_height_tracks_reference_vertical_span(self) -> None:
        aligned = (
            RigidRegion(200.0, 400.0, 100.0, 80.0, point_anchor=True),
            RigidRegion(500.0, 402.0, 100.0, 80.0, point_anchor=True),
            RigidRegion(800.0, 398.0, 100.0, 80.0, point_anchor=True),
        )
        spread = (
            RigidRegion(200.0, 300.0, 100.0, 80.0, point_anchor=True),
            RigidRegion(500.0, 400.0, 100.0, 80.0, point_anchor=True),
            RigidRegion(800.0, 500.0, 100.0, 80.0, point_anchor=True),
        )

        low = make_adaptive_deformed_region(
            1000, 800, (500.0, 400.0), aligned, 800
        )
        tall = make_adaptive_deformed_region(
            1000, 800, (500.0, 400.0), spread, 800
        )

        self.assertAlmostEqual(
            low.height,
            800 * DEFORMED_REGION_MIN_HEIGHT_FRACTION,
        )
        self.assertGreater(tall.height, low.height)

    def test_alignment_controls_are_grouped_and_contextual(self) -> None:
        window = self._window()

        self.assertEqual(window.lbl_alignment_title.text(), "Alinhamento das imagens")
        self.assertEqual(window.btn_toggle_manual_alignment.text(), "▸ Ajuste manual")
        self.assertIs(window.rad_alignment_auto.parentWidget(), window.alignment_method_row)
        self.assertIs(window.rad_alignment_rigid.parentWidget(), window.alignment_method_row)
        self.assertIs(window.btn_start_alignment.parentWidget(), window.alignment_card)
        self.assertIs(
            window.lbl_rigid_region_instruction.parentWidget(),
            window.alignment_card,
        )
        self.assertIs(window.alignment_actions_widget.parentWidget(), window.alignment_card)
        self.assertIs(window.btn_finish_alignment.parentWidget(), window.navigation_footer)
        self.assertIs(window.navigation_footer.parentWidget(), window._controls_scroll.parentWidget())
        self.assertTrue(window.rad_alignment_auto.isChecked())
        self.assertFalse(window.rad_alignment_rigid.isChecked())
        self.assertIs(window.nudge_box.parentWidget(), window.alignment_advanced)
        self.assertFalse(window.lbl_rigid_region_instruction.isHidden())
        self.assertEqual(
            window.lbl_rigid_region_instruction.text(),
            "Escolha um método de alinhamento ou avance direto para a calibração.",
        )
        self.assertTrue(window.alignment_actions_widget.isHidden())
        self.assertTrue(window.btn_rigid_apply.isHidden())
        self.assertTrue(window.btn_rigid_try_again.isHidden())
        self.assertTrue(window.btn_rigid_cancel.isHidden())

    def test_manual_sections_collapse_without_leaving_image_drag_active(self) -> None:
        window = self._window()
        self.assertTrue(window.fine_adjust_group.isHidden())
        self.assertTrue(window.alignment_advanced.isHidden())
        window.btn_toggle_manual_alignment.click()
        self.assertFalse(window.fine_adjust_group.isHidden())
        self.assertEqual(window.btn_toggle_manual_alignment.text(), "▾ Ajuste manual")
        self.assertFalse(window.nudge_box.isVisibleTo(window.fine_adjust_group))
        window.btn_toggle_advanced_alignment.click()
        self.assertTrue(window.nudge_box.isVisibleTo(window.fine_adjust_group))
        self.assertEqual(window.nudge_box.title(), "Translação (px)")
        self.assertEqual(window.lbl_step_deg.text(), "Passo da rotação (°):")
        self.assertEqual(window.lbl_step_pct.text(), "Passo da escala (%):")
        before = window.canvas.get_deformed_transform()
        window.btn_right.click()
        self.assertEqual(window.canvas.get_deformed_transform()["x"], before["x"] + 1)
        self.assertFalse(window.alignment_advanced.isHidden())
        window.show()
        QApplication.processEvents()
        self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0)
        self.assertEqual(window.btn_finish_alignment.width(),
                         window.navigation_footer.layout().contentsRect().width())
        self.assertEqual(
            window.btn_toggle_image_controls.width(),
            window.load_group.layout().contentsRect().width(),
        )
        window._set_language_and_refresh("en")
        QApplication.processEvents()
        self.assertEqual(window.btn_toggle_advanced_alignment.text(), "▾ Precision adjustments")
        self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0)
        window.resize(900, 450)
        QApplication.processEvents()
        scrollbar = window._controls_scroll.verticalScrollBar()
        self.assertGreater(scrollbar.maximum(), 0)
        before_scroll = window.navigation_footer.pos()
        scrollbar.setValue(scrollbar.maximum())
        self.assertTrue(window.btn_finish_alignment.isVisible())
        self.assertEqual(window.navigation_footer.pos(), before_scroll)
        bar = window.canvas_view_bar
        self.assertEqual(bar.width(), window.canvas.width())
        self.assertLessEqual(
            abs(
                bar.mapToGlobal(QPoint(0, bar.height())).y()
                - window.navigation_footer.mapToGlobal(
                    QPoint(0, window.navigation_footer.height())
                ).y()
            ),
            4,
        )
        window.btn_toggle_advanced_alignment.click()
        self.assertTrue(window.alignment_advanced.isHidden())
        self.assertTrue(window.sc_nudge_right.isEnabled())
        window.canvas.setFocus()
        QTest.keyClick(window.canvas, Qt.Key.Key_Right)
        self.assertEqual(window.canvas.get_deformed_transform()["x"], before["x"] + 2)
        window.btn_rotate_plus.click()
        window.btn_scale_plus.click()
        changed = window.canvas.get_deformed_transform()
        self.assertEqual(changed["rotation_deg"], before["rotation_deg"] + 1)
        self.assertAlmostEqual(changed["scale"], before["scale"] * 1.01)
        window.chk_alignment_mode.click()
        self.assertTrue(window.canvas.alignment_mode)
        viewport = window.canvas.viewport()
        start = viewport.rect().center()
        end = start + QPoint(20, 0)
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(viewport, end)
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=end)
        self.assertGreater(window.canvas.get_deformed_transform()["x"], changed["x"])
        window.btn_toggle_manual_alignment.click()
        self.assertTrue(window.fine_adjust_group.isHidden())
        self.assertFalse(window.chk_alignment_mode.isChecked())
        self.assertFalse(window.canvas.alignment_mode)
        self.assertEqual(window.canvas.dragMode(), QGraphicsView.DragMode.ScrollHandDrag)
        self.assertTrue(window.sc_nudge_right.isEnabled())
        window.btn_finish_alignment.click()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)

    def test_reset_alignment_confirms_only_changed_transforms(self) -> None:
        window = self._window()
        window.btn_toggle_manual_alignment.click()
        original = window.canvas.get_reference_transform()
        with patch.object(QMessageBox, "question") as question:
            window.btn_reset_alignment.click()
        question.assert_not_called()
        window.canvas.set_reference_transform(3, 4, 1.1, 2)
        window.canvas.set_deformed_transform(-5, 6, 0.9, -3)
        before = (window.canvas.get_reference_transform(), window.canvas.get_deformed_transform())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as question:
            window.btn_reset_alignment.click()
        question.assert_called_once()
        self.assertEqual((window.canvas.get_reference_transform(), window.canvas.get_deformed_transform()), before)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.btn_reset_alignment.click()
        self.assertEqual(window.canvas.get_reference_transform(), original)
        self.assertEqual(window.canvas.get_deformed_transform(), original)

    def test_opacity_remains_available_after_alignment_and_tracks_images(
        self,
    ) -> None:
        window = self._window()
        ref_path = COMPASS / "reference_vehicle_frame_000.png"
        dam_path = COMPASS / "deformed_vehicle_frame_300.png"

        self.assertEqual(
            window.dockWidgetArea(window._controls_dock),
            Qt.DockWidgetArea.LeftDockWidgetArea,
        )
        self.assertIs(window.opacity_slider.parentWidget(), window.canvas_view_bar)
        self.assertTrue(window.opacity_slider.isEnabled())
        window.workflow.finish_alignment()

        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertFalse(window.nudge_box.isEnabled())
        window.opacity_slider.setValue(35)
        self.assertAlmostEqual(window.project.opacity, 0.35)
        self.assertEqual(window.lbl_opacity_percent.text(), "35%")
        self.assertAlmostEqual(window.canvas.ctrl.dam_item.opacity(), 0.35)

        for stage in (window.Stage.MARKING, window.Stage.DONE):
            window.workflow.set_stage(stage)
            self.assertTrue(window.opacity_slider.isEnabled())
            self.assertFalse(window.fine_adjust_group.isEnabled())

        window.canvas.load_reference(str(ref_path))
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertAlmostEqual(window.canvas.ctrl.dam_item.opacity(), 0.35)

        window.canvas.clear_images()
        self.assertFalse(window.opacity_slider.isEnabled())

        window.canvas.load_deformed(str(dam_path))
        self.assertFalse(window.opacity_slider.isEnabled())
        self.assertEqual(window.canvas.ctrl.dam_item.opacity(), 1.0)
        window.canvas.load_reference(str(ref_path))
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertAlmostEqual(window.canvas.ctrl.dam_item.opacity(), 0.35)
        window.canvas.load_deformed(str(dam_path))
        self.assertAlmostEqual(window.canvas.ctrl.dam_item.opacity(), 0.35)

    def test_saved_overlay_opacity_is_used_only_with_both_images(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            dam_path, ref_path = folder / "dam.png", folder / "ref.png"
            for path, color in ((dam_path, Qt.GlobalColor.red), (ref_path, Qt.GlobalColor.blue)):
                image = QImage(640, 360, QImage.Format.Format_RGB32)
                image.fill(color)
                self.assertTrue(image.save(str(path)))
            project_path = folder / "legacy.json"
            export_path = folder / "export.png"
            data = {"name": "Legacy", "dam_path": str(dam_path), "opacity": 0.27}
            for paired in (False, True, False):
                if paired:
                    data["ref_path"] = str(ref_path)
                else:
                    data.pop("ref_path", None)
                original = json.dumps(data)
                project_path.write_text(original, encoding="utf-8")
                with (
                    patch.object(QFileDialog, "getOpenFileName", return_value=(str(project_path), "")),
                    patch.object(QMessageBox, "information"),
                ):
                    window.io.load_project()
                self.assertEqual(window.stage, window.Stage.ALIGNMENT)
                self.assertTrue(window.btn_finish_images.isHidden())
                self.assertEqual(window.opacity_slider.isEnabled(), paired)
                self.assertEqual(window.opacity_slider.value(), 27)
                self.assertAlmostEqual(window.project.opacity, 0.27)
                self.assertAlmostEqual(window.canvas.ctrl.dam_item.opacity(), 0.27 if paired else 1.0)
                window.canvas.export_scene_png(str(export_path))
                exported = QImage(str(export_path))
                self.assertFalse(exported.isNull())
                pixel = exported.pixelColor(exported.rect().center())
                self.assertEqual(pixel.alpha(), 255)
                if paired:
                    self.assertGreater(pixel.blue(), pixel.red())
                else:
                    self.assertEqual(pixel.getRgb(), (255, 0, 0, 255))
                self.assertEqual(project_path.read_text(encoding="utf-8"), original)
            window.btn_finish_alignment.click()
            self.assertEqual(window.stage, window.Stage.CALIBRATION)

    def test_resizing_left_dock_preserves_overlay_and_png_exports(self) -> None:
        window = self._window()
        window.show()
        QApplication.processEvents()
        canvas = window.canvas
        state = canvas.get_overlay_state()
        state.update(
            cal_p1={"x": 300, "y": 500},
            cal_p2={"x": 600, "y": 500},
            w_p1={"x": 400, "y": 700},
            w_p2={"x": 1000, "y": 700},
            slice_x=[400, 520, 640, 760, 880, 1000],
            c_points={"C1": {"ref": {"x": 400, "y": 700},
                             "def": {"x": 400, "y": 740}}},
            m_per_px=0.005,
        )
        canvas.restore_overlay_state(state)
        before = canvas.get_overlay_state()
        original_width = canvas.viewport().width()
        self.assertEqual(canvas.dragMode(), QGraphicsView.DragMode.ScrollHandDrag)

        with tempfile.TemporaryDirectory() as tmp:
            first = str(Path(tmp) / "before.png")
            second = str(Path(tmp) / "after.png")
            view = str(Path(tmp) / "view.png")
            canvas.export_scene_png(first)
            window.resizeDocks(
                [window._controls_dock],
                [window._controls_dock.width() + 150],
                Qt.Orientation.Horizontal,
            )
            QApplication.processEvents()
            self.assertLess(canvas.viewport().width(), original_width)
            zoom_before = canvas.transform().m11()
            canvas.ctrl.wheel_zoom(2.0)
            self.assertAlmostEqual(canvas.transform().m11(), zoom_before * 2.0)
            scrollbar = canvas.horizontalScrollBar()
            position = scrollbar.value()
            scrollbar.setValue(
                scrollbar.maximum() if position != scrollbar.maximum()
                else scrollbar.minimum()
            )
            self.assertNotEqual(scrollbar.value(), position)
            canvas.export_scene_png(second)
            canvas.export_current_view_png(view)
            self.assertGreater(QImage(first).width(), 0)
            self.assertEqual(QImage(first), QImage(second))
            self.assertEqual(QImage(view).size(), canvas.viewport().grab().size())
        self.assertEqual(canvas.get_overlay_state(), before)

    def test_single_start_button_routes_selected_method(self) -> None:
        window = self._window()
        with patch.object(window, "_on_auto_align") as auto_align:
            window.rad_alignment_auto.setChecked(True)
            window.btn_start_alignment.click()
            auto_align.assert_called_once_with()

        with patch.object(
            window, "_on_start_rigid_region_alignment"
        ) as rigid_align:
            window.rad_alignment_rigid.setChecked(True)
            window.btn_start_alignment.click()
            rigid_align.assert_called_once_with()

    def test_deformed_image_alone_can_continue_directly_to_calibration(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        self.assertTrue(window.btn_finish_alignment.isHidden())
        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            window.io.load_dam()
        self.assertEqual(window.stage, window.Stage.LOAD)
        window.btn_finish_images.click()

        self.assertFalse(window.btn_finish_alignment.isHidden())
        self.assertFalse(window.btn_start_alignment.isEnabled())
        self.assertTrue(window.btn_start_alignment.isHidden())
        self.assertTrue(window.alignment_method_row.isHidden())
        self.assertFalse(window.btn_toggle_manual_alignment.isHidden())
        window.btn_finish_alignment.click()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)

    def test_two_images_can_continue_with_or_without_manual_adjustment(self) -> None:
        for manual in (False, True):
            with self.subTest(manual=manual):
                window = self._window()
                baseline = window.canvas.get_deformed_transform()
                if manual:
                    window.canvas.nudge_selected(4.0, -2.0)
                expected = window.canvas.get_deformed_transform()
                self.assertEqual(expected["x"], baseline["x"] + (4 if manual else 0))

                self.assertFalse(window.btn_finish_alignment.isHidden())
                window.btn_finish_alignment.click()
                self.assertEqual(window.stage, window.Stage.CALIBRATION)
                self.assertEqual(window.canvas.get_deformed_transform(), expected)

    def test_weak_first_search_requests_second_region(self) -> None:
        blank = np.zeros((400, 600), dtype=np.uint8)
        cv2.putText(blank, "texture", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)
        region = RigidRegion(500.0, 330.0, 100.0, 60.0)
        with tempfile.TemporaryDirectory() as tmp:
            ref_path = Path(tmp) / "ref.png"
            dam_path = Path(tmp) / "dam.png"
            cv2.imwrite(str(ref_path), blank)
            cv2.imwrite(str(dam_path), blank)
            result = estimate_rigid_region_alignment(ref_path, dam_path, region)

        self.assertEqual(result.status, "needs_second_region")

    def test_ui_fallback_requests_and_uses_second_region(self) -> None:
        candidate = self._candidate()
        weak = RigidAlignmentResult(
            "needs_second_region",
            "weak_solution",
            RigidAlignmentDiagnostics(100, 100, 20, 7),
            (),
        )
        success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(100, 100, 20, 12),
            (candidate,),
        )
        reference_region = RigidRegion(720.0, 700.0, 800.0, 150.0)
        deformed_region = RigidRegion(720.0, 640.0, 800.0, 150.0)
        window = self._window()

        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                side_effect=(weak, weak, weak, success),
            ) as estimator,
            patch(
                "app.ui.main_window.estimate_multiscale_rigid_alignment",
                return_value=weak,
            ),
            patch.object(QMessageBox, "information"),
        ):
            window._on_start_rigid_region_alignment()
            self._select_three_reference_points(window)
            self.assertEqual(
                window._rigid_instruction_key,
                "alignment.rigid.instruction.deformed",
            )
            self.assertTrue(
                window.canvas.ctrl.controller.flags.rigid_region_mode
            )
            self.assertEqual(
                window.canvas.ctrl._rigid_region_tool._target,  # noqa: SLF001
                "dam",
            )
            window._on_rigid_region_selected("dam", deformed_region)

        self.assertEqual(estimator.call_count, 4)
        self.assertIsNone(estimator.call_args_list[0].kwargs["deformed_region"])
        self.assertIsNone(
            estimator.call_args_list[1].kwargs.get("deformed_region")
        )
        self.assertEqual(
            estimator.call_args_list[3].kwargs["deformed_region"],
            deformed_region,
        )
        self.assertTrue(window._rigid_preview_active)
        self.assertFalse(window.btn_finish_alignment.isHidden())
        self.assertFalse(window.btn_finish_alignment.isEnabled())
        self.assertTrue(window.alignment_method_row.isHidden())
        self.assertTrue(window.btn_start_alignment.isHidden())
        self.assertTrue(window.btn_toggle_manual_alignment.isHidden())
        self.assertFalse(window.btn_rigid_try_again.isHidden())
        window.show()
        QApplication.processEvents()
        self.assertEqual(window.btn_rigid_apply.accessibleName(), "Aplicar alinhamento")
        self.assertEqual(window.btn_rigid_cancel.accessibleName(), "Descartar prévia")
        self.assertEqual(window.btn_rigid_apply.y(), window.btn_rigid_cancel.y())
        self.assertLess(window.btn_rigid_apply.x(), window.btn_rigid_cancel.x())
        self.assertEqual(window._controls_scroll.horizontalScrollBar().maximum(), 0)
        self.assertFalse(window.btn_reset_alignment.isEnabled())
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertFalse(window.sc_nudge_right.isEnabled())
        self.assertFalse(window.workflow_step_labels["images"].isEnabled())
        window._view_workflow_step("images")
        self.assertIsNone(window._viewed_step)
        window._on_finish_alignment()
        self.assertEqual(window.stage, window.Stage.ALIGNMENT)
        self.assertTrue(window._rigid_preview_active)
        self.assertTrue(window.btn_rigid_apply.isEnabled())

    def test_expanded_rois_are_tried_before_manual_fallback(self) -> None:
        weak = RigidAlignmentResult(
            "needs_second_region",
            "weak_solution",
            RigidAlignmentDiagnostics(100, 100, 20, 7, roi_scale=1.0),
            (),
        )
        expanded_success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(100, 100, 30, 12, roi_scale=1.5),
            (self._candidate(),),
        )
        window = self._window()
        with patch(
            "app.ui.main_window.estimate_rigid_region_alignment",
            side_effect=(weak, expanded_success),
        ) as estimator:
            window._on_start_rigid_region_alignment()
            self._select_three_reference_points(window)

        self.assertEqual(estimator.call_count, 2)
        expanded_regions = estimator.call_args_list[1].args[2]
        self.assertTrue(
            all(region.roi_scale == 1.5 for region in expanded_regions)
        )
        self.assertTrue(window._rigid_preview_active)
        self.assertEqual(
            window._rigid_alignment_result.diagnostics.roi_scale,
            1.5,
        )

    def test_multiscale_fallback_precedes_structural_search(self) -> None:
        weak = RigidAlignmentResult(
            "needs_second_region",
            "weak_solution",
            RigidAlignmentDiagnostics(100, 100, 20, 7),
            (),
        )
        multiscale_success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(
                100,
                100,
                30,
                12,
                roi_scale=1.5,
                expansion_attempted=True,
                normalized_multiscale=True,
                detection_scales=(2.0, 0.9),
            ),
            (self._candidate(),),
        )
        window = self._window()
        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                side_effect=(weak, weak),
            ) as estimator,
            patch(
                "app.ui.main_window.estimate_multiscale_rigid_alignment",
                return_value=multiscale_success,
            ) as multiscale,
            patch.object(QMessageBox, "information") as information,
        ):
            window._on_start_rigid_region_alignment()
            self._select_three_reference_points(window)

        self.assertEqual(estimator.call_count, 2)
        multiscale.assert_called_once()
        self.assertTrue(window._rigid_preview_active)
        self.assertTrue(
            window._rigid_alignment_result.diagnostics.normalized_multiscale
        )
        information.assert_not_called()

    def test_structural_fallback_precedes_manual_second_region(self) -> None:
        weak = RigidAlignmentResult(
            "needs_second_region",
            "weak_solution",
            RigidAlignmentDiagnostics(100, 100, 20, 7),
            (),
        )
        structural_success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(
                100,
                100,
                30,
                12,
                roi_scale=1.5,
                expansion_attempted=True,
                structural_fallback=True,
            ),
            (self._candidate(),),
        )
        window = self._window()
        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                side_effect=(weak, weak, structural_success),
            ) as estimator,
            patch(
                "app.ui.main_window.estimate_multiscale_rigid_alignment",
                return_value=weak,
            ),
            patch.object(QMessageBox, "information") as information,
        ):
            window._on_start_rigid_region_alignment()
            self._select_three_reference_points(window)

        self.assertEqual(estimator.call_count, 3)
        structural_call = estimator.call_args_list[2]
        self.assertTrue(structural_call.kwargs["structural_fallback"])
        self.assertTrue(structural_call.kwargs["expansion_attempted"])
        self.assertTrue(window._rigid_preview_active)
        self.assertEqual(
            window._rigid_alignment_result.diagnostics.structural_fallback,
            True,
        )
        information.assert_not_called()

    def test_preview_apply_try_again_cancel_and_persistence(self) -> None:
        candidate = self._candidate()
        success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(100, 100, 20, 15),
            (candidate,),
        )
        region = RigidRegion(720.0, 700.0, 800.0, 150.0)

        window = self._window()
        baseline = window.canvas.get_deformed_transform()
        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                return_value=success,
            ),
            patch.object(QMessageBox, "information"),
        ):
            window._on_start_rigid_region_alignment()
            self.assertIn(
                "Pontos sugeridos exibidos",
                window.lbl_rigid_region_instruction.text(),
            )
            self.assertFalse(window.alignment_actions_widget.isHidden())
            self.assertTrue(window.btn_rigid_apply.isHidden())
            self.assertFalse(window.btn_rigid_cancel.isHidden())
            self._select_three_reference_points(window)
        self.assertTrue(window._rigid_preview_active)
        self.assertEqual(
            window.lbl_rigid_region_instruction.text(),
            "Prévia pronta. Use-a ou tente novamente.",
        )
        self.assertFalse(window.alignment_actions_widget.isHidden())
        self.assertFalse(window.btn_rigid_apply.isHidden())
        self.assertNotEqual(window.canvas.get_deformed_transform(), baseline)
        self.assertEqual(window.project.dam_transform.to_dict(), baseline)

        window._on_try_another_rigid_region()
        self.assertEqual(window.canvas.get_deformed_transform(), baseline)
        self.assertFalse(window._rigid_preview_active)

        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                return_value=success,
            ),
            patch.object(QMessageBox, "information"),
        ):
            self._select_three_reference_points(window)
            tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
            tool.clear_visuals()
            for region in window._rigid_reference_regions:
                tool.show_anchor("ref", region)
            preview = window.canvas.get_deformed_transform()
            window._on_apply_rigid_region_preview()
        self.assertEqual(window.project.dam_transform.to_dict(), preview)
        self.assertEqual(len(window._last_applied_rigid_reference_regions), 3)
        self.assertEqual(tool._anchor_items["ref"], [])  # noqa: SLF001
        self.assertTrue(window.alignment_actions_widget.isHidden())
        self.assertTrue(window.lbl_rigid_region_instruction.isHidden())
        self.assertFalse(window.btn_finish_alignment.isHidden())
        restored = Project.from_dict(window.project.to_dict())
        self.assertEqual(restored.dam_transform.to_dict(), preview)

        window._on_finish_alignment()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        self.assertFalse(window.align_group.isEnabled())
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertFalse(window.nudge_box.isEnabled())
        self.assertTrue(window.cal_group.isEnabled())
        self.assertTrue(window.btn_finish_alignment.isHidden())

        window._on_restart_alignment()
        window._on_start_rigid_region_alignment()
        self.assertEqual(window._last_applied_rigid_reference_regions, ())
        window._on_cancel_rigid_region_alignment()
        self.assertFalse(window._rigid_preview_active)
        self.assertIsNone(window._rigid_baseline_ref_transform)

    def test_preview_is_invalidated_by_external_transform_change(self) -> None:
        window = self._window()
        success = RigidAlignmentResult(
            "success",
            "ok",
            RigidAlignmentDiagnostics(100, 100, 20, 15),
            (self._candidate(),),
        )
        with (
            patch(
                "app.ui.main_window.estimate_rigid_region_alignment",
                return_value=success,
            ),
            patch.object(QMessageBox, "information"),
        ):
            window._on_start_rigid_region_alignment()
            self._select_three_reference_points(window)

        window.canvas.nudge_selected(1.0, 0.0)

        self.assertFalse(window._rigid_preview_active)
        self.assertIsNone(window._rigid_alignment_result)
        self.assertFalse(window.btn_rigid_apply.isVisible())

    def test_image_reload_clears_three_points_and_cancels_selection(self) -> None:
        window = self._window()
        tool = window.canvas.ctrl._rigid_region_tool  # noqa: SLF001
        ref_path = COMPASS / "reference_vehicle_frame_000.png"
        dam_path = COMPASS / "deformed_vehicle_frame_300.png"

        for loader, path in (
            (window.canvas.load_reference, ref_path),
            (window.canvas.load_deformed, dam_path),
        ):
            window._on_start_rigid_region_alignment()
            for center in ((450.0, 760.0), (720.0, 730.0)):
                region = make_point_anchor_region(1440, 1024, center)
                tool.show_anchor("ref", region)
                window._on_rigid_region_selected("ref", region)
            window._last_applied_rigid_reference_regions = tuple(
                window._rigid_reference_regions
            )
            loader(str(path))
            self.assertEqual(tool._anchor_items["ref"], [])  # noqa: SLF001
            self.assertEqual(window._rigid_reference_regions, [])
            self.assertFalse(window.canvas.ctrl.controller.flags.rigid_region_mode)
            self.assertIsNone(window._rigid_baseline_ref_transform)
            self.assertEqual(window._last_applied_rigid_reference_regions, ())

        window._on_start_rigid_region_alignment()
        region = make_point_anchor_region(1440, 1024, (450.0, 760.0))
        tool.show_anchor("ref", region)
        window._on_rigid_region_selected("ref", region)
        window.canvas.clear_images()
        self.assertEqual(tool._anchor_items["ref"], [])  # noqa: SLF001
        self.assertEqual(window._rigid_reference_regions, [])
        self.assertFalse(window.canvas.ctrl.controller.flags.rigid_region_mode)

    def _window(self) -> MainWindow:
        window = MainWindow()
        self.addCleanup(window.close)
        ref_path = COMPASS / "reference_vehicle_frame_000.png"
        dam_path = COMPASS / "deformed_vehicle_frame_300.png"
        window.canvas.load_reference(str(ref_path))
        window.canvas.load_deformed(str(dam_path))
        window.project.ref_path = str(ref_path)
        window.project.dam_path = str(dam_path)
        window.workflow.set_stage(window.Stage.ALIGNMENT)
        window.canvas.set_alignment_target("dam")
        window._update_auto_align_availability()
        return window

    @staticmethod
    def _select_three_reference_points(window: MainWindow) -> None:
        for center in ((480.0, 760.0), (720.0, 730.0), (960.0, 760.0)):
            window._on_rigid_region_selected(
                "ref",
                make_point_anchor_region(1440, 1024, center),
            )

    @staticmethod
    def _candidate(**overrides: object) -> RigidAlignmentCandidate:
        values: dict[str, object] = {
            "dx": 8.0,
            "dy": 14.0,
            "rotation_deg": -2.0,
            "scale": 0.98,
            "inliers": 12,
            "inlier_ratio": 0.6,
            "rmse_px": 0.8,
            "weighted_rmse_px": 0.7,
            "mean_region_weight": 0.8,
            "score": 6.0,
            "spatial_segments": 5,
            "anchor_matches": (),
            "anchor_inliers": (),
        }
        values.update(overrides)
        return RigidAlignmentCandidate(
            dx=float(values["dx"]),
            dy=float(values["dy"]),
            rotation_deg=float(values["rotation_deg"]),
            scale=float(values["scale"]),
            inliers=int(values["inliers"]),
            inlier_ratio=float(values["inlier_ratio"]),
            rmse_px=float(values["rmse_px"]),
            weighted_rmse_px=float(values["weighted_rmse_px"]),
            mean_region_weight=float(values["mean_region_weight"]),
            score=float(values["score"]),
            spatial_segments=int(values["spatial_segments"]),
            anchor_matches=tuple(values["anchor_matches"]),
            anchor_inliers=tuple(values["anchor_inliers"]),
        )


if __name__ == "__main__":
    unittest.main()
