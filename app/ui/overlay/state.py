from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PointF = tuple[float, float]


def _pt(d: Any) -> PointF | None:
    if not d:
        return None
    return (float(d["x"]), float(d["y"]))


def _pt_dict(p: PointF | None) -> dict[str, float] | None:
    if p is None:
        return None
    return {"x": float(p[0]), "y": float(p[1])}


@dataclass
class OverlayState:
    # Scale
    m_per_px: float | None = None

    # Calibration points
    cal_p1: PointF | None = None
    cal_p2: PointF | None = None

    # W points (left/right)
    w_p1: PointF | None = None
    w_p2: PointF | None = None

    # Slice centers (x positions in scene coords)
    slice_x: list[float] = field(default_factory=list)

    # Horizontal guide line for theoretical damage start
    guide_y: float | None = None

    # Visual offset from outer bumper line to bumper crossmember
    bumper_offset_m: float | None = None
    bumper_offset_px: float | None = None
    crossmember_y: float | None = None

    # C points: idx -> (ref_point, def_point) (same x; different y)
    c_points: dict[int, tuple[PointF, PointF]] = field(default_factory=dict)

    def clear_markings(self) -> None:
        self.w_p1 = None
        self.w_p2 = None
        self.slice_x.clear()
        self.guide_y = None
        self.bumper_offset_m = None
        self.bumper_offset_px = None
        self.crossmember_y = None
        self.c_points.clear()

    def clear_calibration(self) -> None:
        self.cal_p1 = None
        self.cal_p2 = None

    def to_dict(self) -> dict[str, Any]:
        c_points_out: dict[str, dict[str, dict[str, float]]] = {}
        for idx, (pref, pdef) in self.c_points.items():
            c_points_out[f"C{idx}"] = {
                "ref": _pt_dict(pref) or {},
                "def": _pt_dict(pdef) or {},
            }

        return {
            "m_per_px": self.m_per_px,
            "cal_p1": _pt_dict(self.cal_p1),
            "cal_p2": _pt_dict(self.cal_p2),
            "w_p1": _pt_dict(self.w_p1),
            "w_p2": _pt_dict(self.w_p2),
            "slice_x": list(self.slice_x) if self.slice_x else None,
            "guide_y": self.guide_y,
            "bumper_offset_m": self.bumper_offset_m,
            "bumper_offset_px": self.bumper_offset_px,
            "crossmember_y": self.crossmember_y,
            "c_points": c_points_out if c_points_out else None,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "OverlayState":
        st = OverlayState()

        st.m_per_px = None if d.get("m_per_px") is None else float(d["m_per_px"])
        if st.m_per_px is None and d.get("cm_per_px") is not None:
            st.m_per_px = float(d["cm_per_px"]) / 100.0

        st.cal_p1 = _pt(d.get("cal_p1"))
        st.cal_p2 = _pt(d.get("cal_p2"))

        st.w_p1 = _pt(d.get("w_p1"))
        st.w_p2 = _pt(d.get("w_p2"))
        st.guide_y = None if d.get("guide_y") is None else float(d["guide_y"])
        st.bumper_offset_m = (
            None if d.get("bumper_offset_m") is None else float(d["bumper_offset_m"])
        )
        st.bumper_offset_px = (
            None if d.get("bumper_offset_px") is None else float(d["bumper_offset_px"])
        )
        st.crossmember_y = (
            None if d.get("crossmember_y") is None else float(d["crossmember_y"])
        )

        sx = d.get("slice_x")

        if isinstance(sx, list):
            st.slice_x = [float(x) for x in sx]

        cp = d.get("c_points")
        if isinstance(cp, dict):
            for ck, vv in cp.items():
                if not isinstance(vv, dict):
                    continue
                try:
                    idx = int(str(ck).replace("C", ""))
                except Exception:
                    continue
                pref = _pt(vv.get("ref"))
                pdef = _pt(vv.get("def"))
                if pref and pdef:
                    st.c_points[idx] = (pref, pdef)

        return st
