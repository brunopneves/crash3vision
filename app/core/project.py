from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.core.crash3 import compute_ees, compute_energy


KGFCM_TO_N_PER_M = 980.665
KGFCM2_TO_N_PER_M2 = 98066.5

SI_CRASH3_UNITS = {"SI_N_per_m", "SI", "N/m"}
LEGACY_CRASH3_UNITS = {"kgf/cm_kgf/cm2"}
CRUSH_KEYS = tuple(f"C{i}" for i in range(1, 7))
PIXEL_STEP = 1.0
LENGTH_STEP_M = 0.01
SCALE_STEP_M_PER_PX = 0.00001
ENERGY_STEP_J = 1.0
MASS_STEP_KG = 1.0
SPEED_STEP_MPS = 0.1
SPEED_STEP_KMH = 0.1
COEFFICIENT_STEP = 0.01
ANGLE_STEP_DEG = 0.01


@dataclass(frozen=True)
class _Interval:
    low: float
    high: float

    @classmethod
    def rounded(cls, value: float, max_step: float, *, nonnegative: bool = True) -> "_Interval":
        # JSON has no precision metadata. Use the visible decimal resolution,
        # bounded by the coarsest convention supported for this field.
        exponent = Decimal(str(value)).normalize().as_tuple().exponent
        half_step = min(max_step, 10.0 ** exponent) / 2
        low = value - half_step
        return cls(max(0.0, low) if nonnegative else low, value + half_step)

    def scaled(self, factor: float) -> "_Interval":
        return _Interval(self.low * factor, self.high * factor)

    def product(self, other: "_Interval") -> "_Interval":
        return _Interval(self.low * other.low, self.high * other.high)

    def intersect(self, other: "_Interval") -> "_Interval | None":
        low = max(self.low, other.low)
        high = min(self.high, other.high)
        if low > high and not math.isclose(low, high, rel_tol=1e-12):
            return None
        return _Interval(low, max(low, high))


class UnsupportedCrash3UnitsError(ValueError):
    def __init__(self, units: object) -> None:
        self.units = units
        super().__init__(f"Unsupported crash3_units: {units!r}")


class InvalidProjectDataError(ValueError):
    def __init__(self, reason: str, **details: Any) -> None:
        self.reason = reason
        self.details = details
        description = ", ".join(f"{key}={value}" for key, value in details.items())
        super().__init__(f"{reason}: {description}")


def _number(
    value: Any, field_name: str, *, minimum: float = -math.inf,
    maximum: float = math.inf, positive: bool = False, maximum_exclusive: bool = False,
) -> float:
    try:
        if isinstance(value, bool) or (isinstance(value, str) and "_" in value):
            raise ValueError
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise InvalidProjectDataError("invalid_number", field=field_name, value=repr(value)) from None
    if not math.isfinite(number):
        raise InvalidProjectDataError("invalid_number", field=field_name, value=repr(value))
    if positive and number <= 0:
        raise InvalidProjectDataError("positive_number", field=field_name, value=repr(value))
    if not minimum <= number <= maximum or (maximum_exclusive and number == maximum):
        if minimum == 0 and maximum == math.inf:
            raise InvalidProjectDataError("nonnegative_number", field=field_name, value=repr(value))
        raise InvalidProjectDataError(
            "out_of_range", field=field_name, value=repr(value), minimum=minimum, maximum=maximum,
            upper_bound="<" if maximum_exclusive else "<=",
        )
    return number


def _object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidProjectDataError("invalid_field", field=field_name)
    return value


def _check_finite_json_numbers(value: Any, field_name: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _check_finite_json_numbers(item, f"{field_name}.{key}" if field_name else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_finite_json_numbers(item, f"{field_name}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise InvalidProjectDataError("invalid_number", field=field_name, value=repr(value))


@dataclass
class Point:
    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        return {"x": float(self.x), "y": float(self.y)}

    @staticmethod
    def from_dict(d: dict[str, Any] | None, field_name: str = "point") -> "Point | None":
        if d is None:
            return None
        d = _object(d, field_name)
        if not d:
            return None
        return Point(x=_number(d.get("x"), f"{field_name}.x"), y=_number(d.get("y"), f"{field_name}.y"))


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
    def from_dict(d: dict[str, Any] | None, field_name: str = "transform") -> "DamTransform":
        if d is None:
            return DamTransform()
        d = _object(d, field_name)
        return DamTransform(
            x=_number(d.get("x", 0.0), f"{field_name}.x"),
            y=_number(d.get("y", 0.0), f"{field_name}.y"),
            scale=_number(d.get("scale", 1.0), f"{field_name}.scale", positive=True),
            rotation_deg=_number(d.get("rotation_deg", 0.0), f"{field_name}.rotation_deg"),
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
        def optional_number(key: str, **limits: Any) -> float | None:
            value = d.get(key)
            return None if value is None else _number(value, key, **limits)

        def metric_length(key: str, legacy_key: str) -> float | None:
            metric = optional_number(key, positive=True)
            legacy = optional_number(legacy_key, positive=True)
            if metric is None and legacy is not None:
                return _number(float(Decimal(str(legacy)).scaleb(-2)), legacy_key, positive=True)
            return metric

        def crush_values(key: str) -> dict[str, float] | None:
            raw = d.get(key)
            if raw is None:
                return None
            values: dict[str, float] = {}
            for name, value in _object(raw, key).items():
                field_name = f"{key}.{name}"
                ci = f"C{name}" if isinstance(name, str) and name.isdecimal() else name
                if ci not in CRUSH_KEYS or ci in values:
                    raise InvalidProjectDataError("invalid_field", field=field_name)
                values[ci] = _number(value, field_name, minimum=0)
            return values

        _check_finite_json_numbers(d)

        # Missing markers belong to legacy projects. Explicit unknown markers
        # must never silently select a conversion (even if A/B are absent).
        raw_units = d.get("crash3_units")
        units = raw_units.strip() if isinstance(raw_units, str) else None
        if "crash3_units" in d and units not in SI_CRASH3_UNITS | LEGACY_CRASH3_UNITS:
            raise UnsupportedCrash3UnitsError(raw_units)
        a_si = optional_number("crash3_A", positive=True)
        b_si = optional_number("crash3_B", positive=True)
        if units not in SI_CRASH3_UNITS:
            if a_si is not None:
                a_si = _number(a_si * KGFCM_TO_N_PER_M, "crash3_A", positive=True)
            if b_si is not None:
                b_si = _number(b_si * KGFCM2_TO_N_PER_M2, "crash3_B", positive=True)

        alpha_deg = optional_number("crash3_alpha_deg", minimum=0, maximum=89, maximum_exclusive=True)
        if alpha_deg is None:
            alpha_deg = 0.0

        c_m = crush_values("c_m")
        c_cm = crush_values("c_cm")
        if c_m is None and c_cm is not None:
            c_m = {key: float(Decimal(str(value)).scaleb(-2)) for key, value in c_cm.items()}

        c_points_raw = d.get("c_points")
        c_points: dict[str, dict[str, Point]] | None = None
        if c_points_raw is not None:
            c_points = {}
            for ck, vv in _object(c_points_raw, "c_points").items():
                path = f"c_points.{ck}"
                points = _object(vv, path)
                ref = Point.from_dict(points.get("ref"), f"{path}.ref")
                deff = Point.from_dict(points.get("def"), f"{path}.def")
                if ref is not None and deff is not None:
                    c_points[ck] = {"ref": ref, "def": deff}
            if not c_points:
                c_points = None

        slice_x_raw = d.get("slice_x")
        if slice_x_raw is not None and not isinstance(slice_x_raw, list):
            raise InvalidProjectDataError("invalid_field", field="slice_x")
        slice_x = None if slice_x_raw is None else [
            _number(x, f"slice_x[{index}]") for index, x in enumerate(slice_x_raw)
        ]

        project = Project(
            name=str(d.get("name", "untitled")),
            ref_path=d.get("ref_path"),
            dam_path=d.get("dam_path"),
            opacity=_number(d.get("opacity", 0.5), "opacity", minimum=0, maximum=1),
            ref_transform=DamTransform.from_dict(d.get("ref_transform"), "ref_transform"),
            dam_transform=DamTransform.from_dict(d.get("dam_transform"), "dam_transform"),
            m_per_px=metric_length("m_per_px", "cm_per_px"),
            cal_p1=Point.from_dict(d.get("cal_p1"), "cal_p1"),
            cal_p2=Point.from_dict(d.get("cal_p2"), "cal_p2"),
            w_px=optional_number("w_px", positive=True),
            w_m=metric_length("w_m", "w_cm"),
            delta_w_px=optional_number("delta_w_px", positive=True),
            delta_w_m=metric_length("delta_w_m", "delta_w_cm"),
            w_p1=Point.from_dict(d.get("w_p1"), "w_p1"),
            w_p2=Point.from_dict(d.get("w_p2"), "w_p2"),
            slice_x=slice_x,
            guide_y=optional_number("guide_y"),
            bumper_offset_m=optional_number("bumper_offset_m", minimum=0),
            bumper_offset_px=optional_number("bumper_offset_px", minimum=0),
            crossmember_y=optional_number("crossmember_y"),
            c_px=crush_values("c_px"),
            c_m=c_m,
            c_points=c_points,
            total_energy_j=optional_number("total_energy_j", positive=True),
            crash3_A=a_si,
            crash3_B=b_si,
            crash3_alpha_deg=alpha_deg,
            crash3_units="SI_N_per_m",
            vehicle_mass_kg=optional_number("vehicle_mass_kg", positive=True),
            damage_speed_mps=optional_number("damage_speed_mps", minimum=0),
            damage_speed_kmh=optional_number("damage_speed_kmh", minimum=0),
            ab_source_type=d.get("ab_source_type"),
            ab_source_ref=d.get("ab_source_ref"),
            ab_source_label=d.get("ab_source_label"),
            ab_source_reference=d.get("ab_source_reference"),
            ab_source_snapshot=d.get("ab_source_snapshot"),
            last_ab_filter=d.get("last_ab_filter"),
        )
        project._derive_missing_width_values()
        width, crush = project._measurement_intervals()
        energy = project._stored_energy_interval(width, crush)
        project._validate_stored_ees(energy)
        return project

    def _derive_missing_width_values(self) -> None:
        if self.w_m is None and self.w_px is not None and self.m_per_px is not None:
            self.w_m = _number(self.w_px * self.m_per_px, "w_m", positive=True)
        if self.delta_w_px is None and self.w_px is not None:
            self.delta_w_px = _number(self.w_px / 5.0, "delta_w_px", positive=True)
        if self.delta_w_m is None and self.w_m is not None:
            self.delta_w_m = _number(self.w_m / 5.0, "delta_w_m", positive=True)

    def _slice_width_interval(self) -> _Interval | None:
        positions = self.slice_x or []
        if len(positions) < len(CRUSH_KEYS):
            return None
        if len(positions) > len(CRUSH_KEYS):
            raise InvalidProjectDataError("invalid_field", field="slice_x")
        coords = [_Interval.rounded(x, PIXEL_STEP, nonnegative=False) for x in positions]
        spacing = _Interval(0.0, math.inf)
        # For a given spacing, X_i - i * spacing bounds the same origin.
        # A common origin exists exactly when all pairs of these bounds overlap.
        for i, left in enumerate(coords):
            for j in range(i + 1, len(coords)):
                right = coords[j]
                spacing = spacing.intersect(_Interval(
                    (right.low - left.high) / (j - i),
                    (right.high - left.low) / (j - i),
                ))
                if spacing is None or spacing.high <= 0:
                    raise InvalidProjectDataError("slice_spacing_mismatch")
        return spacing.scaled(len(CRUSH_KEYS) - 1)

    def _measurement_intervals(self) -> tuple[_Interval | None, dict[str, _Interval]]:
        def constrain_by_delta(
            bounds: _Interval | None, width: float | None, delta: float | None, step: float, field: str,
        ) -> _Interval | None:
            # An interval derived directly from W carries no additional precision.
            if delta is None or (width is not None and math.isclose(delta, width / 5.0, rel_tol=1e-12)):
                return bounds
            delta_bounds = _Interval.rounded(delta, step).scaled(5.0)
            if bounds is None:
                return delta_bounds
            compatible = bounds.intersect(delta_bounds)
            if compatible is None:
                raise InvalidProjectDataError(
                    "width_interval_mismatch", field=field, value=delta, expected=width / 5.0,
                )
            return compatible

        pixels = self.w_px
        meters = self.w_m
        scale = self.m_per_px
        width_px = None if pixels is None else _Interval.rounded(pixels, PIXEL_STEP)
        width_px = constrain_by_delta(width_px, pixels, self.delta_w_px, PIXEL_STEP, "delta_w_px")
        slice_width = self._slice_width_interval()
        if slice_width is not None:
            width_px = slice_width if width_px is None else width_px.intersect(slice_width)
            if width_px is None:
                raise InvalidProjectDataError("slice_spacing_mismatch")

        width_m = None if meters is None else _Interval.rounded(meters, LENGTH_STEP_M)
        scale_bounds = None if scale is None else _Interval.rounded(scale, SCALE_STEP_M_PER_PX)
        if pixels is not None and scale_bounds is not None and meters is not None:
            derived = _number(pixels * scale, "W", positive=True)
            if math.isclose(meters, derived, rel_tol=1e-12):
                # The saved product carries the original pixel and scale precision,
                # including when a formerly missing W has since been saved in SI.
                width_m = width_px.product(scale_bounds)
        width_m = constrain_by_delta(width_m, meters, self.delta_w_m, LENGTH_STEP_M, "delta_w_m")
        crush = {key: _Interval.rounded(value, LENGTH_STEP_M) for key, value in (self.c_m or {}).items()}
        pairs: dict[str, tuple[_Interval, _Interval]] = {}
        if width_px is not None and width_m is not None:
            pairs["W"] = (width_px, width_m)
        for key, value in (self.c_px or {}).items():
            if scale is not None:
                _number(value * scale, key)
            if key in crush:
                pairs[key] = (_Interval.rounded(value, PIXEL_STEP), crush[key])

        # For nonnegative lengths, each pair permits an interval of scales.
        # Intersect all those intervals before projecting any measurements to SI.
        scale_bounds = scale_bounds or _Interval(0.0, math.inf)
        for key, (px, metric) in pairs.items():
            required = _Interval(metric.low / px.high, metric.high / px.low if px.low > 0 else math.inf)
            compatible = scale_bounds.intersect(required)
            if compatible is None or compatible.high <= 0:
                raise InvalidProjectDataError("shared_scale_mismatch", field=key)
            scale_bounds = compatible

        # Given a scale, both ends of each metric interval are nondecreasing
        # in that scale. Their extremes are attainable together at the same end.
        for key, (px, metric) in pairs.items():
            compatible = px.product(scale_bounds).intersect(metric)
            if compatible is None:
                raise InvalidProjectDataError("shared_scale_mismatch", field=key)
            if key == "W":
                width_m = compatible
            else:
                crush[key] = compatible
        return width_m if meters is not None else None, crush

    def _stored_energy_interval(
        self, width: _Interval | None, crush: dict[str, _Interval],
    ) -> _Interval | None:
        energy = self.total_energy_j
        if energy is None:
            return None
        stored = _Interval.rounded(energy, ENERGY_STEP_J)
        a, b, alpha = self.crash3_A, self.crash3_B, self.crash3_alpha_deg
        if width is None or a is None or b is None or alpha is None or len(crush) != len(CRUSH_KEYS):
            return stored
        a_bounds = _Interval.rounded(a, COEFFICIENT_STEP)
        b_bounds = _Interval.rounded(b, COEFFICIENT_STEP)
        alpha_bounds = _Interval.rounded(alpha, ANGLE_STEP_DEG)

        def at_lower_inputs(coefficient_b: float) -> float:
            return compute_energy(
                width.low, *(crush[key].low for key in CRUSH_KEYS), a_bounds.low, coefficient_b, alpha_bounds.low,
            )

        # Energy increases with W, C, A and alpha in the accepted domain. In B
        # it is convex, so the maximum is at an endpoint and the minimum can
        # be interior. Bracket that minimum using only the CRASH3 evaluator.
        left, right = b_bounds.low, b_bounds.high
        for _ in range(80):
            if math.isclose(left, right, rel_tol=1e-14):
                break
            third = (right - left) / 3.0
            first, second = left + third, right - third
            if at_lower_inputs(first) <= at_lower_inputs(second):
                right = second
            else:
                left = first
        center = left + (right - left) / 2.0
        # Each nonnegative contribution varies by a factor B/center,
        # center/B or 1. Bound the remaining numerical bracket from below.
        low = at_lower_inputs(center) * min(left / center, center / right)
        high = max(
            compute_energy(
                width.high, *(crush[key].high for key in CRUSH_KEYS),
                a_bounds.high, endpoint, min(89.0, alpha_bounds.high),
            )
            for endpoint in (b_bounds.low, b_bounds.high)
        )
        compatible = stored.intersect(_Interval(low, high)) if math.isfinite(low) and math.isfinite(high) else None
        if compatible is None:
            expected = compute_energy(self.w_m, *(self.c_m[key] for key in CRUSH_KEYS), a, b, alpha)
            raise InvalidProjectDataError("energy_mismatch", value=energy, expected=expected)
        return compatible

    def _validate_stored_ees(self, energy: _Interval | None) -> None:
        mps, kmh = self.damage_speed_mps, self.damage_speed_kmh
        if mps is None and kmh is None:
            return

        speed = None
        if mps is not None:
            _number(mps * 3.6, "damage_speed_mps")
            speed = _Interval.rounded(mps, SPEED_STEP_MPS).scaled(3.6)
        if kmh is not None:
            kmh_bounds = _Interval.rounded(kmh, SPEED_STEP_KMH)
            speed = kmh_bounds if speed is None else speed.intersect(kmh_bounds)
            if speed is None:
                raise InvalidProjectDataError("ees_units_mismatch", mps=mps, kmh=kmh)

        if energy is None or self.vehicle_mass_kg is None:
            return
        mass = _Interval.rounded(self.vehicle_mass_kg, MASS_STEP_KG)
        expected = _Interval(
            compute_ees(energy.low, mass.high) * 3.6,
            compute_ees(energy.high, mass.low) * 3.6,
        )
        if not math.isfinite(expected.high) or speed.intersect(expected) is None:
            field, value = ("damage_speed_kmh", kmh) if kmh is not None else ("damage_speed_mps", mps)
            raise InvalidProjectDataError(
                "ees_energy_mismatch", field=field, value=value,
                energy=self.total_energy_j, mass=self.vehicle_mass_kg,
            )
