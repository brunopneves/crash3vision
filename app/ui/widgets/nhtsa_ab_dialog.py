from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QGroupBox,
    QMessageBox,
    QScrollArea,
    QWidget,
    QRadioButton,
)

from PySide6.QtCore import QLocale
from app.i18n import tr, get_language
from app.core.number_format import parse_float, format_float
from app.core.nhtsa_ab_calc import compute_ab_from_report
from app.core.nhtsa_ab_library import build_record, upsert_record, DEFAULT_LIBRARY_PATH

CONFIG_TO_META = {
    "rigid_frontal_barrier": {
        "barrier_type": "rigid",
        "impact_direction": "front",
        "overlap_pct": "100",
    },
    "deformable_offset_barrier": {
        "barrier_type": "deformable",
        "impact_direction": "front",
        "overlap_pct": "40",
    },
    "rigid_angled_barrier": {
        "barrier_type": "rigid",
        "impact_direction": "front",
        "overlap_pct": "100",
    },
    "side_moving_deformable_barrier": {
        "barrier_type": "deformable",
        "impact_direction": "side",
        "overlap_pct": "N/A",
    },
    "rigid_pole_side_impact": {
        "barrier_type": "pole",
        "impact_direction": "side",
        "overlap_pct": "N/A",
    },
    "rear_rigid_barrier": {
        "barrier_type": "rigid",
        "impact_direction": "rear",
        "overlap_pct": "100",
    },
    "rear_deformable_barrier": {
        "barrier_type": "deformable",
        "impact_direction": "rear",
        "overlap_pct": "70",
    },
}


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is not None:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parents[3] / relative_path


class NhtsaAbDialog(QDialog):
    LIB_PATH = resource_path("app/data/nhtsa_ab_library.json")

    def __init__(self, parent=None, initial_data: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("nhtsa.dialog.title"))
        self.resize(700, 600)

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        root = QVBoxLayout(container)

        scroll.setWidget(container)

        main_layout.addWidget(scroll)
        container.setMinimumWidth(700)

        # ---------- Test identification ----------
        grp_id = QGroupBox(tr("nhtsa.group.identification"))
        id_form = QFormLayout(grp_id)

        self.txt_test_agency = QLineEdit("NHTSA")
        self.txt_test_agency.setReadOnly(True)

        self.txt_test_number = QLineEdit()
        self.txt_report_number = QLineEdit()
        self.txt_make = QLineEdit()
        self.txt_model = QLineEdit()

        self.spn_year = QSpinBox()
        self.spn_year.setRange(1900, 2100)
        self.spn_year.setSpecialValueText("-")
        self.spn_year.setValue(self.spn_year.minimum())

        self.cmb_test_type = QComboBox()
        self.cmb_test_type.addItem(tr("nhtsa.test_type.frontal"), "frontal")
        self.cmb_test_type.addItem(tr("nhtsa.test_type.side"), "side")
        self.cmb_test_type.addItem(tr("nhtsa.test_type.rear"), "rear")

        self.cmb_test_configuration = QComboBox()
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.rigid_frontal_barrier"),
            "rigid_frontal_barrier",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.deformable_offset_barrier"),
            "deformable_offset_barrier",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.rigid_angled_barrier"),
            "rigid_angled_barrier",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.side_moving_deformable_barrier"),
            "side_moving_deformable_barrier",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.rigid_pole_side_impact"),
            "rigid_pole_side_impact",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.rear_rigid_barrier"),
            "rear_rigid_barrier",
        )
        self.cmb_test_configuration.addItem(
            tr("nhtsa.config.rear_deformable_barrier"),
            "rear_deformable_barrier",
        )

        self.cmb_barrier_type = QComboBox()
        self.cmb_barrier_type.addItem(tr("nhtsa.barrier_type.rigid"), "rigid")
        self.cmb_barrier_type.addItem(tr("nhtsa.barrier_type.deformable"), "deformable")
        self.cmb_barrier_type.addItem(tr("nhtsa.barrier_type.pole"), "pole")
        self.cmb_barrier_type.setEnabled(False)

        self.cmb_overlap_pct = QComboBox()
        self.cmb_overlap_pct.addItem(tr("nhtsa.overlap.na"), "N/A")
        self.cmb_overlap_pct.addItem("40", "40")
        self.cmb_overlap_pct.addItem("70", "70")
        self.cmb_overlap_pct.addItem("100", "100")
        self.cmb_overlap_pct.setEnabled(False)

        self.cmb_impact_direction = QComboBox()
        self.cmb_impact_direction.addItem(tr("nhtsa.direction.front"), "front")
        self.cmb_impact_direction.addItem(tr("nhtsa.direction.side"), "side")
        self.cmb_impact_direction.addItem(tr("nhtsa.direction.rear"), "rear")
        self.cmb_impact_direction.setEnabled(False)

        self.txt_test_label = QLineEdit()
        self.txt_test_label.setReadOnly(True)
        self._saved_record = None

        id_form.addRow(tr("nhtsa.field.test_agency"), self.txt_test_agency)
        id_form.addRow(tr("nhtsa.field.test_number"), self.txt_test_number)
        id_form.addRow(tr("nhtsa.field.report_number"), self.txt_report_number)
        id_form.addRow(tr("nhtsa.field.make"), self.txt_make)
        id_form.addRow(tr("nhtsa.field.model"), self.txt_model)
        id_form.addRow(tr("nhtsa.field.year"), self.spn_year)
        id_form.addRow(tr("nhtsa.field.test_type"), self.cmb_test_type)
        id_form.addRow(
            tr("nhtsa.field.test_configuration"), self.cmb_test_configuration
        )
        id_form.addRow(tr("nhtsa.field.barrier_type"), self.cmb_barrier_type)
        id_form.addRow(tr("nhtsa.field.overlap_pct"), self.cmb_overlap_pct)
        id_form.addRow(tr("nhtsa.field.impact_direction"), self.cmb_impact_direction)
        id_form.addRow(tr("nhtsa.field.test_label"), self.txt_test_label)

        root.addWidget(grp_id)

        # ---------- Test inputs ----------
        grp_input = QGroupBox(tr("nhtsa.group.inputs"))
        input_form = QFormLayout(grp_input)

        self.spn_impact_speed_mps = QDoubleSpinBox()
        self.spn_impact_speed_mps.setRange(0.0, 250.0)
        self.spn_impact_speed_mps.setDecimals(3)
        self.spn_impact_speed_mps.setSingleStep(0.5)
        self.spn_impact_speed_mps.setValue(56.0)

        self.spn_velocity_change_mps = QDoubleSpinBox()
        self.spn_velocity_change_mps.setRange(0.0, 250.0)
        self.spn_velocity_change_mps.setDecimals(3)
        self.spn_velocity_change_mps.setSingleStep(0.5)
        self.spn_velocity_change_mps.setValue(56.0)

        self.spn_impact_angle_deg = QDoubleSpinBox()
        self.spn_impact_angle_deg.setRange(0.0, 360.0)
        self.spn_impact_angle_deg.setDecimals(0)
        self.spn_impact_angle_deg.setSingleStep(5)
        self.spn_impact_angle_deg.setValue(0)

        self.spn_vehicle_mass_kg = QDoubleSpinBox()
        self.spn_vehicle_mass_kg.setRange(0.0, 5000.0)
        self.spn_vehicle_mass_kg.setDecimals(0)
        self.spn_vehicle_mass_kg.setSingleStep(10)

        self.spn_b0_mps = QDoubleSpinBox()
        self.spn_b0_mps.setRange(0.0, 20.0)
        self.spn_b0_mps.setDecimals(2)
        self.spn_b0_mps.setSingleStep(0.1)
        self.spn_b0_mps.setValue(2.2)

        self.spn_L_m = QDoubleSpinBox()
        self.spn_L_m.setRange(0.0, 10.0)
        self.spn_L_m.setDecimals(3)
        self.spn_L_m.setSingleStep(0.01)

        input_form.addRow(
            tr("nhtsa.field.impact_speed_mps"),
            self.spn_impact_speed_mps,
        )
        input_form.addRow(
            tr("nhtsa.field.velocity_change_mps"),
            self.spn_velocity_change_mps,
        )
        input_form.addRow(
            tr("nhtsa.field.impact_angle_deg"),
            self.spn_impact_angle_deg,
        )
        input_form.addRow(tr("nhtsa.field.vehicle_mass_kg"), self.spn_vehicle_mass_kg)
        input_form.addRow(tr("nhtsa.field.b0_mps"), self.spn_b0_mps)
        input_form.addRow(tr("nhtsa.field.L_m"), self.spn_L_m)

        root.addWidget(grp_input)

        # ---------- Derived speeds ----------
        grp_speed = QGroupBox(tr("nhtsa.group.derived_speeds"))
        speed_form = QFormLayout(grp_speed)

        self.lbl_rebound_speed = QLabel("-")
        self.lbl_damage_speed = QLabel("-")

        self.rb_speed_impact = QRadioButton(tr("nhtsa.speed_basis.impact"))
        self.rb_speed_damage = QRadioButton(tr("nhtsa.speed_basis.damage"))
        self.rb_speed_impact.setChecked(True)

        row_basis = QHBoxLayout()
        row_basis.addWidget(self.rb_speed_impact)
        row_basis.addWidget(self.rb_speed_damage)

        speed_form.addRow(tr("nhtsa.output.rebound_speed_mps"), self.lbl_rebound_speed)
        speed_form.addRow(tr("nhtsa.output.damage_speed_mps"), self.lbl_damage_speed)
        speed_form.addRow(tr("nhtsa.field.speed_basis"), row_basis)

        root.addWidget(grp_speed)

        # ---------- Crush ----------
        grp_crush = QGroupBox(tr("nhtsa.group.crush"))
        crush_form = QFormLayout(grp_crush)

        self.c_spins: list[QDoubleSpinBox] = []
        for i in range(1, 7):
            spn = QDoubleSpinBox()
            spn.setRange(0.0, 2.0)
            spn.setDecimals(3)
            spn.setSingleStep(0.01)
            self.c_spins.append(spn)
            crush_form.addRow(tr("nhtsa.field.c_value", index=i), spn)

        self._apply_numeric_locale()

        root.addWidget(grp_crush)

        # ---------- Outputs ----------
        grp_out = QGroupBox(tr("nhtsa.group.outputs"))
        out_form = QFormLayout(grp_out)

        self.lbl_area = QLabel("-")
        self.lbl_cmean = QLabel("-")
        self.lbl_b1 = QLabel("-")
        self.lbl_A = QLabel("-")
        self.lbl_B = QLabel("-")

        out_form.addRow(tr("nhtsa.output.crush_area_m2"), self.lbl_area)
        out_form.addRow(tr("nhtsa.output.c_mean_m"), self.lbl_cmean)
        out_form.addRow(tr("nhtsa.output.b1_per_s"), self.lbl_b1)
        out_form.addRow(tr("nhtsa.output.A_n_per_m"), self.lbl_A)
        out_form.addRow(tr("nhtsa.output.B_n_per_m2"), self.lbl_B)

        root.addWidget(grp_out)

        # ---------- Buttons ----------
        row_btn = QHBoxLayout()
        self.btn_compute = QPushButton(tr("nhtsa.button.compute"))
        self.btn_apply = QPushButton(tr("nhtsa.button.apply"))
        self.btn_save = QPushButton(tr("nhtsa.button.save"))
        self.btn_cancel = QPushButton(tr("nhtsa.button.cancel"))

        self.btn_apply.setEnabled(False)
        self.btn_save.setEnabled(False)

        row_btn.addWidget(self.btn_compute)
        row_btn.addWidget(self.btn_apply)
        row_btn.addWidget(self.btn_save)
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_cancel)

        root.addLayout(row_btn)

        # signals
        self.cmb_test_configuration.currentIndexChanged.connect(
            self._sync_meta_from_config
        )
        self.spn_impact_speed_mps.valueChanged.connect(self._update_test_label)
        self.spn_impact_speed_mps.valueChanged.connect(self._update_derived_speeds)
        self.spn_velocity_change_mps.valueChanged.connect(self._update_derived_speeds)
        self.spn_impact_angle_deg.valueChanged.connect(self._update_test_label)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_compute.clicked.connect(self._on_compute)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_save.clicked.connect(self._on_save)

        self._last_result: dict[str, object] | None = None

        if initial_data:
            self._load_initial_data(initial_data)

        self._sync_meta_from_config()
        self._update_derived_speeds()

        # Connect after initial restoration so saved results remain available.
        for spin in (
            self.spn_vehicle_mass_kg,
            self.spn_L_m,
            *self.c_spins,
            self.spn_impact_speed_mps,
            self.spn_velocity_change_mps,
            self.spn_b0_mps,
        ):
            spin.valueChanged.connect(self._clear_result)
        self.rb_speed_damage.toggled.connect(self._clear_result)

    def _apply_numeric_locale(self) -> None:
        locale = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)

        if get_language() == "en":
            locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

        for spn in (
            self.spn_impact_speed_mps,
            self.spn_velocity_change_mps,
            self.spn_impact_angle_deg,
            self.spn_vehicle_mass_kg,
            self.spn_b0_mps,
            self.spn_L_m,
            *self.c_spins,
        ):
            spn.setLocale(locale)

    def _sync_meta_from_config(self) -> None:
        config_key = self.cmb_test_configuration.currentData()
        meta = CONFIG_TO_META.get(config_key, {})

        barrier = meta.get("barrier_type")
        if barrier is not None:
            idx = self.cmb_barrier_type.findData(barrier)
            if idx >= 0:
                self.cmb_barrier_type.setCurrentIndex(idx)

        overlap = meta.get("overlap_pct")
        if overlap is not None:
            idx = self.cmb_overlap_pct.findData(overlap)
            if idx >= 0:
                self.cmb_overlap_pct.setCurrentIndex(idx)

        direction = meta.get("impact_direction")
        if direction is not None:
            idx = self.cmb_impact_direction.findData(direction)
            if idx >= 0:
                self.cmb_impact_direction.setCurrentIndex(idx)

        if direction == "front":
            idx = self.cmb_test_type.findData("frontal")
            if idx >= 0:
                self.cmb_test_type.setCurrentIndex(idx)
        elif direction == "side":
            idx = self.cmb_test_type.findData("side")
            if idx >= 0:
                self.cmb_test_type.setCurrentIndex(idx)
        elif direction == "rear":
            idx = self.cmb_test_type.findData("rear")
            if idx >= 0:
                self.cmb_test_type.setCurrentIndex(idx)

        self._update_test_label()

    def _update_test_label(self) -> None:
        config_text = self.cmb_test_configuration.currentText()
        speed = f"{format_float(self.spn_impact_speed_mps.value(), 3)} km/h"
        angle = f"{format_float(self.spn_impact_angle_deg.value(), 1)} deg"
        overlap = self.cmb_overlap_pct.currentText()
        self.txt_test_label.setText(
            tr(
                "nhtsa.auto_test_label",
                config=config_text,
                speed=speed,
                angle=angle,
                overlap=overlap,
            )
        )

    def _update_derived_speeds(self) -> None:
        impact_speed_mps = self._kmh_to_mps(self.spn_impact_speed_mps.value())
        velocity_change_mps = self._kmh_to_mps(self.spn_velocity_change_mps.value())

        rebound_speed_mps = max(0.0, velocity_change_mps - impact_speed_mps)
        damage_speed_mps = max(0.0, impact_speed_mps**2 - rebound_speed_mps**2) ** 0.5

        self.lbl_rebound_speed.setText(format_float(rebound_speed_mps * 3.6, 6))
        self.lbl_damage_speed.setText(format_float(damage_speed_mps * 3.6, 6))

    def _to_float(self, value: object, default: float = 0.0) -> float:
        return parse_float(value, default=default)

    def _kmh_to_mps(self, value_kmh: float) -> float:
        return float(value_kmh) / 3.6

    def _mps_to_kmh(self, value_mps: object) -> float:
        return self._to_float(value_mps) * 3.6

    def get_input_data(self) -> dict:
        year = (
            None
            if self.spn_year.value() == self.spn_year.minimum()
            else self.spn_year.value()
        )

        return {
            "test_agency": self.txt_test_agency.text().strip(),
            "test_number": self.txt_test_number.text().strip() or None,
            "report_number": self.txt_report_number.text().strip() or None,
            "make": self.txt_make.text().strip() or None,
            "model": self.txt_model.text().strip() or None,
            "year": year,
            "test_type": self.cmb_test_type.currentData(),
            "test_configuration": self.cmb_test_configuration.currentData(),
            "barrier_type": self.cmb_barrier_type.currentData(),
            "overlap_pct": self.cmb_overlap_pct.currentData(),
            "impact_direction": self.cmb_impact_direction.currentData(),
            "test_label": self.txt_test_label.text().strip(),
            "impact_speed_mps": self._kmh_to_mps(self.spn_impact_speed_mps.value()),
            "velocity_change_mps": self._kmh_to_mps(
                self.spn_velocity_change_mps.value()
            ),
            "impact_angle_deg": self.spn_impact_angle_deg.value(),
            "speed_basis": ("damage" if self.rb_speed_damage.isChecked() else "impact"),
            "vehicle_mass_kg": self.spn_vehicle_mass_kg.value(),
            "b0_mps": self.spn_b0_mps.value(),
            "L_m": self.spn_L_m.value(),
            "c_values_m": [spn.value() for spn in self.c_spins],
        }

    def _clear_result(self) -> None:
        self._last_result = None
        self.btn_apply.setEnabled(False)
        self.btn_save.setEnabled(False)
        for label in (self.lbl_area, self.lbl_cmean, self.lbl_b1, self.lbl_A, self.lbl_B):
            label.setText("-")

    def _on_compute(self) -> None:
        self._clear_result()
        try:
            data = self.get_input_data()

            errors = self._validate_inputs(data)
            if errors:
                QMessageBox.warning(
                    self,
                    tr("msg.warning"),
                    "\n".join(errors),
                )
                return

            result = compute_ab_from_report(
                L_m=data["L_m"],
                c_values_m=data["c_values_m"],
                vehicle_mass_kg=data["vehicle_mass_kg"],
                impact_speed_mps=data["impact_speed_mps"],
                velocity_change_mps=data["velocity_change_mps"],
                b0_mps=data["b0_mps"],
                speed_basis=data["speed_basis"],
            )

            crush_area_m2 = self._to_float(result["crush_area_m2"])
            c_mean_m = self._to_float(result["c_mean_m"])
            b1_per_s = self._to_float(result["b1_per_s"])
            A_n_per_m = self._to_float(result["A_n_per_m"])
            B_n_per_m2 = self._to_float(result["B_n_per_m2"])
            if A_n_per_m <= 0 or B_n_per_m2 <= 0:
                QMessageBox.warning(
                    self, tr("msg.warning"), tr("nhtsa.error.nonpositive_ab")
                )
                return
            rebound_speed_mps = self._to_float(result["rebound_speed_mps"])
            damage_speed_mps = self._to_float(result["damage_speed_mps"])

            self.lbl_area.setText(format_float(crush_area_m2, 6))
            self.lbl_cmean.setText(format_float(c_mean_m, 6))
            self.lbl_b1.setText(format_float(b1_per_s, 6))
            self.lbl_A.setText(format_float(A_n_per_m, 6))
            self.lbl_B.setText(format_float(B_n_per_m2, 6))
            self.lbl_rebound_speed.setText(format_float(rebound_speed_mps * 3.6, 6))
            self.lbl_damage_speed.setText(format_float(damage_speed_mps * 3.6, 6))

            self._last_result = result
            self.btn_apply.setEnabled(True)
            self.btn_save.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, tr("msg.error"), str(e))

    def _on_apply(self) -> None:
        if self._last_result is None:
            QMessageBox.warning(
                self, tr("msg.warning"), tr("nhtsa.error.compute_first")
            )
            return

        self.accept()

    def _on_save(self) -> None:
        if self._last_result is None:
            QMessageBox.warning(
                self, tr("msg.warning"), tr("nhtsa.error.compute_first")
            )
            return

        data = self.get_input_data()

        b1_per_s = self._to_float(self._last_result["b1_per_s"])
        crush_area_m2 = self._to_float(self._last_result["crush_area_m2"])
        c_mean_m = self._to_float(self._last_result["c_mean_m"])
        A_n_per_m = self._to_float(self._last_result["A_n_per_m"])
        B_n_per_m2 = self._to_float(self._last_result["B_n_per_m2"])

        record = build_record(
            test_number=data["test_number"],
            report_number=data["report_number"],
            make=data["make"],
            model=data["model"],
            year=data["year"],
            test_agency=data["test_agency"],
            test_type=data["test_type"],
            test_configuration=data["test_configuration"],
            barrier_type=data["barrier_type"],
            overlap_pct=data["overlap_pct"],
            impact_direction=data["impact_direction"],
            test_label=data["test_label"],
            test_speed_mps=data["impact_speed_mps"],
            # NOVOS CAMPOS
            impact_speed_mps=data["impact_speed_mps"],
            velocity_change_mps=data["velocity_change_mps"],
            rebound_speed_mps=self._to_float(self._last_result["rebound_speed_mps"]),
            damage_speed_mps=self._to_float(self._last_result["damage_speed_mps"]),
            speed_used_mps=self._to_float(self._last_result["speed_used_mps"]),
            speed_basis=data["speed_basis"],
            impact_angle_deg=data["impact_angle_deg"],
            vehicle_mass_kg=data["vehicle_mass_kg"],
            b0=data["b0_mps"],
            b1=b1_per_s,
            L_m=data["L_m"],
            c_m={f"C{i+1}": v for i, v in enumerate(data["c_values_m"])},
            crush_area_m2=crush_area_m2,
            c_mean_m=c_mean_m,
            A_n_per_m=A_n_per_m,
            B_n_per_m2=B_n_per_m2,
            source_reference=data["report_number"],
            notes="",
        )

        try:
            upsert_record(DEFAULT_LIBRARY_PATH, record)
            self._saved_record = record
            QMessageBox.information(
                self, tr("msg.success"), tr("nhtsa.saved_to_library")
            )
        except Exception as e:
            QMessageBox.warning(self, tr("msg.error"), str(e))

    def _load_initial_data(self, data: dict) -> None:
        self.txt_test_number.setText(data.get("test_number") or "")
        self.txt_report_number.setText(data.get("report_number") or "")
        self.txt_make.setText(data.get("make") or "")
        self.txt_model.setText(data.get("model") or "")

        year = data.get("year")
        if year is not None:
            self.spn_year.setValue(int(year))

        idx = self.cmb_test_type.findData(data.get("test_type"))
        if idx >= 0:
            self.cmb_test_type.setCurrentIndex(idx)

        idx = self.cmb_test_configuration.findData(data.get("test_configuration"))
        if idx >= 0:
            self.cmb_test_configuration.setCurrentIndex(idx)

        idx = self.cmb_barrier_type.findData(data.get("barrier_type"))
        if idx >= 0:
            self.cmb_barrier_type.setCurrentIndex(idx)

        idx = self.cmb_overlap_pct.findData(data.get("overlap_pct"))
        if idx >= 0:
            self.cmb_overlap_pct.setCurrentIndex(idx)

        idx = self.cmb_impact_direction.findData(data.get("impact_direction"))
        if idx >= 0:
            self.cmb_impact_direction.setCurrentIndex(idx)

        if data.get("test_label"):
            self.txt_test_label.setText(str(data["test_label"]))

        if data.get("impact_speed_mps") is not None:
            self.spn_impact_speed_mps.setValue(
                self._mps_to_kmh(data["impact_speed_mps"])
            )
        elif data.get("test_speed_mps") is not None:
            self.spn_impact_speed_mps.setValue(self._mps_to_kmh(data["test_speed_mps"]))

        if data.get("velocity_change_mps") is not None:
            self.spn_velocity_change_mps.setValue(
                self._mps_to_kmh(data["velocity_change_mps"])
            )

        if data.get("impact_angle_deg") is not None:
            self.spn_impact_angle_deg.setValue(self._to_float(data["impact_angle_deg"]))

        if data.get("vehicle_mass_kg") is not None:
            self.spn_vehicle_mass_kg.setValue(self._to_float(data["vehicle_mass_kg"]))

        if data.get("b0_mps") is not None:
            self.spn_b0_mps.setValue(self._to_float(data["b0_mps"]))

        if data.get("L_m") is not None:
            self.spn_L_m.setValue(self._to_float(data["L_m"]))

        c_values = data.get("c_values_m") or []
        for i, val in enumerate(c_values[:6]):
            self.c_spins[i].setValue(self._to_float(val))

        self._update_test_label()

        if data.get("crush_area_m2") is not None:
            self.lbl_area.setText(format_float(data["crush_area_m2"], 6))
        if data.get("c_mean_m") is not None:
            self.lbl_cmean.setText(format_float(data["c_mean_m"], 6))
        if data.get("b1_per_s") is not None:
            self.lbl_b1.setText(format_float(data["b1_per_s"], 6))
        if data.get("A_n_per_m") is not None:
            self.lbl_A.setText(format_float(data["A_n_per_m"], 6))
        if data.get("B_n_per_m2") is not None:
            self.lbl_B.setText(format_float(data["B_n_per_m2"], 6))

        speed_basis = data.get("speed_basis")
        if speed_basis == "damage":
            self.rb_speed_damage.setChecked(True)
        else:
            self.rb_speed_impact.setChecked(True)

        if data.get("rebound_speed_mps") is not None:
            self.lbl_rebound_speed.setText(
                format_float(self._mps_to_kmh(data["rebound_speed_mps"]), 6)
            )

        if data.get("damage_speed_mps") is not None:
            self.lbl_damage_speed.setText(
                format_float(self._mps_to_kmh(data["damage_speed_mps"]), 6)
            )
        else:
            self._update_derived_speeds()

        if (
            data.get("crush_area_m2") is not None
            and data.get("c_mean_m") is not None
            and data.get("b1_per_s") is not None
            and data.get("A_n_per_m") is not None
            and data.get("B_n_per_m2") is not None
        ):
            self._last_result = {
                "crush_area_m2": self._to_float(data.get("crush_area_m2")),
                "c_mean_m": self._to_float(data.get("c_mean_m")),
                "b1_per_s": self._to_float(data.get("b1_per_s")),
                "A_n_per_m": self._to_float(data.get("A_n_per_m")),
                "B_n_per_m2": self._to_float(data.get("B_n_per_m2")),
                "impact_speed_mps": self._to_float(
                    data.get("impact_speed_mps", data.get("test_speed_mps")),
                    0.0,
                ),
                "velocity_change_mps": (
                    None
                    if data.get("velocity_change_mps") is None
                    else self._to_float(data.get("velocity_change_mps"))
                ),
                "rebound_speed_mps": self._to_float(
                    data.get("rebound_speed_mps"),
                    0.0,
                ),
                "damage_speed_mps": self._to_float(
                    data.get("damage_speed_mps"),
                    0.0,
                ),
                "speed_used_mps": self._to_float(
                    data.get("speed_used_mps"),
                    0.0,
                ),
                "speed_basis": str(data.get("speed_basis", "impact")),
            }
            if self._last_result["A_n_per_m"] <= 0 or self._last_result["B_n_per_m2"] <= 0:
                self._clear_result()
                QMessageBox.warning(
                    self, tr("msg.warning"), tr("nhtsa.error.nonpositive_ab")
                )
                return
            self.btn_apply.setEnabled(True)

    def _validate_inputs(self, data: dict) -> list[str]:
        errors: list[str] = []

        c_values = data["c_values_m"]
        L = data["L_m"]
        v_impact = data["impact_speed_mps"]
        v_change = data["velocity_change_mps"]
        mass = data["vehicle_mass_kg"]

        if L <= 0:
            errors.append(tr("nhtsa.error.invalid_L"))

        if mass <= 0:
            errors.append(tr("nhtsa.error.invalid_mass"))

        if v_impact <= 0:
            errors.append(tr("nhtsa.error.invalid_impact_speed"))

        if v_change <= 0:
            errors.append(tr("nhtsa.error.invalid_velocity_change"))

        if any(c < 0 for c in c_values):
            errors.append(tr("nhtsa.error.invalid_c_values"))

        if all(c == 0 for c in c_values):
            errors.append(tr("nhtsa.error.all_c_zero"))

        if c_values and max(c_values) > L:
            errors.append(tr("nhtsa.error.c_gt_L"))

        if not (1 <= v_impact <= 40):
            errors.append(tr("nhtsa.error.impact_speed_out_of_range"))

        if not (1 <= v_change <= 80):
            errors.append(tr("nhtsa.error.velocity_change_out_of_range"))

        if v_change < v_impact:
            errors.append(tr("nhtsa.error.velocity_change_lt_impact"))

        if not (300 <= mass <= 4000):
            errors.append(tr("nhtsa.error.mass_out_of_range"))

        return errors
