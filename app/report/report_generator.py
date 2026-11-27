from __future__ import annotations

from datetime import datetime

from app.core.number_format import parse_float
from app.core.project import Project
from app.i18n import tr
from app.version import __version__


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    # A lone separator in historical numeric metadata is a decimal mark.
    # Read it independently of the language used to generate the report.
    language = "pt" if isinstance(value, str) and "," in value and "." not in value else "en"
    try:
        return parse_float(value, language=language)
    except (TypeError, ValueError, OverflowError):
        return None


def _fmt(value: float | None) -> str:
    return "-" if value is None else repr(float(value))


def _test_metadata(snapshot: object) -> list[str]:
    if not isinstance(snapshot, dict):
        return []
    lines = []
    for field, prefix in (
        ("test_type", "nhtsa.test_type"),
        ("test_configuration", "nhtsa.config"),
        ("barrier_type", "nhtsa.barrier_type"),
        ("impact_direction", "nhtsa.direction"),
        ("speed_basis", "nhtsa.speed_basis"),
        ("test_number", None),
        ("report_number", None),
    ):
        value = snapshot.get(field)
        if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
            continue
        if prefix:
            key = f"{prefix}.{value}"
            translation = tr(key)
            value = value if translation == key else translation
        lines.append(f"{tr(f'report.{field}')}: {value}")
    for field in (
        "overlap_pct", "impact_angle_deg", "test_speed_mps", "impact_speed_mps",
        "velocity_change_mps", "rebound_speed_mps", "damage_speed_mps", "speed_used_mps",
    ):
        value = _number(snapshot.get(field))
        if value is not None:
            lines.append(f"{tr(f'report.{field}')}: {_fmt(value)}")
    return lines


def _ees_lines(project: Project) -> list[str]:
    mps = project.damage_speed_mps
    kmh = project.damage_speed_kmh
    if mps is None and kmh is None:
        key = (
            "report.ees.mass_required"
            if project.total_energy_j is not None and project.vehicle_mass_kg is None
            else "report.ees.unavailable"
        )
        return [tr(key)]

    mps_note = kmh_note = ""
    if mps is None:
        mps = kmh / 3.6
        mps_note = f" ({tr('report.ees.converted_from_kmh')})"
    elif kmh is None:
        kmh = _number(mps * 3.6)
        if kmh is not None:
            kmh_note = f" ({tr('report.ees.converted_from_mps')})"

    lines = [f"- EES (m/s): {_fmt(mps)}{mps_note}"]
    if kmh is not None:
        lines.append(f"- EES (km/h): {_fmt(kmh)}{kmh_note}")
    if project.vehicle_mass_kg is None:
        lines.append(tr("report.ees.mass_not_recorded"))
    return lines


def generate_report(project: Project) -> str:
    c_m = project.c_m or {}
    title = tr("report.title")
    lines = [
        title,
        "=" * len(title),
        f"{tr('report.app_version')}: {__version__}",
        f"{tr('report.project')}: {project.name}",
        f"{tr('report.datetime')}: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        tr("report.number_notation"),
        "",
        tr("report.images"),
        f"{tr('report.reference')}: {project.ref_path or '-'}",
        f"{tr('report.deformed')}: {project.dam_path or '-'}",
        "",
        tr("report.calibration"),
        f"{tr('report.scale_m_per_px')}: {_fmt(project.m_per_px)}",
        "",
        tr("report.damage_markings"),
        f"W (px): {_fmt(project.w_px)}",
        f"W (m): {_fmt(project.w_m)}",
        f"ΔW (px): {_fmt(project.delta_w_px)}",
        f"ΔW (m): {_fmt(project.delta_w_m)}",
    ]
    if project.bumper_offset_m is not None:
        lines.append(f"{tr('report.bumper_offset_m')}: {_fmt(project.bumper_offset_m)}")
    lines.extend(f"C{i} (m): {_fmt(c_m.get(f'C{i}'))}" for i in range(1, 7))
    lines.extend([
        "",
        tr("report.crash3_params_extended"),
        f"A (N/m): {_fmt(project.crash3_A)}",
        f"B (N/m²): {_fmt(project.crash3_B)}",
        f"{tr('report.calculation_angle_deg')}: {_fmt(project.crash3_alpha_deg)}",
        f"{tr('report.vehicle_mass_considered_kg')}: {_fmt(project.vehicle_mass_kg)}",
        tr("report.si_units_full"),
        "",
        tr("report.ab_source_full"),
    ])
    source_type = project.ab_source_type
    method = tr(f"report.method.{source_type}") if source_type in (
        "nhtsa_report", "nhtsa_library", "nhtsa_file", "generic_class", "manual",
    ) else "-"
    lines.append(f"{tr('report.method')}: {method}")
    for key, value in (
        ("report.ab_source_label", project.ab_source_label),
        ("report.ab_source_ref", project.ab_source_ref),
        ("report.ab_source_reference", project.ab_source_reference),
    ):
        if value:
            lines.append(f"{tr(key)}: {value}")

    metadata = _test_metadata(project.ab_source_snapshot)
    if metadata:
        lines.extend(["", tr("report.test_description"), *metadata])

    lines.extend([
        "",
        tr("report.results"),
        f"{tr('report.total_energy_deformation_j')}: {_fmt(project.total_energy_j)}",
        *_ees_lines(project),
        "",
        tr("report.methodology"),
        tr("report.methodology.energy"),
        tr("report.methodology.speed"),
        tr("report.methodology.scope"),
    ])
    return "\n".join(lines) + "\n"
