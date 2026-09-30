from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsPixmapItem

from .base import ToolBase


class AlignmentTool(ToolBase):
    """
    Drag-based alignment tool for the currently selected image target.
    The active target is provided externally by CanvasController.
    """

    def __init__(
        self,
        get_target_item: Callable[[], QGraphicsPixmapItem | None],
        is_locked: Callable[[], bool],
    ) -> None:
        self._get_target_item = get_target_item
        self._is_locked = is_locked

        self._dragging = False
        self._last_scene_pos: QPointF | None = None

    def deactivate(self, host) -> None:
        self._dragging = False
        self._last_scene_pos = None

    def mouse_press(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        if self._is_locked():
            return False

        if event.button() != Qt.MouseButton.LeftButton:
            return False

        item = self._get_target_item()
        if item is None:
            return False

        self._dragging = True
        self._last_scene_pos = scene_pos
        return True

    def mouse_move(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = view
        _ = event

        if self._is_locked():
            return False

        if not self._dragging:
            return False

        item = self._get_target_item()
        if item is None or self._last_scene_pos is None:
            return False

        delta = scene_pos - self._last_scene_pos
        item.moveBy(delta.x(), delta.y())
        self._last_scene_pos = scene_pos
        return True

    def mouse_release(self, view, scene_pos: QPointF, event: QMouseEvent) -> bool:
        _ = view
        _ = scene_pos

        if event.button() != Qt.MouseButton.LeftButton:
            return False

        if not self._dragging:
            return False

        self._dragging = False
        self._last_scene_pos = None
        return True
