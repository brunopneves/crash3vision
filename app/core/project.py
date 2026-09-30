from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


KGFCM_TO_N_PER_M = 980.665
KGFCM2_TO_N_PER_M2 = 98066.5

SI_CRASH3_UNITS = {"SI_N_per_m", "SI", "N/m"}
LEGACY_CRASH3_UNITS = {"kgf/cm_kgf/cm2"}


class UnsupportedCrash3UnitsError(ValueError):
    def __init__(self, units: object) -> None:
        self.units = units
        super().__init__(f"Unsupported crash3_units: {units!r}")


def _f(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    return float(v)


@dataclass
class Point:
    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {"x": float(self.x), "y": float(self.y)}

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "Point | None":
        if not d:
            return None
        return Point(x=float(d["x"]), y=float(d["y"]))


@dataclass
class DamTransform:
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation_deg: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "x": float(self.x),
            "y": float(self.y),
            "scale": float(self.scale),
            "rotation_deg": float(self.rotation_deg),
        }

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "DamTransform":
        if not d:
            return DamTransform()
        return DamTransform(
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            scale=float(d.get("scale", 1.0)),
            rotation_deg=float(d.get("rotation_deg", 0.0)),
        )


@dataclass
class Project:
    name: str = "untitled"

    # Images
    ref_path: str | None = None
    dam_path: str | None = None
    opacity: float = 0.5

    # Alignment transforms
    ref_transform: DamTransform = field(default_factory=DamTransform)
    dam_transform: DamTransform = field(default_factory=DamTransform)

    # Calibration / scale (meters)
    m_per_px: float | None = None
    cal_p1: Point | None = None
    cal_p2: Point | None = None

    # Marking W and slices
    w_px: float | None = None
    w_m: float | None = None
    delta_w_px: float | None = None
    delta_w_m: float | None = None
    w_p1: Point | None = None
    w_p2: Point | None = None
    slice_x: list[float] | None = None
    guide_y: float | None = None
    bumper_offset_m: float | None = None
    bumper_offset_px: float | None = None
    crossmember_y: float | None = None

    # C measurements
    c_px: dict[str, float] | None = None
    c_m: dict[str, float] | None = None

    # C point overlays
    c_points: dict[str, dict[str, Point]] | None = None

    # Calculation output
    total_energy_j: float | None = None

    # Last CRASH3 parameters used (SI units)
    crash3_A: float | None = None  # N/m
    crash3_B: float | None = None  # N/m²
    crash3_alpha_deg: float | None = 0.0
    crash3_units: str = "SI_N_per_m"

    # Vehicle mass / damage speed
    vehicle_mass_kg: float | None = None
    damage_speed_mps: float | None = None
    damage_speed_kmh: float | None = None

    # A/B source metadata
    ab_source_type: str | None = None
    ab_source_ref: str | None = None
    ab_source_label: str | None = None
    ab_source_reference: str | None = None
    ab_source_snapshot: dict[str, Any] | None = None
    last_ab_filter: str | None = None

    def to_dict(self) -> dict[str, Any]:
        def pt(p: Point | None) -> dict[str, float] | None:
            return None if p is None else p.to_dict()

        c_points_dict: dict[str, dict[str, dict[str, float]]] | None = None
        if self.c_points:
            c_points_dict = {}
            for ck, vv in self.c_points.items():
                ref = vv.get("ref")
                deff = vv.get("def")
                if ref is None or deff is None:
                    continue
                c_points_dict[str(ck)] = {"ref": ref.to_dict(), "def": deff.to_dict()}

        return {
            "name": self.name,
            "ref_path": self.ref_path,
            "dam_path": self.dam_path,
            "opacity": float(self.opacity),
            "ref_transform": self.ref_transform.to_dict(),
            "dam_transform": self.dam_transform.to_dict(),
            "m_per_px": self.m_per_px,
            "cal_p1": pt(self.cal_p1),
            "cal_p2": pt(self.cal_p2),
            "w_px": self.w_px,
            "w_m": self.w_m,
            "delta_w_px": self.delta_w_px,
            "delta_w_m": self.delta_w_m,
            "w_p1": pt(self.w_p1),
            "w_p2": pt(self.w_p2),
            "slice_x": self.slice_x,
            "guide_y": self.guide_y,
            "bumper_offset_m": self.bumper_offset_m,
            "bumper_offset_px": self.bumper_offset_px,
            "crossmember_y": self.crossmember_y,
            "c_px": self.c_px,
            "c_m": self.c_m,
            "c_points": c_points_dict,
            "total_energy_j": self.total_energy_j,
            "crash3_A": self.crash3_A,
            "crash3_B": self.crash3_B,
            "crash3_alpha_deg": self.crash3_alpha_deg,
            "crash3_units": self.crash3_units,
            "vehicle_mass_kg": self.vehicle_mass_kg,
            "damage_speed_mps": self.damage_speed_mps,
            "damage_speed_kmh": self.damage_speed_kmh,
            "ab_source_type": self.ab_source_type,
            "ab_source_ref": self.ab_source_ref,
            "ab_source_label": self.ab_source_label,
            "ab_source_reference": self.ab_source_reference,
            "ab_source_snapshot": self.ab_source_snapshot,
            "last_ab_filter": self.last_ab_filter,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Project":
        def pt(obj: dict[str, Any] | None) -> Point | None:
            return Point.from_dict(obj)

        # Missing markers belong to legacy projects. Explicit unknown markers
        # must never silently select a conversion (even if A/B are absent).
        raw_units = d.get("crash3_units")
        units = raw_units.strip() if isinstance(raw_units, str) else None
        if "crash3_units" in d and units not in SI_CRASH3_UNITS | LEGACY_CRASH3_UNITS:
            raise UnsupportedCrash3UnitsError(raw_units)
        raw_A = _f(d.get("crash3_A"))
        raw_B = _f(d.get("crash3_B"))

        if raw_A is not None and raw_B is not None:
            if units in SI_CRASH3_UNITS:
                A_si = raw_A
                B_si = raw_B
            else:
                # backward compatibility for older projects saved in kgf/cm and kgf/cm²
                A_si = raw_A * KGFCM_TO_N_PER_M
                B_si = raw_B * KGFCM2_TO_N_PER_M2
        else:
            A_si = None
            B_si = None

        alpha_deg = _f(d.get("crash3_alpha_deg"), 0.0)
        if alpha_deg is None:
            alpha_deg = 0.0

        # backward compatibility: old files stored geometry in centimeters
        m_per_px = _f(d.get("m_per_px"))
        cm_per_px = d.get("cm_per_px")
        if m_per_px is None and cm_per_px is not None:
            m_per_px = float(cm_per_px) / 100.0

        w_m = _f(d.get("w_m"))
        if w_m is None:
            old_w_cm = _f(d.get("w_cm"))
            w_m = None if old_w_cm is None else old_w_cm / 100.0

        delta_w_m = _f(d.get("delta_w_m"))
        if delta_w_m is None:
            old_delta_w_cm = _f(d.get("delta_w_cm"))
            delta_w_m = None if old_delta_w_cm is None else old_delta_w_cm / 100.0

        c_m_raw = d.get("c_m")
        if isinstance(c_m_raw, dict):
            c_m = {str(k): float(v) for k, v in c_m_raw.items()}
        else:
            old_c_cm = d.get("c_cm")
            if isinstance(old_c_cm, dict):
                c_m = {str(k): float(v) / 100.0 for k, v in old_c_cm.items()}
            else:
                c_m = None

        c_points_raw = d.get("c_points")
        c_points: dict[str, dict[str, Point]] | None = None
        if isinstance(c_points_raw, dict):
            c_points = {}
            for ck, vv in c_points_raw.items():
                if not isinstance(vv, dict):
                    continue
                ref = pt(vv.get("ref"))
                deff = pt(vv.get("def"))
                if ref is None or deff is None:
                    continue
                c_points[str(ck)] = {"ref": ref, "def": deff}
            if not c_points:
                c_points = None

        slice_x_raw = d.get("slice_x")
        slice_x = (
            [float(x) for x in slice_x_raw] if isinstance(slice_x_raw, list) else None
        )

        c_px_raw = d.get("c_px")
        c_px = (
            {str(k): float(v) for k, v in c_px_raw.items()}
            if isinstance(c_px_raw, dict)
            else None
        )

        return Project(
            name=str(d.get("name", "untitled")),
            ref_path=d.get("ref_path"),
            dam_path=d.get("dam_path"),
            opacity=float(d.get("opacity", 0.5)),
            ref_transform=DamTransform.from_dict(d.get("ref_transform")),
            dam_transform=DamTransform.from_dict(d.get("dam_transform")),
            m_per_px=m_per_px,
            cal_p1=pt(d.get("cal_p1")),
            cal_p2=pt(d.get("cal_p2")),
            w_px=_f(d.get("w_px")),
            w_m=w_m,
            delta_w_px=_f(d.get("delta_w_px")),
            delta_w_m=delta_w_m,
            w_p1=pt(d.get("w_p1")),
            w_p2=pt(d.get("w_p2")),
            slice_x=slice_x,
            guide_y=_f(d.get("guide_y")),
            bumper_offset_m=_f(d.get("bumper_offset_m")),
            bumper_offset_px=_f(d.get("bumper_offset_px")),
            crossmember_y=_f(d.get("crossmember_y")),
            c_px=c_px,
            c_m=c_m,
            c_points=c_points,
            total_energy_j=_f(d.get("total_energy_j")),
            crash3_A=A_si,
            crash3_B=B_si,
            crash3_alpha_deg=alpha_deg,
            crash3_units="SI_N_per_m",
            vehicle_mass_kg=_f(d.get("vehicle_mass_kg")),
            damage_speed_mps=_f(d.get("damage_speed_mps")),
            damage_speed_kmh=_f(d.get("damage_speed_kmh")),
            ab_source_type=d.get("ab_source_type"),
            ab_source_ref=d.get("ab_source_ref"),
            ab_source_label=d.get("ab_source_label"),
            ab_source_reference=d.get("ab_source_reference"),
            ab_source_snapshot=d.get("ab_source_snapshot"),
            last_ab_filter=d.get("last_ab_filter"),
        )
