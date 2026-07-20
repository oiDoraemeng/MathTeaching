"""用于控制场景灯光方位的圆环控件。"""

from math import atan2, cos, degrees, radians, sin

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget


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
        painter.setBrush(QColor("#f4f6f9"))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        ring_gradient = QConicalGradient(center, -90)
        ring_gradient.setColorAt(0.0, QColor("#2563eb"))
        ring_gradient.setColorAt(0.42, QColor("#60a5fa"))
        ring_gradient.setColorAt(0.72, QColor("#1d4ed8"))
        ring_gradient.setColorAt(1.0, QColor("#2563eb"))
        painter.setPen(QPen(ring_gradient, ring_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        sphere_gradient = QRadialGradient(center - QPointF(8, 8), 24)
        sphere_gradient.setColorAt(0.0, QColor("#eef1f5"))
        sphere_gradient.setColorAt(0.72, QColor("#aab2bd"))
        sphere_gradient.setColorAt(1.0, QColor("#727b88"))
        painter.setPen(QPen(QColor("#8b95a2"), 1.0))
        painter.setBrush(sphere_gradient)
        painter.drawEllipse(center, 20, 20)

        theta = radians(self._angle)
        marker = QPointF(center.x() + radius * sin(theta), center.y() - radius * cos(theta))
        painter.setPen(QPen(QColor("#1e3a8a"), 1.3))
        painter.setBrush(QColor("#fbbf24"))
        painter.drawEllipse(marker, 8.5, 8.5)
        painter.setPen(QPen(QColor("#f59e0b"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for ray in range(8):
            ray_angle = radians(ray * 45.0)
            inner = QPointF(marker.x() + 12 * sin(ray_angle), marker.y() - 12 * cos(ray_angle))
            outer = QPointF(marker.x() + 16 * sin(ray_angle), marker.y() - 16 * cos(ray_angle))
            painter.drawLine(inner, outer)

        painter.setPen(QColor("#475569"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        painter.drawText(0, 188, self.width(), 22, Qt.AlignmentFlag.AlignCenter, "灯光方位")
        painter.setPen(QColor("#1d4ed8"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
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
