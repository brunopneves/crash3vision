ACTION_STYLES = """
QPushButton[uiRole], QToolButton[uiRole="disclosure"] {
    background: #f1f4f8;
    color: #23313f;
    border: 2px solid #c4cedb;
    border-radius: 5px;
    padding: 4px 7px;
    font-size: 12px;
}
QPushButton[uiRole]:hover, QToolButton[uiRole="disclosure"]:hover {
    background: #e6ecf4;
}
QPushButton[uiRole]:pressed, QToolButton[uiRole="disclosure"]:pressed {
    background: #d9e4f1;
}
QPushButton[uiRole]:checked {
    background: #dceaf8;
    color: #164673;
    border-color: #6f95bc;
}
QPushButton[uiRole="primary"] {
    background: #245b96;
    color: #ffffff;
    border-color: #245b96;
    font-weight: bold;
}
QPushButton[uiRole="primary"]:hover { background: #1c4f86; }
QPushButton[uiRole="primary"]:pressed { background: #153d69; }
QPushButton[uiRole="destructive"] {
    background: #faf6f6;
    color: #82383d;
    border-color: #d7bfc2;
}
QPushButton[uiRole="destructive"]:hover { background: #f5e9ea; }
QPushButton[uiRole="destructive"]:pressed { background: #efdcde; }
QPushButton[uiRole="secondary"][uiCompact="true"],
QPushButton[uiRole="primary"][uiCompact="true"] {
    padding: 4px;
    font-size: 10px;
}
QToolButton[uiRole="disclosure"] {
    background: #edf0f3;
    padding: 3px 7px;
    font-size: 11px;
}
QPushButton[uiRole]:focus, QToolButton[uiRole="disclosure"]:focus {
    border-color: #245b96;
}
QPushButton[uiRole="primary"]:focus { border-color: #a9d3ff; }
QPushButton[uiRole]:disabled, QToolButton[uiRole="disclosure"]:disabled {
    background: #f0f2f5;
    color: #566371;
    border-color: #d0d7df;
}
"""

WORKFLOW_PANEL_STYLES = """
QLabel#imagesTitle, QLabel#alignmentTitle, QLabel#calibrationTitle, QLabel#measurementTitle,
QLabel#calculationTitle {
    color: #172f50;
    font-size: 23px;
    font-weight: bold;
}
QLabel#imageCardDescription, QFrame#alignmentCard QLabel, QLabel#alignmentShortcuts,
QLabel#measurementOrientation, QGroupBox[measurementCard="true"] QLabel,
QGroupBox[calculationCard="true"] QLabel, QFrame[calculationCard="true"] QLabel {
    color: #44566c;
    font-size: 13px;
}
QFrame#imageLoadCard, QFrame#alignmentCard, QGroupBox#alignmentManualCard,
QFrame[calibrationCard="true"], QGroupBox[measurementCard="true"], QFrame[measurementCard="true"],
QGroupBox[calculationCard="true"], QFrame[calculationCard="true"] {
    background: #f8faff;
    border: 1px solid #d6dfe9;
    border-radius: 9px;
}
QLabel#imageCardTitle, QLabel#alignmentMethodLabel, QLabel#alignmentTargetLabel,
QLabel#alignmentStatusTitle, QFrame[calibrationCard="true"] QLabel[calibrationHeading="true"],
QGroupBox[measurementCard="true"] QLabel[measurementHeading="true"],
QGroupBox[calculationCard="true"] QLabel[calculationHeading="true"] {
    color: #192f4c;
    font-size: 14px;
    font-weight: bold;
}
QLabel#imageCardStatus {
    background: #edf1f6;
    color: #44566c;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 12px;
    font-weight: bold;
}
QLabel#imageCardStatus[imageLoaded="true"] {
    background: #e3f3e9;
    color: #245c3e;
}
QPushButton[imageAction="true"], QPushButton[panelAction="true"] {
    padding: 7px 8px;
    font-size: 13px;
}
QToolButton#imagesDisclosure, QToolButton[panelDisclosure="true"] {
    background: #edf1f6;
    color: #283b53;
    padding: 7px 9px;
    font-size: 13px;
    font-weight: bold;
}
QToolButton#imagesDisclosure:hover, QToolButton[panelDisclosure="true"]:hover {
    background: #e3eaf3;
}
QToolButton#imagesDisclosure:pressed, QToolButton[panelDisclosure="true"]:pressed {
    background: #d9e4f1;
}
QToolButton[panelDisclosure="true"]:disabled {
    background: #f0f2f5;
    color: #566371;
}
QGroupBox#alignmentPanel, QGroupBox#calibrationPanel, QGroupBox#measurementPanel,
QGroupBox#measurementCiGrid, QGroupBox#calculationPanel { border: none; }
QLabel#imagesTitle, QLabel#alignmentTitle, QLabel#calibrationTitle, QLabel#measurementTitle,
QLabel#calculationTitle {
    padding: 4px 8px;
}
QLabel#measurementOrientation { padding: 0 8px; }
QFrame#alignmentCard QRadioButton { font-size: 12px; spacing: 5px; }
QToolButton#alignmentPrecisionDisclosure { font-size: 12px; }
QLabel#alignmentStatusTitle[tone="success"] { color: #245c3e; }
QLabel#alignmentStatusTitle[tone="warning"] { color: #775025; }
QPushButton[alignmentDecision="true"] {
    padding: 5px 7px;
    font-size: 12px;
}
QGroupBox[alignmentSection="true"] {
    border: none;
    margin-top: 16px;
    font-size: 13px;
    font-weight: bold;
    color: #192f4c;
}
QGroupBox[alignmentSection="true"]::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
}
QGroupBox#alignmentManualCard QComboBox,
QGroupBox#alignmentManualCard QDoubleSpinBox {
    min-height: 24px;
}
QFrame[calibrationCard="true"] QLabel {
    color: #44566c;
    font-size: 13px;
}
QLabel#calibrationPointsStatus[complete="true"] {
    color: #245c3e;
    font-weight: bold;
}
QFrame[calibrationCard="true"][hasScale="true"] {
    background: #eaf5ee;
    border-color: #c5dece;
}
QLabel#calibrationScaleValue {
    color: #172f50;
    font-size: 23px;
    font-weight: bold;
}
QLineEdit#calibrationDistanceInput, QLineEdit[calculationInput="true"] {
    background: #ffffff;
    color: #23313f;
    border: 2px solid #c4cedb;
    border-radius: 5px;
    padding: 6px 8px;
    font-size: 14px;
}
QLineEdit#calibrationDistanceInput:focus, QLineEdit[calculationInput="true"]:focus {
    border-color: #245b96;
}
QLineEdit#calibrationDistanceInput[invalidDistance="true"] { border-color: #b05a59; }
QLineEdit#calibrationDistanceInput[invalidDistance="true"]:focus { border-color: #853d3d; }
QLineEdit#calibrationDistanceInput:disabled, QLineEdit[calculationInput="true"]:disabled {
    background: #f0f2f5;
    color: #566371;
    border-color: #d0d7df;
}
QLabel#measurementWidthValue {
    color: #172f50;
    font-size: 23px;
    font-weight: bold;
}
QLabel[measurementStatus="true"][complete="true"] {
    color: #245c3e;
    font-weight: bold;
}
QGroupBox#measurementCiGrid QRadioButton {
    background: #edf1f6;
    color: #23313f;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 6px;
    font-size: 13px;
    font-weight: bold;
}
QGroupBox#measurementCiGrid QRadioButton:hover { background: #e3eaf3; }
QGroupBox#measurementCiGrid QRadioButton:checked {
    background: #dceaf8;
    color: #164673;
    border-color: #6f95bc;
}
QGroupBox#measurementCiGrid QRadioButton:focus { border-color: #245b96; }
QGroupBox#measurementCiGrid QRadioButton:disabled { color: #566371; }
QLabel[measurementCiValue="true"] { color: #23313f; font-weight: bold; }
QToolButton#measurementReferencesDisclosure { font-size: 12px; }
QFrame[measurementCard="true"] QDoubleSpinBox { min-height: 24px; }
QGroupBox[calculationCard="true"] QComboBox { min-height: 26px; font-size: 13px; }
QLabel[calculationFieldLabel="true"] { font-weight: bold; }
QLineEdit[calculationInput="true"]:read-only {
    background: #edf1f6;
    color: #344861;
}
QLabel#calculationSource {
    background: #eaf0f8;
    color: #344861;
    border-radius: 5px;
    padding: 7px 8px;
}
QLabel[calculationOutput="true"] {
    background: #edf1f6;
    border-radius: 5px;
    padding: 6px 8px;
}
QLabel#calculationFormula {
    background: #edf1f6;
    border-radius: 5px;
    padding: 6px 8px;
}
"""


def set_style_property(widget, name: str, value) -> None:
    if widget.property(name) != value:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
