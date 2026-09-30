from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QRadioButton,
    QButtonGroup,
)

from app.i18n import tr


class MarkingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # ------------------------------------------------
        # W measurement
        # ------------------------------------------------

        self.grp_w = QGroupBox(tr("marking.measure_w"))
        w_layout = QVBoxLayout()

        self.btn_set_w_mode = QPushButton(tr("marking.set_w_mode"))
        self.btn_generate_slices = QPushButton(tr("marking.generate_slices"))

        w_layout.addWidget(self.btn_set_w_mode)
        w_layout.addWidget(self.btn_generate_slices)

        self.grp_w.setLayout(w_layout)
        layout.addWidget(self.grp_w)

        # ------------------------------------------------
        # Ci selection
        # ------------------------------------------------

        self.grp_c = QGroupBox(tr("marking.select_c"))
        c_layout = QVBoxLayout()

        self.c_button_group = QButtonGroup(self)

        row = QHBoxLayout()

        self.radio_c1 = QRadioButton("C1")
        self.radio_c2 = QRadioButton("C2")
        self.radio_c3 = QRadioButton("C3")
        self.radio_c4 = QRadioButton("C4")
        self.radio_c5 = QRadioButton("C5")
        self.radio_c6 = QRadioButton("C6")

        radios = [
            self.radio_c1,
            self.radio_c2,
            self.radio_c3,
            self.radio_c4,
            self.radio_c5,
            self.radio_c6,
        ]

        for idx, r in enumerate(radios, start=1):
            self.c_button_group.addButton(r, idx)
            row.addWidget(r)

        c_layout.addLayout(row)

        self.grp_c.setLayout(c_layout)
        layout.addWidget(self.grp_c)

        # ------------------------------------------------
        # Restart marking
        # ------------------------------------------------

        self.btn_restart_marking = QPushButton(tr("marking.restart_marking"))
        layout.addWidget(self.btn_restart_marking)

        layout.addStretch()
