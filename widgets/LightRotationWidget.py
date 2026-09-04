"""用于控制场景灯光方位的圆环控件。"""

from math import atan2, cos, degrees, radians, sin
from collections.abc import Mapping

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget
from ui.tokens import flatten_theme


class LightRotationWidget(QWidget):
    """使用圆环拖动来设置灯光绕 Z 轴的方位角。"""

    angle_changed = Signal(float)

    def __init__(self, angle: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = angle % 360.0
        self._dragging = False
        self.setMinimumSize(210, 236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.set_theme(flatten_theme("light"))

    def set_theme(self, tokens: Mapping[str, str | int]) -> None:
        self._paint_colors = {
            "card": str(tokens["bg_elevated"]),
            "label": str(tokens["text_secondary"]),
            "value": str(tokens["accent_default"]),
            "ring_default": str(tokens["accent_default"]),
            "ring_hover": str(tokens["accent_hover"]),
            "ring_pressed": str(tokens["accent_pressed"]),
            "sphere_light": str(tokens["border_strong"]),
            "sphere_mid": str(tokens["border_default"]),
            "sphere_dark": str(tokens["text_muted"]),
            "sphere_border": str(tokens["border_strong"]),
            "marker_border": str(tokens["text_primary"]),
        }
        self.update()

    @property
    def angle(self) -> float:
        return self._angle

    def set_angle(self, angle: float, emit_signal: bool = False) -> None:
        normalized = angle % 360.0
        if abs(normalized - self._angle) < 0.01:
            return
        self._angle = normalized
        self.update()
        if emit_signal:
            self.angle_changed.emit(self._angle)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 事件名
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2.0, 104.0)
        radius = min(self.width() * 0.34, 70.0)
        ring_width = 7.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._paint_colors["card"]))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        ring_gradient = QConicalGradient(center, -90)
        ring_gradient.setColorAt(0.0, QColor(self._paint_colors["ring_default"]))
        ring_gradient.setColorAt(0.42, QColor(self._paint_colors["ring_hover"]))
        ring_gradient.setColorAt(0.72, QColor(self._paint_colors["ring_pressed"]))
        ring_gradient.setColorAt(1.0, QColor(self._paint_colors["ring_default"]))
        painter.setPen(QPen(ring_gradient, ring_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        sphere_gradient = QRadialGradient(center - QPointF(8, 8), 24)
        sphere_gradient.setColorAt(0.0, QColor(self._paint_colors["sphere_light"]))
        sphere_gradient.setColorAt(0.72, QColor(self._paint_colors["sphere_mid"]))
        sphere_gradient.setColorAt(1.0, QColor(self._paint_colors["sphere_dark"]))
        painter.setPen(QPen(QColor(self._paint_colors["sphere_border"]), 1.0))
        painter.setBrush(sphere_gradient)
        painter.drawEllipse(center, 20, 20)

        theta = radians(self._angle)
        marker = QPointF(center.x() + radius * sin(theta), center.y() - radius * cos(theta))
        painter.setPen(QPen(QColor(self._paint_colors["marker_border"]), 1.3))
        painter.setBrush(QColor("#fbbf24"))
        painter.drawEllipse(marker, 8.5, 8.5)
        painter.setPen(QPen(QColor("#f59e0b"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for ray in range(8):
            ray_angle = radians(ray * 45.0)
            inner = QPointF(marker.x() + 12 * sin(ray_angle), marker.y() - 12 * cos(ray_angle))
            outer = QPointF(marker.x() + 16 * sin(ray_angle), marker.y() - 16 * cos(ray_angle))
            painter.drawLine(inner, outer)

        label_font = QFont(self.font())
        label_font.setPixelSize(13)
        label_font.setWeight(QFont.Weight.DemiBold)
        painter.setPen(QColor(self._paint_colors["label"]))
        painter.setFont(label_font)
        painter.drawText(0, 188, self.width(), 22, Qt.AlignmentFlag.AlignCenter, "灯光方位")
        value_font = QFont(self.font())
        value_font.setPixelSize(15)
        value_font.setWeight(QFont.Weight.Bold)
        painter.setPen(QColor(self._paint_colors["value"]))
        painter.setFont(value_font)
        painter.drawText(0, 208, self.width(), 25, Qt.AlignmentFlag.AlignCenter, f"{self._angle:.0f}°")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt 事件名
        if event.button() == Qt.MouseButton.LeftButton and self._is_on_ring(event.position()):
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._set_angle_from_position(event.position())
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt 事件名
        if self._dragging:
            self._set_angle_from_position(event.position())
            event.accept()
            return
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt 事件名
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        event.ignore()

    def _is_on_ring(self, position: QPointF) -> bool:
        center = QPointF(self.width() / 2.0, 104.0)
        radius = min(self.width() * 0.34, 70.0)
        distance = ((position.x() - center.x()) ** 2 + (position.y() - center.y()) ** 2) ** 0.5
        return abs(distance - radius) <= 22

    def _set_angle_from_position(self, position: QPointF) -> None:
        center = QPointF(self.width() / 2.0, 104.0)
        angle = degrees(atan2(position.x() - center.x(), center.y() - position.y())) % 360.0
        self.set_angle(angle, emit_signal=True)
