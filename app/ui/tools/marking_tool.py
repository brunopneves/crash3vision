from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsView

from .base import ToolBase


class MarkingTool(ToolBase):
    name = "marking"

    def __init__(self, state, renderer, get_bounds_rect, emit_w_px, emit_ci, emit_w_cleared) -> None:
        self.state = state
        self.renderer = renderer
        self.get_bounds_rect = get_bounds_rect
        self.emit_w_px = emit_w_px
        self.emit_ci = emit_ci
        self.emit_w_cleared = emit_w_cleared

        self._mode: str = "idle"  # "setw" | "guide" | "ci" | "idle"
        self._ci_index: int = 1
        self._ci_ref: QPointF | None = None

    def activate(self, host) -> None:
        host.setCursor(Qt.CursorShape.CrossCursor)
        host.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self, host) -> None:
        _ = host
        self._clear_ci_preview()

    def set_w_mode(self, enabled: bool) -> None:
        if enabled:
            self._mode = "setw"
            self._clear_ci_preview()
        elif self._mode == "setw":
            self._mode = "idle"

    def set_guide_mode(self, enabled: bool) -> None:
        if enabled:
            self._mode = "guide"
            self._clear_ci_preview()
        elif self._mode == "guide":
            self._mode = "idle"

    def set_ci_mode(self, enabled: bool) -> None:
        if enabled:
            self._mode = "ci"
            self._clear_ci_preview()
            self._ci_index = 1
        elif self._mode == "ci":
            self._mode = "idle"

    def set_ci_index(self, idx: int) -> None:
        self._ci_index = max(1, min(6, int(idx)))
        self._clear_ci_preview()

    def generate_slices(self, n: int = 6) -> None:
        if self.state.w_p1 is None or self.state.w_p2 is None:
            return

        if n < 2:
            return

        x1 = self.state.w_p1[0]
        x2 = self.state.w_p2[0]
        left_x, right_x = (x1, x2) if x1 <= x2 else (x2, x1)

        w_px = abs(right_x - left_x)
        delta = w_px / (n - 1)

        self.state.slice_x = [left_x + k * delta for k in range(n)]

        b = self.get_bounds_rect()
        self.renderer.render_w_and_slices(self.state, b)
        self.renderer.render_guide_line(self.state, b)
        self.renderer.render_crossmember_line(self.state, b)
        self.renderer.ensure_legend(self.state, b)
        self.renderer.render_ci(self.state)
        self.renderer.render_ci_profile(self.state)
        self.renderer.apply_scaling()

    def clear_markings(self) -> None:
        self._clear_ci_preview()
        self.state.clear_markings()
        self.renderer.clear_all()

    def _clear_ci_preview(self) -> None:
        self._ci_ref = None
        self.renderer.clear_ci_preview()
        self.renderer.apply_scaling()

    def mouse_press(self, host, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = host
        if not self.is_left_click(event):
            return False

        b = self.get_bounds_rect()

        if self._mode == "setw":
            if self.state.w_p1 is None:
                self.state.w_p1 = (float(scene_pos.x()), float(scene_pos.y()))
                self.renderer.render_w_and_slices(self.state, b)
                self.renderer.render_guide_line(self.state, b)
                self.renderer.apply_scaling()
                return True

            if self.state.w_p2 is None:
                self.state.w_p2 = (float(scene_pos.x()), float(scene_pos.y()))
                self.renderer.render_w_and_slices(self.state, b)
                self.renderer.render_guide_line(self.state, b)
                self.renderer.apply_scaling()

                w_px = abs(self.state.w_p2[0] - self.state.w_p1[0])
                self.emit_w_px(float(w_px))
                return True

            self.state.clear_markings()
            self._clear_ci_preview()
            self.renderer.render_w_and_slices(self.state, b)
            self.renderer.render_guide_line(self.state, b)
            self.renderer.render_crossmember_line(self.state, b)
            self.renderer.render_ci(self.state)
            self.renderer.render_ci_profile(self.state)
            self.renderer.clear_legend()
            self.renderer.apply_scaling()
            self.emit_w_cleared()
            return True

        if self._mode == "guide":
            self.state.guide_y = float(scene_pos.y())

            if (
                self.state.bumper_offset_m is not None
                and self.state.bumper_offset_m > 0
                and self.state.m_per_px is not None
            ):
                self.state.bumper_offset_px = float(self.state.bumper_offset_m) / float(
                    self.state.m_per_px
                )
                self.state.crossmember_y = float(self.state.guide_y) - float(
                    self.state.bumper_offset_px
                )
            else:
                self.state.bumper_offset_px = None
                self.state.crossmember_y = None

            self.renderer.render_w_and_slices(self.state, b)
            self.renderer.render_guide_line(self.state, b)
            self.renderer.render_crossmember_line(self.state, b)
            self.renderer.render_ci(self.state)
            self.renderer.render_ci_profile(self.state)
            if self.state.slice_x:
                self.renderer.ensure_legend(self.state, b)
                self.renderer.refresh_legend(self.state)
            self.renderer.apply_scaling()
            return True

        if self._mode == "ci":
            if not self.state.slice_x:
                return True

            cx = float(self.state.slice_x[self._ci_index - 1])
            snapped = QPointF(cx, scene_pos.y())

            if self._ci_ref is None:
                self._ci_ref = snapped
                self.renderer.render_ci_preview(ref_point=self._ci_ref, def_point=None)
                self.renderer.apply_scaling()
                return True

            pref = (float(self._ci_ref.x()), float(self._ci_ref.y()))
            pdef = (float(snapped.x()), float(snapped.y()))
            self.state.c_points[self._ci_index] = (pref, pdef)

            self.renderer.clear_ci_preview()
            self.renderer.render_w_and_slices(self.state, b)
            self.renderer.render_guide_line(self.state, b)
            self.renderer.render_crossmember_line(self.state, b)
            self.renderer.ensure_legend(self.state, b)
            self.renderer.render_ci(self.state)
            self.renderer.render_ci_profile(self.state)
            self.renderer.apply_scaling()

            ci_px = abs(pdef[1] - pref[1])
            ci_m = (
                (ci_px * self.state.m_per_px)
                if self.state.m_per_px is not None
                else 0.0
            )
            self.emit_ci(int(self._ci_index), float(ci_px), float(ci_m))

            self._ci_ref = None
            return True

        return False
