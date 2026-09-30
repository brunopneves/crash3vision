from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QGraphicsSimpleTextItem,
    QGraphicsRectItem,
)

from app.ui.overlay.state import OverlayState

PointLike = Union[Tuple[float, float], QPointF]


@dataclass
class _TextMeta:
    base_pt: float
    kind: str  # "legend" | "label" | "generic"


@dataclass
class _LineMeta:
    base_width: float


class OverlayRenderer:
    """
    Draws/refreshes overlay items on a QGraphicsScene.

    Scaling rule:
      - zoom OUT -> overlay (texts/lines) should grow
      - zoom IN  -> overlay (texts/lines) should shrink
    """

    def __init__(
        self, scene: QGraphicsScene, get_zoom_factor: Callable[[], float]
    ) -> None:
        self._scene = scene
        self._get_zoom_factor = get_zoom_factor

        self._items: Dict[str, QGraphicsItem] = {}
        self._text_meta: Dict[str, _TextMeta] = {}
        self._line_meta: Dict[str, _LineMeta] = {}

        # base sizes (scaled by apply_scaling)
        self._legend_base_pt = 22.0
        self._c_label_base_pt = 24.0  # larger "C1..C6" labels on image

        # pens
        self._pen_cal_line = QPen(QColor(255, 255, 0, 220))
        self._pen_cal_line.setStyle(Qt.PenStyle.SolidLine)
        self._pen_cal_line.setWidthF(3.0)

        self._pen_cal_point = QPen(QColor(255, 255, 0, 220))
        self._pen_cal_point.setWidthF(2.0)

        self._pen_w_dashed = QPen(QColor(0, 150, 255, 220))
        self._pen_w_dashed.setStyle(Qt.PenStyle.DashLine)
        self._pen_w_dashed.setWidthF(3.0)

        self._pen_slice_dashed = QPen(QColor(0, 150, 255, 220))
        self._pen_slice_dashed.setStyle(Qt.PenStyle.DashLine)
        self._pen_slice_dashed.setWidthF(3.0)

        self._pen_guide = QPen(QColor(255, 220, 0, 220))
        self._pen_guide.setStyle(Qt.PenStyle.DashLine)
        self._pen_guide.setWidthF(3.0)

        self._pen_ci = QPen(QColor(220, 0, 0, 230))
        self._pen_ci.setStyle(Qt.PenStyle.SolidLine)
        self._pen_ci.setWidthF(4.0)

        self._pen_ci_profile = QPen(QColor(255, 170, 0, 220))
        self._pen_ci_profile.setStyle(Qt.PenStyle.SolidLine)
        self._pen_ci_profile.setWidthF(3.0)

        self._pen_crossmember = QPen(QColor(0, 255, 255, 220))
        self._pen_crossmember.setStyle(Qt.PenStyle.DashLine)
        self._pen_crossmember.setWidthF(3.0)

        # preview pen (slightly transparent)
        self._pen_preview = QPen(QColor(255, 80, 80, 190))
        self._pen_preview.setStyle(Qt.PenStyle.SolidLine)
        self._pen_preview.setWidthF(3.0)

        # brushes
        self._brush_legend_bg = QBrush(QColor(0, 0, 0, 150))

    # ----------------------------- public API -----------------------------

    def clear_all(self) -> None:
        for it in list(self._items.values()):
            self._scene.removeItem(it)
        self._items.clear()
        self._text_meta.clear()
        self._line_meta.clear()

    def apply_scaling(self) -> None:
        z = float(self._get_zoom_factor() or 1.0)
        if z <= 0:
            z = 1.0

        ui_scale = 1.0 / z
        ui_scale = max(0.6, min(5.0, ui_scale))

        # texts
        for key, meta in self._text_meta.items():
            it = self._items.get(key)
            if isinstance(it, QGraphicsSimpleTextItem):
                f = it.font()
                f.setPointSizeF(max(6.0, meta.base_pt * ui_scale))
                it.setFont(f)

        # line widths / outline widths
        for key, meta in self._line_meta.items():
            it = self._items.get(key)
            if isinstance(it, QGraphicsLineItem):
                pen = it.pen()
                pen.setWidthF(max(1.0, meta.base_width * ui_scale))
                it.setPen(pen)
            elif isinstance(it, QGraphicsEllipseItem):
                pen = it.pen()
                pen.setWidthF(max(1.0, meta.base_width * ui_scale))
                it.setPen(pen)

        # legend bg padding depends on zoom too
        self._update_legend_bg(ui_scale=ui_scale)

    def render_calibration(self, state: OverlayState) -> None:
        self._set_or_clear_point(
            "cal_p1_dot", state.cal_p1, radius=5.0, pen=self._pen_cal_point
        )
        self._set_or_clear_point(
            "cal_p2_dot", state.cal_p2, radius=5.0, pen=self._pen_cal_point
        )

        if state.cal_p1 is not None and state.cal_p2 is not None:
            self._set_line(
                "cal_line",
                state.cal_p1,
                state.cal_p2,
                pen=self._pen_cal_line,
                base_width=3.0,
                z=30,
            )
        else:
            self._remove("cal_line")

        self.apply_scaling()

    def render_w_and_slices(
        self, state: OverlayState, bounds_rect: Optional[QRectF]
    ) -> None:
        # Robust fallback: if bounds not provided, use sceneRect()
        if bounds_rect is None:
            bounds_rect = self._scene.sceneRect()

        if state.w_p1 is not None:
            self._set_vertical_dashed(
                "w_left",
                x=float(state.w_p1[0]),
                bounds=bounds_rect,
                pen=self._pen_w_dashed,
            )
        else:
            self._remove("w_left")

        if state.w_p2 is not None:
            self._set_vertical_dashed(
                "w_right",
                x=float(state.w_p2[0]),
                bounds=bounds_rect,
                pen=self._pen_w_dashed,
            )
        else:
            self._remove("w_right")

        existing = [k for k in self._items.keys() if k.startswith("slice_")]
        keep = set()

        for i, sx in enumerate(list(state.slice_x)):
            key = f"slice_{i}"
            keep.add(key)
            self._set_vertical_dashed(
                key, x=float(sx), bounds=bounds_rect, pen=self._pen_slice_dashed
            )

        for k in existing:
            if k not in keep:
                self._remove(k)

        self.apply_scaling()

    def render_guide_line(
        self, state: OverlayState, bounds_rect: Optional[QRectF]
    ) -> None:
        if state.guide_y is None or not state.slice_x:
            self._remove("guide_line")
            self.apply_scaling()
            return

        y = float(state.guide_y)

        # limitar estritamente entre C1 e C6
        left_x = min(float(x) for x in state.slice_x)
        right_x = max(float(x) for x in state.slice_x)

        self._set_line(
            key="guide_line",
            p1=(left_x, y),
            p2=(right_x, y),
            pen=self._pen_guide,
            base_width=3.0,
            z=35,
        )
        self.apply_scaling()

    def render_crossmember_line(
        self, state: OverlayState, bounds_rect: Optional[QRectF]
    ) -> None:
        if state.crossmember_y is None or not state.slice_x:
            self._remove("crossmember_line")
            self.apply_scaling()
            return

        y = float(state.crossmember_y)

        left_x = min(float(x) for x in state.slice_x)
        right_x = max(float(x) for x in state.slice_x)

        pen = QPen(QColor(0, 255, 255, 220))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidthF(3.0)

        self._set_line(
            key="crossmember_line",
            p1=(left_x, y),
            p2=(right_x, y),
            pen=self._pen_crossmember,
            base_width=3.0,
            z=34,
        )

        self.apply_scaling()

    # ---------- Legend (top-left) ----------

    def ensure_legend(self, state: OverlayState, bounds_rect: Optional[QRectF]) -> None:
        if bounds_rect is None:
            bounds_rect = self._scene.sceneRect()

        if "legend_bg" not in self._items:
            bg = QGraphicsRectItem()
            bg.setZValue(60)
            bg.setPen(QPen(Qt.PenStyle.NoPen))
            bg.setBrush(self._brush_legend_bg)
            self._scene.addItem(bg)
            self._items["legend_bg"] = bg

        for i in range(1, 7):
            key = f"legend_c{i}"
            if key not in self._items:
                txt = QGraphicsSimpleTextItem(f"C{i} = ")
                txt.setZValue(61)
                txt.setBrush(QBrush(QColor(255, 255, 255, 235)))
                self._scene.addItem(txt)
                self._items[key] = txt
                self._text_meta[key] = _TextMeta(
                    base_pt=self._legend_base_pt, kind="legend"
                )

        self._layout_legend(bounds_rect=bounds_rect)
        self.refresh_legend(state)
        self.apply_scaling()

    def refresh_legend(self, state: OverlayState) -> None:
        for i in range(1, 7):
            key = f"legend_c{i}"
            it = self._items.get(key)
            if not isinstance(it, QGraphicsSimpleTextItem):
                continue

            m_val: Optional[float] = None
            if i in state.c_points:
                p1, p2 = state.c_points[i]
                dx = float(p2[0]) - float(p1[0])
                dy = float(p2[1]) - float(p1[1])
                px = (dx * dx + dy * dy) ** 0.5
                if state.m_per_px is not None:
                    m_val = px * float(state.m_per_px)

            if m_val is None:
                it.setText(f"C{i} = ")
            else:
                it.setText(f"C{i} = {m_val:.3f} m")

        self.apply_scaling()

    # ---------- Ci final render ----------

    def render_ci(self, state: OverlayState) -> None:
        for k in [
            k
            for k in self._items.keys()
            if k.startswith("ci_line_")
            or k.startswith("ci_lbl_")
            or k.startswith("ci_x_")
        ]:
            self._remove(k)

        for i, pts in state.c_points.items():
            p1, p2 = pts
            self._set_line(
                key=f"ci_line_{i}",
                p1=p1,
                p2=p2,
                pen=self._pen_ci,
                base_width=4.0,
                z=40,
            )

            self._set_cross(key=f"ci_x_{i}_a", p=p1, z=45)
            self._set_cross(key=f"ci_x_{i}_b", p=p2, z=45)

            midx = (float(p1[0]) + float(p2[0])) / 2.0
            midy = (float(p1[1]) + float(p2[1])) / 2.0
            self._set_text(
                key=f"ci_lbl_{i}",
                text=f"C{i}",
                pos=(midx, midy + 20.0),
                color=QColor(255, 255, 255, 235),
                base_pt=self._c_label_base_pt,
                z=46,
                kind="label",
            )

        self.apply_scaling()

    def render_ci_profile(self, state: OverlayState) -> None:
        # remove old profile segments
        for k in [k for k in self._items.keys() if k.startswith("ci_profile_")]:
            self._remove(k)

        # only show when all C1..C6 are present
        if not all(i in state.c_points for i in range(1, 7)):
            self.apply_scaling()
            return

        profile_points: list[tuple[float, float]] = []

        for i in range(1, 7):
            p1, p2 = state.c_points[i]

            # connect the upper endpoint of each Ci segment
            upper_pt = p1 if float(p1[1]) <= float(p2[1]) else p2
            profile_points.append((float(upper_pt[0]), float(upper_pt[1])))

        # draw polyline as connected line segments
        for i in range(len(profile_points) - 1):
            self._set_line(
                key=f"ci_profile_{i}",
                p1=profile_points[i],
                p2=profile_points[i + 1],
                pen=self._pen_ci_profile,
                base_width=3.0,
                z=39,
            )

        self.apply_scaling()

    # ---------- Ci preview (needed by MarkingTool) ----------

    def clear_ci_preview(self) -> None:
        for k in [k for k in self._items.keys() if k.startswith("ci_preview_")]:
            self._remove(k)
        self.apply_scaling()

    def render_ci_preview(
        self, ref_point: PointLike, def_point: Optional[PointLike]
    ) -> None:
        ref = self._to_xy(ref_point)
        self._set_cross(key="ci_preview_ref", p=ref, z=80)

        if def_point is not None:
            dp = self._to_xy(def_point)
            self._set_line(
                key="ci_preview_line",
                p1=ref,
                p2=dp,
                pen=self._pen_preview,
                base_width=3.0,
                z=79,
            )
            self._set_cross(key="ci_preview_def", p=dp, z=80)
        else:
            self._remove("ci_preview_line")
            for k in ["ci_preview_def_h", "ci_preview_def_v"]:
                self._remove(k)

        self.apply_scaling()

    # ----------------------------- internal helpers -----------------------------

    def _to_xy(self, p: PointLike) -> Tuple[float, float]:
        if isinstance(p, QPointF):
            return float(p.x()), float(p.y())
        return float(p[0]), float(p[1])

    def _remove(self, key: str) -> None:
        it = self._items.pop(key, None)
        if it is not None:
            self._scene.removeItem(it)
        self._text_meta.pop(key, None)
        self._line_meta.pop(key, None)

    def _set_line(
        self,
        key: str,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        pen: QPen,
        base_width: float,
        z: float,
    ) -> None:
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])

        it = self._items.get(key)
        if isinstance(it, QGraphicsLineItem):
            it.setLine(x1, y1, x2, y2)
            it.setPen(QPen(pen))
            it.setZValue(z)
        else:
            li = QGraphicsLineItem(x1, y1, x2, y2)
            li.setPen(QPen(pen))
            li.setZValue(z)
            self._scene.addItem(li)
            self._items[key] = li

        self._line_meta[key] = _LineMeta(base_width=base_width)

    def _set_or_clear_point(
        self, key: str, p: Optional[Tuple[float, float]], radius: float, pen: QPen
    ) -> None:
        if p is None:
            self._remove(key)
            return

        x, y = float(p[0]), float(p[1])
        r = float(radius)
        rect = QRectF(x - r, y - r, 2 * r, 2 * r)

        it = self._items.get(key)
        if isinstance(it, QGraphicsEllipseItem):
            it.setRect(rect)
            it.setPen(QPen(pen))
            it.setBrush(Qt.BrushStyle.NoBrush)
            it.setZValue(35)
        else:
            dot = QGraphicsEllipseItem(rect)
            dot.setPen(QPen(pen))
            dot.setBrush(Qt.BrushStyle.NoBrush)
            dot.setZValue(35)
            self._scene.addItem(dot)
            self._items[key] = dot

        self._line_meta[key] = _LineMeta(base_width=2.0)

    def _set_vertical_dashed(
        self, key: str, x: float, bounds: QRectF, pen: QPen
    ) -> None:
        y1 = float(bounds.top())
        y2 = float(bounds.bottom())

        self._set_line(
            key=key,
            p1=(x, y1),
            p2=(x, y2),
            pen=pen,
            base_width=float(pen.widthF() or 3.0),
            z=25,
        )

    def _set_text(
        self,
        key: str,
        text: str,
        pos: Tuple[float, float],
        color: QColor,
        base_pt: float,
        z: float,
        kind: str,
    ) -> None:
        it = self._items.get(key)
        if isinstance(it, QGraphicsSimpleTextItem):
            it.setText(text)
            t = it
        else:
            t = QGraphicsSimpleTextItem(text)
            self._scene.addItem(t)
            self._items[key] = t

        t.setBrush(QBrush(color))
        f = t.font()
        f.setPointSizeF(base_pt)
        t.setFont(f)
        t.setPos(float(pos[0]), float(pos[1]))
        t.setZValue(z)

        self._text_meta[key] = _TextMeta(base_pt=base_pt, kind=kind)

    def _set_cross(self, key: str, p: Tuple[float, float], z: float) -> None:
        x, y = float(p[0]), float(p[1])
        size = 8.0
        pen = QPen(QColor(255, 255, 255, 220))
        pen.setWidthF(2.0)

        self._set_line(
            key=f"{key}_h",
            p1=(x - size, y),
            p2=(x + size, y),
            pen=pen,
            base_width=2.0,
            z=z,
        )
        self._set_line(
            key=f"{key}_v",
            p1=(x, y - size),
            p2=(x, y + size),
            pen=pen,
            base_width=2.0,
            z=z,
        )

    # -------- legend layout / background --------

    def _layout_legend(self, bounds_rect: QRectF) -> None:
        x0 = float(bounds_rect.left()) + 12.0
        y0 = float(bounds_rect.top()) + 12.0
        line_h = 30.0

        for i in range(1, 7):
            key = f"legend_c{i}"
            it = self._items.get(key)
            if isinstance(it, QGraphicsSimpleTextItem):
                it.setPos(x0, y0 + (i - 1) * line_h)
                it.setZValue(61)

                f = it.font()
                f.setPointSizeF(self._legend_base_pt)
                it.setFont(f)

                self._text_meta[key] = _TextMeta(
                    base_pt=self._legend_base_pt, kind="legend"
                )

        self._update_legend_bg(ui_scale=1.0)

    def _update_legend_bg(self, ui_scale: float) -> None:

        it = self._items.get("legend_bg")
        if not isinstance(it, QGraphicsRectItem):
            return
        bg = it

        rects: List[QRectF] = []
        for i in range(1, 7):
            k = f"legend_c{i}"
            ti = self._items.get(k)
            if isinstance(ti, QGraphicsSimpleTextItem):
                rects.append(ti.mapToScene(ti.boundingRect()).boundingRect())

        if not rects:
            bg.setRect(QRectF())
            return

        union = rects[0]
        for r in rects[1:]:
            union = union.united(r)

        pad = 10.0 * ui_scale
        bg.setRect(union.adjusted(-pad, -pad, pad, pad))
        bg.setZValue(60)
        bg.setPen(QPen(Qt.PenStyle.NoPen))
        bg.setBrush(self._brush_legend_bg)

    def clear_legend(self) -> None:
        keys_to_remove = [
            k
            for k in self._items.keys()
            if k == "legend_bg" or k.startswith("legend_c")
        ]
        for k in keys_to_remove:
            self._remove(k)
        self.apply_scaling()
