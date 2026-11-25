from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.auto_alignment import (
    AlignmentHypothesis,
    AlignmentDiagnostics,
    AutoAlignmentResult,
    AutoAlignmentError,
    _ExtractedHypothesis,
    _classify_confidence,
    _refine_hypothesis_in_rigid_region,
    estimate_auto_alignment,
)
from app.core.project import Project
from app.ui.canvas_view import CanvasView
from app.ui.main_window import MainWindow


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPASS_DIR = (
    REPOSITORY_ROOT / "examples" / "nhtsa_jeep_compass_2024_m20240300"
)


def _texture(rng: np.random.Generator, height: int, width: int) -> np.ndarray:
    image = rng.integers(0, 256, size=(height, width), dtype=np.uint8)
    return cv2.GaussianBlur(image, (3, 3), 0)


class AutoAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _estimate_arrays(
        self,
        reference: np.ndarray,
        deformed: np.ndarray,
        **kwargs,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            ref_path = Path(tmp) / "reference.png"
            dam_path = Path(tmp) / "deformed.png"
            self.assertTrue(cv2.imwrite(str(ref_path), reference))
            self.assertTrue(cv2.imwrite(str(dam_path), deformed))
            return estimate_auto_alignment(ref_path, dam_path, **kwargs)

    def test_compass_selects_vehicle_hypothesis_over_static_background(self) -> None:
        result = estimate_auto_alignment(
            COMPASS_DIR / "reference_vehicle_frame_000.png",
            COMPASS_DIR / "deformed_vehicle_frame_300.png",
        )

        self.assertEqual(result.confidence, "medium")
        self.assertEqual(len(result.hypotheses), 3)
        self.assertIsNone(result.selected)
        best = result.best
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.model_index, 3)
        self.assertAlmostEqual(best.dx, 9.32, delta=3.0)
        self.assertAlmostEqual(best.dy, 85.36, delta=3.0)
        self.assertAlmostEqual(best.rotation_deg, -0.28, delta=0.5)
        self.assertAlmostEqual(best.scale, 0.9776, delta=0.01)
        self.assertGreater(best.score, result.hypotheses[1].score)
        self.assertIn("insufficient_inliers", result.confidence_reasons)
        background = next(item for item in result.hypotheses if item.model_index == 1)
        self.assertTrue(background.near_identity)
        self.assertGreater(background.edge_fraction, 0.65)
        self.assertLess(background.score, best.score)

    def test_known_similarity_is_recovered(self) -> None:
        rng = np.random.default_rng(20261119)
        reference = _texture(rng, 480, 640)
        expected_rotation = -2.0
        expected_scale = 0.98
        theta = math.radians(expected_rotation)
        expected = np.array(
            [
                [
                    expected_scale * math.cos(theta),
                    -expected_scale * math.sin(theta),
                    8.0,
                ],
                [
                    expected_scale * math.sin(theta),
                    expected_scale * math.cos(theta),
                    14.0,
                ],
            ],
            dtype=np.float64,
        )
        deformed = cv2.warpAffine(
            reference,
            cv2.invertAffineTransform(expected),
            (reference.shape[1], reference.shape[0]),
        )

        result = self._estimate_arrays(reference, deformed)
        selected = result.selected
        self.assertEqual(result.confidence, "high")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertAlmostEqual(selected.dx, 8.0, delta=0.8)
        self.assertAlmostEqual(selected.dy, 14.0, delta=0.8)
        self.assertAlmostEqual(selected.rotation_deg, expected_rotation, delta=0.15)
        self.assertAlmostEqual(selected.scale, expected_scale, delta=0.005)

    def test_current_180_degree_gui_rotation_is_used(self) -> None:
        rng = np.random.default_rng(66)
        reference = np.zeros((480, 640), dtype=np.uint8)
        reference[250:420, 170:470] = _texture(rng, 170, 300)
        deformed = cv2.rotate(reference, cv2.ROTATE_180)

        result = self._estimate_arrays(
            reference,
            deformed,
            deformed_transform={
                "x": 0.0,
                "y": 0.0,
                "scale": 1.0,
                "rotation_deg": 180.0,
            },
        )
        selected = result.selected
        self.assertEqual(result.confidence, "high")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertLess(math.hypot(selected.dx, selected.dy), 1.0)
        self.assertAlmostEqual(selected.rotation_deg, 0.0, delta=0.02)
        self.assertAlmostEqual(selected.scale, 1.0, delta=0.001)

    def test_static_background_does_not_beat_vehicle_motion(self) -> None:
        rng = np.random.default_rng(44)
        reference = cv2.GaussianBlur(_texture(rng, 480, 640), (5, 5), 0)
        deformed = reference.copy()
        patch = _texture(rng, 150, 260)
        reference[270:420, 190:450] = patch
        deformed[292:442, 208:468] = patch

        result = self._estimate_arrays(reference, deformed)
        selected = result.selected
        self.assertEqual(result.confidence, "high")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.model_index, 2)
        self.assertAlmostEqual(selected.dx, -18.0, delta=0.5)
        self.assertAlmostEqual(selected.dy, -22.0, delta=0.5)
        identity = next(item for item in result.hypotheses if item.model_index == 1)
        self.assertGreater(identity.inliers, selected.inliers)
        self.assertLess(identity.score, selected.score)

    def test_large_lateral_panel_is_penalized(self) -> None:
        rng = np.random.default_rng(55)
        reference = np.full((480, 640), 32, dtype=np.uint8)
        deformed = reference.copy()
        panel = _texture(rng, 480, 180)
        patch = _texture(rng, 150, 260)
        reference[:, :180] = panel
        deformed[:, :180] = panel
        reference[270:420, 250:510] = patch
        deformed[288:438, 264:524] = patch

        result = self._estimate_arrays(reference, deformed)
        selected = result.selected
        self.assertEqual(result.confidence, "high")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertAlmostEqual(selected.dx, -14.0, delta=0.5)
        self.assertAlmostEqual(selected.dy, -18.0, delta=0.5)
        panel_model = next(item for item in result.hypotheses if item.model_index == 1)
        self.assertGreater(panel_model.lateral_fraction, 0.60)
        self.assertLess(panel_model.score, selected.score)

    def test_incompatible_blank_images_fail_without_a_solution(self) -> None:
        blank = np.zeros((480, 640), dtype=np.uint8)
        with self.assertRaises(AutoAlignmentError) as context:
            self._estimate_arrays(blank, blank)
        self.assertEqual(context.exception.code, "insufficient_features")

    def test_canvas_composes_correction_and_manual_adjustment_remains_available(
        self,
    ) -> None:
        ref_path = COMPASS_DIR / "reference_vehicle_frame_000.png"
        dam_path = COMPASS_DIR / "deformed_vehicle_frame_300.png"
        result = estimate_auto_alignment(ref_path, dam_path)
        selected = result.best
        assert selected is not None

        canvas = CanvasView()
        canvas.load_reference(str(ref_path))
        canvas.load_deformed(str(dam_path))
        canvas.set_deformed_transform(11.0, -7.0, 1.03, 2.0)
        dam_points = (QPointF(0.0, 0.0), QPointF(700.0, 700.0))
        before_scene = [canvas.ctrl.dam_item.mapToScene(point) for point in dam_points]
        applied = canvas.apply_deformed_correction(
            selected.dx,
            selected.dy,
            selected.scale,
            selected.rotation_deg,
        )

        theta = math.radians(selected.rotation_deg)
        for dam_point, current_scene in zip(dam_points, before_scene):
            expected_scene = QPointF(
                selected.dx
                + selected.scale
                * (
                    math.cos(theta) * current_scene.x()
                    - math.sin(theta) * current_scene.y()
                ),
                selected.dy
                + selected.scale
                * (
                    math.sin(theta) * current_scene.x()
                    + math.cos(theta) * current_scene.y()
                ),
            )
            actual_scene = canvas.ctrl.dam_item.mapToScene(dam_point)
            self.assertAlmostEqual(actual_scene.x(), expected_scene.x(), places=5)
            self.assertAlmostEqual(actual_scene.y(), expected_scene.y(), places=5)

        self.assertAlmostEqual(applied["scale"], 1.03 * selected.scale, places=6)
        self.assertAlmostEqual(
            applied["rotation_deg"], 2.0 + selected.rotation_deg, places=6
        )
        canvas.set_alignment_locked(False)
        canvas.set_alignment_target("dam")
        before = canvas.get_deformed_transform()
        canvas.nudge_selected(1.0, -2.0)
        after = canvas.get_deformed_transform()
        self.assertAlmostEqual(after["x"], before["x"] + 1.0)
        self.assertAlmostEqual(after["y"], before["y"] - 2.0)

        project = Project()
        project.dam_transform.x = after["x"]
        project.dam_transform.y = after["y"]
        project.dam_transform.scale = after["scale"]
        project.dam_transform.rotation_deg = after["rotation_deg"]
        restored = Project.from_dict(project.to_dict())
        self.assertEqual(
            restored.dam_transform.to_dict(), project.dam_transform.to_dict()
        )

    def test_high_confidence_requires_ten_inliers(self) -> None:
        best = self._high_quality_hypothesis(inliers=9)
        confidence, selected, reasons = _classify_confidence((best,))

        self.assertEqual(confidence, "medium")
        self.assertIsNone(selected)
        self.assertIn("insufficient_inliers", reasons)

    def test_high_confidence_requires_a_clear_score_margin(self) -> None:
        best = self._high_quality_hypothesis(score=95.0)
        runner_up = self._high_quality_hypothesis(model_index=2, score=90.0)
        confidence, selected, reasons = _classify_confidence((best, runner_up))

        self.assertEqual(confidence, "medium")
        self.assertIsNone(selected)
        self.assertIn("insufficient_score_margin", reasons)

    def test_extreme_similarity_transform_is_not_high_confidence(self) -> None:
        best = self._high_quality_hypothesis(scale=1.17, rotation_deg=5.1)
        confidence, selected, reasons = _classify_confidence((best,))

        self.assertEqual(confidence, "medium")
        self.assertIsNone(selected)
        self.assertIn("scale_change_too_large", reasons)
        self.assertIn("rotation_too_large", reasons)

    def test_sparse_transform_uses_stricter_geometry_gate(self) -> None:
        best = self._high_quality_hypothesis(
            inliers=12, scale=1.06, rotation_deg=3.1
        )
        confidence, selected, reasons = _classify_confidence((best,))

        self.assertEqual(confidence, "medium")
        self.assertIsNone(selected)
        self.assertIn("sparse_extreme_transform", reasons)

    def test_rigid_region_refines_only_the_same_similarity_model(self) -> None:
        src = np.array(
            [
                [250.0, 450.0],
                [350.0, 470.0],
                [450.0, 500.0],
                [550.0, 530.0],
                [650.0, 560.0],
                [750.0, 590.0],
                [280.0, 650.0],
                [380.0, 680.0],
                [480.0, 710.0],
                [580.0, 740.0],
                [680.0, 770.0],
                [720.0, 820.0],
            ],
            dtype=np.float32,
        ).reshape(-1, 1, 2)
        theta = math.radians(2.0)
        true_matrix = np.array(
            [
                [0.98 * math.cos(theta), -0.98 * math.sin(theta), 5.0],
                [0.98 * math.sin(theta), 0.98 * math.cos(theta), 7.0],
            ],
            dtype=np.float64,
        )
        dst = cv2.transform(src, true_matrix)
        normalized_dst = dst.reshape(-1, 2) / 1000.0
        initial = self._high_quality_hypothesis(
            dx=6.0,
            dy=8.0,
            rotation_deg=1.9,
            scale=0.981,
            inliers=len(src),
        )
        extracted = _ExtractedHypothesis(
            initial, np.arange(len(src), dtype=np.int32)
        )

        refined = _refine_hypothesis_in_rigid_region(
            extracted,
            src,
            dst,
            normalized_dst,
            math.sqrt(2.0) * 1000.0,
        )

        self.assertIsNotNone(refined.refinement)
        assert refined.refinement is not None
        self.assertTrue(refined.refinement.used_refined)
        self.assertLess(
            refined.refinement.rmse_after_px,
            refined.refinement.rmse_before_px,
        )
        self.assertAlmostEqual(refined.dx, 5.0, delta=0.05)
        self.assertAlmostEqual(refined.dy, 7.0, delta=0.05)
        self.assertAlmostEqual(refined.rotation_deg, 2.0, delta=0.01)
        self.assertAlmostEqual(refined.scale, 0.98, delta=0.001)

    def test_rigid_region_keeps_original_with_too_few_points(self) -> None:
        src = np.array(
            [[300.0, 500.0], [400.0, 550.0], [500.0, 600.0]],
            dtype=np.float32,
        ).reshape(-1, 1, 2)
        dst = src.copy()
        initial = self._high_quality_hypothesis(dx=1.0, dy=1.0)
        extracted = _ExtractedHypothesis(
            initial, np.arange(len(src), dtype=np.int32)
        )

        refined = _refine_hypothesis_in_rigid_region(
            extracted,
            src,
            dst,
            dst.reshape(-1, 2) / 1000.0,
            math.sqrt(2.0) * 1000.0,
        )

        self.assertEqual(refined.dx, initial.dx)
        self.assertEqual(refined.dy, initial.dy)
        self.assertIsNotNone(refined.refinement)
        assert refined.refinement is not None
        self.assertFalse(refined.refinement.used_refined)

    def test_high_result_shows_preview_before_explicit_use(self) -> None:
        window = self._alignment_window()
        hypothesis = self._high_quality_hypothesis(dx=7.0, dy=11.0)
        result = self._alignment_result("high", hypothesis, selected_index=0)
        baseline = window.canvas.get_deformed_transform()

        with (
            patch(
                "app.ui.main_window.estimate_auto_alignment",
                return_value=result,
            ),
            patch.object(QMessageBox, "information"),
            patch.object(
                window.canvas,
                "apply_deformed_correction",
                wraps=window.canvas.apply_deformed_correction,
            ) as apply_correction,
        ):
            window._on_auto_align()

        apply_correction.assert_called_once_with(7.0, 11.0, 1.0, 1.0)
        self.assertIs(window._pending_auto_alignment, hypothesis)
        self.assertNotEqual(window.canvas.get_deformed_transform(), baseline)
        self.assertEqual(window.project.dam_transform.to_dict(), baseline)
        self.assertFalse(window.btn_apply_alignment_suggestion.isHidden())
        self.assertTrue(window.btn_finish_alignment.isHidden())
        window._on_finish_alignment()
        window.workflow.finish_alignment()
        self.assertEqual(window.stage, window.Stage.ALIGNMENT)
        self.assertIs(window._pending_auto_alignment, hypothesis)

    def test_medium_result_waits_for_explicit_application(self) -> None:
        window = self._alignment_window()
        hypothesis = self._high_quality_hypothesis(dx=9.0, dy=13.0)
        result = self._alignment_result("medium", hypothesis)
        before = window.canvas.get_deformed_transform()

        with (
            patch(
                "app.ui.main_window.estimate_auto_alignment",
                return_value=result,
            ),
            patch.object(QMessageBox, "information"),
            patch.object(
                window.canvas,
                "apply_deformed_correction",
                wraps=window.canvas.apply_deformed_correction,
            ) as apply_correction,
        ):
            window._on_auto_align()

        apply_correction.assert_called_once_with(9.0, 13.0, 1.0, 1.0)
        self.assertNotEqual(window.canvas.get_deformed_transform(), before)
        self.assertEqual(window.project.dam_transform.to_dict(), before)
        self.assertIs(window._pending_auto_alignment, hypothesis)
        self.assertIs(window._pending_auto_alignment, result.best)
        self.assertTrue(window.btn_apply_alignment_suggestion.isEnabled())
        self.assertFalse(window.btn_apply_alignment_suggestion.isHidden())
        self.assertFalse(window.alignment_actions_widget.isHidden())

    def test_cancel_automatic_preview_restores_previous_transform(self) -> None:
        window = self._alignment_window()
        baseline = window.canvas.get_deformed_transform()
        window._preview_auto_alignment(
            self._high_quality_hypothesis(dx=9.0, dy=13.0)
        )

        self.assertNotEqual(window.canvas.get_deformed_transform(), baseline)
        window._on_cancel_alignment_preview()

        self.assertEqual(window.canvas.get_deformed_transform(), baseline)
        self.assertEqual(window.project.dam_transform.to_dict(), baseline)
        self.assertIsNone(window._pending_auto_alignment)
        self.assertTrue(window.alignment_actions_widget.isHidden())
        self.assertFalse(window.btn_finish_alignment.isHidden())

    def test_apply_suggestion_uses_exact_hypothesis_and_remains_editable(
        self,
    ) -> None:
        window = self._alignment_window()
        hypothesis = self._high_quality_hypothesis(
            dx=8.0, dy=14.0, scale=0.98, rotation_deg=-2.0
        )
        with patch.object(
            window.canvas,
            "apply_deformed_correction",
            wraps=window.canvas.apply_deformed_correction,
        ) as apply_correction:
            window._preview_auto_alignment(hypothesis)
            window._on_apply_auto_alignment_suggestion()

        apply_correction.assert_called_once_with(8.0, 14.0, 0.98, -2.0)
        applied = window.canvas.get_deformed_transform()
        self.assertEqual(window.project.dam_transform.to_dict(), applied)
        self.assertIsNone(window._pending_auto_alignment)
        self.assertTrue(window.lbl_rigid_region_instruction.isHidden())
        self.assertFalse(window.btn_finish_alignment.isHidden())

        window.canvas.nudge_selected(1.0, -2.0)
        adjusted = window.canvas.get_deformed_transform()
        self.assertAlmostEqual(adjusted["x"], applied["x"] + 1.0)
        self.assertAlmostEqual(adjusted["y"], applied["y"] - 2.0)

        window._sync_ui_to_project()
        restored = Project.from_dict(window.project.to_dict())
        self.assertEqual(restored.dam_transform.to_dict(), adjusted)

        window._on_finish_alignment()
        self.assertEqual(window.stage, window.Stage.CALIBRATION)
        self.assertFalse(window.align_group.isEnabled())
        self.assertTrue(window.opacity_slider.isEnabled())
        self.assertFalse(window.nudge_box.isEnabled())
        self.assertTrue(window.cal_group.isEnabled())

    def test_low_result_does_not_offer_a_suggestion(self) -> None:
        window = self._alignment_window()
        hypothesis = self._high_quality_hypothesis()
        result = self._alignment_result("low", hypothesis)

        with (
            patch(
                "app.ui.main_window.estimate_auto_alignment",
                return_value=result,
            ),
            patch.object(QMessageBox, "warning"),
        ):
            window._on_auto_align()

        self.assertIsNone(window._pending_auto_alignment)
        self.assertFalse(window.btn_apply_alignment_suggestion.isEnabled())
        self.assertTrue(window.btn_apply_alignment_suggestion.isHidden())

    def test_pending_suggestion_is_invalidated_by_transform_change(self) -> None:
        window = self._alignment_window()
        hypothesis = self._high_quality_hypothesis()
        window._preview_auto_alignment(hypothesis)

        window.canvas.nudge_selected(1.0, 0.0)

        self.assertIsNone(window._pending_auto_alignment)
        self.assertFalse(window.btn_apply_alignment_suggestion.isEnabled())
        self.assertTrue(window.btn_apply_alignment_suggestion.isHidden())

    def test_pending_suggestion_is_invalidated_by_image_reload(self) -> None:
        window = self._alignment_window()
        window._preview_auto_alignment(
            self._high_quality_hypothesis()
        )

        window.canvas.load_reference(
            str(COMPASS_DIR / "reference_vehicle_frame_000.png")
        )

        self.assertIsNone(window._pending_auto_alignment)
        self.assertTrue(window.btn_apply_alignment_suggestion.isHidden())

    def _alignment_window(self) -> MainWindow:
        window = MainWindow()
        self.addCleanup(window.close)
        ref_path = COMPASS_DIR / "reference_vehicle_frame_000.png"
        dam_path = COMPASS_DIR / "deformed_vehicle_frame_300.png"
        window.canvas.load_reference(str(ref_path))
        window.canvas.load_deformed(str(dam_path))
        window.project.ref_path = str(ref_path)
        window.project.dam_path = str(dam_path)
        window.canvas.set_alignment_target("dam")
        window.workflow.set_stage(window.Stage.ALIGNMENT)
        window._update_auto_align_availability()
        return window

    @staticmethod
    def _alignment_result(
        confidence: str,
        hypothesis: AlignmentHypothesis,
        *,
        selected_index: int | None = None,
    ) -> AutoAlignmentResult:
        return AutoAlignmentResult(
            diagnostics=AlignmentDiagnostics(100, 110, 80, 40),
            hypotheses=(hypothesis,),
            confidence=confidence,
            selected_index=selected_index,
            confidence_reasons=(f"{confidence}_test",),
        )

    @staticmethod
    def _high_quality_hypothesis(**overrides) -> AlignmentHypothesis:
        values = {
            "model_index": 1,
            "dx": 10.0,
            "dy": 20.0,
            "rotation_deg": 1.0,
            "scale": 1.0,
            "inliers": 20,
            "inlier_ratio": 0.75,
            "inlier_rmse_px": 1.0,
            "centroid_x": 0.5,
            "centroid_y": 0.6,
            "bbox_x_min": 0.25,
            "bbox_y_min": 0.35,
            "bbox_x_max": 0.75,
            "bbox_y_max": 0.85,
            "dispersion_x": 0.15,
            "dispersion_y": 0.15,
            "support_area_ratio": 0.25,
            "edge_fraction": 0.0,
            "lateral_fraction": 0.0,
            "body_fraction": 0.9,
            "plausible": True,
            "near_identity": False,
            "score": 95.0,
        }
        values.update(overrides)
        return AlignmentHypothesis(**values)


if __name__ == "__main__":
    unittest.main()
