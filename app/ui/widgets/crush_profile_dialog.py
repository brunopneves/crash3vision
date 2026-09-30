from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
)

from app.i18n import tr


class _CrushProfilePlot(QWidget):
    def __init__(self, values_m: list[float], parent=None) -> None:
        super().__init__(parent)
        self.values_m = values_m
        self.setMinimumSize(700, 420)

    def paintEvent(self, event) -> None:
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_plot(painter, self.width(), self.height())

    def _draw_plot(self, painter: QPainter, width: int, height: int) -> None:
        if not self.values_m:
            return

        rect = QRectF(0, 0, width, height)
        painter.fillRect(rect, QColor(250, 250, 250))

        left = 70
        right = 25
        top = 35
        bottom = 60

        plot_rect = QRectF(
            left,
            top,
            max(10, width - left - right),
            max(10, height - top - bottom),
        )

        n = len(self.values_m)
        max_val = max(self.values_m)
        y_min = 0.0

        if max_val <= 0:
            y_max = 0.05
        else:
            y_max = max_val * 1.15

        axis_pen = QPen(QColor(30, 30, 30))
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)

        painter.drawLine(
            int(plot_rect.left()),
            int(plot_rect.top()),
            int(plot_rect.left()),
            int(plot_rect.bottom()),
        )
        painter.drawLine(
            int(plot_rect.left()),
            int(plot_rect.bottom()),
            int(plot_rect.right()),
            int(plot_rect.bottom()),
        )

        grid_pen = QPen(QColor(210, 210, 210))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        grid_pen.setWidth(1)

        tick_font = QFont()
        tick_font.setPointSize(9)
        painter.setFont(tick_font)

        tick_count = 5
        tick_step = (y_max - y_min) / tick_count if tick_count > 0 else 1.0

        for i in range(tick_count + 1):
            y_val = y_min + i * tick_step
            y = (
                plot_rect.bottom()
                - ((y_val - y_min) / (y_max - y_min)) * plot_rect.height()
            )

            painter.setPen(grid_pen)
            painter.drawLine(
                int(plot_rect.left()), int(y), int(plot_rect.right()), int(y)
            )

            painter.setPen(axis_pen)
            painter.drawLine(
                int(plot_rect.left()) - 5, int(y), int(plot_rect.left()), int(y)
            )
            painter.drawText(
                8, int(y) + 4, 50, 18, Qt.AlignmentFlag.AlignRight, f"{y_val:.1f}"
            )

        if n == 1:
            xs = [plot_rect.center().x()]
        else:
            xs = [
                plot_rect.left() + (i / (n - 1)) * plot_rect.width() for i in range(n)
            ]

        points: list[QPointF] = []
        for i, value in enumerate(self.values_m):
            x = xs[i]
            y = (
                plot_rect.bottom()
                - ((value - y_min) / (y_max - y_min)) * plot_rect.height()
            )
            points.append(QPointF(x, y))

        line_pen = QPen(QColor(30, 90, 180))
        line_pen.setWidth(3)
        painter.setPen(line_pen)

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        point_pen = QPen(QColor(180, 30, 30))
        point_pen.setWidth(2)
        painter.setPen(point_pen)
        painter.setBrush(QColor(220, 40, 40))

        for pt in points:
            painter.drawEllipse(pt, 4, 4)

        value_font = QFont()
        value_font.setPointSize(9)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.setPen(QColor(50, 50, 50))

        for i, pt in enumerate(points):
            painter.drawText(
                int(pt.x()) - 24,
                int(pt.y()) - 24,
                48,
                18,
                Qt.AlignmentFlag.AlignCenter,
                f"{self.values_m[i]:.2f}",
            )

        x_font = QFont()
        x_font.setPointSize(10)
        painter.setFont(x_font)
        painter.setPen(axis_pen)

        for i, x in enumerate(xs):
            painter.drawLine(
                int(x), int(plot_rect.bottom()), int(x), int(plot_rect.bottom()) + 5
            )
            painter.drawText(
                int(x) - 20,
                int(plot_rect.bottom()) + 10,
                40,
                20,
                Qt.AlignmentFlag.AlignCenter,
                f"C{i + 1}",
            )

        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)

        painter.drawText(
            int(plot_rect.left()),
            6,
            int(plot_rect.width()),
            20,
            Qt.AlignmentFlag.AlignCenter,
            tr("profile.title"),
        )

        painter.save()
        painter.translate(28, int(plot_rect.center().y()))
        painter.rotate(-90)
        painter.drawText(
            -120, -12, 240, 24, Qt.AlignmentFlag.AlignCenter, tr("profile.y_axis")
        )
        painter.restore()

        painter.drawText(
            int(plot_rect.left()),
            int(plot_rect.bottom()) + 34,
            int(plot_rect.width()),
            20,
            Qt.AlignmentFlag.AlignCenter,
            tr("profile.x_axis"),
        )


class CrushProfileDialog(QDialog):
    def __init__(self, crush_m: list[float], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("profile.window_title"))
        self.resize(860, 560)

        layout = QVBoxLayout(self)

        subtitle = QLabel(tr("profile.subtitle"))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.crush_plot = _CrushProfilePlot(crush_m, self)
        layout.addWidget(self.crush_plot)

        self.btn_export = QPushButton(tr("profile.export_png"))
        self.btn_export.clicked.connect(self._on_export_png)
        layout.addWidget(self.btn_export)

    def _on_export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("profile.export_dialog_title"),
            "",
            "PNG Image (*.png)",
        )
        if not path:
            return

        if not path.lower().endswith(".png"):
            path += ".png"

        try:
            pixmap = QPixmap(self.size())
            pixmap.fill(QColor(255, 255, 255))
            self.render(pixmap)
            if not pixmap.save(path, "PNG"):
                raise ValueError(tr("profile.error.save_failed", path=path))
            QMessageBox.information(
                self, tr("profile.export_dialog_title"), tr("dialog.saved", path=path)
            )
        except Exception as e:
            QMessageBox.critical(self, tr("profile.export_dialog_title"), str(e))
