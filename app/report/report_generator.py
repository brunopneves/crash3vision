from __future__ import annotations

from datetime import datetime
from json import dumps
from math import hypot

from app.core.ab_provenance import LOCKED_AB_SOURCES, ab_source_status, historical_ab_sources
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


def _text(value: object) -> str:
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value).strip()
    return ""


def _calibration(project: Project) -> list[str]:
    p1, p2 = project.cal_p1, project.cal_p2
    distance_px = (
        _number(hypot(p2.x - p1.x, p2.y - p1.y))
        if p1 is not None and p2 is not None
        else None
    )
    # The project stores the points and scale, but not the original distance input.
    distance_m = _number(distance_px * project.m_per_px) if (
        distance_px is not None and distance_px > 0 and project.m_per_px is not None
    ) else None
    lines = [
        f"{tr('report.calibration_distance_px')}: {_fmt(distance_px)}",
        f"{tr('report.calibration_distance_m')}: {_fmt(distance_m)}",
        f"{tr('report.scale_m_per_px')}: {_fmt(project.m_per_px)}",
    ]
    for index, point in enumerate((p1, p2), 1):
        if point is not None:
            lines.append(
                f"{tr('report.calibration_point', index=index)}: "
                f"x={_fmt(point.x)}, y={_fmt(point.y)}"
            )
    return lines


def _test_metadata(snapshot: dict) -> list[str]:
    lines = []
    vehicle = " ".join(part for key in ("make", "model", "year") if (part := _text(snapshot.get(key))))
    if vehicle:
        lines.append(f"{tr('report.test_vehicle')}: {vehicle}")
    for field, prefix in (
        ("test_agency", None),
        ("test_number", None),
        ("report_number", None),
        ("test_type", "nhtsa.test_type"),
        ("test_configuration", "nhtsa.config"),
        ("barrier_type", "nhtsa.barrier_type"),
        ("impact_direction", "nhtsa.direction"),
        ("speed_basis", "nhtsa.speed_basis"),
    ):
        value = _text(snapshot.get(field))
        if not value:
            continue
        if prefix:
            key = f"{prefix}.{value}"
            translation = tr(key)
            value = value if translation == key else translation
        lines.append(f"{tr(f'report.{field}')}: {value}")
    impact_speed = _number(snapshot.get("impact_speed_mps"))
    for field in (
        "overlap_pct", "impact_angle_deg",
        "test_speed_mps", "impact_speed_mps", "velocity_change_mps", "rebound_speed_mps",
        "damage_speed_mps", "speed_used_mps",
    ):
        value = _number(snapshot.get(field))
        if field == "test_speed_mps" and value == impact_speed:
            continue
        if value is not None:
            lines.append(f"{tr(f'report.{field}')}: {_fmt(value)}")

    b0 = _number(snapshot.get("b0_mps"))
    for key, value in (
        ("calc.ab.test_mass", _number(snapshot.get("vehicle_mass_kg"))),
        ("report.test_width", _number(snapshot.get("L_m"))),
        ("nhtsa.field.b0_mps", b0 if b0 is not None else _number(snapshot.get("b0"))),
    ):
        if value is not None:
            lines.append(f"{tr(key)}: {_fmt(value)}")

    c_list, c_map = snapshot.get("c_values_m"), snapshot.get("c_m")
    crush = []
    for index in range(1, 7):
        key = f"C{index}"
        value = (
            _number(c_list[index - 1])
            if isinstance(c_list, (list, tuple)) and index <= len(c_list)
            else None
        )
        if value is None and isinstance(c_map, dict):
            value = _number(c_map.get(key))
        crush.append(value)
    if any(value is not None for value in crush):
        values = "  ".join(f"C{index}={_fmt(value)}" for index, value in enumerate(crush, 1))
        lines.append(f"{tr('report.test_crush')}: {values}")
    return lines


def _source_lines(
    source: str | None, raw_snapshot: object, label: object, ref: object, document: object,
    *, method_key: str = "report.method",
) -> list[str]:
    snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else {}
    # Older projects may have stored test metadata without an explicit source type.
    has_test_source = source not in ("manual", "generic_class")
    method = tr(f"report.method.{source}") if source in (*LOCKED_AB_SOURCES, "manual") else "-"
    lines = [f"{tr(method_key)}: {method}"]
    label = _text(label)
    ref = _text(ref)
    document = _text(document) or _text(snapshot.get("source_reference"))
    shown = set()
    if source == "generic_class":
        class_name = _text(snapshot.get("class_name")) or label or ref
        lines.append(f"{tr('calc.generic_class')}: {class_name or '-'}")
        lines.append(tr("report.generic_illustrative"))
        shown.add(class_name)
    elif has_test_source:
        label = label or _text(snapshot.get("test_label"))
        ref = ref or _text(snapshot.get("id"))
        shown.update(_text(snapshot.get(key)) for key in ("test_number", "report_number"))
    elif label == "Manual entry":
        label = ""  # The translated method already identifies this default label.

    for key, value in (
        ("report.ab_source_reference", document),
        ("report.ab_source_label", label),
        ("report.ab_source_ref", ref),
    ):
        if value and value not in shown:
            lines.append(f"{tr(key)}: {value}")
            shown.add(value)

    if has_test_source and (metadata := _test_metadata(snapshot)):
        lines.extend(["", tr("report.test_description"), *metadata])
    return lines


def historical_ab_lines(project: Project, *, include_full_record: bool = False) -> list[str]:
    history = historical_ab_sources(project.ab_source_snapshot)
    if not history:
        return []
    lines = [tr("ab.history.title")]
    for record in history:
        snapshot = record.get("snapshot")
        reason = record["reason"]
        lines.extend([
            "",
            tr(f"ab.history.{reason}"),
            *_source_lines(
                record["source_type"], snapshot, record.get("source_label"),
                record.get("source_ref"), record.get("source_reference"),
                method_key="ab.history.method",
            ),
        ])
        if isinstance(snapshot, dict):
            for key, label in (("A_n_per_m", "ab.history.recorded_a"), ("B_n_per_m2", "ab.history.recorded_b")):
                value = snapshot.get(key)
                if isinstance(value, (str, int, float)):
                    lines.append(f"{tr(label)}: {value!r}")
        if include_full_record:
            lines.extend(["", tr("ab.history.full_record"), dumps(record, ensure_ascii=False, indent=2)])
    return lines


def _coefficient_source(project: Project) -> list[str]:
    lines = _source_lines(
        project.ab_source_type, project.ab_source_snapshot, project.ab_source_label,
        project.ab_source_ref, project.ab_source_reference,
    )
    if ab_source_status(project) in ("incomplete", "unverifiable", "mismatch"):
        lines.insert(1, tr("ab.source.declared_unverified"))
    if history := historical_ab_lines(project):
        if project.ab_source_type == "manual":
            lines.append(tr("ab.history.effective_manual"))
        lines.extend(["", *history])
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
        tr("report.images_and_calibration"),
        f"{tr('report.reference')}: {project.ref_path or '-'}",
        f"{tr('report.deformed')}: {project.dam_path or '-'}",
        *_calibration(project),
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
        tr("report.ab_source_full"),
        f"A (N/m): {_fmt(project.crash3_A)}",
        f"B (N/m²): {_fmt(project.crash3_B)}",
        *_coefficient_source(project),
        "",
        tr("report.calculation_parameters"),
        f"{tr('report.calculation_angle_deg')}: {_fmt(project.crash3_alpha_deg)}",
        f"{tr('report.vehicle_mass_considered_kg')}: {_fmt(project.vehicle_mass_kg)}",
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
