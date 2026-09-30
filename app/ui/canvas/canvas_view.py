from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from app.ui.canvas.canvas_controller import CanvasController


class CanvasView(QGraphicsView):
    calibration_px_measured = Signal(float)
    w_px_measured = Signal(float)
    w_cleared = Signal()
    ci_measured = Signal(int, float, float)

    def __init__(self) -> None:
        super().__init__()

        scene = QGraphicsScene(self)
        self.setScene(scene)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.ctrl = CanvasController(
            host_view=self,
            scene=scene,
            emit_calibration_px=lambda v: self.calibration_px_measured.emit(v),
            emit_w_px=lambda v: self.w_px_measured.emit(v),
            emit_w_cleared=self.w_cleared.emit,
            emit_ci=lambda i, px, cm: self.ci_measured.emit(i, px, cm),
        )

    # ---------------- public API passthrough ----------------

    def reset_interaction(self) -> None:
        self.ctrl.reset_interaction()

    @property
    def alignment_mode(self) -> bool:
        return self.ctrl.alignment_mode

    @property
    def calibration_mode(self) -> bool:
        return self.ctrl.calibration_mode

    @property
    def set_w_mode(self) -> bool:
        return self.ctrl.set_w_mode

    @property
    def guide_mode(self) -> bool:
        return self.ctrl.guide_mode

    @property
    def measure_ci_mode(self) -> bool:
        return self.ctrl.measure_ci_mode

    @property
    def cal_p1(self):
        return self.ctrl.cal_p1

    @property
    def cal_p2(self):
        return self.ctrl.cal_p2

    @property
    def w_p1(self):
        return self.ctrl.w_p1

    @property
    def w_p2(self):
        return self.ctrl.w_p2

    @property
    def slice_x(self):
        return self.ctrl.slice_x

    @property
    def c_points(self):
        return self.ctrl.c_points

    @property
    def cm_per_px(self):
        return self.ctrl.cm_per_px

    @property
    def delta_w_px(self):
        w_total_px = self.ctrl.w_total_px
        if w_total_px is None:
            return None
        return w_total_px / 6.0

    def set_alignment_mode(self, enabled: bool) -> None:
        self.ctrl.set_alignment_mode(enabled)

    def set_alignment_locked(self, locked: bool) -> None:
        self.ctrl.set_alignment_locked(locked)

    def set_alignment_target(self, target: str) -> None:
        self.ctrl.set_alignment_target(target)  # type: ignore[arg-type]

    def get_alignment_target(self) -> str:
        return self.ctrl.get_alignment_target()

    def nudge_selected(self, dx: float, dy: float) -> None:
        self.ctrl.nudge_selected(dx, dy)

    def rotate_selected(self, delta_deg: float) -> None:
        self.ctrl.rotate_selected(delta_deg)

    def scale_selected(self, factor: float) -> None:
        self.ctrl.scale_selected(factor)

    def reset_selected_transform(self) -> None:
        self.ctrl.reset_selected_transform()

    def set_calibration_mode(self, enabled: bool) -> None:
        self.ctrl.set_calibration_mode(enabled)

    def set_w_measure_mode(self, enabled: bool) -> None:
        self.ctrl.set_w_measure_mode(enabled)

    def set_guide_mode(self, enabled: bool) -> None:
        self.ctrl.set_guide_mode(enabled)

    def set_measure_ci_mode(self, enabled: bool) -> None:
        self.ctrl.set_measure_ci_mode(enabled)

    def set_ci_index(self, idx: int) -> None:
        self.ctrl.set_ci_index(idx)

    def set_crossmember_offset_m(self, offset_m: float | None) -> None:
        self.ctrl.set_crossmember_offset_m(offset_m)

    def apply_scale(self, cm_per_px: float) -> None:
        self.ctrl.apply_scale(cm_per_px)

    def generate_slices(self, n: int = 6) -> None:
        self.ctrl.generate_slices(n)

    def clear_calibration(self) -> None:
        self.ctrl.clear_calibration()

    def clear_markings(self) -> None:
        self.ctrl.clear_markings()

    def reset_alignment_visual(self) -> None:
        self.ctrl.reset_alignment_visual()

    def nudge_deformed(self, dx: float, dy: float) -> None:
        self.ctrl.nudge_deformed(dx, dy)

    def reset_deformed_transform(self) -> None:
        self.ctrl.reset_deformed_transform()

    def reset_reference_transform(self) -> None:
        self.ctrl.reset_reference_transform()

    def reset_all_transforms(self) -> None:
        self.ctrl.reset_all_transforms()

    def get_deformed_transform(self):
        return self.ctrl.get_deformed_transform()

    def set_deformed_transform(self, x, y, scale, rotation_deg):
        self.ctrl.set_deformed_transform(x, y, scale, rotation_deg)

    def get_reference_transform(self):
        return self.ctrl.get_reference_transform()

    def set_reference_transform(self, x, y, scale, rotation_deg):
        self.ctrl.set_reference_transform(x, y, scale, rotation_deg)

    def load_reference(self, image_path: str | QPixmap) -> None:
        self.ctrl.load_reference(image_path)

    def load_deformed(self, image_path: str | QPixmap) -> None:
        self.ctrl.load_deformed(image_path)

    def set_deformed_opacity(self, opacity: float) -> None:
        self.ctrl.set_deformed_opacity(opacity)

    def export_scene_png(self, path: str) -> None:
        self.ctrl.export_scene_png(path)

    def get_overlay_state(self):
        return self.ctrl.get_overlay_state()

    def restore_overlay_state(self, state):
        self.ctrl.restore_overlay_state(state)

    # ---------------- events delegation ----------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        tool = self.ctrl.active_tool()
        if tool and tool.mouse_press(self, scene_pos, event):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        tool = self.ctrl.active_tool()
        if tool and tool.mouse_move(self, scene_pos, event):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        tool = self.ctrl.active_tool()
        if tool and tool.mouse_release(self, scene_pos, event):
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else (1 / 1.15)
        self.ctrl.wheel_zoom(factor)

    def clear_images(self) -> None:
        self.ctrl.clear_images()
