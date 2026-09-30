from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsView

from .base import ToolBase


class CalibrationTool(ToolBase):
    name = "calibration"

    def __init__(self, state, renderer, emit_px_measured) -> None:
        self.state = state
        self.renderer = renderer
        self.emit_px_measured = emit_px_measured

    def activate(self, host) -> None:
        host.setCursor(Qt.CursorShape.CrossCursor)
        host.setDragMode(QGraphicsView.DragMode.NoDrag)

    def mouse_press(self, host, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = host
        if not self.is_left_click(event):
            return False

        if self.state.cal_p1 is None:
            self.state.cal_p1 = (float(scene_pos.x()), float(scene_pos.y()))
            self.renderer.render_calibration(self.state)
            return True

        if self.state.cal_p2 is None:
            self.state.cal_p2 = (float(scene_pos.x()), float(scene_pos.y()))
            self.renderer.render_calibration(self.state)

            x1, y1 = self.state.cal_p1
            x2, y2 = self.state.cal_p2
            dist_px = math.hypot(x2 - x1, y2 - y1)
            self.emit_px_measured(float(dist_px))
            return True

        # third click resets
        self.state.clear_calibration()
        self.renderer.render_calibration(self.state)
        return True