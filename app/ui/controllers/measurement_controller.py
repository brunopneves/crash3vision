from __future__ import annotations

import math

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QMessageBox

from app.i18n import tr

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


class MeasurementController:
    SLICE_COUNT = 6

    def __init__(self, host: "MainWindow") -> None:
        self.host = host

    # ---------------- Calibration ----------------
    def on_calibration_px_measured(self, dist_px: float) -> None:
        self.host._calibration_px = dist_px
        self.host.chk_calibration_mode.setChecked(False)
        self.host._refresh_calibration_panel()

    def calibration_candidate(self) -> tuple[float | None, str | None]:
        p1, p2 = self.host.canvas.cal_p1, self.host.canvas.cal_p2
        if p1 is None or p2 is None:
            return None, "measurement.error.measure_2_points_first"
        dist_px = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if not math.isfinite(dist_px) or dist_px <= 0:
            return None, "measurement.error.measure_2_points_first"
        try:
            real_m = float(self.host.txt_real_m.text().replace(",", "."))
        except ValueError:
            return None, "measurement.error.invalid_real_distance"
        if not math.isfinite(real_m) or real_m <= 0:
            return None, "measurement.error.real_distance_positive"
        scale = real_m / dist_px
        if not math.isfinite(scale) or scale <= 0:
            return None, "measurement.error.invalid_real_distance"
        return scale, None

    def apply_calibration(self) -> bool:
        m_per_px, reason = self.calibration_candidate()
        if m_per_px is None:
            assert reason is not None
            QMessageBox.warning(self.host, tr("group.calibration"), tr(reason))
            return False

        self.host._m_per_px = m_per_px
        self.host.canvas.apply_scale(m_per_px)
        self.host.project.m_per_px = m_per_px

        if m_per_px < 0.00005 or m_per_px > 0.05:
            QMessageBox.warning(
                self.host,
                tr("group.calibration"),
                tr("measurement.warning.unusual_scale", value=f"{m_per_px:.6f}"),
            )

        self.refresh_w_labels()
        return True

    # ---------------- Marking: W/Δw ----------------
    def on_w_px_measured(self, w_px: float) -> None:
        self.host._w_px = w_px
        self.host._ci_px.clear()
        self.host._ci_m.clear()
        self.host._current_ci_index = 1
        self.host.workflow.reset_canvas_tools()
        self.host._sync_ci_radio_buttons()
        self.host._update_ci_label()
        self.refresh_w_labels()
        self.update_ci_values_label()
        # clear_markings also removes the structural-reference offset.
        with QSignalBlocker(self.host.spn_bumper_offset):
            self.host.spn_bumper_offset.setValue(0.0)
        self.host.workflow.invalidate_energy()
        self.host._sync_ui_to_project()
        self.host._refresh_summary()

    def refresh_w_labels(self) -> None:
        if self.host._w_px is None:
            self.host._w_m = None
            self.host._delta_w_px = None
            self.host._delta_w_m = None
            self.host.lbl_w.setText(tr("label.w_default"))
            self.host.lbl_delta_w.setText(tr("label.delta_w_default"))
            return

        m_per_px = self.host._m_per_px

        w_total_px = float(self.host._w_px)
        w_m = (w_total_px * m_per_px) if m_per_px is not None else None
        self.host._w_m = w_m

        self.host.lbl_w.setText(
            tr("measurement.w_value_full", m=f"{w_m:.3f}")
            if w_m is not None
            else tr("measurement.w_value_px_only", px=f"{w_total_px:.2f}")
        )

        delta_w_px = w_total_px / (self.SLICE_COUNT - 1)
        self.host._delta_w_px = delta_w_px

        delta_w_m = (delta_w_px * m_per_px) if m_per_px is not None else None
        self.host._delta_w_m = delta_w_m

        self.host.lbl_delta_w.setText(
            tr(
                "measurement.delta_w_value_full",
                px=f"{delta_w_px:.2f}",
                m=f"{delta_w_m:.3f}",
            )
            if delta_w_m is not None
            else tr("measurement.delta_w_value_px_only", px=f"{delta_w_px:.2f}")
        )

    # ---------------- Marking: Ci ----------------
    def on_ci_measured(self, idx: int, ci_px: float, ci_m: float) -> None:
        self.host._ci_px[idx] = ci_px
        self.host._ci_m[idx] = (
            (ci_px * self.host._m_per_px) if self.host._m_per_px is not None else ci_m
        )
        self.update_ci_values_label()

        if idx < self.SLICE_COUNT:
            self.host._current_ci_index = idx + 1
            self.host.canvas.set_ci_index(self.host._current_ci_index)
            self.host._sync_ci_radio_buttons()
            self.host._update_ci_label()

        self.host.workflow.invalidate_energy()
        self.host._refresh_summary()

    def update_ci_values_label(self) -> None:
        parts = []
        for i in range(1, 7):
            parts.append(
                f"C{i}={self.host._ci_m[i]:.3f}" if i in self.host._ci_m else f"C{i}=-"
            )
        self.host.lbl_ci_values.setText(
            tr("measurement.c_values_prefix") + "  " + "  ".join(parts)
        )
