from PySide6.QtCore import QLocale
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox, QToolTip

from app.core.number_format import parse_float, relocalize_decimal_input
from app.i18n import get_language, tr


class _StrictNumericInput:
    def __init__(self, parent=None):
        self._rejected_input = False
        super().__init__(parent)
        self.refresh_numeric_locale()
        self.setKeyboardTracking(False)
        self.lineEdit().textEdited.connect(self._clear_rejection)

    def refresh_numeric_locale(self) -> None:
        locale = QLocale("pt_BR" if get_language() == "pt" else "en_US")
        if self.locale() != locale:
            text = self.text()
            pending = (
                text != self.specialValueText()
                and self.hasAcceptableInput() and self._parse_input(text) != self.value()
            )
            translated = relocalize_decimal_input(text, self._input_language()) if pending else None
            self.setLocale(locale)
            if translated is not None:
                self.lineEdit().setText(translated)
        self.setToolTip(tr("number.input_hint"))

    def _input_language(self) -> str:
        return "pt" if self.locale().decimalPoint() == "," else "en"

    def _parse_input(self, text: str) -> float:
        return parse_float(text, language=self._input_language())

    def _clear_rejection(self, _value) -> None:
        self._rejected_input = False

    def setValue(self, value) -> None:
        self._rejected_input = False
        super().setValue(value)

    def validate(self, text: str, position: int):
        try:
            value = self._parse_input(text)
        except ValueError:
            # Keep the text editable so Qt cannot drop the last character and
            # silently accept a different value.
            return QValidator.State.Intermediate, text, position
        decimals = self.decimals() if isinstance(self, QDoubleSpinBox) else 0
        if not self.minimum() <= value <= self.maximum() or round(value, decimals) != value:
            return QValidator.State.Intermediate, text, position
        return QValidator.State.Acceptable, text, position

    def fixup(self, text: str) -> str:
        self._rejected_input = True
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), tr("number.error.rejected"), self)
        return self.textFromValue(self.value())

    def take_invalid_input(self) -> bool:
        invalid = self._rejected_input or not self.hasAcceptableInput()
        self.interpretText()
        self._rejected_input = False
        return invalid


class NumericDoubleSpinBox(_StrictNumericInput, QDoubleSpinBox):
    def valueFromText(self, text: str) -> float:
        return self._parse_input(text)


class NumericSpinBox(_StrictNumericInput, QSpinBox):
    def valueFromText(self, text: str) -> int:
        return int(self._parse_input(text))
