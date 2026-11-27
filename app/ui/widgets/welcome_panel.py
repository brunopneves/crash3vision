from html import escape
from pathlib import Path
import sys

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor, QFontMetrics, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient,
)
from PySide6.QtWidgets import (
    QBoxLayout, QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QHBoxLayout, QVBoxLayout, QWidget,
)

from app.i18n import tr
from app.ui.styles import set_style_property


class _WelcomeSurface(QWidget):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.save()
        painter.scale(self.width(), self.height())

        glow = QRadialGradient(0.50, 0.45, 0.71)
        glow.setColorAt(0.0, QColor("#ffffff"))
        glow.setColorAt(0.56, QColor("#fcfdff"))
        glow.setColorAt(1.0, QColor("#eaf3fd"))
        painter.fillRect(QRectF(0, 0, 1, 1), glow)

        far_wave = QPainterPath()
        far_wave.moveTo(0, 0.94)
        far_wave.cubicTo(0.23, 0.86, 0.43, 0.99, 0.62, 0.979)
        far_wave.cubicTo(0.77, 0.975, 0.90, 0.92, 1, 0.94)
        near_wave = QPainterPath()
        near_wave.moveTo(0, 0.995)
        near_wave.cubicTo(0.18, 0.904, 0.35, 0.941, 0.51, 0.985)
        near_wave.cubicTo(0.70, 1.034, 0.87, 0.973, 1, 0.964)
        for wave, color in ((far_wave, (98, 157, 222, 54)), (near_wave, (108, 169, 229, 49))):
            wave.lineTo(1, 1)
            wave.lineTo(0, 1)
            wave.closeSubpath()
            fade = QLinearGradient(0, 0.87, 1, 1)
            fade.setColorAt(0, QColor(*color))
            fade.setColorAt(1, QColor(126, 182, 231, 24))
            painter.fillPath(wave, fade)
        painter.restore()

        self._paint_car(painter)
        painter.end()

    def _paint_car(self, painter: QPainter) -> None:
        width = min(248, self.width() * 0.47, self.height() * 0.48)
        painter.save()
        painter.translate(self.width() - width * 0.96, self.height() - width * 0.29)
        painter.scale(width / 280, width / 280)

        outline = QPainterPath()
        outline.moveTo(4, 80)
        outline.cubicTo(4, 67, 8, 62, 22, 58)
        outline.cubicTo(41, 51, 66, 49, 88, 45)
        outline.cubicTo(108, 33, 130, 17, 152, 15)
        outline.cubicTo(188, 10, 216, 15, 248, 29)
        outline.lineTo(272, 34)
        outline.cubicTo(275, 49, 275, 58, 281, 68)
        roofline = QPainterPath()
        roofline.moveTo(30, 62)
        roofline.cubicTo(86, 53, 151, 47, 218, 43)
        roofline.cubicTo(238, 41, 256, 41, 273, 44)
        for center in (54, 230):
            roofline.moveTo(center - 24, 87)
            roofline.cubicTo(center - 24, 55, center + 24, 55, center + 24, 87)

        tint = QLinearGradient(0, 10, 0, 89)
        tint.setColorAt(0, QColor(77, 142, 215, 86))
        tint.setColorAt(0.55, QColor(92, 153, 220, 53))
        tint.setColorAt(1, QColor(109, 168, 230, 0))
        pen = QPen()
        pen.setBrush(tint)
        pen.setWidthF(4.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(outline)
        painter.drawPath(roofline)
        painter.restore()


class _BrandArc(QWidget):
    def paintEvent(self, event) -> None:
        width = self.width() * 0.28
        left = (self.width() - width) / 2 + width * 0.25
        right = left + width
        base = self.height() - 1
        path = QPainterPath()
        path.moveTo(left, base)
        path.cubicTo(left + width * 0.30, -2, left + width * 0.72, -2, right, base)
        path.cubicTo(left + width * 0.72, base * 0.25, left + width * 0.30, base * 0.25, left, base)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillPath(path, QColor("#0874d1"))
        painter.end()


def _welcome_icon(kind: str, color: str) -> QIcon:
    pixmap = QPixmap(48, 48)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    if kind == "info":
        painter.drawEllipse(QRectF(2, 2, 20, 20))
        painter.drawPoint(12, 7)
        painter.drawLine(12, 11, 12, 17)
    else:
        shape = QPainterPath()
        if kind == "folder":
            shape.moveTo(3, 6)
            for x, y in ((9, 6), (12, 9), (21, 9), (21, 19), (3, 19)):
                shape.lineTo(x, y)
        else:
            shape.moveTo(6, 3)
            for x, y in ((14, 3), (19, 8), (19, 21), (6, 21)):
                shape.lineTo(x, y)
            painter.drawLine(9, 12, 16, 12)
            painter.drawLine(9, 16, 16, 16)
        shape.closeSubpath()
        painter.drawPath(shape)
    painter.end()
    return QIcon(pixmap)


class _ProcessIllustration(QWidget):
    # Content bounds in welcome.png, excluding the original frames and arrows.
    _PANELS = (
        (0.028, 0.227, 0.248, 0.747),
        (0.272, 0.475, 0.248, 0.747),
        (0.525, 0.721, 0.248, 0.747),
        (0.762, 0.970, 0.362, 0.655),
    )

    def __init__(self) -> None:
        super().__init__()
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        self._pixmap = QPixmap(str(root / "app/assets/welcome.png"))
        self._gap = 0
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setHidden(self._pixmap.isNull())

    def fit(self, width: int, gap: int, maximum: int) -> None:
        self._gap = gap
        tile_width = (width - 3 * gap) / 4
        self.setFixedHeight(min(maximum, max(24, round(tile_width * 1.12))))
        self.update()

    def panel_rect(self, index: int) -> QRectF:
        width = max(0.0, (self.width() - 3 * self._gap) / 4)
        return QRectF(index * (width + self._gap) + 0.5, 0.5, max(0.0, width - 1), self.height() - 1)

    def paintEvent(self, event) -> None:
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for index, bounds in enumerate(self._PANELS):
            rect = self.panel_rect(index)
            self._paint_panel(painter, rect, bounds)
            if index:
                self._paint_arrow(painter, self.panel_rect(index - 1).right(), rect.left(), rect.center().y())
        painter.end()

    def _paint_panel(self, painter: QPainter, rect: QRectF, bounds: tuple[float, float, float, float]) -> None:
        radius = min(14.0, rect.width() * 0.085)
        shape = QPainterPath()
        shape.addRoundedRect(rect, radius, radius)
        painter.fillPath(shape.translated(0, min(2.0, radius * 0.30)), QColor(41, 96, 150, 14))
        fill = QLinearGradient(0, rect.top(), 0, rect.bottom())
        fill.setColorAt(0, QColor("#fbfdff"))
        fill.setColorAt(1, QColor("#e3effd"))
        painter.fillPath(shape, fill)

        # Keep the source illustrations intact and scale each one proportionally
        # inside the common card geometry, without the source frame or arrows.
        width, height = self._pixmap.width(), self._pixmap.height()
        left, right, top, bottom = bounds
        source = QRectF(left * width, top * height, (right - left) * width, (bottom - top) * height)
        padding = rect.width() * 0.045
        area = rect.adjusted(padding, padding, -padding, -padding)
        target_size = source.size().scaled(area.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF(QPointF(), target_size)
        target.moveCenter(area.center())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        painter.drawPixmap(target, self._pixmap, source)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.strokePath(shape, QPen(QColor("#4b87ca"), 1))

    @staticmethod
    def _paint_arrow(painter: QPainter, start: float, end: float, y: float) -> None:
        size = min(11.0, (end - start) / 2)
        middle = end - size
        arrow = QPainterPath()
        arrow.moveTo(start, y - size * 0.29)
        arrow.lineTo(middle, y - size * 0.29)
        arrow.lineTo(middle, y - size)
        arrow.lineTo(end, y)
        arrow.lineTo(middle, y + size)
        arrow.lineTo(middle, y + size * 0.29)
        arrow.lineTo(start, y + size * 0.29)
        arrow.closeSubpath()
        fade = QLinearGradient(start, y, end, y)
        fade.setColorAt(0, QColor("#79a6d9"))
        fade.setColorAt(1, QColor("#145da6"))
        painter.fillPath(arrow, fade)


class WelcomePanel(QScrollArea):
    def __init__(self, canvas_viewport: QWidget) -> None:
        super().__init__()
        self._canvas_viewport = canvas_viewport
        self.setObjectName("welcomePanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        surface = _WelcomeSurface()
        surface.setObjectName("welcomeSurface")
        surface.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setWidget(surface)
        layout = QGridLayout(surface)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 12)
        layout.setRowStretch(2, 1)
        self.card = QFrame()
        self.card.setObjectName("welcomeCard")
        self.card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.card, 1, 0, Qt.AlignmentFlag.AlignHCenter)

        self.content = QVBoxLayout(self.card)
        self.content.setContentsMargins(20, 24, 20, 24)
        self.content.setSpacing(12)
        self.content.addStretch(1)
        self.title = QLabel()
        self.subtitle = QLabel()
        self.instruction = QLabel()
        self.reference_note = QLabel()
        self.illustration = _ProcessIllustration()
        for label, name in (
            (self.title, "welcomeTitle"), (self.subtitle, "welcomeSubtitle"),
            (self.instruction, "welcomeInstruction"), (self.reference_note, "welcomeReferenceNote"),
        ):
            label.setObjectName(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        logo = QVBoxLayout()
        logo.setSpacing(0)
        self.arc = _BrandArc()
        self.arc.setFixedHeight(16)
        logo.addWidget(self.arc)
        logo.addWidget(self.title)
        self.content.addLayout(logo)
        self.content.addWidget(self.subtitle)
        process = QVBoxLayout()
        process.setSpacing(3)
        process.addWidget(self.illustration)

        self.steps: dict[str, tuple[QWidget, QLabel, QLabel]] = {}
        captions = QWidget()
        captions.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.caption_grid = QGridLayout(captions)
        self.caption_grid.setContentsMargins(0, 0, 0, 0)
        self.caption_grid.setSpacing(6)
        self._caption_columns = 0
        for key in ("images", "calibration", "measurement", "calculation"):
            step = QFrame()
            step.setObjectName("welcomeStep")
            step.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            layout = QVBoxLayout(step)
            layout.setContentsMargins(6, 4, 6, 5)
            layout.setSpacing(3)
            heading = QLabel()
            description = QLabel()
            for label, name in ((heading, "welcomeStepTitle"), (description, "welcomeStepDescription")):
                label.setObjectName(name)
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setWordWrap(True)
                label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                layout.addWidget(label)
            layout.addStretch()
            self.steps[key] = (step, heading, description)
        process.addWidget(captions)
        self.content.addLayout(process)

        self.info = QFrame()
        self.info.setObjectName("welcomeInfoCard")
        self.info_layout = QHBoxLayout(self.info)
        self.info_icon = QLabel()
        self.info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_icon = _welcome_icon("info", "#1262ac")
        self.info_layout.addWidget(self.info_icon)
        info_text = QVBoxLayout()
        info_text.setSpacing(3)
        self.info_layout.addLayout(info_text, 1)
        info_text.addWidget(self.instruction)
        info_text.addWidget(self.reference_note)
        info_row = QHBoxLayout()
        info_row.addStretch(1)
        info_row.addWidget(self.info)
        info_row.addStretch(1)
        self.content.addLayout(info_row)

        self.actions = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.actions.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.actions.setSpacing(8)
        self.load_image = QPushButton()
        self.open_project = QPushButton()
        self.load_image.setIcon(_welcome_icon("folder", "#ffffff"))
        self.open_project.setIcon(_welcome_icon("project", "#104b82"))
        for button, role in ((self.load_image, "primary"), (self.open_project, "secondary")):
            button.setProperty("uiRole", role)
            button.setMinimumHeight(36)
            self.actions.addWidget(button)
        self.content.addLayout(self.actions)
        self.content.addStretch(1)
        self.retranslate_ui()
        self._canvas_viewport.installEventFilter(self)

    def retranslate_ui(self) -> None:
        title = tr("welcome.title")
        before, numeral, after = title.partition("3")
        self.title.setTextFormat(Qt.TextFormat.RichText)
        self.title.setText(f'{escape(before)}<span style="color:#0874d1">{numeral}</span>{escape(after)}')
        self.title.setAccessibleName(title)
        self.subtitle.setText(tr("welcome.subtitle"))
        self.illustration.setAccessibleName(tr("welcome.illustration"))
        for key, (_, heading, description) in self.steps.items():
            heading.setText(tr(f"welcome.step.{key}.title"))
            description.setText(tr(f"welcome.step.{key}.description"))
        self.load_image.setText(tr("welcome.load_image"))
        self.open_project.setText(tr("welcome.open_project"))
        self._update_layout()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "actions"):
            self._update_layout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_layout()

    def eventFilter(self, watched, event) -> bool:
        if (
            watched is self._canvas_viewport and self.isVisible()
            and event.type() in (QEvent.Type.Resize, QEvent.Type.Move)
        ):
            self._update_layout()
        return super().eventFilter(watched, event)

    def _update_layout(self) -> None:
        width, height = self._canvas_viewport.width(), self.viewport().height()
        compact = width < 380 or height < 420
        hide_descriptions = width < 580 or height < 480
        viewport = self.viewport()
        origin = self._canvas_viewport.mapToGlobal(QPoint()).x() - viewport.mapToGlobal(QPoint()).x()
        center_offset = 2 * origin + width - viewport.width() if self.isVisible() else 0
        left = 8 + max(0, center_offset)
        right = 8 + max(0, -center_offset)
        available = max(0, viewport.width() - left - right)
        content_width = min(available, width - 16) if compact else min(available, round(width * 0.75), 1150)
        content_width = max(1, content_width)
        inset = 4 if compact else 16
        self.widget().layout().setContentsMargins(left, inset, right, inset)
        self.card.setFixedWidth(content_width)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(5 if compact else max(10, round(content_width * 0.021)))
        self.arc.setFixedHeight(10 if compact else round(content_width * 0.026))
        gap = max(4, round(content_width * 0.025)) if compact else max(22, min(30, round(content_width * 0.025)))
        self.illustration.fit(content_width, gap, 60 if compact else round(height * 0.37))
        self.caption_grid.setHorizontalSpacing(5 if compact else gap)
        self.caption_grid.setVerticalSpacing(4)
        self.info.setFixedWidth(content_width if compact else round(content_width * 0.83))
        self.instruction.setText(tr("welcome.instruction_compact" if compact else "welcome.instruction"))
        self.reference_note.setText(tr("welcome.reference_note_compact" if compact else "welcome.reference_note"))
        info_margin, info_padding = (5, 4) if compact else (16, 10)
        self.info_layout.setContentsMargins(info_margin, info_padding, info_margin, info_padding)
        self.info_layout.setSpacing(4 if compact else 12)
        icon_size = 17 if compact else 28
        self.info_icon.setPixmap(self._info_icon.pixmap(QSize(icon_size, icon_size)))
        for label in (self.instruction, self.reference_note):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignLeft)
        font = self.title.font()
        font.setPixelSize(48)
        units = QFontMetrics(font).horizontalAdvance(self.title.accessibleName())
        logo_fraction = 0.86 if compact else 0.55
        logo_size = round(48 * logo_fraction * content_width / max(1, units))
        logo_style = f"font-size: {max(15, min(26 if compact else 105, logo_size))}px;"
        if self.title.styleSheet() != logo_style:
            self.title.setStyleSheet(logo_style)
        for label in (self.title, self.subtitle, self.instruction, self.reference_note):
            set_style_property(label, "compact", compact)
        columns = 2 if compact else 4
        if columns != self._caption_columns:
            for index, (step, _, _) in enumerate(self.steps.values()):
                self.caption_grid.removeWidget(step)
                self.caption_grid.addWidget(step, index // columns, index % columns)
            for column in range(4):
                self.caption_grid.setColumnStretch(column, int(column < columns))
            self._caption_columns = columns
        caption_margins = (3, 2, 3, 2) if compact else (6, 4, 6, 5)
        for step, heading, description in self.steps.values():
            step.layout().setContentsMargins(*caption_margins)
            set_style_property(heading, "compact", compact)
            description.setVisible(not hide_descriptions)
        self.actions.setSpacing(5 if compact else max(12, round(content_width * 0.03)))
        for button, fraction in ((self.load_image, 0.36), (self.open_project, 0.285)):
            button.setMinimumHeight(32 if compact else max(40, round(content_width * 0.062)))
            button.setMinimumWidth(0 if compact else round(content_width * fraction))
            button.setIconSize(QSize(16, 16) if compact else QSize(23, 23))
        needed = self.load_image.sizeHint().width() + self.open_project.sizeHint().width() + self.actions.spacing()
        direction = QBoxLayout.Direction.LeftToRight if content_width >= needed else QBoxLayout.Direction.TopToBottom
        self.actions.setDirection(direction)
        alignment = Qt.AlignmentFlag.AlignHCenter if direction == QBoxLayout.Direction.TopToBottom else Qt.AlignmentFlag(0)
        for button in (self.load_image, self.open_project):
            self.actions.setAlignment(button, alignment)
