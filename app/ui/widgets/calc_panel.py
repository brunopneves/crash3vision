from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtGui import QAction

from PySide6.QtWidgets import (
    QFrame,
    QFileDialog,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QMenu,
)

from app.core.nhtsa_ab_library import (
    DEFAULT_LIBRARY_PATH,
    list_records,
    load_record_file,
    save_record_file,
)
from app.i18n import tr
from app.core.number_format import parse_float, format_float
from app.ui.widgets.crush_profile_dialog import CrushProfileDialog
from app.ui.widgets.nhtsa_ab_dialog import NhtsaAbDialog


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parents[3] / relative_path


class CalcPanel(QGroupBox):
    ENERGY_UNIT = "J"
    SPEED_UNIT_KMH = "km/h"
    A_UNIT = "N/m"
    B_UNIT = "N/m²"

    KGFCM_TO_N_PER_M = 980.665
    KGFCM2_TO_N_PER_M2 = 98066.5

    LIB_PATH = resource_path("app/data/stiffness_library.json")
    NHTSA_LIB_PATH = DEFAULT_LIBRARY_PATH

    def __init__(self, main_window):
        super().__init__(tr("calc.group.title"))

        self.main = main_window
        self._stiffness_classes = self._load_stiffness_classes()
        self._profile_dialog: CrushProfileDialog | None = None

        layout = QVBoxLayout(self)

        self.grp_source = QGroupBox(tr("calc.group.source"))
        src_layout = QVBoxLayout(self.grp_source)

        self.grp_params = QGroupBox(tr("calc.group.params"))
        params_layout = QVBoxLayout(self.grp_params)

        self.grp_calc = QGroupBox(tr("calc.group.calc"))
        calc_layout = QVBoxLayout(self.grp_calc)

        # ---------------- Generic stiffness class ----------------
        row_class = QHBoxLayout()
        self.lbl_generic_class = QLabel(tr("calc.generic_class"))
        row_class.addWidget(self.lbl_generic_class)

        self.cmb_class = QComboBox()
        self.cmb_class.addItem(tr("calc.manual_entry"), None)
        for class_name in sorted(self._stiffness_classes.keys()):
            self.cmb_class.addItem(class_name, class_name)
        row_class.addWidget(self.cmb_class)
        params_layout.addLayout(row_class)

        # self.btn_apply_class = QPushButton(tr("calc.apply_class_values"))
        # params_layout.addWidget(self.btn_apply_class)

        self.cmb_class.currentIndexChanged.connect(self._on_class_changed)

        self.btn_compute_ab_nhtsa = QPushButton(tr("calc.compute_ab_from_nhtsa"))
        src_layout.addWidget(self.btn_compute_ab_nhtsa)

        self.btn_edit_ab_nhtsa = QPushButton(tr("calc.edit_ab_from_nhtsa"))
        src_layout.addWidget(self.btn_edit_ab_nhtsa)

        self.btn_ab_menu = QPushButton(tr("calc.ab_menu"))
        self.ab_menu = QMenu(self)

        self.act_load_ab_library = QAction(tr("calc.ab_menu.load_library"), self)
        self.act_import_ab_file = QAction(tr("calc.ab_menu.import_file"), self)
        self.act_export_ab_file = QAction(tr("calc.ab_menu.export_file"), self)

        self.ab_menu.addAction(self.act_load_ab_library)
        self.ab_menu.addSeparator()
        self.ab_menu.addAction(self.act_import_ab_file)
        self.ab_menu.addAction(self.act_export_ab_file)

        self.btn_ab_menu.setMenu(self.ab_menu)
        src_layout.addWidget(self.btn_ab_menu)

        self.lbl_ab_source = QLabel(tr("calc.ab_source_default"))
        src_layout.addWidget(self.lbl_ab_source)
        self.lbl_ab_source.setWordWrap(True)
        self.lbl_ab_source.setMinimumWidth(0)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep1)
        # ---------------- Active parameters ----------------
        # ---------------- A coefficient ----------------
        row_a = QHBoxLayout()
        self.lbl_a = QLabel(f"{tr('calc.a_coefficient')} ({self.A_UNIT})")
        row_a.addWidget(self.lbl_a)
        self.txt_A = QLineEdit()
        self.txt_A.setPlaceholderText("e.g. 65637")
        row_a.addWidget(self.txt_A)
        params_layout.addLayout(row_a)

        # ---------------- B coefficient ----------------
        row_b = QHBoxLayout()
        self.lbl_b = QLabel(f"{tr('calc.b_coefficient')} ({self.B_UNIT})")
        row_b.addWidget(self.lbl_b)
        self.txt_B = QLineEdit()
        self.txt_B.setPlaceholderText("e.g. 856265")
        row_b.addWidget(self.txt_B)
        params_layout.addLayout(row_b)

        # ---------------- Alpha ----------------
        row_alpha = QHBoxLayout()
        self.lbl_alpha = QLabel(tr("calc.alpha_deg"))
        row_alpha.addWidget(self.lbl_alpha)
        self.txt_alpha_deg = QLineEdit()
        self.txt_alpha_deg.setPlaceholderText("e.g. 0.0")
        self.txt_alpha_deg.setText("0.0")
        row_alpha.addWidget(self.txt_alpha_deg)
        params_layout.addLayout(row_alpha)

        self.lbl_formula_hint = QLabel(tr("calc.formula_hint"))
        self.lbl_formula_hint.setWordWrap(True)
        params_layout.addWidget(self.lbl_formula_hint)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)

        # ---------------- Compute energy ----------------
        self.btn_compute = QPushButton(tr("calc.compute_energy"))
        calc_layout.addWidget(self.btn_compute)

        self.lbl_energy = QLabel(tr("calc.total_energy_default"))
        calc_layout.addWidget(self.lbl_energy)

        # ---------------- Vehicle mass ----------------
        row_mass = QHBoxLayout()
        self.lbl_vehicle_mass = QLabel(tr("calc.vehicle_mass"))
        row_mass.addWidget(self.lbl_vehicle_mass)

        self.txt_vehicle_mass = QLineEdit()
        self.txt_vehicle_mass.setPlaceholderText("e.g. 1700")
        row_mass.addWidget(self.txt_vehicle_mass)

        calc_layout.addLayout(row_mass)

        self.btn_compute_speed = QPushButton(tr("calc.compute_speed"))
        calc_layout.addWidget(self.btn_compute_speed)

        self.lbl_speed = QLabel(tr("calc.damage_speed_default"))
        calc_layout.addWidget(self.lbl_speed)

        # ---------------- Profile ----------------
        self.btn_show_profile = QPushButton(tr("calc.show_crush_profile"))
        calc_layout.addWidget(self.btn_show_profile)

        layout.addWidget(self.grp_source)
        layout.addWidget(self.grp_params)
        layout.addWidget(self.grp_calc)

        # ---------------- Signals ----------------
        self.act_load_ab_library.triggered.connect(self._on_load_ab_from_library)
        self.act_import_ab_file.triggered.connect(self._on_import_ab_file)
        self.act_export_ab_file.triggered.connect(self._on_export_ab_file)

        self.btn_compute.clicked.connect(self._on_compute)
        self.btn_compute_speed.clicked.connect(self._on_compute_speed)
        self.btn_show_profile.clicked.connect(self._on_show_profile)
        self.btn_compute_ab_nhtsa.clicked.connect(self._on_compute_ab_from_nhtsa)
        self.btn_edit_ab_nhtsa.clicked.connect(self._on_edit_ab_from_nhtsa)

        self._on_class_changed()
        self.retranslate_ui()

        for field, attribute in (
            (self.txt_A, "crash3_A"),
            (self.txt_B, "crash3_B"),
            (self.txt_alpha_deg, "crash3_alpha_deg"),
            (self.txt_vehicle_mass, "vehicle_mass_kg"),
        ):
            field.textChanged.connect(
                lambda text, attribute=attribute: self._on_parameter_changed(attribute, text)
            )

    def _on_parameter_changed(self, attribute: str, text: str) -> None:
        try:
            value = parse_float(text)
        except ValueError:
            value = None
        setattr(self.main.project, attribute, value)
        if attribute == "vehicle_mass_kg":
            self.main._vehicle_mass_kg = value
            self.main.workflow.invalidate_speed()
        else:
            self.main.workflow.invalidate_energy()

    def retranslate_ui(self) -> None:
        self.setTitle(tr("calc.group.title"))
        self.lbl_generic_class.setText(tr("calc.generic_class"))

        current_data = self.cmb_class.currentData()
        self.cmb_class.setItemText(0, tr("calc.manual_entry"))
        idx = self.cmb_class.findData(current_data)
        if idx >= 0:
            self.cmb_class.setCurrentIndex(idx)

        self.btn_ab_menu.setText(tr("calc.ab_menu"))
        self.act_load_ab_library.setText(tr("calc.ab_menu.load_library"))
        self.act_import_ab_file.setText(tr("calc.ab_menu.import_file"))
        self.act_export_ab_file.setText(tr("calc.ab_menu.export_file"))
        self.btn_compute_ab_nhtsa.setText(tr("calc.compute_ab_from_nhtsa"))
        self.btn_edit_ab_nhtsa.setText(tr("calc.edit_ab_from_nhtsa"))

        self.lbl_a.setText(f"{tr('calc.a_coefficient')} ({self.A_UNIT})")
        self.lbl_b.setText(f"{tr('calc.b_coefficient')} ({self.B_UNIT})")
        self.lbl_alpha.setText(tr("calc.alpha_deg"))
        self.lbl_formula_hint.setText(tr("calc.formula_hint"))
        self.btn_compute.setText(tr("calc.compute_energy"))

        if self.main._total_energy is None:
            self.lbl_energy.setText(tr("calc.total_energy_default"))
        else:
            self.lbl_energy.setText(
                tr(
                    "calc.total_energy_value",
                    value=f"{self.main._total_energy:.2f}",
                    unit=self.ENERGY_UNIT,
                )
            )

        self.lbl_vehicle_mass.setText(tr("calc.vehicle_mass"))
        self.btn_compute_speed.setText(tr("calc.compute_speed"))

        if self.main._damage_speed_kmh is None:
            self.lbl_speed.setText(tr("calc.damage_speed_default"))
        else:
            self.lbl_speed.setText(
                tr(
                    "calc.damage_speed_value",
                    value=f"{self.main._damage_speed_kmh:.2f}",
                    unit=self.SPEED_UNIT_KMH,
                )
            )

        self.grp_source.setTitle(tr("calc.group.source"))
        self.grp_params.setTitle(tr("calc.group.params"))
        self.grp_calc.setTitle(tr("calc.group.calc"))

        self._refresh_ab_source_ui()
        self.btn_show_profile.setText(tr("calc.show_crush_profile"))

    def _to_float(self, value: object, default: float = 0.0) -> float:
        return parse_float(value, default=default)

    def _load_stiffness_classes(self) -> dict[str, dict[str, float]]:
        if not self.LIB_PATH.exists():
            return {}

        try:
            with open(self.LIB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}

        classes = data.get("stiffness_classes")
        if not isinstance(classes, dict):
            return {}

        units = str(data.get("units", "")).strip().lower()

        normalized: dict[str, dict[str, float]] = {}
        for key, value in classes.items():
            if not isinstance(value, dict):
                continue

            try:
                a_raw = float(value["A"])
                b_raw = float(value["B"])
            except (KeyError, TypeError, ValueError):
                continue

            if units in {"si", "si_n_per_m", "n/m"}:
                a_si = a_raw
                b_si = b_raw
            else:
                a_si = a_raw * self.KGFCM_TO_N_PER_M
                b_si = b_raw * self.KGFCM2_TO_N_PER_M2

            normalized[str(key)] = {"A": a_si, "B": b_si}

        return normalized

    def _on_class_changed(self):
        class_name = self.cmb_class.currentData()

        if not class_name:
            self.txt_A.setText("")
            self.txt_B.setText("")
            self.txt_A.setReadOnly(False)
            self.txt_B.setReadOnly(False)

            self.main.project.ab_source_type = "manual"
            self.main.project.ab_source_ref = None
            self.main.project.ab_source_label = "Manual entry"
            self.main.project.ab_source_reference = None
            self.main.project.ab_source_snapshot = None

            self._refresh_ab_source_ui()
            return

        params = self._stiffness_classes.get(class_name)
        if not params:
            QMessageBox.warning(
                self,
                tr("calc.dialog.title"),
                tr("calc.error.class_not_found"),
            )
            return

        self.txt_A.setText(f"{params['A']:.2f}")
        self.txt_B.setText(f"{params['B']:.2f}")
        self.txt_A.setReadOnly(True)
        self.txt_B.setReadOnly(True)

        self.main.project.ab_source_type = "generic_class"
        self.main.project.ab_source_ref = class_name
        self.main.project.ab_source_label = class_name
        self.main.project.ab_source_reference = None
        self.main.project.ab_source_snapshot = {
            "class_name": class_name,
            "A_n_per_m": params["A"],
            "B_n_per_m2": params["B"],
        }

        self._refresh_ab_source_ui()

    def _on_load_ab_from_library(self):
        records = list_records(self.NHTSA_LIB_PATH)

        if not records:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.library_empty"),
            )
            return

        flt = self.main.project.last_ab_filter
        if flt:
            filtered = [r for r in records if r.get("test_type") == flt]
            if filtered:
                records = filtered

        options: list[str] = []
        record_map: dict[str, dict] = {}

        for rec in records:
            rec_id = rec.get("id") or ""
            test_number = rec.get("test_number") or "-"
            report_number = rec.get("report_number") or "-"
            test_label = rec.get("test_label") or "-"
            a_val = rec.get("A_n_per_m")
            b_val = rec.get("B_n_per_m2")

            label = (
                f"{test_label} | "
                f"test={test_number} | "
                f"report={report_number} | "
                f"id={rec_id}"
            )

            if a_val is None or b_val is None:
                label += " | [no A/B]"

            options.append(label)
            record_map[label] = rec

        if not options:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.library_no_valid_ab"),
            )
            return

        options.sort()

        selected, ok = QInputDialog.getItem(
            self,
            tr("dialog.select_ab_title"),
            tr("dialog.select_ab_label"),
            options,
            0,
            False,
        )
        if not ok or not selected:
            return

        rec = record_map[selected]
        self.main.project.last_ab_filter = rec.get("test_type")

        if rec.get("A_n_per_m") is None or rec.get("B_n_per_m2") is None:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.library_no_valid_ab"),
            )
            return

        A_n_per_m = self._to_float(rec.get("A_n_per_m"))
        B_n_per_m2 = self._to_float(rec.get("B_n_per_m2"))

        self.txt_A.setText(format_float(A_n_per_m, 2))
        self.txt_B.setText(format_float(B_n_per_m2, 2))

        self.main.project.crash3_A = A_n_per_m
        self.main.project.crash3_B = B_n_per_m2

        self.main.project.ab_source_type = "nhtsa_library"
        self.main.project.ab_source_ref = rec.get("id")
        self.main.project.ab_source_label = rec.get("test_label") or rec.get("id")
        self.main.project.ab_source_reference = rec.get("source_reference")

        c_m = rec.get("c_m") or {}
        c_values_m = [
            float(c_m.get("C1", 0.0)),
            float(c_m.get("C2", 0.0)),
            float(c_m.get("C3", 0.0)),
            float(c_m.get("C4", 0.0)),
            float(c_m.get("C5", 0.0)),
            float(c_m.get("C6", 0.0)),
        ]

        self.main.project.ab_source_snapshot = {
            "id": rec.get("id"),
            "test_number": rec.get("test_number"),
            "report_number": rec.get("report_number"),
            "test_agency": rec.get("test_agency"),
            "make": rec.get("make"),
            "model": rec.get("model"),
            "year": rec.get("year"),
            "test_type": rec.get("test_type"),
            "test_configuration": rec.get("test_configuration"),
            "barrier_type": rec.get("barrier_type"),
            "overlap_pct": rec.get("overlap_pct"),
            "impact_direction": rec.get("impact_direction"),
            "test_label": rec.get("test_label"),
            "test_speed_mps": rec.get("test_speed_mps"),
            "impact_speed_mps": rec.get("impact_speed_mps"),
            "velocity_change_mps": rec.get("velocity_change_mps"),
            "rebound_speed_mps": rec.get("rebound_speed_mps"),
            "damage_speed_mps": rec.get("damage_speed_mps"),
            "speed_used_mps": rec.get("speed_used_mps"),
            "speed_basis": rec.get("speed_basis"),
            "impact_angle_deg": rec.get("impact_angle_deg"),
            "vehicle_mass_kg": rec.get("vehicle_mass_kg"),
            "b0_mps": rec.get("b0"),
            "L_m": rec.get("L_m"),
            "c_values_m": c_values_m,
            "crush_area_m2": rec.get("crush_area_m2"),
            "c_mean_m": rec.get("c_mean_m"),
            "b1_per_s": rec.get("b1"),
            "A_n_per_m": rec.get("A_n_per_m"),
            "B_n_per_m2": rec.get("B_n_per_m2"),
            "source_reference": rec.get("source_reference"),
        }

        mass_kg = rec.get("vehicle_mass_kg")
        if mass_kg is not None:
            self.txt_vehicle_mass.setText(format_float(float(mass_kg), 2))

        self._refresh_ab_source_ui()
        self._on_compute()

    def _on_import_ab_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("calc.ab_file.import_title"),
            "",
            "A/B JSON (*.json)",
        )
        if not path:
            return

        try:
            rec = load_record_file(path)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("msg.error"),
                f"{tr('calc.ab_file.invalid')}\n{e}",
            )
            return

        a_val = rec.get("A_n_per_m")
        b_val = rec.get("B_n_per_m2")

        if a_val is None or b_val is None:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.library_no_valid_ab"),
            )
            return

        A_n_per_m = self._to_float(a_val)
        B_n_per_m2 = self._to_float(b_val)

        self.txt_A.setText(format_float(A_n_per_m, 2))
        self.txt_B.setText(format_float(B_n_per_m2, 2))
        self.txt_A.setReadOnly(True)
        self.txt_B.setReadOnly(True)

        self.main.project.crash3_A = A_n_per_m
        self.main.project.crash3_B = B_n_per_m2

        self.main.project.ab_source_type = "nhtsa_file"
        self.main.project.ab_source_ref = rec.get("id")
        self.main.project.ab_source_label = rec.get("test_label") or rec.get("id")
        self.main.project.ab_source_reference = rec.get("source_reference")

        c_m = rec.get("c_m") or {}
        c_values_m = [
            float(c_m.get("C1", 0.0)),
            float(c_m.get("C2", 0.0)),
            float(c_m.get("C3", 0.0)),
            float(c_m.get("C4", 0.0)),
            float(c_m.get("C5", 0.0)),
            float(c_m.get("C6", 0.0)),
        ]

        self.main.project.ab_source_snapshot = {
            "id": rec.get("id"),
            "test_number": rec.get("test_number"),
            "report_number": rec.get("report_number"),
            "test_agency": rec.get("test_agency"),
            "make": rec.get("make"),
            "model": rec.get("model"),
            "year": rec.get("year"),
            "test_type": rec.get("test_type"),
            "test_configuration": rec.get("test_configuration"),
            "barrier_type": rec.get("barrier_type"),
            "overlap_pct": rec.get("overlap_pct"),
            "impact_direction": rec.get("impact_direction"),
            "test_label": rec.get("test_label"),
            "test_speed_mps": rec.get("test_speed_mps"),
            "impact_speed_mps": rec.get("impact_speed_mps"),
            "velocity_change_mps": rec.get("velocity_change_mps"),
            "rebound_speed_mps": rec.get("rebound_speed_mps"),
            "damage_speed_mps": rec.get("damage_speed_mps"),
            "speed_used_mps": rec.get("speed_used_mps"),
            "speed_basis": rec.get("speed_basis"),
            "impact_angle_deg": rec.get("impact_angle_deg"),
            "vehicle_mass_kg": rec.get("vehicle_mass_kg"),
            "b0_mps": rec.get("b0"),
            "L_m": rec.get("L_m"),
            "c_values_m": c_values_m,
            "crush_area_m2": rec.get("crush_area_m2"),
            "c_mean_m": rec.get("c_mean_m"),
            "b1_per_s": rec.get("b1"),
            "A_n_per_m": rec.get("A_n_per_m"),
            "B_n_per_m2": rec.get("B_n_per_m2"),
            "source_reference": rec.get("source_reference"),
        }

        mass_kg = rec.get("vehicle_mass_kg")
        if mass_kg is not None:
            self.txt_vehicle_mass.setText(format_float(float(mass_kg), 2))

        self._refresh_ab_source_ui()
        self._on_compute()

    def _on_export_ab_file(self):
        snap = self.main.project.ab_source_snapshot
        if not snap:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.no_nhtsa_snapshot"),
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("calc.ab_file.export_title"),
            "",
            "A/B JSON (*.json)",
        )
        if not path:
            return

        if not path.lower().endswith(".json"):
            path += ".json"

        record = {
            "id": snap.get("id"),
            "test_number": snap.get("test_number"),
            "report_number": snap.get("report_number"),
            "make": snap.get("make"),
            "model": snap.get("model"),
            "year": snap.get("year"),
            "test_agency": snap.get("test_agency"),
            "test_type": snap.get("test_type"),
            "test_configuration": snap.get("test_configuration"),
            "barrier_type": snap.get("barrier_type"),
            "overlap_pct": snap.get("overlap_pct"),
            "impact_direction": snap.get("impact_direction"),
            "test_label": snap.get("test_label"),
            "test_speed_mps": snap.get("test_speed_mps"),
            "impact_speed_mps": snap.get("impact_speed_mps"),
            "velocity_change_mps": snap.get("velocity_change_mps"),
            "rebound_speed_mps": snap.get("rebound_speed_mps"),
            "damage_speed_mps": snap.get("damage_speed_mps"),
            "speed_used_mps": snap.get("speed_used_mps"),
            "speed_basis": snap.get("speed_basis"),
            "impact_angle_deg": snap.get("impact_angle_deg"),
            "vehicle_mass_kg": snap.get("vehicle_mass_kg"),
            "b0": snap.get("b0_mps"),
            "b1": snap.get("b1_per_s"),
            "L_m": snap.get("L_m"),
            "c_m": {
                "C1": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[0]),
                "C2": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[1]),
                "C3": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[2]),
                "C4": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[3]),
                "C5": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[4]),
                "C6": float((snap.get("c_values_m") or [0, 0, 0, 0, 0, 0])[5]),
            },
            "crush_area_m2": snap.get("crush_area_m2"),
            "c_mean_m": snap.get("c_mean_m"),
            "A_n_per_m": snap.get("A_n_per_m"),
            "B_n_per_m2": snap.get("B_n_per_m2"),
            "source_reference": snap.get("source_reference"),
            "notes": "",
        }

        try:
            save_record_file(path, record)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("msg.error"),
                str(e),
            )
            return

        QMessageBox.information(
            self,
            tr("msg.success"),
            tr("calc.ab_file.exported"),
        )

    def _on_compute(self):
        try:
            A, B, alpha_deg = self._parse_ab_alpha()
        except ValueError as e:
            QMessageBox.warning(
                self,
                tr("calc.dialog.title"),
                str(e),
            )
            return

        self.main.project.crash3_A = A
        self.main.project.crash3_B = B
        self.main.project.crash3_alpha_deg = alpha_deg
        self.main.project.crash3_units = "SI_N_per_m"

        self.main._sync_ui_to_project()

        try:
            result = self.main.calc.compute_crash3(A, B, alpha_deg)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("calc.dialog.title"),
                str(e),
            )
            return

        energy_j = float(result["total_energy_j"])

        self.lbl_energy.setText(
            tr(
                "calc.total_energy_value",
                value=f"{energy_j:.2f}",
                unit=self.ENERGY_UNIT,
            )
        )

        self.main._total_energy = energy_j
        self.main.project.total_energy_j = energy_j

        self.lbl_speed.setText(tr("calc.damage_speed_default"))
        self.main._damage_speed_mps = None
        self.main._damage_speed_kmh = None
        self.main.project.damage_speed_mps = None
        self.main.project.damage_speed_kmh = None

        if self.main.project.ab_source_type not in (
            "nhtsa_library",
            "nhtsa_file",
            "generic_class",
            "nhtsa_report",
        ):
            self.main.project.ab_source_type = "manual"
            self.main.project.ab_source_ref = None
            self.main.project.ab_source_label = "Manual entry"
            self.main.project.ab_source_reference = None
            self.main.project.ab_source_snapshot = {
                "A_n_per_m": A,
                "B_n_per_m2": B,
                "alpha_deg": alpha_deg,
            }
            self._refresh_ab_source_ui()

        self.main._refresh_summary()

    def _on_compute_speed(self):
        try:
            mass_kg = parse_float(self.txt_vehicle_mass.text())
        except ValueError:
            QMessageBox.warning(
                self,
                tr("calc.speed.dialog.title"),
                tr("calc.error.invalid_vehicle_mass"),
            )
            return

        self.main._sync_ui_to_project()

        try:
            result = self.main.calc.compute_damage_speed(mass_kg)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("calc.speed.dialog.title"),
                str(e),
            )
            return

        speed_kmh = float(result["speed_kmh"])

        self.lbl_speed.setText(
            tr(
                "calc.damage_speed_value",
                value=f"{speed_kmh:.2f}",
                unit=self.SPEED_UNIT_KMH,
            )
        )

        self.main._vehicle_mass_kg = mass_kg
        self.main._damage_speed_mps = float(result["speed_mps"])
        self.main._damage_speed_kmh = speed_kmh

        self.main.project.vehicle_mass_kg = mass_kg
        self.main.project.damage_speed_mps = float(result["speed_mps"])
        self.main.project.damage_speed_kmh = speed_kmh

        self.main._refresh_summary()

    def _on_show_profile(self):
        try:
            A, B, alpha_deg = self._parse_ab_alpha()
        except ValueError as e:
            QMessageBox.warning(
                self,
                tr("calc.profile.dialog.title"),
                str(e),
            )
            return

        self.main.project.crash3_A = A
        self.main.project.crash3_B = B
        self.main.project.crash3_alpha_deg = alpha_deg
        self.main.project.crash3_units = "SI_N_per_m"

        self.main._sync_ui_to_project()

        try:
            data = self.main.calc.build_damage_profile_data(A, B, alpha_deg)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("calc.profile.dialog.title"),
                str(e),
            )
            return

        crush_m = list(data.get("crush_m", []))
        self._profile_dialog = CrushProfileDialog(
            crush_m=crush_m,
            parent=self,
        )
        self._profile_dialog.exec()

    def _on_compute_ab_from_nhtsa(self):
        dlg = NhtsaAbDialog(self)

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        if dlg._last_result is None:
            return

        result = dlg._last_result
        data = dlg.get_input_data()

        A_n_per_m = self._to_float(result["A_n_per_m"])
        B_n_per_m2 = self._to_float(result["B_n_per_m2"])

        self.txt_A.setText(format_float(A_n_per_m, 2))
        self.txt_B.setText(format_float(B_n_per_m2, 2))

        self.main.project.crash3_A = A_n_per_m
        self.main.project.crash3_B = B_n_per_m2

        label = data["test_label"] or data["report_number"] or "NHTSA report"

        self.main.project.ab_source_type = "nhtsa_report"
        self.main.project.ab_source_ref = data["report_number"]
        self.main.project.ab_source_label = label
        self.main.project.ab_source_reference = data["report_number"]

        self.main.project.ab_source_snapshot = {
            "test_agency": data["test_agency"],
            "test_number": data["test_number"],
            "report_number": data["report_number"],
            "make": data["make"],
            "model": data["model"],
            "year": data["year"],
            "test_type": data["test_type"],
            "test_configuration": data["test_configuration"],
            "barrier_type": data["barrier_type"],
            "overlap_pct": data["overlap_pct"],
            "impact_direction": data["impact_direction"],
            "test_label": data["test_label"],
            "test_speed_mps": data["impact_speed_mps"],
            "impact_speed_mps": data["impact_speed_mps"],
            "velocity_change_mps": data["velocity_change_mps"],
            "rebound_speed_mps": result["rebound_speed_mps"],
            "damage_speed_mps": result["damage_speed_mps"],
            "speed_used_mps": result["speed_used_mps"],
            "speed_basis": data["speed_basis"],
            "impact_angle_deg": data["impact_angle_deg"],
            "vehicle_mass_kg": data["vehicle_mass_kg"],
            "b0_mps": data["b0_mps"],
            "L_m": data["L_m"],
            "c_values_m": data["c_values_m"],
            "crush_area_m2": result["crush_area_m2"],
            "c_mean_m": result["c_mean_m"],
            "b1_per_s": result["b1_per_s"],
            "A_n_per_m": result["A_n_per_m"],
            "B_n_per_m2": result["B_n_per_m2"],
        }

        self._refresh_ab_source_ui()
        self._on_compute()

    def _on_edit_ab_from_nhtsa(self):
        snap = self.main.project.ab_source_snapshot
        if not snap:
            QMessageBox.warning(
                self,
                tr("msg.warning"),
                tr("calc.no_nhtsa_snapshot"),
            )
            return

        dlg = NhtsaAbDialog(self, initial_data=snap)

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        if dlg._last_result is None:
            return

        result = dlg._last_result
        data = dlg.get_input_data()

        A_n_per_m = self._to_float(result["A_n_per_m"])
        B_n_per_m2 = self._to_float(result["B_n_per_m2"])

        self.txt_A.setText(format_float(A_n_per_m, 2))
        self.txt_B.setText(format_float(B_n_per_m2, 2))

        self.main.project.crash3_A = A_n_per_m
        self.main.project.crash3_B = B_n_per_m2

        label = data["test_label"] or data["report_number"] or "NHTSA report"

        self.main.project.ab_source_type = "nhtsa_report"
        self.main.project.ab_source_ref = data["report_number"]
        self.main.project.ab_source_label = label
        self.main.project.ab_source_reference = data["report_number"]

        self.main.project.ab_source_snapshot = {
            "test_agency": data["test_agency"],
            "test_number": data["test_number"],
            "report_number": data["report_number"],
            "make": data["make"],
            "model": data["model"],
            "year": data["year"],
            "test_type": data["test_type"],
            "test_configuration": data["test_configuration"],
            "barrier_type": data["barrier_type"],
            "overlap_pct": data["overlap_pct"],
            "impact_direction": data["impact_direction"],
            "test_label": data["test_label"],
            "test_speed_mps": data["impact_speed_mps"],
            "impact_speed_mps": data["impact_speed_mps"],
            "velocity_change_mps": data["velocity_change_mps"],
            "rebound_speed_mps": result["rebound_speed_mps"],
            "damage_speed_mps": result["damage_speed_mps"],
            "speed_used_mps": result["speed_used_mps"],
            "speed_basis": data["speed_basis"],
            "impact_angle_deg": data["impact_angle_deg"],
            "vehicle_mass_kg": data["vehicle_mass_kg"],
            "b0_mps": data["b0_mps"],
            "L_m": data["L_m"],
            "c_values_m": data["c_values_m"],
            "crush_area_m2": result["crush_area_m2"],
            "c_mean_m": result["c_mean_m"],
            "b1_per_s": result["b1_per_s"],
            "A_n_per_m": result["A_n_per_m"],
            "B_n_per_m2": result["B_n_per_m2"],
        }

        self._refresh_ab_source_ui()
        self._on_compute()

    def _refresh_ab_source_ui(self) -> None:
        p = self.main.project

        if p.ab_source_type == "nhtsa_library":
            label = p.ab_source_label or "-"
            self.lbl_ab_source.setText(tr("calc.ab_source_nhtsa", label=label))

        elif p.ab_source_type == "nhtsa_report":
            label = p.ab_source_label or "-"
            self.lbl_ab_source.setText(tr("calc.ab_source_nhtsa_report", label=label))

        elif p.ab_source_type == "nhtsa_file":
            label = p.ab_source_label or "-"
            self.lbl_ab_source.setText(tr("calc.ab_source_nhtsa_file", label=label))

        elif p.ab_source_type == "generic_class":
            label = p.ab_source_label or "-"
            self.lbl_ab_source.setText(tr("calc.ab_source_generic", label=label))

        elif p.ab_source_type == "manual":
            self.lbl_ab_source.setText(tr("calc.ab_source_manual"))

        else:
            self.lbl_ab_source.setText(tr("calc.ab_source_default"))

        snap = p.ab_source_snapshot or {}
        if snap:

            def _to_kmh(v):
                return round(float(v) * 3.6, 2) if v is not None else None

            self.lbl_ab_source.setToolTip(
                tr(
                    "calc.ab_tooltip",
                    label=snap.get("test_label"),
                    test_number=snap.get("test_number"),
                    report_number=snap.get("report_number"),
                    impact_speed=_to_kmh(
                        snap.get("impact_speed_mps", snap.get("test_speed_mps"))
                    ),
                    velocity_change=_to_kmh(snap.get("velocity_change_mps")),
                    damage_speed=_to_kmh(snap.get("damage_speed_mps")),
                    speed_basis=snap.get("speed_basis"),
                    angle=snap.get("impact_angle_deg"),
                    A=snap.get("A_n_per_m"),
                    B=snap.get("B_n_per_m2"),
                )
            )
        else:
            self.lbl_ab_source.setToolTip("")

    def _parse_ab_alpha(self):
        try:
            A = parse_float(self.txt_A.text())
            B = parse_float(self.txt_B.text())
            alpha_deg = parse_float(self.txt_alpha_deg.text())
        except ValueError:
            raise ValueError(tr("calc.error.invalid_ab_alpha"))

        if A <= 0:
            raise ValueError(tr("calc.error.a_positive"))

        if B <= 0:
            raise ValueError(tr("calc.error.b_positive"))

        if alpha_deg < 0 or alpha_deg >= 89.0:
            raise ValueError(tr("calc.error.alpha_range"))

        return A, B, alpha_deg
