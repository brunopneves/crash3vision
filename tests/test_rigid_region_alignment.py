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
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QGraphicsView, QMessageBox

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
    def test_workflow_progress_tracks_images_and_alignment(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        steps = window.workflow_step_labels
        self.assertEqual(steps["images"].property("progressStatus"), "current")
        self.assertEqual(steps["alignment"].property("progressStatus"), "future")

        dam_path = str(COMPASS / "deformed_vehicle_frame_300.png")
        with patch.object(window.io, "pick_image_file", return_value=dam_path):
            window.io.load_dam()
        self.assertEqual(steps["images"].property("progressStatus"), "complete")
        self.assertEqual(steps["alignment"].property("progressStatus"), "current")
        self.assertIn("opcional", steps["alignment"].text())
        window.btn_finish_alignment.click()
        self.assertIn("pulado", steps["alignment"].text())
        self.assertEqual(steps["calibration"].property("progressStatus"), "current")

        ref_path = str(COMPASS / "reference_vehicle_frame_000.png")
        with patch.object(window.io, "pick_image_file", return_value=ref_path):
            window.io.load_ref()
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
        self.assertEqual(
            {step: label.property("progressStatus") for step, label in steps.items()},
            dict.fromkeys(steps, "complete") | {"alignment": "passed"},
        )
        self.assertNotIn("✓", steps["alignment"].text())
        self.assertIn("Etapa superada", steps["alignment"].toolTip())

        window.workflow.restart_from_marking()
        self.assertEqual(steps["measurement"].property("progressStatus"), "current")
        window.workflow.finish_marking()
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")
        window.calc_panel.btn_compute.click()
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")
        window.calc_panel.btn_compute_speed.click()
        self.assertEqual(steps["calculation"].property("progressStatus"), "complete")
        self.assertEqual(steps["result"].property("progressStatus"), "complete")
        self.assertIn("#245b96", steps["result"].styleSheet())
        window.workflow.invalidate_speed()
        self.assertEqual(steps["calculation"].property("progressStatus"), "current")
        self.assertEqual(steps["result"].property("progressStatus"), "future")

        window.workflow.restart_from_calibration()
        self.assertEqual(steps["calibration"].property("progressStatus"), "current")
        self.assertEqual(steps["measurement"].property("progressStatus"), "future")
        window._m_per_px = 0.005
        window.workflow.confirm_calibration()
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

        self.assertEqual(window.align_group.title(), "Alinhamento das imagens")
        self.assertEqual(window.fine_adjust_group.title(), "Ajuste fino")
        self.assertIs(window.rad_alignment_auto.parentWidget(), window.align_group)
        self.assertIs(window.rad_alignment_rigid.parentWidget(), window.align_group)
        self.assertIs(window.btn_start_alignment.parentWidget(), window.align_group)
        self.assertIs(
            window.lbl_rigid_region_instruction.parentWidget(),
            window.align_group,
        )
        self.assertIs(window.alignment_actions_widget.parentWidget(), window.align_group)
        self.assertIs(window.btn_finish_alignment.parentWidget(), window.align_group)
        self.assertTrue(window.rad_alignment_auto.isChecked())
        self.assertFalse(window.rad_alignment_rigid.isChecked())
        self.assertIs(window.nudge_box.parentWidget(), window.fine_adjust_group)
        self.assertFalse(window.lbl_rigid_region_instruction.isHidden())
        self.assertEqual(
            window.lbl_rigid_region_instruction.text(),
            "Escolha um método de alinhamento ou avance direto para a calibração.",
        )
        self.assertTrue(window.alignment_actions_widget.isHidden())
        self.assertTrue(window.btn_rigid_apply.isHidden())
        self.assertTrue(window.btn_rigid_try_again.isHidden())
        self.assertTrue(window.btn_rigid_cancel.isHidden())

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

        window.canvas.clear_images()
        self.assertFalse(window.opacity_slider.isEnabled())

        window.canvas.load_reference(str(ref_path))
        self.assertFalse(window.opacity_slider.isEnabled())
        window.canvas.load_deformed(str(dam_path))
        self.assertTrue(window.opacity_slider.isEnabled())

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

        self.assertFalse(window.btn_finish_alignment.isHidden())
        self.assertFalse(window.btn_start_alignment.isEnabled())
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
        self.assertTrue(window.btn_finish_alignment.isHidden())
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
