from __future__ import annotations

import json
import math
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.core.crash3 import compute_ees, compute_energy
from app.core.project import Project
from app.i18n import get_language, set_language, tr
from app.report import generate_report
from app.version import __version__


ROOT = Path(__file__).resolve().parents[1]
COMPASS = (
    ROOT / "examples" / "nhtsa_jeep_compass_2024_m20240300" / "crash3vision_reference_project.json"
)


def _compass() -> Project:
    return Project.from_dict(json.loads(COMPASS.read_text(encoding="utf-8")))


def _reference_energy(width: float, crush: list[float], a: float, b: float, angle: float) -> float:
    # Simpson integration is exact for the quadratic density on a linear segment.
    def density(c: float) -> float:
        return a * a / (2 * b) + a * c + b * c * c / 2

    total = math.fsum(density(l) + 4 * density((l + r) / 2) + density(r) for l, r in zip(crush, crush[1:]))
    return total * width / 30 / math.cos(math.radians(angle)) ** 2


def _fields(report: str) -> dict[str, str]:
    return dict(line.split(": ", 1) for line in report.splitlines() if ": " in line)


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(set_language, get_language())

    def test_txt_reproduces_energy_and_ees_from_full_precision_inputs(self) -> None:
        compass = _compass()
        self.assertAlmostEqual(compass.total_energy_j, 218416.488633, places=6)
        small = replace(
            compass,
            ref_path=None,
            crash3_A=0.0149,
            crash3_B=0.0149,
            crash3_alpha_deg=0.004912345678901,
            vehicle_mass_kg=1815.123456789012,
        )
        crush = [small.c_m[f"C{i}"] for i in range(1, 7)]
        small.total_energy_j = compute_energy(
            small.w_m, *crush, small.crash3_A, small.crash3_B, small.crash3_alpha_deg,
        )
        small.damage_speed_mps = compute_ees(small.total_energy_j, small.vehicle_mass_kg)
        small.damage_speed_kmh = small.damage_speed_mps * 3.6
        for language in ("pt", "en"):
            set_language(language)
            for project in (compass, small):
                with self.subTest(language=language, a=project.crash3_A):
                    original = deepcopy(project.to_dict())
                    report = generate_report(project)
                    fields = _fields(report)
                    self.assertTrue(report.startswith(tr("report.title") + "\n"))
                    self.assertEqual(fields[tr("report.app_version")], __version__)
                    self.assertEqual(fields[tr("report.project")], project.name)
                    self.assertIsNotNone(datetime.fromisoformat(fields[tr("report.datetime")]).utcoffset())
                    self.assertIn(tr("report.number_notation"), report)
                    self.assertIn(tr("report.methodology.speed"), report)
                    self.assertIn(tr("report.methodology.scope"), report)
                    self.assertNotIn(tr("report.test_description"), report)
                    for label, expected in (
                        (tr("report.scale_m_per_px"), project.m_per_px),
                        ("W (m)", project.w_m),
                        ("W (px)", project.w_px),
                        ("ΔW (m)", project.delta_w_m),
                        ("ΔW (px)", project.delta_w_px),
                        ("A (N/m)", project.crash3_A),
                        ("B (N/m²)", project.crash3_B),
                        (tr("report.calculation_angle_deg"), project.crash3_alpha_deg),
                        (tr("report.vehicle_mass_considered_kg"), project.vehicle_mass_kg),
                        (tr("report.total_energy_deformation_j"), project.total_energy_j),
                        ("- EES (m/s)", project.damage_speed_mps),
                        ("- EES (km/h)", project.damage_speed_kmh),
                    ):
                        self.assertEqual(float(fields[label]), expected, label)
                    values = [float(fields[f"C{i} (m)"]) for i in range(1, 7)]
                    self.assertEqual(values, [project.c_m[f"C{i}"] for i in range(1, 7)])
                    result = _reference_energy(
                        float(fields["W (m)"]), values, float(fields["A (N/m)"]), float(fields["B (N/m²)"]),
                        float(fields[tr("report.calculation_angle_deg")]),
                    )
                    self.assertTrue(math.isclose(result, project.total_energy_j, rel_tol=1e-13))
                    speed = math.sqrt(2 * result / float(fields[tr("report.vehicle_mass_considered_kg")]))
                    self.assertTrue(math.isclose(speed, project.damage_speed_mps, rel_tol=1e-13))
                    self.assertEqual(project.to_dict(), original)

    def test_txt_keeps_nhtsa_speeds_in_mps_and_accepts_historical_metadata(self) -> None:
        project = replace(_compass(), ab_source_type="nhtsa_library", ab_source_ref="M20240300")
        project.ab_source_snapshot = {
            "test_configuration": "rigid_frontal_barrier",
            "report_number": "M20240300",
            "test_speed_mps": "15,639",
            "impact_speed_mps": 15.639,
            "velocity_change_mps": "18.383",
            "rebound_speed_mps": 0,
            "damage_speed_mps": "15.397",
            "speed_used_mps": "unknown",
            "impact_angle_deg": "0",
            "overlap_pct": "100",
        }
        original = deepcopy(project.to_dict())
        for language in ("pt", "en"):
            set_language(language)
            report = generate_report(project)
            fields = _fields(report)
            self.assertIn(tr("report.test_description"), report)
            self.assertEqual(fields[tr("report.method")], tr("report.method.nhtsa_library"))
            self.assertEqual(fields[tr("report.report_number")], "M20240300")
            for key, expected in (
                ("test_speed_mps", 15.639), ("impact_speed_mps", 15.639),
                ("velocity_change_mps", 18.383), ("rebound_speed_mps", 0.0),
                ("damage_speed_mps", 15.397),
            ):
                label = tr(f"report.{key}")
                self.assertIn("(m/s)", label)
                self.assertEqual(float(fields[label]), expected)
            self.assertNotIn(tr("report.speed_used_mps"), fields)
            self.assertEqual(float(fields[tr("report.impact_angle_deg")]), 0)
            self.assertEqual(float(fields[tr("report.overlap_pct")]), 100)
            self.assertEqual(float(fields["- EES (km/h)"]), project.damage_speed_kmh)
        self.assertEqual(project.to_dict(), original)
        self.assertNotIn(tr("report.test_description"), generate_report(replace(project, ab_source_snapshot=[])))

    def test_txt_distinguishes_legacy_conversion_from_energy_without_mass(self) -> None:
        compass = _compass()
        legacy = Project.from_dict(compass.to_dict() | {"damage_speed_mps": None, "damage_speed_kmh": 55.85})
        energy_only = replace(
            compass, vehicle_mass_kg=None, damage_speed_mps=None, damage_speed_kmh=None,
            ab_source_type="generic_class", ab_source_label="compact",
        )
        for language in ("pt", "en"):
            set_language(language)
            original = deepcopy(legacy.to_dict())
            historical = _fields(generate_report(legacy))
            self.assertEqual(historical["- EES (km/h)"], "55.85")
            marker = tr("report.ees.converted_from_kmh")
            self.assertEqual(historical["- EES (m/s)"], f"{55.85 / 3.6!r} ({marker})")
            self.assertEqual(legacy.to_dict(), original)
            report = generate_report(energy_only)
            self.assertIn(tr("report.ees.mass_required"), report)
            self.assertNotIn("- EES (m/s):", report)
            self.assertNotIn("- EES (km/h):", report)
            fields = _fields(report)
            self.assertEqual(fields[tr("report.method")], tr("report.method.generic_class"))
            self.assertEqual(fields[tr("report.vehicle_mass_considered_kg")], "-")
            self.assertEqual(float(fields[tr("report.total_energy_deformation_j")]), compass.total_energy_j)
