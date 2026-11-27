from __future__ import annotations

import json
import math
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.core.ab_provenance import (
    HISTORICAL_AB_KEY, HISTORY_FORMAT, LEGACY_HISTORY_KEY, ab_source_status,
    historical_ab_sources, regularize_ab_source, replace_ab_snapshot,
)
from app.core.crash3 import compute_ees, compute_energy
from app.core.project import Point, Project
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

    def test_ab_source_comparison_is_deterministic_and_ulp_bounded(self) -> None:
        for language in ("pt", "en"):
            set_language(language)
            for recorded, effective, reason in (
                (math.nextafter(179048.0, math.inf), 179048.0, None),
                (179048.05781761295, 179048.0, "mismatch"),
                ("0,0149", 0.0149, None),
                ("179,048.05781761295", 179048.05781761295, None),
                ("179.048,05781761295", 179048.05781761295, None),
                ("1,234", 1.234, "unverifiable"),
                ("1,234", 1234.0, "unverifiable"),
                ("1.234", 1.234, "unverifiable"),
                ("1,8,00.00", 1800.0, "unverifiable"),
                (True, 1.0, "unverifiable"),
            ):
                with self.subTest(language=language, recorded=recorded, effective=effective):
                    snapshot = {"A_n_per_m": recorded, "B_n_per_m2": "8000"}
                    project = Project(
                        crash3_A=effective, crash3_B=8000, ab_source_type="nhtsa_library",
                        ab_source_snapshot=snapshot,
                    )
                    self.assertEqual(regularize_ab_source(project), reason)
                    self.assertEqual((project.crash3_A, project.crash3_B), (effective, 8000))
                    if reason != "mismatch":
                        self.assertEqual(project.ab_source_type, "nhtsa_library")
                        self.assertEqual(project.ab_source_snapshot, snapshot)
                    else:
                        self.assertEqual(project.ab_source_type, "manual")
                        self.assertEqual(historical_ab_sources(project.ab_source_snapshot)[0]["snapshot"], snapshot)

    def test_ab_source_subnormals_require_equality_and_invalid_numbers_are_unverified(self) -> None:
        smallest = math.ulp(0.0)
        for recorded, status in (
            (smallest, "verified"), ("5e-324", "verified"),
            (5 * smallest, "mismatch"), (0.0, "unverifiable"), (-smallest, "unverifiable"),
            ("1e-999", "unverifiable"), ("3e-324", "unverifiable"),
            ("NaN", "unverifiable"), ("inf", "unverifiable"),
        ):
            with self.subTest(recorded=recorded):
                project = Project.from_dict({
                    "crash3_units": "SI_N_per_m", "crash3_A": smallest, "crash3_B": 8000.0,
                    "ab_source_type": "nhtsa_library", "ab_source_snapshot": {
                        "A_n_per_m": recorded, "B_n_per_m2": 8000.0,
                    },
                })
                self.assertEqual(ab_source_status(project), status)
                regularize_ab_source(project)
                self.assertEqual(project.crash3_A, smallest)
                self.assertEqual(project.ab_source_type, "manual" if status == "mismatch" else "nhtsa_library")

    def test_ab_history_preserves_legacy_keys_and_reads_previous_format(self) -> None:
        project = Project(crash3_A=2.0, crash3_B=5.0, ab_source_type="nhtsa_library")
        snapshot = {
            "A_n_per_m": 1, "B_n_per_m2": 5,
            LEGACY_HISTORY_KEY: [{"source_type": "nhtsa_library", "extension": {"name": "custom"}}],
            HISTORICAL_AB_KEY: {"format": HISTORY_FORMAT, "version": 99, "records": ["unknown version"]},
        }
        project.ab_source_snapshot = deepcopy(snapshot)
        self.assertEqual(regularize_ab_source(project), "mismatch")
        self.assertEqual(project.ab_source_snapshot[HISTORICAL_AB_KEY]["version"], 1)
        record = historical_ab_sources(project.ab_source_snapshot)[0]
        self.assertEqual(record["snapshot"], snapshot)

        previous_record = {**record, "snapshot": {"A_n_per_m": 1, "legacy_extension": {"key": True}}}
        project.ab_source_snapshot = {LEGACY_HISTORY_KEY: [previous_record]}
        self.assertEqual(historical_ab_sources(project.ab_source_snapshot), [previous_record])
        replace_ab_snapshot(project, {"A_n_per_m": 2.0})
        self.assertNotIn(LEGACY_HISTORY_KEY, project.ab_source_snapshot)
        self.assertEqual(historical_ab_sources(project.ab_source_snapshot), [previous_record])

    def test_ab_history_deduplication_distinguishes_json_types(self) -> None:
        project = Project(crash3_A=2.0, crash3_B=5.0)
        for flag in (True, 1, True, 1):
            project.ab_source_type = "nhtsa_library"
            project.ab_source_label = "Same source"
            replace_ab_snapshot(project, {"A_n_per_m": 1, "revision": [{"flags": [flag]}]})
            self.assertEqual(regularize_ab_source(project), "mismatch")
        history = historical_ab_sources(project.ab_source_snapshot)
        self.assertEqual(len(history), 2)
        self.assertIs(history[0]["snapshot"]["revision"][0]["flags"][0], True)
        self.assertIs(type(history[1]["snapshot"]["revision"][0]["flags"][0]), int)

    def test_txt_marks_incomplete_declared_sources_unverified_without_archiving(self) -> None:
        for source in ("nhtsa_library", "nhtsa_file", "nhtsa_report", "generic_class"):
            for snapshot in (None, {}, {"A_n_per_m": 179048.0, "id": "legacy"}):
                with self.subTest(source=source, snapshot=snapshot):
                    project = replace(_compass(), ab_source_type=source, ab_source_snapshot=snapshot)
                    original = deepcopy(project.to_dict())
                    self.assertEqual(regularize_ab_source(project), "incomplete")
                    self.assertEqual(project.to_dict(), original)
                    report = generate_report(project)
                    self.assertIn(tr("ab.source.declared_unverified"), report)
                    self.assertNotIn(tr("ab.history.title"), report)

    def test_ab_history_is_flat_and_deduplicated(self) -> None:
        project = Project(crash3_A=5.0, crash3_B=10.0)
        for source in ("nhtsa_library", "nhtsa_file", "nhtsa_library"):
            project.ab_source_type = source
            project.ab_source_label = source
            replace_ab_snapshot(project, {"A_n_per_m": 4.0, "B_n_per_m2": 10.0})
            self.assertEqual(regularize_ab_source(project), "mismatch")
        history = historical_ab_sources(project.ab_source_snapshot)
        self.assertEqual([record["source_type"] for record in history], ["nhtsa_library", "nhtsa_file"])
        self.assertTrue(all(HISTORICAL_AB_KEY not in record["snapshot"] for record in history))
        self.assertIsNone(regularize_ab_source(project))
        self.assertEqual(historical_ab_sources(project.ab_source_snapshot), history)

    def test_txt_distinguishes_effective_and_original_ab_source_for_all_types(self) -> None:
        source_types = ("nhtsa_library", "nhtsa_file", "nhtsa_report", "generic_class")
        for source in source_types:
            compass = replace(_compass(), ab_source_type=source, ab_source_ref="original-id",
                              ab_source_label="Original label", ab_source_reference="Original document")
            original_snapshot = {
                "A_n_per_m": math.nextafter(compass.crash3_A, math.inf),
                "B_n_per_m2": compass.crash3_B + 1,
                "report_number": "Historical test",
                "extension": {"original": ["a", 3]},
            }
            compass.ab_source_snapshot = deepcopy(original_snapshot)
            measurements = {key: compass.to_dict()[key] for key in (
                "crash3_A", "crash3_B", "total_energy_j", "damage_speed_mps", "damage_speed_kmh",
            )}
            self.assertEqual(regularize_ab_source(compass), "mismatch")
            updated = compass.to_dict()
            self.assertEqual({key: updated[key] for key in measurements}, measurements)
            self.assertEqual(historical_ab_sources(compass.ab_source_snapshot), [{
                "source_type": source, "source_ref": "original-id", "source_label": "Original label",
                "source_reference": "Original document", "reason": "mismatch", "snapshot": original_snapshot,
            }])
            for language in ("pt", "en"):
                set_language(language)
                with self.subTest(source=source, language=language):
                    report = generate_report(compass)
                    effective, history = report.split(tr("ab.history.title"), 1)
                    self.assertEqual(_fields(effective)[tr("report.method")], tr("report.method.manual"))
                    self.assertIn(tr("ab.history.effective_manual"), effective)
                    self.assertNotIn("Original document", effective)
                    self.assertIn("Original document", history)
                    self.assertEqual(_fields(history)[tr("ab.history.method")], tr(f"report.method.{source}"))
                    self.assertEqual(float(_fields(history)[tr("ab.history.recorded_b")]), original_snapshot["B_n_per_m2"])
                    self.assertEqual(float(_fields(effective)["A (N/m)"]), compass.crash3_A)
                    self.assertEqual(float(_fields(effective)["B (N/m²)"]), compass.crash3_B)
                    self.assertEqual(compass.to_dict(), updated)

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
            "test_speed_mps": "15,638",
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
                ("test_speed_mps", 15.638), ("impact_speed_mps", 15.639),
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

    def test_txt_reports_calibration_available_in_saved_project(self) -> None:
        compass = _compass()
        for language in ("pt", "en"):
            set_language(language)
            for reference in (compass.ref_path, None):
                project = replace(compass, ref_path=reference)
                original = deepcopy(project.to_dict())
                report = generate_report(project)
                fields = _fields(report)
                p1, p2 = project.cal_p1, project.cal_p2
                distance_px = math.hypot(p2.x - p1.x, p2.y - p1.y)
                self.assertEqual(fields[tr("report.reference")], reference or "-")
                self.assertEqual(float(fields[tr("report.calibration_distance_px")]), distance_px)
                self.assertEqual(float(fields[tr("report.calibration_distance_m")]), distance_px * project.m_per_px)
                self.assertEqual(fields[tr("report.calibration_point", index=1)], f"x={p1.x!r}, y={p1.y!r}")
                self.assertEqual(fields[tr("report.calibration_point", index=2)], f"x={p2.x!r}, y={p2.y!r}")
                self.assertEqual(project.to_dict(), original)

            historical = Project.from_dict({"m_per_px": 0.00217})
            partial = Project(cal_p1=Point(1.5, 2.0))
            for project in (historical, partial):
                fields = _fields(generate_report(project))
                self.assertEqual(fields[tr("report.calibration_distance_px")], "-")
                self.assertEqual(fields[tr("report.calibration_distance_m")], "-")
                self.assertNotIn(tr("report.calibration_point", index=2), fields)
            points_only = Project(cal_p1=Point(0, 0), cal_p2=Point(3, 4))
            fields = _fields(generate_report(points_only))
            self.assertEqual(fields[tr("report.calibration_distance_px")], "5.0")
            self.assertEqual(fields[tr("report.calibration_distance_m")], "-")

    def test_txt_keeps_test_provenance_separate_from_project_inputs(self) -> None:
        library = json.loads((ROOT / "app/data/nhtsa_ab_library.json").read_text(encoding="utf-8"))
        record = next(item for item in library["records"] if item["report_number"] == "M20240300")
        project = replace(_compass(), vehicle_mass_kg=1900.123456789012)
        project.damage_speed_mps = compute_ees(project.total_energy_j, project.vehicle_mass_kg)
        project.damage_speed_kmh = project.damage_speed_mps * 3.6
        snapshot = record | {"L_m": "1,192", "vehicle_mass_kg": "1815,0"}
        report_snapshot = snapshot.copy()
        report_snapshot["c_values_m"] = [str(value) for value in report_snapshot.pop("c_m").values()]
        report_snapshot["b0_mps"] = report_snapshot.pop("b0")
        for language in ("pt", "en"):
            set_language(language)
            for source in ("nhtsa_library", "nhtsa_file", "nhtsa_report"):
                with self.subTest(language=language, source=source):
                    case = replace(
                        project, ab_source_type=source,
                        ab_source_snapshot=snapshot if source == "nhtsa_file" else report_snapshot,
                    )
                    original = deepcopy(case.to_dict())
                    report = generate_report(case)
                    fields = _fields(report)
                    self.assertEqual(fields[tr("report.method")], tr(f"report.method.{source}"))
                    self.assertEqual(fields[tr("report.test_vehicle")], "Jeep Compass 2024")
                    self.assertEqual(fields[tr("report.test_agency")], "NHTSA")
                    self.assertEqual(fields[tr("report.report_number")], "M20240300")
                    self.assertEqual(report.count("M20240300"), 1)
                    self.assertEqual(float(fields[tr("calc.ab.test_mass")]), 1815.0)
                    self.assertEqual(float(fields[tr("report.vehicle_mass_considered_kg")]), case.vehicle_mass_kg)
                    self.assertEqual(float(fields[tr("report.test_width")]), 1.192)
                    self.assertEqual(float(fields[tr("nhtsa.field.b0_mps")]), 3.35)
                    self.assertEqual(
                        fields[tr("report.test_crush")],
                        "  ".join(f"{key}={value!r}" for key, value in record["c_m"].items()),
                    )
                    self.assertEqual(float(fields["C1 (m)"]), case.c_m["C1"])
                    energy = _reference_energy(
                        float(fields["W (m)"]), [float(fields[f"C{i} (m)"]) for i in range(1, 7)],
                        float(fields["A (N/m)"]), float(fields["B (N/m²)"]),
                        float(fields[tr("report.calculation_angle_deg")]),
                    )
                    self.assertTrue(math.isclose(energy, float(fields[tr("report.total_energy_deformation_j")]), rel_tol=1e-13))
                    ees = math.sqrt(2 * energy / float(fields[tr("report.vehicle_mass_considered_kg")]))
                    self.assertTrue(math.isclose(ees, float(fields["- EES (m/s)"]), rel_tol=1e-13))
                    self.assertNotIn(tr("report.test_speed_mps"), fields)
                    self.assertLess(report.index(tr("report.ab_source_full")), report.index(tr("report.test_description")))
                    self.assertLess(report.index(tr("report.test_description")), report.index(tr("report.calculation_parameters")))
                    self.assertEqual(case.to_dict(), original)

            partial = Project(ab_source_snapshot={"c_m": {"C2": "0", "C5": "0,123"}})
            fields = _fields(generate_report(partial))
            self.assertEqual(fields[tr("report.test_crush")], "C1=-  C2=0.0  C3=-  C4=-  C5=0.123  C6=-")
            self.assertNotIn(tr("calc.ab.test_mass"), fields)

    def test_txt_identifies_generic_and_manual_sources_without_test_block(self) -> None:
        for language in ("pt", "en"):
            set_language(language)
            generic = Project(
                ab_source_type="generic_class", ab_source_label="Compact", ab_source_ref="Compact",
                ab_source_snapshot={"class_name": "Compact", "source_reference": "Class document"},
            )
            report = generate_report(generic)
            fields = _fields(report)
            self.assertEqual(fields[tr("calc.generic_class")], "Compact")
            self.assertEqual(fields[tr("report.ab_source_reference")], "Class document")
            self.assertEqual(report.count("Compact"), 1)
            self.assertIn(tr("report.generic_illustrative"), report)
            self.assertNotIn(tr("report.test_description"), report)

            report = generate_report(Project(ab_source_type="manual", ab_source_label="Manual entry"))
            self.assertEqual(_fields(report)[tr("report.method")], tr("report.method.manual"))
            self.assertNotIn(tr("report.ab_source_label"), _fields(report))
            self.assertNotIn(tr("report.test_description"), report)

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
