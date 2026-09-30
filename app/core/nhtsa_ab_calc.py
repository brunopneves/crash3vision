from __future__ import annotations

from typing import Iterable
import math


def _as_list(c_values_m: Iterable[float]) -> list[float]:
    vals = [float(v) for v in c_values_m]
    if len(vals) != 6:
        raise ValueError("Exactly 6 crush values are required.")
    return vals


def crush_area(L_m: float, c_values_m: Iterable[float]) -> float:
    vals = _as_list(c_values_m)
    if L_m <= 0:
        raise ValueError("L_m must be > 0.")

    c1, c2, c3, c4, c5, c6 = vals
    return (L_m / 10.0) * (c1 + 2 * c2 + 2 * c3 + 2 * c4 + 2 * c5 + c6)


def mean_crush(L_m: float, c_values_m: Iterable[float]) -> float:
    if L_m <= 0:
        raise ValueError("L_m must be > 0.")
    area_m2 = crush_area(L_m, c_values_m)
    return area_m2 / L_m


def compute_b1(*, test_speed_mps: float, b0_mps: float, c_mean_m: float) -> float:
    if test_speed_mps <= 0:
        raise ValueError("test_speed_mps must be > 0.")
    if c_mean_m <= 0:
        raise ValueError("c_mean_m must be > 0.")
    return (test_speed_mps - b0_mps) / c_mean_m


def compute_rebound_speed(impact_speed_mps: float, velocity_change_mps: float) -> float:
    return max(0.0, float(velocity_change_mps) - float(impact_speed_mps))


def compute_damage_speed(impact_speed_mps: float, rebound_speed_mps: float) -> float:
    v2 = float(impact_speed_mps) ** 2 - float(rebound_speed_mps) ** 2
    return math.sqrt(max(0.0, v2))


def compute_A_from_report(
    *,
    vehicle_mass_kg: float,
    b0_mps: float,
    b1_per_s: float,
    L_m: float,
) -> float:
    if vehicle_mass_kg <= 0:
        raise ValueError("vehicle_mass_kg must be > 0.")
    if L_m <= 0:
        raise ValueError("L_m must be > 0.")
    return (vehicle_mass_kg * b0_mps * b1_per_s) / L_m


def compute_B_from_report(
    *,
    vehicle_mass_kg: float,
    b1_per_s: float,
    L_m: float,
) -> float:
    if vehicle_mass_kg <= 0:
        raise ValueError("vehicle_mass_kg must be > 0.")
    if L_m <= 0:
        raise ValueError("L_m must be > 0.")
    return (vehicle_mass_kg * (b1_per_s**2)) / L_m


def compute_ab_from_report(
    *,
    L_m: float,
    c_values_m: Iterable[float],
    vehicle_mass_kg: float,
    impact_speed_mps: float,
    velocity_change_mps: float | None,
    b0_mps: float = 2.2,
    speed_basis: str = "impact",
) -> dict[str, object]:
    vals = _as_list(c_values_m)

    if vehicle_mass_kg <= 0:
        raise ValueError("vehicle_mass_kg must be > 0.")
    if impact_speed_mps <= 0:
        raise ValueError("impact_speed_mps must be > 0.")
    if velocity_change_mps is not None and velocity_change_mps <= 0:
        raise ValueError("velocity_change_mps must be > 0 when provided.")
    if L_m <= 0:
        raise ValueError("L_m must be > 0.")
    if speed_basis not in {"impact", "damage"}:
        raise ValueError("speed_basis must be 'impact' or 'damage'.")

    area_m2 = crush_area(L_m, vals)
    c_mean_m = mean_crush(L_m, vals)

    rebound_speed_mps: float = 0.0
    damage_speed_mps: float = float(impact_speed_mps)

    if velocity_change_mps is not None:
        rebound_speed_mps = compute_rebound_speed(
            impact_speed_mps=impact_speed_mps,
            velocity_change_mps=velocity_change_mps,
        )
        damage_speed_mps = compute_damage_speed(
            impact_speed_mps=impact_speed_mps,
            rebound_speed_mps=rebound_speed_mps,
        )

    speed_used_mps = (
        damage_speed_mps if speed_basis == "damage" else float(impact_speed_mps)
    )

    b1_per_s = compute_b1(
        test_speed_mps=speed_used_mps,
        b0_mps=b0_mps,
        c_mean_m=c_mean_m,
    )
    A_n_per_m = compute_A_from_report(
        vehicle_mass_kg=vehicle_mass_kg,
        b0_mps=b0_mps,
        b1_per_s=b1_per_s,
        L_m=L_m,
    )
    B_n_per_m2 = compute_B_from_report(
        vehicle_mass_kg=vehicle_mass_kg,
        b1_per_s=b1_per_s,
        L_m=L_m,
    )

    return {
        "crush_area_m2": area_m2,
        "c_mean_m": c_mean_m,
        "b1_per_s": b1_per_s,
        "A_n_per_m": A_n_per_m,
        "B_n_per_m2": B_n_per_m2,
        "impact_speed_mps": float(impact_speed_mps),
        "velocity_change_mps": (
            None if velocity_change_mps is None else float(velocity_change_mps)
        ),
        "rebound_speed_mps": float(rebound_speed_mps),
        "damage_speed_mps": float(damage_speed_mps),
        "speed_used_mps": float(speed_used_mps),
        "speed_basis": speed_basis,
    }
