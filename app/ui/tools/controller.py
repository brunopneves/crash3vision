from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView

from .base import ToolBase


@dataclass
class ToolFlags:
    alignment_mode: bool = False
    calibration_mode: bool = False
    set_w_mode: bool = False
    set_guide_mode: bool = False
    measure_ci_mode: bool = False


class ToolController:
    """
    Owns:
      - active tool lifecycle (activate/deactivate)
      - flags mirroring current UI mode (optional but useful)

    CanvasView remains the host. Tools mutate state and call renderer;
    controller just orchestrates which tool is active.
    """

    def __init__(self, host: Any) -> None:
        self.host = host
        self.flags = ToolFlags()
        self._active: Optional[ToolBase] = None

    @property
    def active_tool(self) -> Optional[ToolBase]:
        return self._active

    def set_active(self, tool: ToolBase | None) -> None:
        if self._active is tool:
            return

        if self._active is not None:
            self._active.deactivate(self.host)

        self._active = tool

        if self._active is not None:
            self._active.activate(self.host)
        else:
            self.host.setCursor(Qt.CursorShape.ArrowCursor)
            self.host.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def disable_all(self) -> None:
        self.flags = ToolFlags()
        self.set_active(None)

    def set_mode_alignment(self, enabled: bool, tool: ToolBase) -> None:
        if enabled:
            self.flags = ToolFlags(alignment_mode=True)
            self.set_active(tool)
        else:
            self.flags.alignment_mode = False
            self.set_active(None)

    def set_mode_calibration(self, enabled: bool, tool: ToolBase) -> None:
        if enabled:
            self.flags = ToolFlags(calibration_mode=True)
            self.set_active(tool)
        else:
            self.flags.calibration_mode = False
            self.set_active(None)

    def set_mode_marking_w(self, enabled: bool, tool: ToolBase) -> None:
        if enabled:
            self.flags = ToolFlags(set_w_mode=True)
            self.set_active(tool)
        else:
            self.flags.set_w_mode = False

    def set_mode_marking_guide(self, enabled: bool, tool: ToolBase) -> None:
        if enabled:
            self.flags = ToolFlags(set_guide_mode=True)
            self.set_active(tool)
        else:
            self.flags.set_guide_mode = False

    def set_mode_marking_ci(self, enabled: bool, tool: ToolBase) -> None:
        if enabled:
            self.flags = ToolFlags(measure_ci_mode=True)
            self.set_active(tool)
        else:
            self.flags.measure_ci_mode = False
