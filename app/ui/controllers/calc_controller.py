from __future__ import annotations

import math


class CalcController:
    """
    CRASH3 extended formula working in SI units:
    - A in N/m
    - B in N/m²
    - width L in m
    - crush C in m
    - energy in J
    """

    def __init__(self, main_window):
        self.main = main_window

    def compute_crash3(
        self, A_n_per_m: float, B_n_per_m2: float, alpha_deg: float = 0.0
    ):
        project = self.main.project

        if project.c_m is None:
            raise ValueError("C measurements missing.")

        if project.w_m is None or project.w_m <= 0:
            raise ValueError("W missing.")

        if A_n_per_m <= 0:
            raise ValueError("A must be > 0.")

        if B_n_per_m2 <= 0:
            raise ValueError("B must be > 0.")

        if alpha_deg < 0 or alpha_deg >= 89.0:
            raise ValueError("Alpha must be between 0 and 89 degrees.")

        c_m = []
        for i in range(1, 7):
            key = f"C{i}"
            if key not in project.c_m:
                raise ValueError(f"{key} missing.")
            c_m.append(float(project.c_m[key]))

        L_m = float(project.w_m)

        c1, c2, c3, c4, c5, c6 = c_m

        # G = A² / (2B)
        G_n = (A_n_per_m * A_n_per_m) / (2.0 * B_n_per_m2)

        weighted_linear = c1 + 2.0 * c2 + 2.0 * c3 + 2.0 * c4 + 2.0 * c5 + c6

        weighted_quadratic = (
            c1 * c1
            + 2.0 * c2 * c2
            + 2.0 * c3 * c3
            + 2.0 * c4 * c4
            + 2.0 * c5 * c5
            + c6 * c6
            + c1 * c2
            + c2 * c3
            + c3 * c4
            + c4 * c5
            + c5 * c6
        )

        alpha_rad = math.radians(alpha_deg)
        angle_factor = 1.0 + math.tan(alpha_rad) ** 2

        total_energy_j = (
            (L_m / 5.0)
            * (
                (A_n_per_m / 2.0) * weighted_linear
                + (B_n_per_m2 / 6.0) * weighted_quadratic
                + 5.0 * G_n
            )
            * angle_factor
        )

        return {
            "formula": "extended",
            "A_n_per_m": float(A_n_per_m),
            "B_n_per_m2": float(B_n_per_m2),
            "alpha_deg": float(alpha_deg),
            "G_n": float(G_n),
            "width_m": float(L_m),
            "crush_m": list(c_m),
            "total_energy_j": float(total_energy_j),
        }

    def compute_damage_speed(self, mass_kg: float):
        project = self.main.project

        if project.total_energy_j is None or project.total_energy_j <= 0:
            raise ValueError("Total Energy missing.")

        if mass_kg <= 0:
            raise ValueError("Vehicle mass must be > 0.")

        total_energy_j = float(project.total_energy_j)

        speed_mps = math.sqrt((2.0 * total_energy_j) / float(mass_kg))
        speed_kmh = speed_mps * 3.6

        return {
            "mass_kg": float(mass_kg),
            "total_energy_j": total_energy_j,
            "speed_mps": float(speed_mps),
            "speed_kmh": float(speed_kmh),
        }

    def build_damage_profile_data(
        self, A_n_per_m: float, B_n_per_m2: float, alpha_deg: float = 0.0
    ):
        result = self.compute_crash3(A_n_per_m, B_n_per_m2, alpha_deg)

        return {
            "formula": "extended",
            "crush_m": list(result["crush_m"]),
            "alpha_deg": float(result["alpha_deg"]),
        }
