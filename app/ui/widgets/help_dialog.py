from dataclasses import dataclass
from html import escape
from pathlib import Path
import sys

from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QDesktopServices, QPyTextObject, QTextCharFormat, QTextFormat, QTextOption
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout

from app.i18n import tr
from app.version import __version__


# Repository and authorship metadata are documented in CITATION.cff.
REPOSITORY_URL = "https://github.com/brunopneves/crash3vision"
ENERGY_EQUATION = "E = (W/5)[(A/2)L + (B/6)Q + 5G](1 + tan²α)"
ENERGY_TERMS = (
    "L = C₁ + 2C₂ + 2C₃ + 2C₄ + 2C₅ + C₆\n"
    "Q = C₁² + 2C₂² + 2C₃² + 2C₄² + 2C₅² + C₆²\n"
    "    + C₁C₂ + C₂C₃ + C₃C₄ + C₄C₅ + C₅C₆\n"
    "G = A²/(2B)"
)
EES_EQUATION = "EES = √(2E / m)"
EQUATION_OBJECT = int(QTextFormat.ObjectTypes.UserObject) + 1
EQUATION_KEY = QTextFormat.Property.UserProperty


@dataclass(frozen=True)
class Equation:
    svg: QSvgRenderer
    compact: QSvgRenderer | None
    number: str
    text: str


class EquationRenderer(QPyTextObject):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.width = 1
        self.equations: dict[str, Equation] = {}

    def _graphics(self, char_format):
        equation = self.equations[char_format.property(EQUATION_KEY)]
        # Reserve equal space on both sides so the number does not shift the equation.
        available = max(1, self.width - (48 if equation.number else 0))
        svg = equation.svg
        if equation.compact is not None and available < svg.defaultSize().width():
            svg = equation.compact
        natural = svg.defaultSize()
        width = min(available, natural.width())
        return svg, QSizeF(width, natural.height() * width / natural.width()), equation.number

    def intrinsicSize(self, document, position, char_format) -> QSizeF:
        _, size, _ = self._graphics(char_format)
        return QSizeF(self.width, size.height())

    def drawObject(self, painter, rect, document, position, char_format) -> None:
        svg, size, number = self._graphics(char_format)
        graphic = QRectF(0, 0, size.width(), size.height())
        graphic.moveCenter(rect.center())
        painter.save()
        svg.render(painter, graphic)
        if number:
            font = painter.font()
            font.setPixelSize(13)
            painter.setFont(font)
            painter.setPen(QColor("#44566c"))
            painter.drawText(
                rect.adjusted(0, 0, -2, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                number,
            )
        painter.restore()


class HelpArticle(QTextBrowser):
    def __init__(self) -> None:
        super().__init__()
        self._equation_renderer = EquationRenderer(self)
        self.document().documentLayout().registerHandler(EQUATION_OBJECT, self._equation_renderer)

    def add_equation(
        self, filename: str, text: str, number: str = "", compact_filename: str | None = None
    ) -> str:
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        assets = root / "app" / "assets"
        svg = QSvgRenderer(str(assets / filename))
        if not svg.isValid():
            return "<p align='center'>" + "<br>".join(escape(line) for line in text.splitlines()) + "</p>"
        compact = QSvgRenderer(str(assets / compact_filename)) if compact_filename else None
        if compact is not None and not compact.isValid():
            compact = None
        marker = chr(0xE000 + len(self._equation_renderer.equations))
        self._equation_renderer.equations[marker] = Equation(svg, compact, number, text)
        return f"<p>{marker}</p>"

    def insert_equations(self) -> None:
        document = self.document()
        self._update_equation_width()
        for marker in self._equation_renderer.equations:
            cursor = document.find(marker)
            if not cursor.isNull():
                char_format = QTextCharFormat()
                char_format.setObjectType(EQUATION_OBJECT)
                char_format.setProperty(EQUATION_KEY, marker)
                cursor.insertText("\uFFFC", char_format)

    def _equation_cursors(self):
        document = self.document()
        # An inline object occupies one object-replacement character in the document.
        cursor = document.find("\uFFFC")
        while not cursor.isNull():
            if cursor.charFormat().objectType() == EQUATION_OBJECT:
                yield cursor
            cursor = document.find("\uFFFC", cursor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_equation_width()

    def _update_equation_width(self) -> None:
        if not self._equation_renderer.equations:
            return
        document = self.document()
        width = max(1, self.viewport().width() - 2 * document.documentMargin() - 1)
        if width != self._equation_renderer.width:
            self._equation_renderer.width = width
            document.markContentsDirty(0, document.characterCount())

    def createMimeDataFromSelection(self):
        data = super().createMimeDataFromSelection()
        selection = self.textCursor()
        equations = [
            self._equation_renderer.equations[cursor.charFormat().property(EQUATION_KEY)].text
            for cursor in self._equation_cursors()
            if selection.selectionStart() <= cursor.selectionStart()
            and cursor.selectionEnd() <= selection.selectionEnd()
        ]
        if equations:
            parts = data.text().split("\uFFFC")
            data.setText(parts[0] + "".join(equation + part for equation, part in zip(equations, parts[1:])))
        return data


class HelpDialog(QDialog):
    def __init__(self, topic: str, parent, project_shortcuts: dict[str, str]) -> None:
        super().__init__(parent)
        title = tr(f"help.{topic}.title")
        self.setWindowTitle(title)
        self.setObjectName("helpDialog")
        available = parent.screen().availableGeometry()
        width, height = (500, 320) if topic == "about" else (620, 520)
        self.resize(
            min(width, parent.width() - 32, available.width() - 32),
            min(height, parent.height() - 48, available.height() - 64),
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("helpTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        self.browser = HelpArticle()
        self.browser.setObjectName("helpArticle")
        self.browser.setAccessibleName(title)
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(QDesktopServices.openUrl)
        self.browser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        document = self.browser.document()
        document.setDocumentMargin(14)
        document.setDefaultStyleSheet("""
            body { color: #23313f; font-size: 14px; }
            h2 { color: #192f4c; font-size: 16px; margin-top: 12px; margin-bottom: 5px; }
            li { margin-bottom: 6px; }
            a { color: #245b96; }
        """)
        equations = {}
        if topic == "methodology":
            equations = {
                "energy_equation": self.browser.add_equation(
                    "crash3_energy.svg", ENERGY_EQUATION, "(1)", "crash3_energy_compact.svg"
                ),
                "energy_terms": self.browser.add_equation("crash3_energy_terms.svg", ENERGY_TERMS),
                "ees_equation": self.browser.add_equation("crash3_ees.svg", EES_EQUATION, "(2)"),
            }
        article = tr(
            f"help.{topic}.body",
            version=__version__,
            repository_url=REPOSITORY_URL,
            methodology_url=f"{REPOSITORY_URL}/blob/main/docs/methodology.md",
            license_url=f"{REPOSITORY_URL}/blob/main/LICENSE",
            **project_shortcuts,
            **equations,
        )
        self.browser.setHtml(f"<html><body>{article}</body></html>")
        self.browser.insert_equations()
        layout.addWidget(self.browser, 1)

        buttons = QDialogButtonBox()
        close = buttons.addButton(tr("help.close"), QDialogButtonBox.ButtonRole.AcceptRole)
        close.setProperty("uiRole", "secondary")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
