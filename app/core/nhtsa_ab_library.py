# app/core/nhtsa_ab_library.py
from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

LIB_VERSION = 1
DEFAULT_LIBRARY = {
    "version": LIB_VERSION,
    "records": [],
}


def _resource_base_path() -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        return Path(base_path)
    return Path(__file__).resolve().parents[2]


def _user_data_dir() -> Path:
    return Path.home() / ".crash3vision" / "data"


def _bundled_library_path() -> Path:
    return _resource_base_path() / "app" / "data" / "nhtsa_ab_library.json"


def _migrate_legacy_data() -> None:
    old_path = Path.home() / ".crash3mvp" / "data" / "nhtsa_ab_library.json"
    new_path = Path.home() / ".crash3vision" / "data" / "nhtsa_ab_library.json"

    if old_path.exists() and not new_path.exists():
        import shutil

        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_path, new_path)


def _ensure_user_library() -> Path:
    _migrate_legacy_data()
    user_path = _user_data_dir() / "nhtsa_ab_library.json"
    user_path.parent.mkdir(parents=True, exist_ok=True)

    if not user_path.exists():
        bundled = _bundled_library_path()
        if bundled.exists():
            with open(bundled, "r", encoding="utf-8") as src:
                data = json.load(src)
            with open(user_path, "w", encoding="utf-8") as dst:
                json.dump(data, dst, ensure_ascii=False, indent=2)
        else:
            with open(user_path, "w", encoding="utf-8") as dst:
                json.dump(DEFAULT_LIBRARY, dst, ensure_ascii=False, indent=2)

    return user_path


DEFAULT_LIBRARY_PATH = _ensure_user_library()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(record)

    out.setdefault("id", None)
    out.setdefault("test_number", None)
    out.setdefault("report_number", None)
    out.setdefault("make", None)
    out.setdefault("model", None)
    out.setdefault("year", None)
    out.setdefault("test_agency", None)
    out.setdefault("test_type", None)
    out.setdefault("test_label", None)
    out.setdefault("test_speed_mps", None)
    out.setdefault("impact_speed_mps", None)
    out.setdefault("velocity_change_mps", None)
    out.setdefault("rebound_speed_mps", None)
    out.setdefault("damage_speed_mps", None)
    out.setdefault("speed_used_mps", None)
    out.setdefault("speed_basis", "impact")
    out.setdefault("impact_angle_deg", 0.0)
    out.setdefault("vehicle_mass_kg", None)
    out.setdefault("b0", None)
    out.setdefault("b1", None)
    out.setdefault("L_m", None)
    out.setdefault("c_m", None)
    out.setdefault("crush_area_m2", None)
    out.setdefault("c_mean_m", None)
    out.setdefault("A_n_per_m", None)
    out.setdefault("B_n_per_m2", None)
    out.setdefault("source_reference", None)
    out.setdefault("notes", "")
    out.setdefault("created_at", _now_iso())
    out.setdefault("test_configuration", None)
    out.setdefault("barrier_type", None)
    out.setdefault("overlap_pct", None)
    out.setdefault("impact_direction", None)

    if out["year"] is not None:
        out["year"] = int(out["year"])

    for key in (
        "test_speed_mps",
        "impact_speed_mps",
        "velocity_change_mps",
        "rebound_speed_mps",
        "damage_speed_mps",
        "speed_used_mps",
        "impact_angle_deg",
        "vehicle_mass_kg",
        "b0",
        "b1",
        "L_m",
        "crush_area_m2",
        "c_mean_m",
        "A_n_per_m",
        "B_n_per_m2",
    ):
        if out[key] is not None:
            out[key] = float(out[key])

    if out["impact_speed_mps"] is None and out["test_speed_mps"] is not None:
        out["impact_speed_mps"] = out["test_speed_mps"]

    if out["test_speed_mps"] is None and out["impact_speed_mps"] is not None:
        out["test_speed_mps"] = out["impact_speed_mps"]

    if out["speed_basis"] is None:
        out["speed_basis"] = "impact"

    if isinstance(out["c_m"], dict):
        out["c_m"] = {str(k): float(v) for k, v in out["c_m"].items()}

    if out["overlap_pct"] not in (None, "N/A"):
        out["overlap_pct"] = int(out["overlap_pct"])

    return out


def make_record_id(
    make: str | None,
    model: str | None,
    year: int | None,
    test_agency: str | None,
    test_type: str | None,
    test_number: str | None,
    report_number: str | None,
) -> str:
    parts = [
        (test_agency or "unknown").strip().lower().replace(" ", "_"),
        (make or "unknown").strip().lower().replace(" ", "_"),
        (model or "unknown").strip().lower().replace(" ", "_"),
        str(year) if year is not None else "unknown",
        (test_type or "unknown").strip().lower().replace(" ", "_"),
        (test_number or "no_test").strip().lower().replace(" ", "_"),
        (report_number or "no_report").strip().lower().replace(" ", "_"),
    ]
    return "_".join(parts)


def build_record(
    *,
    test_configuration: str | None = None,
    barrier_type: str | None = None,
    overlap_pct: int | str | None = None,
    impact_direction: str | None = None,
    test_number: str | None,
    report_number: str | None,
    make: str | None,
    model: str | None,
    year: int | None,
    test_agency: str,
    test_type: str,
    test_label: str,
    test_speed_mps: float,
    impact_speed_mps: float | None = None,
    velocity_change_mps: float | None = None,
    rebound_speed_mps: float | None = None,
    damage_speed_mps: float | None = None,
    speed_used_mps: float | None = None,
    speed_basis: str = "impact",
    impact_angle_deg: float = 0.0,
    vehicle_mass_kg: float | None = None,
    b0: float | None = None,
    b1: float | None = None,
    L_m: float | None = None,
    c_m: dict[str, float] | None = None,
    crush_area_m2: float | None = None,
    c_mean_m: float | None = None,
    A_n_per_m: float | None = None,
    B_n_per_m2: float | None = None,
    source_reference: str | None = None,
    notes: str = "",
    record_id: str | None = None,
) -> dict[str, Any]:
    if not record_id:
        record_id = make_record_id(
            make=make,
            model=model,
            year=year,
            test_agency=test_agency,
            test_type=test_type,
            test_number=test_number,
            report_number=report_number,
        )

    record = {
        "id": record_id,
        "test_number": test_number,
        "report_number": report_number,
        "test_configuration": test_configuration,
        "barrier_type": barrier_type,
        "overlap_pct": overlap_pct,
        "impact_direction": impact_direction,
        "make": make,
        "model": model,
        "year": year,
        "test_agency": test_agency,
        "test_type": test_type,
        "test_label": test_label,
        "test_speed_mps": test_speed_mps,
        "impact_speed_mps": impact_speed_mps,
        "velocity_change_mps": velocity_change_mps,
        "rebound_speed_mps": rebound_speed_mps,
        "damage_speed_mps": damage_speed_mps,
        "speed_used_mps": speed_used_mps,
        "speed_basis": speed_basis,
        "impact_angle_deg": impact_angle_deg,
        "vehicle_mass_kg": vehicle_mass_kg,
        "b0": b0,
        "b1": b1,
        "L_m": L_m,
        "c_m": c_m,
        "crush_area_m2": crush_area_m2,
        "c_mean_m": c_mean_m,
        "A_n_per_m": A_n_per_m,
        "B_n_per_m2": B_n_per_m2,
        "source_reference": source_reference,
        "notes": notes,
        "created_at": _now_iso(),
    }
    return _normalize_record(record)


def load_library(path: str | Path) -> dict[str, Any]:
    p = Path(path)

    if not p.exists():
        return deepcopy(DEFAULT_LIBRARY)

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return deepcopy(DEFAULT_LIBRARY)

    version = int(data.get("version", LIB_VERSION))
    records_raw = data.get("records", [])

    records: list[dict[str, Any]] = []
    if isinstance(records_raw, list):
        for item in records_raw:
            if isinstance(item, dict):
                records.append(_normalize_record(item))

    return {
        "version": version,
        "records": records,
    }


def save_library(path: str | Path, library_data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    records_raw = library_data.get("records", [])
    records: list[dict[str, Any]] = []

    if isinstance(records_raw, list):
        for item in records_raw:
            if isinstance(item, dict):
                records.append(_normalize_record(item))

    payload = {
        "version": int(library_data.get("version", LIB_VERSION)),
        "records": records,
    }

    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def list_records(path: str | Path) -> list[dict[str, Any]]:
    return load_library(path)["records"]


def get_record_by_id(path: str | Path, record_id: str) -> dict[str, Any] | None:
    for rec in list_records(path):
        if rec.get("id") == record_id:
            return rec
    return None


def upsert_record(path: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    lib = load_library(path)
    norm = _normalize_record(record)

    if not norm.get("id"):
        norm["id"] = make_record_id(
            make=norm.get("make"),
            model=norm.get("model"),
            year=norm.get("year"),
            test_agency=norm.get("test_agency"),
            test_type=norm.get("test_type"),
            test_number=norm.get("test_number"),
            report_number=norm.get("report_number"),
        )

    replaced = False
    for i, rec in enumerate(lib["records"]):
        if rec.get("id") == norm["id"]:
            lib["records"][i] = norm
            replaced = True
            break

    if not replaced:
        lib["records"].append(norm)

    save_library(path, lib)
    return norm


def delete_record(path: str | Path, record_id: str) -> bool:
    lib = load_library(path)
    old_len = len(lib["records"])
    lib["records"] = [r for r in lib["records"] if r.get("id") != record_id]

    changed = len(lib["records"]) != old_len
    if changed:
        save_library(path, lib)
    return changed


def add_record(path: str | Path, record: dict) -> None:
    data = load_library(path)

    records = data.get("records", [])

    # evita duplicidade por id
    existing_ids = {r.get("id") for r in records}

    base_id = record.get("id") or "record"
    new_id = base_id
    counter = 1

    while new_id in existing_ids:
        new_id = f"{base_id}_{counter}"
        counter += 1

    record["id"] = new_id

    records.append(record)
    data["records"] = records

    save_library(path, data)


def load_record_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Invalid A/B file format.")

    record = data.get("record")
    if not isinstance(record, dict):
        raise ValueError("Missing 'record' in A/B file.")

    return _normalize_record(record)


def save_record_file(path: str | Path, record: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": LIB_VERSION,
        "record": _normalize_record(record),
    }

    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parents[2] / relative_path
