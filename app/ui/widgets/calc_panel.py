from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction

from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFrame,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QMenu,
    QSizePolicy,
    QToolButton,
)

from app.core.nhtsa_ab_library import (
    DEFAULT_LIBRARY_PATH,
    list_records,
    load_record_file,
    save_record_file,
)
from app.i18n import tr
from app.core.number_format import format_display_number, parse_float, relocalize_decimal_input
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
    NHTSA_AB_SOURCES = ("nhtsa_library", "nhtsa_file", "nhtsa_report")
    LOCKED_AB_SOURCES = (*NHTSA_AB_SOURCES, "generic_class")

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("calculationPanel")

        self.main = main_window
        self._stiffness_classes = self._load_stiffness_classes()
        self._profile_dialog: CrushProfileDialog | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("calculationTitle")
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        self.grp_source = QGroupBox()
        src_layout = QVBoxLayout(self.grp_source)
        self.grp_params = QGroupBox()
        params_layout = QGridLayout(self.grp_params)
        self.grp_calc = QGroupBox()
        calc_layout = QVBoxLayout(self.grp_calc)
        for card in (self.grp_source, self.grp_params, self.grp_calc):
            card.setProperty("calculationCard", True)
            card.layout().setContentsMargins(12, 11, 12, 11)
            card.layout().setSpacing(8)

        self.lbl_source_heading = QLabel()
        self.lbl_params_heading = QLabel()
        self.lbl_calc_heading = QLabel()
        for heading in (self.lbl_source_heading, self.lbl_params_heading, self.lbl_calc_heading):
            heading.setProperty("calculationHeading", True)
            heading.setWordWrap(True)
        src_layout.addWidget(self.lbl_source_heading)
        params_layout.addWidget(self.lbl_params_heading, 0, 0, 1, 2)
        calc_layout.addWidget(self.lbl_calc_heading)

        self.lbl_generic_class = QLabel(tr("calc.generic_class"))
        self.cmb_class = QComboBox()
        self.cmb_class.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lbl_generic_class.setBuddy(self.cmb_class)
        self.cmb_class.addItem(tr("calc.manual_entry"), None)
        for class_name in sorted(self._stiffness_classes):
            self.cmb_class.addItem(class_name, class_name)
        self.cmb_class.currentIndexChanged.connect(self._on_class_changed)
        src_layout.addWidget(self.lbl_generic_class)
        src_layout.addWidget(self.cmb_class)

        self.btn_ab_menu = QPushButton(tr("calc.ab_menu"))
        self.btn_ab_menu.setProperty("uiRole", "secondary")
        self.btn_ab_menu.setProperty("panelAction", True)
        self.btn_ab_menu.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
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

        self.btn_compute_ab_nhtsa = QPushButton(tr("calc.compute_ab_from_nhtsa"))
        self.btn_edit_ab_nhtsa = QPushButton(tr("calc.edit_ab_from_nhtsa"))
        for button in (self.btn_compute_ab_nhtsa, self.btn_edit_ab_nhtsa):
            button.setProperty("uiRole", "secondary")
            button.setProperty("panelAction", True)
            src_layout.addWidget(button)

        self.lbl_ab_source = QLabel(tr("calc.ab_source_default"))
        self.lbl_ab_source.setObjectName("calculationSource")
        self.lbl_ab_source.setTextFormat(Qt.TextFormat.PlainText)
        src_layout.addWidget(self.lbl_ab_source)

        self.lbl_a = QLabel(f"{tr('calc.a_coefficient')} ({self.A_UNIT})")
        self.txt_A = QLineEdit()
        self.txt_A.setPlaceholderText("65637")
        self.lbl_b = QLabel(f"{tr('calc.b_coefficient')} ({self.B_UNIT})")
        self.txt_B = QLineEdit()
        self.txt_B.setPlaceholderText("856265")
        self.lbl_alpha = QLabel(tr("calc.alpha_deg"))
        self.txt_alpha_deg = QLineEdit(format_display_number(0.0))
        self.lbl_vehicle_mass = QLabel(tr("calc.vehicle_mass"))
        self.txt_vehicle_mass = QLineEdit()
        self.txt_vehicle_mass.setPlaceholderText("1700")

        for label, field, row, column in (
            (self.lbl_a, self.txt_A, 1, 0),
            (self.lbl_b, self.txt_B, 1, 1),
            (self.lbl_alpha, self.txt_alpha_deg, 3, 0),
            (self.lbl_vehicle_mass, self.txt_vehicle_mass, 3, 1),
        ):
            label.setBuddy(field)
            label.setProperty("calculationFieldLabel", True)
            field.setProperty("calculationInput", True)
            params_layout.addWidget(label, row, column)
            params_layout.addWidget(field, row + 1, column)
        for column in range(2):
            params_layout.setColumnStretch(column, 1)
        self.lbl_mass_hint = QLabel(tr("calc.mass_hint"))
        params_layout.addWidget(self.lbl_mass_hint, 5, 0, 1, 2)

        self.btn_compute = QPushButton(tr("calc.compute_energy"))
        self.btn_compute.setProperty("uiRole", "primary")
        self.btn_compute.setProperty("panelAction", True)
        self.btn_compute.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_energy = QLabel(tr("calc.total_energy_default"))
        self.lbl_speed = QLabel(tr("calc.damage_speed_default"))
        calc_layout.addWidget(self.btn_compute)
        outputs = QHBoxLayout()
        outputs.setSpacing(8)
        for label in (self.lbl_energy, self.lbl_speed):
            label.setProperty("calculationOutput", True)
            outputs.addWidget(label, 1, Qt.AlignmentFlag.AlignTop)
        calc_layout.addLayout(outputs)

        self.btn_show_profile = QPushButton(tr("calc.show_crush_profile"))
        self.btn_show_profile.setProperty("uiRole", "secondary")
        self.btn_show_profile.setProperty("panelAction", True)
        self.btn_toggle_details = QToolButton()
        self.main._style_disclosure(self.btn_toggle_details)
        self.btn_toggle_details.setProperty("panelDisclosure", True)
        self.btn_toggle_details.toggled.connect(self._refresh_details_visibility)
        self.details = QFrame()
        self.details.setProperty("calculationCard", True)
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(12, 11, 12, 11)
        details_layout.setSpacing(8)
        self.lbl_formula_hint = QLabel(tr("calc.formula_hint"))
        self.lbl_formula_hint.setObjectName("calculationFormula")
        self.lbl_ab_details = QLabel()
        self.lbl_ab_details.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_ab_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_layout.addWidget(self.lbl_formula_hint)
        details_layout.addWidget(self.lbl_ab_details)

        for label in (
            self.lbl_generic_class, self.lbl_ab_source, self.lbl_a, self.lbl_b, self.lbl_alpha,
            self.lbl_vehicle_mass, self.lbl_mass_hint,
            self.lbl_energy, self.lbl_speed, self.lbl_formula_hint, self.lbl_ab_details,
        ):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        for widget in (
            self.grp_source, self.grp_params, self.grp_calc,
            self.btn_show_profile, self.btn_toggle_details, self.details,
        ):
            layout.addWidget(widget)

        # ---------------- Signals ----------------
        self.act_load_ab_library.triggered.connect(self._on_load_ab_from_library)
        self.act_import_ab_file.triggered.connect(self._on_import_ab_file)
        self.act_export_ab_file.triggered.connect(self._on_export_ab_file)

        self.btn_compute.clicked.connect(self._on_calculate)
        self.btn_show_profile.clicked.connect(self._on_show_profile)
        self.btn_compute_ab_nhtsa.clicked.connect(self._on_compute_ab_from_nhtsa)
        self.btn_edit_ab_nhtsa.clicked.connect(self._on_edit_ab_from_nhtsa)

        self._parameter_fields = (
            (self.txt_A, "crash3_A"),
            (self.txt_B, "crash3_B"),
            (self.txt_alpha_deg, "crash3_alpha_deg"),
            (self.txt_vehicle_mass, "vehicle_mass_kg"),
        )
        self._on_class_changed()
        self.retranslate_ui()

        for field, attribute in self._parameter_fields:
            field.textChanged.connect(
                lambda text, attribute=attribute: self._on_parameter_changed(attribute, text)
            )

    def _set_coefficients(self, a: float, b: float) -> None:
        self.main.project.crash3_A = a
        self.main.project.crash3_B = b
        with QSignalBlocker(self.txt_A), QSignalBlocker(self.txt_B):
            self.txt_A.setText(self._format_parameter("crash3_A", a))
            self.txt_B.setText(self._format_parameter("crash3_B", b))
        self.main.workflow.invalidate_energy()

    @staticmethod
    def _format_parameter(attribute: str, value: float, language: str | None = None) -> str:
        if attribute in ("crash3_A", "crash3_B") and math.isfinite(value):
            compact = f"{value:.10g}"
            # Keep a decimal separator in grouped integers so they can be edited
            # unambiguously in either language.
            if "e" in compact or ("." in compact and round(value, 2) != value):
                return format_display_number(
                    value, 10, language=language, significant_digits=True,
                )
        return format_display_number(value, language=language)

    def restore_parameter_fields(self) -> None:
        project = self.main.project
        snapshot = project.ab_source_snapshot
        if project.ab_source_type in self.LOCKED_AB_SOURCES and isinstance(snapshot, dict):
            for attribute, key in (("crash3_A", "A_n_per_m"), ("crash3_B", "B_n_per_m2")):
                recorded = snapshot.get(key)
                if recorded is None:
                    continue
                try:
                    recorded = parse_float(recorded)
                except (ValueError, OverflowError):
                    recorded = math.nan
                if getattr(project, attribute) != recorded:
                    # Older projects could contain edited values with an unchanged source.
                    self._set_manual_ab_source()
                    break
        for field, attribute in self._parameter_fields:
            value = getattr(project, attribute)
            with QSignalBlocker(field):
                field.setText("" if value is None else self._format_parameter(attribute, value))
        self._refresh_ab_source_ui()

    def _set_manual_ab_source(self) -> None:
        project = self.main.project
        project.ab_source_type = "manual"
        project.ab_source_ref = None
        project.ab_source_label = "Manual entry"
        project.ab_source_reference = None
        project.ab_source_snapshot = None

    def _update_manual_snapshot(self) -> None:
        project = self.main.project
        try:
            a, b, alpha = self._parse_ab_alpha()
        except ValueError:
            project.ab_source_snapshot = None
        else:
            project.ab_source_snapshot = {"A_n_per_m": a, "B_n_per_m2": b, "alpha_deg": alpha}

    def _on_parameter_changed(self, attribute: str, text: str) -> None:
        try:
            value = parse_float(text)
        except ValueError:
            value = None
        if value is not None and not math.isfinite(value):
            value = None
        setattr(self.main.project, attribute, value)
        if attribute == "vehicle_mass_kg":
            self.main._vehicle_mass_kg = value
            self.main.workflow.invalidate_speed()
        else:
            if self.main.project.ab_source_type == "manual":
                self._update_manual_snapshot()
            self.main.workflow.invalidate_energy()
        self._refresh_ab_source_ui()

    def retranslate_ui(self) -> None:
        self.lbl_title.setText(tr("calc.group.title"))
        self.setAccessibleName(self.lbl_title.text())
        self.lbl_generic_class.setText(tr("calc.generic_class"))

        self.cmb_class.setItemText(0, tr("calc.manual_entry"))
        self.cmb_class.setPlaceholderText(tr("calc.ab_source_selected"))

        self.btn_ab_menu.setText(tr("calc.ab_menu"))
        self.btn_ab_menu.setToolTip(self.btn_ab_menu.text())
        self.act_load_ab_library.setText(tr("calc.ab_menu.load_library"))
        self.act_import_ab_file.setText(tr("calc.ab_menu.import_file"))
        self.act_export_ab_file.setText(tr("calc.ab_menu.export_file"))
        self.btn_compute_ab_nhtsa.setText(tr("calc.compute_ab_from_nhtsa"))
        self.btn_edit_ab_nhtsa.setText(tr("calc.edit_ab_from_nhtsa"))

        self.lbl_a.setText(f"{tr('calc.a_coefficient')} ({self.A_UNIT})")
        self.lbl_b.setText(f"{tr('calc.b_coefficient')} ({self.B_UNIT})")
        self.lbl_alpha.setText(tr("calc.alpha_deg"))
        self.lbl_formula_hint.setText(tr("calc.formula_hint"))
        self.refresh_compute_action()

        if self.main._total_energy is None:
            self.lbl_energy.setText(tr("calc.total_energy_default"))
        else:
            self.lbl_energy.setText(
                tr(
                    "calc.total_energy_value",
                    value=format_display_number(self.main._total_energy),
                    unit=self.ENERGY_UNIT,
                )
            )

        self.lbl_vehicle_mass.setText(tr("calc.vehicle_mass"))
        self.lbl_mass_hint.setText(tr("calc.mass_hint"))

        if self.main._damage_speed_kmh is None:
            self.lbl_speed.setText(tr("calc.damage_speed_default"))
        else:
            self.lbl_speed.setText(
                tr(
                    "calc.damage_speed_value",
                    value=format_display_number(self.main._damage_speed_kmh),
                    unit=self.SPEED_UNIT_KMH,
                )
            )

        for group, heading, key in (
            (self.grp_source, self.lbl_source_heading, "calc.group.source"),
            (self.grp_params, self.lbl_params_heading, "calc.group.params"),
            (self.grp_calc, self.lbl_calc_heading, "calc.group.calc"),
        ):
            heading.setText(tr(key))
            group.setAccessibleName(heading.text())

        self._refresh_ab_source_ui()
        self.btn_show_profile.setText(tr("calc.show_crush_profile"))
        self._refresh_details_visibility()

    def retranslate_numeric_fields(self, previous_language: str) -> None:
        project = self.main.project
        for field, attribute in self._parameter_fields:
            value = getattr(project, attribute)
            if value is None:
                continue
            text = field.text()
            if text == self._format_parameter(attribute, value, previous_language):
                translated = self._format_parameter(attribute, value)
            else:
                translated = relocalize_decimal_input(text, previous_language)
            if translated != text:
                with QSignalBlocker(field):
                    field.setText(translated)

    def _refresh_details_visibility(self) -> None:
        expanded = self.btn_toggle_details.isChecked()
        title = tr("calc.technical_details")
        self.btn_toggle_details.setText(f"{'▾' if expanded else '▸'} {title}")
        self.btn_toggle_details.setAccessibleName(title)
        self.details.setVisible(expanded)

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
        if self.cmb_class.currentIndex() < 0:
            return
        class_name = self.cmb_class.currentData()

        if not class_name:
            project = self.main.project
            if project.ab_source_type == "generic_class":
                project.crash3_A = project.crash3_B = None
                with QSignalBlocker(self.txt_A), QSignalBlocker(self.txt_B):
                    self.txt_A.clear()
                    self.txt_B.clear()
                self.main.workflow.invalidate_energy()
            self._set_manual_ab_source()
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

        self._set_coefficients(params["A"], params["B"])
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

        entries: list[tuple[str, dict]] = []
        missing_value = "—"

        for rec in records:
            vehicle = " ".join(
                str(value).strip()
                for value in (rec.get("make"), rec.get("model"), rec.get("year"))
                if value is not None and str(value).strip()
            ) or missing_value

            test_configuration = rec.get("test_configuration")
            if test_configuration:
                config_key = f"nhtsa.config.{test_configuration}"
                config_label = tr(config_key)
                if config_label == config_key:
                    config_label = str(test_configuration)
            else:
                config_label = missing_value

            test_speed = rec.get("test_speed_mps")
            try:
                speed_label = f"{format_display_number(float(test_speed), 3)} m/s"
            except (TypeError, ValueError):
                speed_label = missing_value

            test_number = rec.get("test_number") or missing_value
            report_number = rec.get("report_number") or missing_value
            a_val = rec.get("A_n_per_m")
            b_val = rec.get("B_n_per_m2")

            label = (
                f"{vehicle} | "
                f"{config_label} | "
                f"{speed_label} | "
                f"{tr('calc.ab_list.test')}={test_number} | "
                f"{tr('calc.ab_list.report')}={report_number}"
            )

            if a_val is None or b_val is None:
                label += " | [no A/B]"

            entries.append((label, rec))

        label_counts = Counter(label for label, _rec in entries)
        options: list[str] = []
        record_map: dict[str, dict] = {}

        for index, (label, rec) in enumerate(entries, start=1):
            display_label = label
            if label_counts[label] > 1:
                identifier = rec.get("id") or f"record-{index}"
                display_label = f"{label} | id={identifier}"

            unique_label = display_label
            suffix = 2
            while unique_label in record_map:
                unique_label = f"{display_label} #{suffix}"
                suffix += 1

            options.append(unique_label)
            record_map[unique_label] = rec

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

        self._set_coefficients(A_n_per_m, B_n_per_m2)

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
            mass = float(mass_kg)
            with QSignalBlocker(self.txt_vehicle_mass):
                self.txt_vehicle_mass.setText(format_display_number(mass))
            self.main._vehicle_mass_kg = self.main.project.vehicle_mass_kg = mass
            self.main.workflow.invalidate_speed()

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

        self._set_coefficients(A_n_per_m, B_n_per_m2)
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
            mass = float(mass_kg)
            with QSignalBlocker(self.txt_vehicle_mass):
                self.txt_vehicle_mass.setText(format_display_number(mass))
            self.main._vehicle_mass_kg = self.main.project.vehicle_mass_kg = mass
            self.main.workflow.invalidate_speed()

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

    def refresh_compute_action(self) -> None:
        if self.main.has_ees_result():
            key = "calc.view_result"
        elif not self.txt_vehicle_mass.text().strip():
            key = "calc.compute_energy"
        elif self.main.has_energy_result():
            key = "calc.compute_speed"
        else:
            key = "calc.compute_energy_and_ees"
        self.btn_compute.setText(tr(key))

    def _parse_mass(self) -> float:
        mass_kg = self.main._vehicle_mass_kg
        if mass_kg is None or not math.isfinite(mass_kg) or mass_kg <= 0:
            raise ValueError(tr("calc.error.invalid_vehicle_mass"))
        return mass_kg

    def _on_calculate(self) -> None:
        if self.main.has_ees_result():
            self.main._view_workflow_step("result")
            return
        if not self.txt_vehicle_mass.text().strip():
            self._on_compute()
            return
        try:
            mass_kg = self._parse_mass()
        except ValueError as error:
            QMessageBox.warning(self, tr("calc.speed.dialog.title"), str(error))
            return

        if not self.main.has_energy_result() and not self._on_compute():
            return
        if self._on_compute_speed(mass_kg):
            self.main._view_workflow_step("result")

    def _on_compute(self) -> bool:
        try:
            A, B, alpha_deg = self._parse_ab_alpha()
        except ValueError as e:
            QMessageBox.warning(
                self,
                tr("calc.dialog.title"),
                str(e),
            )
            return False

        self.main._sync_ui_to_project()

        try:
            result = self.main.calc.compute_crash3(A, B, alpha_deg)
            energy_j = float(result["total_energy_j"])
            if not math.isfinite(energy_j) or energy_j <= 0:
                raise ValueError(tr("calc.error.invalid_energy_result"))
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("calc.dialog.title"),
                str(e),
            )
            return False

        self.main.project.crash3_A = A
        self.main.project.crash3_B = B
        self.main.project.crash3_alpha_deg = alpha_deg
        self.main.project.crash3_units = "SI_N_per_m"

        self.lbl_energy.setText(
            tr(
                "calc.total_energy_value",
                value=format_display_number(energy_j),
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

        if self.main.project.ab_source_type not in self.LOCKED_AB_SOURCES:
            self._set_manual_ab_source()
            self._update_manual_snapshot()
            self._refresh_ab_source_ui()

        self.main._refresh_summary()
        return True

    def _on_compute_speed(self, mass_kg: float | None = None) -> bool:
        try:
            if mass_kg is None:
                mass_kg = self._parse_mass()
            if not math.isfinite(mass_kg) or mass_kg <= 0:
                raise ValueError(tr("calc.error.invalid_vehicle_mass"))
            if not self.main.has_energy_result():
                raise ValueError(tr("calc.error.invalid_energy_result"))
            self.main._sync_ui_to_project()
            result = self.main.calc.compute_damage_speed(mass_kg)
            speed_mps = float(result["speed_mps"])
            speed_kmh = float(result["speed_kmh"])
            if not all(math.isfinite(value) and value > 0 for value in (speed_mps, speed_kmh)):
                raise ValueError(tr("calc.error.invalid_speed_result"))
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("calc.speed.dialog.title"),
                str(e),
            )
            return False

        self.lbl_speed.setText(
            tr(
                "calc.damage_speed_value",
                value=format_display_number(speed_kmh),
                unit=self.SPEED_UNIT_KMH,
            )
        )

        self.main._vehicle_mass_kg = mass_kg
        self.main._damage_speed_mps = speed_mps
        self.main._damage_speed_kmh = speed_kmh

        self.main.project.vehicle_mass_kg = mass_kg
        self.main.project.damage_speed_mps = speed_mps
        self.main.project.damage_speed_kmh = speed_kmh

        self.main._refresh_summary()
        return True

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

        self._set_coefficients(A_n_per_m, B_n_per_m2)

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

        self._set_coefficients(A_n_per_m, B_n_per_m2)

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

    @staticmethod
    def _metadata_text(value: object) -> str:
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return ""
        if isinstance(value, float) and not math.isfinite(value):
            return ""
        text = str(value).strip()
        return "" if text.casefold() in {
            "", "-", "—", "none", "null", "n/a", "na", "not applicable", "não aplicável",
        } else text

    def _refresh_ab_source_ui(self) -> None:
        project = self.main.project
        snap = project.ab_source_snapshot
        snap = snap if isinstance(snap, dict) else {}
        source_type = project.ab_source_type
        locked = source_type in self.LOCKED_AB_SOURCES
        self.txt_A.setReadOnly(locked)
        self.txt_B.setReadOnly(locked)
        index = self.cmb_class.findData(project.ab_source_ref) if source_type == "generic_class" else (
            -1 if locked else 0
        )
        with QSignalBlocker(self.cmb_class):
            self.cmb_class.setCurrentIndex(index)
        for field, attribute in self._parameter_fields:
            value = getattr(project, attribute)
            exact_value = "" if value is None else tr(
                "calc.exact_value", value=format_display_number(value, None)
            )
            hint = "" if field.isReadOnly() else tr("number.input_hint")
            field.setToolTip("\n".join(filter(None, (exact_value, hint))))
        source_key = {
            "nhtsa_library": "calc.ab_source_nhtsa",
            "nhtsa_report": "calc.ab_source_nhtsa_report",
            "nhtsa_file": "calc.ab_source_nhtsa_file",
            "generic_class": "calc.ab_source_generic",
            "manual": "calc.ab_source_manual",
        }.get(source_type, "calc.ab_source_default")
        label = self._metadata_text(project.ab_source_label)
        lines = []
        if source_type == "generic_class":
            class_name = self._metadata_text(snap.get("class_name")) or label or (
                self._metadata_text(project.ab_source_ref)
            )
            label = class_name
            reference = self._metadata_text(snap.get("source_reference")) or (
                self._metadata_text(project.ab_source_reference)
            )
            if class_name:
                lines.append(f"{tr('calc.generic_class')}: {class_name}")
            if reference and reference != class_name:
                lines.append(f"{tr('report.ab_source_reference')}: {reference}")
        elif source_type in self.NHTSA_AB_SOURCES:
            vehicle = " ".join(
                value for key in ("make", "model", "year")
                if (value := self._metadata_text(snap.get(key)))
            )
            label = vehicle or label
            lines = self._nhtsa_source_details(snap, label)

        self.lbl_ab_source.setText(tr(source_key, label=f" | {label}" if label else ""))
        details = "\n".join(lines)
        self.lbl_ab_source.setToolTip(details)
        self.lbl_ab_details.setText(details)
        self.lbl_ab_details.setVisible(bool(details))

    def _nhtsa_source_details(self, snap: dict, source_label: str) -> list[str]:
        lines = []

        def add(label_key: str, value: object) -> None:
            if text := self._metadata_text(value):
                lines.append(f"{tr(label_key)}: {text}")

        def number(value: object) -> float | None:
            if not self._metadata_text(value):
                return None
            try:
                result = parse_float(value)
            except (TypeError, ValueError, OverflowError):
                return None
            return result if math.isfinite(result) else None

        def add_number(label_key: str, value: float | None, decimals: int = 3) -> None:
            if value is not None and math.isfinite(value):
                add(label_key, format_display_number(value, decimals))

        for key in ("test_agency", "test_number", "report_number"):
            add(f"nhtsa.field.{key}", snap.get(key))
        reference = self._metadata_text(snap.get("source_reference")) or (
            self._metadata_text(self.main.project.ab_source_reference)
        )
        if reference != self._metadata_text(snap.get("report_number")):
            add("report.ab_source_reference", reference)

        test_label = self._metadata_text(snap.get("test_label"))
        if test_label != source_label:
            add("nhtsa.field.test_label", test_label)
        for key, prefix in (
            ("test_type", "nhtsa.test_type"),
            ("test_configuration", "nhtsa.config"),
            ("barrier_type", "nhtsa.barrier_type"),
            ("impact_direction", "nhtsa.direction"),
            ("speed_basis", "nhtsa.speed_basis"),
        ):
            if value := self._metadata_text(snap.get(key)):
                translation_key = f"{prefix}.{value}"
                translated = tr(translation_key)
                add(f"nhtsa.field.{key}", value if translated == translation_key else translated)
        add_number("calc.ab.overlap", number(snap.get("overlap_pct")), 1)

        impact_speed = number(snap.get("impact_speed_mps"))
        if impact_speed is None:
            impact_speed = number(snap.get("test_speed_mps"))
        for label_key, speed_mps in (
            ("nhtsa.field.impact_speed_mps", impact_speed),
            ("nhtsa.field.velocity_change_mps", number(snap.get("velocity_change_mps"))),
            ("nhtsa.output.rebound_speed_mps", number(snap.get("rebound_speed_mps"))),
            ("nhtsa.output.damage_speed_mps", number(snap.get("damage_speed_mps"))),
            ("calc.ab.test_speed_used", number(snap.get("speed_used_mps"))),
        ):
            if speed_mps is not None:
                add_number(label_key, speed_mps * 3.6, 2)

        for key, field, label_key in (
            ("impact_angle_deg", self.txt_alpha_deg, "calc.ab.test_angle"),
            ("vehicle_mass_kg", self.txt_vehicle_mass, "calc.ab.test_mass"),
        ):
            value = number(snap.get(key))
            active = number(field.text())
            if value is not None and (active is None or round(value, 2) != round(active, 2)):
                add_number(label_key, value, 2)

        for label_key, key in (
            ("nhtsa.field.L_m", "L_m"),
            ("nhtsa.field.b0_mps", "b0_mps"),
            ("nhtsa.output.b1_per_s", "b1_per_s"),
            ("nhtsa.output.crush_area_m2", "crush_area_m2"),
            ("nhtsa.output.c_mean_m", "c_mean_m"),
        ):
            add_number(label_key, number(snap.get(key)))
        c_values = snap.get("c_values_m")
        if isinstance(c_values, (tuple, list)):
            values = [number(raw) for raw in c_values[:6]]
            points = [
                f"C{index}={format_display_number(value, 3)}"
                for index, value in enumerate(values, 1) if value is not None
            ]
            # The library may represent missing crush measurements as six zeroes.
            if any(value is not None and value > 0 for value in values):
                add("calc.ab.test_crush", " · ".join(points))
        add("calc.ab.notes", snap.get("notes"))
        return lines

    def _parse_ab_alpha(self):
        project = self.main.project
        A, B, alpha_deg = project.crash3_A, project.crash3_B, project.crash3_alpha_deg
        if A is None or B is None or alpha_deg is None:
            raise ValueError(tr("calc.error.invalid_ab_alpha"))

        if not math.isfinite(A) or A <= 0:
            raise ValueError(tr("calc.error.a_positive"))

        if not math.isfinite(B) or B <= 0:
            raise ValueError(tr("calc.error.b_positive"))

        if not math.isfinite(alpha_deg) or alpha_deg < 0 or alpha_deg >= 89.0:
            raise ValueError(tr("calc.error.alpha_range"))

        return A, B, alpha_deg
