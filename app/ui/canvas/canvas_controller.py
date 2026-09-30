from __future__ import annotations

import sys
from pathlib import Path

from typing import Any, Mapping, Callable, Literal

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from app.ui.overlay.state import OverlayState
from app.ui.overlay.renderer import OverlayRenderer
from app.ui.tools import (
    AlignmentTool,
    CalibrationTool,
    MarkingTool,
    ToolBase,
    ToolController,
)
from app.ui.canvas.canvas_export import CanvasExport

AlignmentTarget = Literal["ref", "dam"]


class CanvasController:
    """
    Owns state, renderer, tools and exposes the public API that main_window expects.
    CanvasView is thin and delegates to this controller.

    Important coordinate policy:
    - overlay/marking/calibration use SCENE coordinates
    - bounds used for W/slices/legend must also be in SCENE coordinates
    - sceneRect must be updated from the union of transformed image items
    """

    def __init__(
        self,
        host_view: QGraphicsView,
        scene: QGraphicsScene,
        emit_calibration_px: Callable[[float], None],
        emit_w_px: Callable[[float], None],
        emit_ci: Callable[[int, float, float], None],
        emit_w_cleared: Callable[[], None],
    ) -> None:
        self.host = host_view
        self.scene = scene

        self._emit_calibration_px = emit_calibration_px
        self._emit_w_px = emit_w_px
        self._emit_ci = emit_ci

        self.ref_item: QGraphicsPixmapItem | None = None
        self.dam_item: QGraphicsPixmapItem | None = None

        self._zoom_factor: float = 1.0
        self._alignment_target: AlignmentTarget = "dam"

        self.state = OverlayState()
        self.renderer = OverlayRenderer(
            self.scene, get_zoom_factor=lambda: self._zoom_factor
        )

        self.alignment_locked: bool = False

        self._alignment_tool = AlignmentTool(
            get_target_item=self._get_alignment_target_item,
            is_locked=lambda: self.alignment_locked,
        )

        self._calibration_tool = CalibrationTool(
            state=self.state,
            renderer=self.renderer,
            emit_px_measured=lambda v: self._emit_calibration_px(v),
        )

        self._marking_tool = MarkingTool(
            state=self.state,
            renderer=self.renderer,
            get_bounds_rect=self._bounds_rect,
            emit_w_px=lambda v: self._emit_w_px(v),
            emit_ci=lambda i, px, cm: self._emit_ci(i, px, cm),
            emit_w_cleared=emit_w_cleared,
        )

        self._welcome_item = None
        self._show_welcome()

        self.controller = ToolController(host=self.host)
        self.exporter = CanvasExport(self.scene, self.renderer, self.state)

    # ---------------------- mode flags ----------------------

    @property
    def alignment_mode(self) -> bool:
        return self.controller.flags.alignment_mode

    @property
    def calibration_mode(self) -> bool:
        return self.controller.flags.calibration_mode

    @property
    def set_w_mode(self) -> bool:
        return self.controller.flags.set_w_mode

    @property
    def guide_mode(self) -> bool:
        return self.controller.flags.set_guide_mode

    @property
    def measure_ci_mode(self) -> bool:
        return self.controller.flags.measure_ci_mode

    # ---------------------- alignment target ----------------------

    def set_alignment_target(self, target: AlignmentTarget) -> None:
        if target not in ("ref", "dam"):
            raise ValueError("Alignment target must be 'ref' or 'dam'")
        self._alignment_target = target

    def get_alignment_target(self) -> AlignmentTarget:
        return self._alignment_target

    def _get_alignment_target_item(self) -> QGraphicsPixmapItem | None:
        if self._alignment_target == "ref":
            return self.ref_item
        return self.dam_item

    # ---------------------- compatibility attrs ----------------------

    @property
    def cal_p1(self):
        return self.state.cal_p1

    @property
    def cal_p2(self):
        return self.state.cal_p2

    @property
    def w_p1(self):
        return self.state.w_p1

    @property
    def w_p2(self):
        return self.state.w_p2

    @property
    def slice_x(self):
        return list(self.state.slice_x)

    @property
    def c_points(self):
        return dict(self.state.c_points)

    @property
    def cm_per_px(self):
        return self.state.m_per_px

    @property
    def w_total_px(self):
        if self.state.w_p1 is None or self.state.w_p2 is None:
            return None
        return abs(float(self.state.w_p2[0]) - float(self.state.w_p1[0]))

    # ---------------------- tool access ----------------------

    def active_tool(self) -> ToolBase | None:
        return self.controller.active_tool

    def reset_interaction(self) -> None:
        """Clear transient tool state without changing restored geometry."""
        self.controller.disable_all()
        self._alignment_tool.deactivate(self.host)
        self._marking_tool.set_w_mode(False)
        self._marking_tool.set_guide_mode(False)
        self._marking_tool.set_ci_mode(False)
        self._marking_tool.set_ci_index(1)

    # ---------------------- API used by main_window ----------------------

    def set_alignment_mode(self, enabled: bool) -> None:
        self.controller.set_mode_alignment(enabled, self._alignment_tool)

    def set_alignment_locked(self, locked: bool) -> None:
        self.alignment_locked = locked

    def set_calibration_mode(self, enabled: bool) -> None:
        self.controller.set_mode_calibration(enabled, self._calibration_tool)

    def set_w_measure_mode(self, enabled: bool) -> None:
        if enabled:
            self.controller.set_mode_marking_w(True, self._marking_tool)
            self._marking_tool.set_w_mode(True)
            self._marking_tool.set_ci_mode(False)
        else:
            self._marking_tool.set_w_mode(False)
            self.controller.set_mode_marking_w(False, self._marking_tool)

    def set_guide_mode(self, enabled: bool) -> None:
        if enabled:
            self.controller.set_mode_marking_guide(True, self._marking_tool)
            self._marking_tool.set_guide_mode(True)
            self._marking_tool.set_w_mode(False)
            self._marking_tool.set_ci_mode(False)
        else:
            self._marking_tool.set_guide_mode(False)
            self.controller.set_mode_marking_guide(False, self._marking_tool)

    def set_measure_ci_mode(self, enabled: bool) -> None:
        if enabled:
            self.controller.set_mode_marking_ci(True, self._marking_tool)
            self._marking_tool.set_ci_mode(True)
            self._marking_tool.set_w_mode(False)
        else:
            self._marking_tool.set_ci_mode(False)
            self.controller.set_mode_marking_ci(False, self._marking_tool)

    def set_ci_index(self, idx: int) -> None:
        self._marking_tool.set_ci_index(idx)

    def apply_scale(self, cm_per_px: float) -> None:
        self.state.m_per_px = float(cm_per_px)

        if (
            self.state.bumper_offset_m is not None
            and self.state.bumper_offset_m > 0
            and self.state.guide_y is not None
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

        bounds = self._bounds_rect()
        self.renderer.render_guide_line(self.state, bounds)
        self.renderer.render_crossmember_line(self.state, bounds)
        self.renderer.refresh_legend(self.state)
        self.renderer.apply_scaling()

    def generate_slices(self, n: int = 6) -> None:
        self._marking_tool.generate_slices(n)

    def clear_calibration(self) -> None:
        self.state.clear_calibration()
        self.state.bumper_offset_px = None
        self.state.crossmember_y = None
        self.renderer.clear_all()

        bounds = self._bounds_rect()
        self.renderer.render_w_and_slices(self.state, bounds)
        self.renderer.render_guide_line(self.state, bounds)
        self.renderer.render_crossmember_line(self.state, bounds)

        if self.state.slice_x:
            self.renderer.ensure_legend(self.state, bounds)
            self.renderer.refresh_legend(self.state)

        self.renderer.render_ci(self.state)
        self.renderer.apply_scaling()

    def clear_markings(self) -> None:
        self._marking_tool._clear_ci_preview()  # noqa: SLF001
        self.state.clear_markings()
        self.renderer.clear_all()

        self.renderer.render_calibration(self.state)
        self.renderer.apply_scaling()

    def reset_alignment_visual(self) -> None:
        self.reset_reference_transform()
        self.reset_deformed_transform()

        self.state.clear_calibration()
        self.state.clear_markings()
        self.renderer.clear_all()
        self._update_scene_rect_from_items()
        self.renderer.apply_scaling()

    def set_crossmember_offset_m(self, offset_m: float | None) -> None:
        if offset_m is None or offset_m <= 0 or self.state.m_per_px is None:
            self.state.bumper_offset_m = None
            self.state.bumper_offset_px = None
            self.state.crossmember_y = None
        else:
            offset_px = float(offset_m) / float(self.state.m_per_px)

            self.state.bumper_offset_m = float(offset_m)
            self.state.bumper_offset_px = float(offset_px)

            if self.state.guide_y is not None:
                # frente do veículo para baixo → travessa acima
                self.state.crossmember_y = float(self.state.guide_y) - offset_px
            else:
                self.state.crossmember_y = None

        bounds = self._bounds_rect()
        self.renderer.render_guide_line(self.state, bounds)
        self.renderer.render_crossmember_line(self.state, bounds)
        self.renderer.apply_scaling()

    # ---------------------- selected image transforms ----------------------

    def nudge_selected(self, dx: float, dy: float) -> None:
        item = self._get_alignment_target_item()
        if item is not None and not self.alignment_locked:
            item.moveBy(dx, dy)
            self._update_scene_rect_from_items()

    def rotate_selected(self, delta_deg: float) -> None:
        item = self._get_alignment_target_item()
        if item is not None and not self.alignment_locked:
            item.setRotation(float(item.rotation()) + float(delta_deg))
            self._update_scene_rect_from_items()

    def scale_selected(self, factor: float) -> None:
        item = self._get_alignment_target_item()
        if item is not None and not self.alignment_locked:
            new_scale = float(item.scale()) * float(factor)
            item.setScale(new_scale)
            self._update_scene_rect_from_items()

    def reset_selected_transform(self) -> None:
        item = self._get_alignment_target_item()
        if item is not None and not self.alignment_locked:
            item.setRotation(0.0)
            item.setScale(1.0)
            item.setPos(0.0, 0.0)
            self._update_scene_rect_from_items()

    def reset_all_transforms(self) -> None:
        if self.ref_item is not None:
            self.ref_item.setRotation(0.0)
            self.ref_item.setScale(1.0)
            self.ref_item.setPos(0.0, 0.0)

        if self.dam_item is not None:
            self.dam_item.setRotation(0.0)
            self.dam_item.setScale(1.0)
            self.dam_item.setPos(0.0, 0.0)

        self._update_scene_rect_from_items()

    # ---------------------- legacy helpers (compatibility) ----------------------

    def nudge_deformed(self, dx: float, dy: float) -> None:
        if self.dam_item is not None and not self.alignment_locked:
            self.dam_item.moveBy(dx, dy)
            self._update_scene_rect_from_items()

    def reset_deformed_transform(self) -> None:
        if self.dam_item is not None and not self.alignment_locked:
            self.dam_item.setRotation(0.0)
            self.dam_item.setScale(1.0)
            self.dam_item.setPos(0.0, 0.0)
            self._update_scene_rect_from_items()

    def reset_reference_transform(self) -> None:
        if self.ref_item is not None:
            self.ref_item.setRotation(0.0)
            self.ref_item.setScale(1.0)
            self.ref_item.setPos(0.0, 0.0)
            self._update_scene_rect_from_items()

    def get_deformed_transform(self):
        if self.dam_item is None:
            return {"x": 0.0, "y": 0.0, "scale": 1.0, "rotation_deg": 0.0}

        return {
            "x": float(self.dam_item.pos().x()),
            "y": float(self.dam_item.pos().y()),
            "scale": float(self.dam_item.scale()),
            "rotation_deg": float(self.dam_item.rotation()),
        }

    def set_deformed_transform(self, x, y, scale, rotation_deg):
        if self.dam_item is None:
            return

        self.dam_item.setScale(float(scale))
        self.dam_item.setRotation(float(rotation_deg))
        self.dam_item.setPos(float(x), float(y))
        self._update_scene_rect_from_items()

    def get_reference_transform(self):
        if self.ref_item is None:
            return {"x": 0.0, "y": 0.0, "scale": 1.0, "rotation_deg": 0.0}

        return {
            "x": float(self.ref_item.pos().x()),
            "y": float(self.ref_item.pos().y()),
            "scale": float(self.ref_item.scale()),
            "rotation_deg": float(self.ref_item.rotation()),
        }

    def set_reference_transform(self, x, y, scale, rotation_deg):
        if self.ref_item is None:
            return

        self.ref_item.setScale(float(scale))
        self.ref_item.setRotation(float(rotation_deg))
        self.ref_item.setPos(float(x), float(y))
        self._update_scene_rect_from_items()

    def _resource_path(self, relative: str) -> Path:
        base = getattr(sys, "_MEIPASS", None)
        if base is not None:
            return Path(base) / relative
        return Path(__file__).resolve().parents[3] / relative

    def _show_welcome(self) -> None:
        if hasattr(self, "_welcome_item") and self._welcome_item is not None:
            return
        img_path = self._resource_path("app/assets/welcome.png")
        pix = QPixmap(str(img_path))
        if pix.isNull():
            self._welcome_item = None
            return
        item = self.scene.addPixmap(pix)
        item.setZValue(-1)
        item.setOpacity(0.85)
        self.scene.setSceneRect(pix.rect().toRectF())
        self._welcome_item = item
        self.host.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _hide_welcome(self) -> None:
        if hasattr(self, "_welcome_item") and self._welcome_item is not None:
            self.scene.removeItem(self._welcome_item)
            self._welcome_item = None

    # ---------------------- image loading ----------------------

    def load_reference(self, image_path: str | QPixmap) -> None:
        self._hide_welcome()
        pix = QPixmap(image_path)
        if pix.isNull():
            raise ValueError(f"Failed to load image: {image_path}")

        if self.ref_item is None:
            item = self.scene.addPixmap(pix)
            if item is None:
                raise ValueError(
                    f"Failed to create graphics item for image: {image_path}"
                )
            item.setZValue(0)
            self.ref_item = item
        else:
            self.ref_item.setPixmap(pix)

        self._set_item_transform_origin_to_center(self.ref_item)
        self._fit_if_possible()

    def load_deformed(self, image_path: str | QPixmap) -> None:
        self._hide_welcome()
        pix = QPixmap(image_path)
        if pix.isNull():
            raise ValueError(f"Failed to load image: {image_path}")

        if self.dam_item is None:
            item = self.scene.addPixmap(pix)
            if item is None:
                raise ValueError(
                    f"Failed to create graphics item for image: {image_path}"
                )
            item.setZValue(1)
            item.setOpacity(0.5)
            self.dam_item = item
        else:
            self.dam_item.setPixmap(pix)

        self._set_item_transform_origin_to_center(self.dam_item)
        self._fit_if_possible()

    def set_deformed_opacity(self, opacity: float) -> None:
        if self.dam_item is not None:
            self.dam_item.setOpacity(max(0.0, min(1.0, float(opacity))))

    # ---------------------- export ----------------------

    def export_scene_png(self, path: str) -> None:
        self.exporter.export_scene_png(path)

    def get_overlay_state(self) -> dict[str, Any]:
        return self.exporter.get_overlay_state()

    # ---------------------- restore state ----------------------

    def restore_overlay_state(self, state: Mapping[str, Any]) -> None:
        self.exporter.restore_overlay_state(
            state, bounds_rect_provider=self._bounds_rect
        )

        bounds = self._bounds_rect()
        if bounds is None:
            bounds = self.scene.sceneRect()

        self.renderer.render_guide_line(self.state, bounds)
        self.renderer.render_crossmember_line(self.state, bounds)
        self.renderer.ensure_legend(self.state, bounds)
        self.renderer.render_ci(self.state)
        self.renderer.refresh_legend(self.state)
        self.renderer.apply_scaling()

    # ---------------------- zoom ----------------------

    def wheel_zoom(self, factor: float) -> None:
        self._zoom_factor *= factor
        self.host.scale(factor, factor)
        self.renderer.apply_scaling()

    # ---------------------- helpers ----------------------

    def _item_scene_rect(self, item: QGraphicsPixmapItem | None) -> QRectF | None:
        if item is None:
            return None
        # sceneBoundingRect already includes position, rotation and scale
        rect = item.sceneBoundingRect()
        if rect.isNull() or not rect.isValid():
            return None
        return rect

    def _combined_items_scene_rect(self) -> QRectF | None:
        rects: list[QRectF] = []

        ref_rect = self._item_scene_rect(self.ref_item)
        if ref_rect is not None:
            rects.append(ref_rect)

        dam_rect = self._item_scene_rect(self.dam_item)
        if dam_rect is not None:
            rects.append(dam_rect)

        if not rects:
            return None

        union = QRectF(rects[0])
        for r in rects[1:]:
            union = union.united(r)
        return union

    def _bounds_rect(self):
        """
        Bounds used by marking/overlay must be in SCENE coordinates.
        """
        rect = self._combined_items_scene_rect()
        if rect is not None:
            return rect
        return None

    def _update_scene_rect_from_items(self) -> None:
        rect = self._combined_items_scene_rect()
        if rect is None:
            return

        # small padding to avoid items/overlay feeling clipped at the edges
        pad = 80.0
        padded = rect.adjusted(-pad, -pad, pad, pad)
        self.scene.setSceneRect(padded)

    def _fit_if_possible(self):
        rect = self._combined_items_scene_rect()
        if rect is None:
            return

        pad = 20.0
        padded = rect.adjusted(-pad, -pad, pad, pad)

        self.scene.setSceneRect(padded)
        self.host.fitInView(
            padded,
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        self._zoom_factor = 1.0
        self.renderer.apply_scaling()

    def _set_item_transform_origin_to_center(
        self, item: QGraphicsPixmapItem | None
    ) -> None:
        if item is None:
            return

        rect = item.boundingRect()
        item.setTransformOriginPoint(rect.center())

    def clear_images(self) -> None:
        if self.ref_item is not None:
            self.scene.removeItem(self.ref_item)
            self.ref_item = None

        if self.dam_item is not None:
            self.scene.removeItem(self.dam_item)
            self.dam_item = None

        self.state.clear_calibration()
        self.state.clear_markings()
        self.renderer.clear_all()
        self.scene.setSceneRect(QRectF())
        self._zoom_factor = 1.0
        self._show_welcome()
