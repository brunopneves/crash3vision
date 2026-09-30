from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent


class ToolBase:
    """
    Base class for tools.

    NOTE:
    We intentionally keep 'host' typed as Any because PySide6 Qt methods
    use position-only parameters and overloaded signatures that don't
    play nicely with Protocol-based typing in Pylance.
    """
    name: str = "base"

    def activate(self, host: Any) -> None:
        _ = host

    def deactivate(self, host: Any) -> None:
        _ = host

    def mouse_press(self, host: Any, scene_pos, event: QMouseEvent) -> bool:
        _ = host, scene_pos, event
        return False

    def mouse_move(self, host: Any, scene_pos, event: QMouseEvent) -> bool:
        _ = host, scene_pos, event
        return False

    def mouse_release(self, host: Any, scene_pos, event: QMouseEvent) -> bool:
        _ = host, scene_pos, event
        return False

    def wheel(self, host: Any, factor: float) -> None:
        _ = host, factor

    @staticmethod
    def is_left_click(event: QMouseEvent) -> bool:
        return event.button() == Qt.MouseButton.LeftButton