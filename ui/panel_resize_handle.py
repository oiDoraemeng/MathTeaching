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
    FIXED_WIDTH = 6
    SETTINGS_ORGANIZATION = "Math3DTeaching"
    SETTINGS_APPLICATION = "Math3DTeaching"
    # 位移超过该阈值才算真正拖动，用于区分"连续点击微调"与"双击复位"。
    DRAG_THRESHOLD = 3
    width_changed = Signal(int)
    drag_state_changed = Signal(bool)

    def __init__(self, spec: PanelResizeSpec, *, settings: QSettings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.settings = (
            settings
            if settings is not None
            else QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)
        )
        self.setObjectName("panelResizeHandle")
        self.setFixedWidth(self.FIXED_WIDTH)
        self.setToolTip("拖动调整宽度，双击复位")
        self.setProperty("dragging", False)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._press_x: int | None = None
        # 以面板"当前实际宽度"为拖动基准，避免持久化值与显示宽度不同步时按下即跳变。
        self._current_width = self.restore_width()
        self._press_width = self._current_width
        self._drag_moved = False
        self._last_drag_moved = False

    def _clamp(self, value: int) -> int:
        return max(self.spec.minimum, min(self.spec.maximum, int(value)))

    def restore_width(self) -> int:
        value = self.settings.value(self.spec.settings_key, self.spec.default)
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = self.spec.default
        return self._clamp(value)

    @property
    def current_width(self) -> int:
        """面板当前实际宽度，供拖动基准与松开时持久化使用。"""
        return self._current_width

    def set_width(self, value: int, *, persist: bool = True) -> int:
        width = self._clamp(value)
        self._current_width = width
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
            self._press_width = self._current_width
            self._drag_moved = False
            self._set_dragging(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press_x is not None:
            current_x = event.globalPosition().toPoint().x()
            delta_x = current_x - self._press_x
            if abs(delta_x) >= self.DRAG_THRESHOLD:
                self._drag_moved = True
            # 拖动过程中只更新界面，松开后再持久化，避免每帧同步写磁盘拖慢交互。
            self.set_width(self.width_for_delta(start_width=self._press_width, delta_x=delta_x), persist=False)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._press_x is not None:
            # 只有"点击过程中没有拖动"才允许之后的双击复位。
            self._last_drag_moved = self._drag_moved
            self.settings.setValue(self.spec.settings_key, self._current_width)
            self.settings.sync()
        self._press_x = None
        self._set_dragging(False)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            # 用户在双击间隔内连续微调时系统会把第二次按下识别成双击；
            # 若上一次点击伴随拖动，则视为继续拖动而不复位。
            if not self._last_drag_moved:
                self.set_width(self.spec.default)
            # 双击后仍允许按住继续拖动，基准取当前宽度。
            self._press_x = event.globalPosition().toPoint().x()
            self._press_width = self._current_width
            self._drag_moved = False
        super().mouseDoubleClickEvent(event)

    def _set_dragging(self, value: bool) -> None:
        value = bool(value)
        changed = bool(self.property("dragging")) != value
        self.setProperty("dragging", value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        if changed:
            self.drag_state_changed.emit(value)
