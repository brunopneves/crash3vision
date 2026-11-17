from __future__ import annotations

import math


def compute_energy(
    W: float,
    C1: float,
    C2: float,
    C3: float,
    C4: float,
    C5: float,
    C6: float,
    A: float,
    B: float,
    alpha: float,
) -> float:
    """Compute CRASH3 deformation energy in joules from SI inputs."""
    G = (A * A) / (2.0 * B)

    weighted_linear = C1 + 2.0 * C2 + 2.0 * C3 + 2.0 * C4 + 2.0 * C5 + C6

    weighted_quadratic = (
        C1 * C1
        + 2.0 * C2 * C2
        + 2.0 * C3 * C3
        + 2.0 * C4 * C4
        + 2.0 * C5 * C5
        + C6 * C6
        + C1 * C2
        + C2 * C3
        + C3 * C4
        + C4 * C5
        + C5 * C6
    )

    alpha_rad = math.radians(alpha)
    angle_factor = 1.0 + math.tan(alpha_rad) ** 2

    return (
        (W / 5.0)
        * (
            (A / 2.0) * weighted_linear
            + (B / 6.0) * weighted_quadratic
            + 5.0 * G
        )
        * angle_factor
    )


def compute_ees(
    total_energy_j: float,
    mass_kg: float,
) -> float:
    """Compute energy equivalent speed in m/s from SI inputs."""
    return math.sqrt((2.0 * total_energy_j) / mass_kg)
