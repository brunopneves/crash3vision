from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QGraphicsScene

from app.ui.overlay.state import OverlayState
from app.ui.overlay.renderer import OverlayRenderer


class CanvasExport:
    """Export and overlay persistence helpers (no UI)."""

    def __init__(
        self, scene: QGraphicsScene, renderer: OverlayRenderer, state: OverlayState
    ) -> None:
        self.scene = scene
        self.renderer = renderer
        self.state = state

    def export_scene_png(self, path: str) -> None:
        rect = self.scene.sceneRect()
        w = max(1, int(rect.width()))
        h = max(1, int(rect.height()))

        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        painter = QPainter(img)
        self.scene.render(painter)
        painter.end()

        img.save(path)

    def get_overlay_state(self) -> dict[str, Any]:
        return self.state.to_dict()

    def restore_overlay_state(
        self, state_dict: Mapping[str, Any], bounds_rect_provider
    ) -> None:
        new_state = OverlayState.from_dict(dict(state_dict))

        self.state.cal_p1 = new_state.cal_p1
        self.state.cal_p2 = new_state.cal_p2
        self.state.w_p1 = new_state.w_p1
        self.state.w_p2 = new_state.w_p2
        self.state.slice_x = list(new_state.slice_x)
        self.state.guide_y = new_state.guide_y
        self.state.bumper_offset_m = new_state.bumper_offset_m
        self.state.bumper_offset_px = new_state.bumper_offset_px
        self.state.crossmember_y = new_state.crossmember_y
        self.state.c_points = dict(new_state.c_points)
        self.state.m_per_px = new_state.m_per_px

        self.renderer.clear_all()
        self.renderer.render_calibration(self.state)

        bounds = bounds_rect_provider()
        self.renderer.render_w_and_slices(self.state, bounds)
        self.renderer.render_guide_line(self.state, bounds)

        if self.state.slice_x:
            self.renderer.ensure_legend(self.state, bounds)

        self.renderer.render_ci(self.state)

        if self.state.slice_x:
            self.renderer.refresh_legend(self.state)

        self.renderer.apply_scaling()
