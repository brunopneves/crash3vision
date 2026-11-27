from __future__ import annotations

import json
import math
import sys
from decimal import Decimal
from typing import TYPE_CHECKING

from app.core.number_format import parse_float

if TYPE_CHECKING:
    from app.core.project import Project


NHTSA_AB_SOURCES = ("nhtsa_library", "nhtsa_file", "nhtsa_report")
LOCKED_AB_SOURCES = (*NHTSA_AB_SOURCES, "generic_class")
HISTORICAL_AB_KEY = "_crash3vision_ab_history"
LEGACY_HISTORY_KEY = "historical_sources"
HISTORY_FORMAT = "CRASH3Vision/A-B provenance"
HISTORY_VERSION = 1
AB_COMPARISON_ULPS = 4


def _history_records(value: object, *, legacy: bool = False) -> list[dict] | None:
    if not isinstance(value, list) or not value:
        return None
    reasons = ("mismatch", "unverifiable") if legacy else ("mismatch", "unverifiable", "incomplete")
    fields = {"source_type", "source_ref", "source_label", "source_reference", "snapshot", "reason"}
    if all(
        isinstance(record, dict)
        and record.keys() == fields
        and record["source_type"] in LOCKED_AB_SOURCES
        and record["reason"] in reasons
        and (not legacy or isinstance(record["snapshot"], dict))
        for record in value
    ):
        return list(value)
    return None


def _split_snapshot(snapshot: object) -> tuple[object, list[dict]]:
    if not isinstance(snapshot, dict):
        return snapshot, []
    container = snapshot.get(HISTORICAL_AB_KEY)
    if (
        isinstance(container, dict)
        and container.keys() == {"format", "version", "records"}
        and container["format"] == HISTORY_FORMAT
        and type(container["version"]) is int
        and container["version"] == HISTORY_VERSION
        and (records := _history_records(container["records"])) is not None
    ):
        return {key: value for key, value in snapshot.items() if key != HISTORICAL_AB_KEY}, records
    if (records := _history_records(snapshot.get(LEGACY_HISTORY_KEY), legacy=True)) is not None:
        return {key: value for key, value in snapshot.items() if key != LEGACY_HISTORY_KEY}, records
    return snapshot, []


def historical_ab_sources(snapshot: object) -> list[dict]:
    return _split_snapshot(snapshot)[1]


def _with_history(snapshot: dict | None, history: list[dict]) -> dict | None:
    if not history:
        return snapshot
    return {
        **(snapshot or {}),
        HISTORICAL_AB_KEY: {"format": HISTORY_FORMAT, "version": HISTORY_VERSION, "records": history},
    }


def _read_recorded_coefficient(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Expected a numeric coefficient.")
    # Accept legacy text only if both parsers agree. A lone separator in
    # "1,234" or "1.234" cannot establish decimal versus thousands notation.
    number = parse_float(value, language="en")
    if number != parse_float(value, language="pt"):
        raise ValueError("Ambiguous coefficient.")
    # This also rejects numeric text that underflows to zero.
    if number <= 0:
        raise ValueError("Expected a positive coefficient.")
    # Text below the smallest positive float can round up to that float.
    if isinstance(value, str) and number == math.ulp(0.0):
        if Decimal(value.strip().replace(",", ".")) < Decimal.from_float(number):
            raise ValueError("Coefficient underflows the supported range.")
    return number


def ab_source_status(project: Project) -> str | None:
    if project.ab_source_type not in LOCKED_AB_SOURCES:
        return None
    snapshot = project.ab_source_snapshot
    if not isinstance(snapshot, dict):
        return "incomplete" if snapshot is None else "unverifiable"
    status = "verified"
    for effective, key in ((project.crash3_A, "A_n_per_m"), (project.crash3_B, "B_n_per_m2")):
        value = snapshot.get(key)
        if value is None or effective is None:
            if status == "verified":
                status = "incomplete"
            continue
        if not math.isfinite(effective) or effective <= 0:
            status = "unverifiable"
            continue
        try:
            recorded = _read_recorded_coefficient(value)
        except (ValueError, OverflowError):
            status = "unverifiable"
            continue
        if effective == recorded:
            continue
        if min(effective, recorded) < sys.float_info.min or (
            abs(effective - recorded) > AB_COMPARISON_ULPS * max(math.ulp(effective), math.ulp(recorded))
        ):
            return "mismatch"
    return status


def archive_ab_source(project: Project, reason: str) -> None:
    snapshot, history = _split_snapshot(project.ab_source_snapshot)
    record = {
        "source_type": project.ab_source_type,
        "source_ref": project.ab_source_ref,
        "source_label": project.ab_source_label,
        "source_reference": project.ab_source_reference,
        "snapshot": snapshot,
    }
    # JSON encoding retains types (including true vs. 1) recursively and ignores key order.
    identity = json.dumps(record, sort_keys=True)
    if not any(json.dumps({key: entry[key] for key in record}, sort_keys=True) == identity for entry in history):
        history.append({**record, "reason": reason})
    project.ab_source_type = "manual"
    project.ab_source_ref = None
    project.ab_source_label = "Manual entry"
    project.ab_source_reference = None
    project.ab_source_snapshot = _with_history(None, history)


def regularize_ab_source(project: Project) -> str | None:
    status = ab_source_status(project)
    if status == "mismatch":
        archive_ab_source(project, status)
    return status if status in ("mismatch", "unverifiable", "incomplete") else None


def replace_ab_snapshot(project: Project, snapshot: dict | None) -> None:
    history = historical_ab_sources(project.ab_source_snapshot)
    project.ab_source_snapshot = _with_history(snapshot, history)
