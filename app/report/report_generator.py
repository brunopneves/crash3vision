from __future__ import annotations

from datetime import datetime

from app.i18n import tr
from app.core.number_format import format_float


def _fmt(
    v,
    decimals: int = 2,
    suffix: str = "",
) -> str:
    return format_float(
        value=v,
        decimals=decimals,
        suffix=suffix,
    )


def generate_report(project) -> str:
    c_m = project.c_m or {}
    source_snapshot = project.ab_source_snapshot or {}

    lines: list[str] = []
    lines.append(tr("report.title"))
    lines.append("=" * 40)
    lines.append(f"{tr('report.project')}: {project.name}")
    lines.append(
        f"{tr('report.datetime')}: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    lines.append("")

    if project.total_energy_j is None or project.damage_speed_kmh is None:
        lines.append(f"⚠ {tr('report.warning.incomplete')}")
        lines.append("")

    lines.append(tr("report.images"))
    lines.append(f"{tr('report.reference')}: {project.ref_path or '-'}")
    lines.append(f"{tr('report.deformed')}: {project.dam_path or '-'}")
    lines.append("")

    lines.append(tr("report.calibration"))
    lines.append(f"{tr('report.scale_m_per_px')}: {_fmt(project.m_per_px, 6)}")
    lines.append("")

    lines.append(tr("report.damage_markings"))
    lines.append(f"W (px): {_fmt(project.w_px)}")
    lines.append(f"W (m): {_fmt(project.w_m)}")
    lines.append(f"Δw (px): {_fmt(project.delta_w_px)}")
    lines.append(f"Δw (m): {_fmt(project.delta_w_m)}")
    lines.append(f"{tr('report.bumper_offset_m')}: {_fmt(project.bumper_offset_m, 3)}")
    for i in range(1, 7):
        lines.append(f"C{i} (m): {_fmt(c_m.get(f'C{i}'))}")
    lines.append("")

    lines.append(tr("report.crash3_params_extended"))
    lines.append(f"A (N/m): {_fmt(project.crash3_A)}")
    lines.append(f"B (N/m²): {_fmt(project.crash3_B)}")
    lines.append(f"Alpha (deg): {_fmt(project.crash3_alpha_deg)}")
    lines.append(tr("report.si_units_full"))
    lines.append("")

    lines.append(tr("report.ab_source_full"))
    if project.ab_source_type == "nhtsa_report":
        method_text = tr("report.method.nhtsa_report")
    elif project.ab_source_type == "nhtsa_library":
        method_text = tr("report.method.nhtsa_library")
    elif project.ab_source_type == "nhtsa_file":
        method_text = tr("report.method.nhtsa_file")
    elif project.ab_source_type == "generic_class":
        method_text = tr("report.method.generic_class")
    elif project.ab_source_type == "manual":
        method_text = tr("report.method.manual")
    else:
        method_text = "-"

    lines.append(f"{tr('report.method')}: {method_text}")
    lines.append(f"{tr('report.ab_source_label')}: {project.ab_source_label or '-'}")
    lines.append(f"{tr('report.ab_source_ref')}: {project.ab_source_ref or '-'}")
    lines.append(
        f"{tr('report.ab_source_reference')}: {project.ab_source_reference or '-'}"
    )

    if source_snapshot:
        test_type = source_snapshot.get("test_type")
        test_configuration = source_snapshot.get("test_configuration")
        barrier_type = source_snapshot.get("barrier_type")
        overlap_pct = source_snapshot.get("overlap_pct")
        impact_direction = source_snapshot.get("impact_direction")
        test_speed_mps = source_snapshot.get("test_speed_mps")
        impact_speed_mps = source_snapshot.get("impact_speed_mps")
        velocity_change_mps = source_snapshot.get("velocity_change_mps")
        rebound_speed_mps = source_snapshot.get("rebound_speed_mps")
        damage_speed_mps = source_snapshot.get("damage_speed_mps")
        speed_used_mps = source_snapshot.get("speed_used_mps")
        speed_basis = source_snapshot.get("speed_basis")
        impact_angle_deg = source_snapshot.get("impact_angle_deg")
        test_number = source_snapshot.get("test_number")
        report_number = source_snapshot.get("report_number")

        lines.append("")
        lines.append(tr("report.test_description") + ":")
        lines.append(f"{tr('report.test_type')}: {test_type or '-'}")
        lines.append(f"{tr('report.test_configuration')}: {test_configuration or '-'}")
        lines.append(f"{tr('report.barrier_type')}: {barrier_type or '-'}")
        lines.append(f"{tr('report.impact_direction')}: {impact_direction or '-'}")
        lines.append(
            f"{tr('report.overlap_pct')}: "
            f"{overlap_pct if overlap_pct is not None else '-'}"
        )
        lines.append(
            f"{tr('report.test_speed_mps')}: {_fmt(test_speed_mps * 3.6 if test_speed_mps else None)} km/h"
        )
        lines.append(
            f"{tr('report.impact_speed_mps')}: {_fmt(impact_speed_mps * 3.6 if impact_speed_mps else None)} km/h"
        )
        lines.append(
            f"{tr('report.velocity_change_mps')}: {_fmt(velocity_change_mps * 3.6 if velocity_change_mps else None)} km/h"
        )
        lines.append(
            f"{tr('report.rebound_speed_mps')}: {_fmt(rebound_speed_mps * 3.6 if rebound_speed_mps else None)} km/h"
        )
        lines.append(
            f"{tr('report.damage_speed_mps')}: {_fmt(damage_speed_mps * 3.6 if damage_speed_mps else None)} km/h"
        )
        lines.append(
            f"{tr('report.speed_used_mps')}: {_fmt(speed_used_mps * 3.6 if speed_used_mps else None)} km/h"
        )
        lines.append(f"{tr('report.speed_basis')}: {speed_basis or '-'}")
        lines.append(f"{tr('report.impact_angle_deg')}: {_fmt(impact_angle_deg)}")
        lines.append(f"{tr('report.test_number')}: {test_number or '-'}")
        lines.append(f"{tr('report.report_number')}: {report_number or '-'}")

    lines.append("")

    lines.append(tr("report.methodology"))
    lines.append(tr("report.methodology.energy"))
    lines.append(tr("report.methodology.speed"))
    lines.append("")

    lines.append(tr("report.results"))
    lines.append(
        f"{tr('report.total_energy_deformation_j')}: {_fmt(project.total_energy_j)}"
    )
    lines.append(
        f"{tr('report.vehicle_mass_considered_kg')}: "
        f"{_fmt(project.vehicle_mass_kg)}"
    )
    lines.append(tr("report.damage_speed_estimated") + ":")
    lines.append(f"- EES (m/s): {_fmt(project.damage_speed_mps)}")
    lines.append(f"- EES (km/h): {_fmt(project.damage_speed_kmh)}")

    return "\n".join(lines) + "\n"
