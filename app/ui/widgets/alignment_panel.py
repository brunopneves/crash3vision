from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
)

from app.i18n import tr


class AlignmentPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # -------------------------
        # Nudge
        # -------------------------

        self.grp_nudge = QGroupBox(tr("alignment.nudge"))
        nudge_layout = QVBoxLayout()

        row = QHBoxLayout()

        self.btn_left = QPushButton("←")
        self.btn_right = QPushButton("→")
        self.btn_up = QPushButton("↑")
        self.btn_down = QPushButton("↓")

        self.spin_step = QSpinBox()
        self.spin_step.setRange(1, 200)
        self.spin_step.setValue(5)

        row.addWidget(self.btn_left)
        row.addWidget(self.btn_right)
        row.addWidget(self.btn_up)
        row.addWidget(self.btn_down)

        row.addWidget(QLabel(tr("alignment.step_px")))
        row.addWidget(self.spin_step)

        nudge_layout.addLayout(row)
        self.grp_nudge.setLayout(nudge_layout)

        layout.addWidget(self.grp_nudge)

        # -------------------------
        # Rotate
        # -------------------------

        self.grp_rotate = QGroupBox(tr("alignment.rotate"))
        rotate_layout = QHBoxLayout()

        self.spin_rotate = QDoubleSpinBox()
        self.spin_rotate.setRange(-180.0, 180.0)
        self.spin_rotate.setDecimals(2)
        self.spin_rotate.setSingleStep(0.5)

        self.btn_rotate_apply = QPushButton(tr("alignment.apply"))

        rotate_layout.addWidget(self.spin_rotate)
        rotate_layout.addWidget(self.btn_rotate_apply)

        self.grp_rotate.setLayout(rotate_layout)

        layout.addWidget(self.grp_rotate)

        # -------------------------
        # Scale
        # -------------------------

        self.grp_scale = QGroupBox(tr("alignment.scale"))
        scale_layout = QHBoxLayout()

        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.1, 10.0)
        self.spin_scale.setDecimals(3)
        self.spin_scale.setSingleStep(0.01)
        self.spin_scale.setValue(1.0)

        self.btn_scale_apply = QPushButton(tr("alignment.apply"))

        scale_layout.addWidget(self.spin_scale)
        scale_layout.addWidget(self.btn_scale_apply)

        self.grp_scale.setLayout(scale_layout)

        layout.addWidget(self.grp_scale)

        layout.addStretch()
