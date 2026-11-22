from __future__ import annotations

import math
from typing import Callable, Literal

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QBrush, QFont, QMouseEvent, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from app.core.rigid_region_alignment import (
    POINT_ANCHOR_COUNT,
    RigidRegion,
    make_adaptive_deformed_region,
    make_point_anchor_region,
)
from .base import ToolBase


RegionTarget = Literal["ref", "dam"]


class RigidRegionTool(ToolBase):
    name = "rigid_region"

    def __init__(
        self,
        get_item: Callable[[RegionTarget], QGraphicsPixmapItem | None],
        on_region_selected: Callable[[RegionTarget, RigidRegion], None],
    ) -> None:
        self._get_item = get_item
        self._on_region_selected = on_region_selected
        self._target: RegionTarget = "ref"
        self._press_local: QPointF | None = None
        self._pressed_suggestion_index: int | None = None
        self._hover_item: QGraphicsPolygonItem | None = None
        self._anchor_items: dict[RegionTarget, list[tuple[QGraphicsItem, ...]]] = {
            "ref": [],
            "dam": [],
        }
        self._regions: dict[RegionTarget, list[RigidRegion]] = {
            "ref": [],
            "dam": [],
        }
        self._suggestion_items: list[tuple[QGraphicsItem, ...]] = []
        self._suggestion_regions: list[RigidRegion] = []

    def activate(self, host) -> None:
        host.setCursor(Qt.CursorShape.CrossCursor)
        host.setDragMode(QGraphicsView.DragMode.NoDrag)

    def deactivate(self, host) -> None:
        self._press_local = None
        self._pressed_suggestion_index = None
        self._remove_hover()
        host.setCursor(Qt.CursorShape.ArrowCursor)

    def set_target(self, target: RegionTarget) -> None:
        self._target = target
        self._press_local = None
        self._pressed_suggestion_index = None
        self._remove_hover()

    def clear_visuals(self) -> None:
        self._remove_hover()
        self._remove_anchor()
        self._remove_suggestions()

    def set_visuals_visible(self, visible: bool) -> None:
        for anchors in self._anchor_items.values():
            for visuals in anchors:
                for visual in visuals:
                    visual.setVisible(visible)
        for visuals in self._suggestion_items:
            for visual in visuals:
                visual.setVisible(visible)

    def show_anchor(self, target: RegionTarget, region: RigidRegion) -> None:
        self._target = target
        self._set_anchor(region)

    def show_suggestions(self, regions: tuple[RigidRegion, ...]) -> None:
        self._remove_suggestions()
        item = self._get_item("ref")
        if item is None:
            return
        for index, region in enumerate(regions, start=1):
            outline = QGraphicsPolygonItem(item)
            outline.setPolygon(self._polygon(region))
            outline.setBrush(QBrush(QColor(255, 196, 64, 12)))
            pen = QPen(QColor(255, 204, 72, 220))
            pen.setStyle(Qt.PenStyle.DotLine)
            pen.setWidthF(2.0)
            pen.setCosmetic(True)
            outline.setPen(pen)
            outline.setZValue(86)
            radius = 5.0
            dot = QGraphicsEllipseItem(
                region.center_x - radius,
                region.center_y - radius,
                radius * 2.0,
                radius * 2.0,
                item,
            )
            dot_pen = QPen(QColor(255, 204, 72, 235))
            dot_pen.setWidthF(2.0)
            dot_pen.setCosmetic(True)
            dot.setPen(dot_pen)
            dot.setBrush(QBrush(QColor(255, 196, 64, 105)))
            dot.setZValue(87)
            label = QGraphicsSimpleTextItem(str(index), item)
            font = QFont()
            font.setBold(True)
            font.setPixelSize(15)
            label.setFont(font)
            label.setBrush(QBrush(QColor(255, 214, 96, 255)))
            label.setPos(region.center_x + 8.0, region.center_y - 21.0)
            label.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                True,
            )
            label.setZValue(88)
            self._suggestion_items.append((outline, dot, label))
            self._suggestion_regions.append(region)

    def mouse_press(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        local = self._local_point(scene_pos)
        if local is None:
            return False
        self._press_local = local
        self._pressed_suggestion_index = self._nearest_suggestion(local)
        hover_center = local
        if self._pressed_suggestion_index is not None:
            suggestion = self._suggestion_regions[self._pressed_suggestion_index]
            hover_center = QPointF(suggestion.center_x, suggestion.center_y)
        self._set_hover(self._region_at(hover_center, None))
        return True

    def mouse_move(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = view
        local = self._local_point(scene_pos)
        if local is None:
            self._remove_hover()
            return self._press_local is not None
        if self._press_local is None:
            self._set_hover(self._region_at(local, None))
        elif self._pressed_suggestion_index is not None:
            self._set_hover(self._region_at(local, None))
        else:
            self._set_hover(self._region_at(self._press_local, local))
        return True

    def mouse_release(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = view
        if event.button() != Qt.MouseButton.LeftButton or self._press_local is None:
            return False
        release_local = self._local_point(scene_pos)
        if release_local is None:
            release_local = self._press_local
        center = self._press_local
        if self._pressed_suggestion_index is not None:
            moved = math.hypot(
                release_local.x() - self._press_local.x(),
                release_local.y() - self._press_local.y(),
            )
            if moved <= 2.0:
                suggestion = self._suggestion_regions[
                    self._pressed_suggestion_index
                ]
                center = QPointF(suggestion.center_x, suggestion.center_y)
            else:
                center = release_local
        region = self._region_at(center, release_local)
        suggestion_index = self._pressed_suggestion_index
        self._press_local = None
        self._pressed_suggestion_index = None
        self._remove_hover()
        if self._target == "ref":
            self._consume_suggestion(region, suggestion_index)
        self._set_anchor(region)
        self._on_region_selected(self._target, region)
        return True

    def _nearest_suggestion(self, point: QPointF) -> int | None:
        if self._target != "ref" or not self._suggestion_regions:
            return None
        nearest: tuple[float, int] | None = None
        for index, region in enumerate(self._suggestion_regions):
            distance = math.hypot(
                point.x() - region.center_x,
                point.y() - region.center_y,
            )
            capture = max(region.length, region.height) * 0.35
            if distance <= capture and (nearest is None or distance < nearest[0]):
                nearest = (distance, index)
        return None if nearest is None else nearest[1]

    def _consume_suggestion(
        self,
        region: RigidRegion,
        preferred_index: int | None,
    ) -> None:
        if not self._suggestion_regions:
            return
        index = preferred_index
        if index is None:
            index = min(
                range(len(self._suggestion_regions)),
                key=lambda current: math.hypot(
                    region.center_x - self._suggestion_regions[current].center_x,
                    region.center_y - self._suggestion_regions[current].center_y,
                ),
            )
        visuals = self._suggestion_items.pop(index)
        self._suggestion_regions.pop(index)
        for visual in visuals:
            if visual.scene() is not None:
                visual.scene().removeItem(visual)

    def _target_item(self) -> QGraphicsPixmapItem | None:
        return self._get_item(self._target)

    def _local_point(self, scene_pos: QPointF) -> QPointF | None:
        item = self._target_item()
        if item is None:
            return None
        local = item.mapFromScene(scene_pos)
        if not item.boundingRect().contains(local):
            return None
        return local

    def _region_at(
        self, center: QPointF, drag_end: QPointF | None
    ) -> RigidRegion:
        item = self._target_item()
        if item is None:
            raise RuntimeError("Rigid-region target image is not loaded")
        rect = item.boundingRect()
        if self._target == "ref":
            return make_point_anchor_region(
                int(rect.width()),
                int(rect.height()),
                (center.x(), center.y()),
            )
        end = None if drag_end is None else (drag_end.x(), drag_end.y())
        reference_item = self._get_item("ref")
        reference_height = (
            int(reference_item.boundingRect().height())
            if reference_item is not None
            else int(rect.height())
        )
        return make_adaptive_deformed_region(
            int(rect.width()),
            int(rect.height()),
            (center.x(), center.y()),
            self._regions["ref"],
            reference_height,
            end,
        )

    @staticmethod
    def _polygon(region: RigidRegion) -> QPolygonF:
        half_length = region.length / 2.0
        half_height = region.height / 2.0
        theta = math.radians(region.angle_deg)
        cosine = math.cos(theta)
        sine = math.sin(theta)
        points = []
        for longitudinal, transverse in (
            (-half_length, -half_height),
            (half_length, -half_height),
            (half_length, half_height),
            (-half_length, half_height),
        ):
            points.append(
                QPointF(
                    region.center_x
                    + cosine * longitudinal
                    - sine * transverse,
                    region.center_y
                    + sine * longitudinal
                    + cosine * transverse,
                )
            )
        return QPolygonF(points)

    @staticmethod
    def _pen(alpha: int) -> QPen:
        pen = QPen(QColor(0, 255, 255, alpha))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(2.0)
        pen.setCosmetic(True)
        return pen

    def _set_hover(self, region: RigidRegion) -> None:
        item = self._target_item()
        if item is None:
            return
        if self._hover_item is None or self._hover_item.parentItem() is not item:
            self._remove_hover()
            self._hover_item = QGraphicsPolygonItem(item)
            self._hover_item.setZValue(90)
            self._hover_item.setBrush(QBrush(QColor(0, 255, 255, 22)))
            self._hover_item.setPen(self._pen(190))
        self._hover_item.setPolygon(self._polygon(region))

    def _set_anchor(self, region: RigidRegion) -> None:
        item = self._target_item()
        if item is None:
            return
        if self._target == "dam":
            self._remove_anchor(self._target)
        elif len(self._anchor_items["ref"]) >= POINT_ANCHOR_COUNT:
            return
        anchor_item = QGraphicsPolygonItem(item)
        anchor_item.setPolygon(self._polygon(region))
        anchor_item.setBrush(QBrush(QColor(0, 255, 255, 12)))
        anchor_item.setPen(self._pen(230))
        anchor_item.setZValue(91)
        radius = 5.0
        anchor_dot = QGraphicsEllipseItem(
            region.center_x - radius,
            region.center_y - radius,
            radius * 2.0,
            radius * 2.0,
            item,
        )
        dot_pen = QPen(QColor(0, 255, 255, 240))
        dot_pen.setWidthF(2.0)
        dot_pen.setCosmetic(True)
        anchor_dot.setPen(dot_pen)
        anchor_dot.setBrush(QBrush(QColor(0, 255, 255, 120)))
        anchor_dot.setZValue(92)
        visuals: tuple[QGraphicsItem, ...] = (anchor_item, anchor_dot)
        if self._target == "ref":
            label = QGraphicsSimpleTextItem(
                str(len(self._anchor_items["ref"]) + 1),
                item,
            )
            font = QFont()
            font.setBold(True)
            font.setPixelSize(14)
            label.setFont(font)
            label.setBrush(QBrush(QColor(0, 255, 255, 255)))
            label.setPos(region.center_x + 8.0, region.center_y - 20.0)
            label.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                True,
            )
            label.setZValue(93)
            visuals = (anchor_item, anchor_dot, label)
        self._anchor_items[self._target].append(visuals)
        self._regions[self._target].append(region)

    def _remove_hover(self) -> None:
        if self._hover_item is not None:
            scene = self._hover_item.scene()
            if scene is not None:
                scene.removeItem(self._hover_item)
            self._hover_item = None

    def _remove_anchor(self, target: RegionTarget | None = None) -> None:
        targets = tuple(self._anchor_items) if target is None else (target,)
        for current_target in targets:
            anchors = self._anchor_items[current_target]
            self._anchor_items[current_target] = []
            self._regions[current_target] = []
            for visuals in anchors:
                for visual in visuals:
                    if visual.scene() is not None:
                        visual.scene().removeItem(visual)

    def _remove_suggestions(self) -> None:
        suggestions = self._suggestion_items
        self._suggestion_items = []
        self._suggestion_regions = []
        for visuals in suggestions:
            for visual in visuals:
                if visual.scene() is not None:
                    visual.scene().removeItem(visual)
