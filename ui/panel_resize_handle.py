"""Reusable persisted horizontal panel resize handle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import QPoint, QSettings, Qt, Signal
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class PanelResizeSpec:
    minimum: int
    maximum: int
    default: int
    settings_key: str
    edge: Literal["right", "left"]


class _PanelResizeHandle(QWidget):
    width_changed = Signal(int)

    def __init__(self, spec: PanelResizeSpec, *, settings: QSettings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.settings = settings or QSettings()
        self.setFixedWidth(5)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._press_x: int | None = None
        self._press_width = self.restore_width()

    def _clamp(self, value: int) -> int:
        return max(self.spec.minimum, min(self.spec.maximum, int(value)))

    def restore_width(self) -> int:
        value = self.settings.value(self.spec.settings_key, self.spec.default)
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = self.spec.default
        return self._clamp(value)

    def set_width(self, value: int, *, persist: bool = True) -> int:
        width = self._clamp(value)
        if persist:
            self.settings.setValue(self.spec.settings_key, width)
        self.width_changed.emit(width)
        return width

    def width_for_delta(self, *, start_width: int, delta_x: int) -> int:
        delta = delta_x if self.spec.edge == "right" else -delta_x
        return self._clamp(start_width + delta)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_x = event.globalPosition().toPoint().x()
            self._press_width = self.restore_width()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_x is not None:
            current_x = event.globalPosition().toPoint().x()
            self.set_width(self.width_for_delta(start_width=self._press_width, delta_x=current_x - self._press_x))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_x = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_width(self.spec.default)
        super().mouseDoubleClickEvent(event)
