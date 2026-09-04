"""Optional native title-bar theming with safe platform fallbacks."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget

from ui.icons import apply_icon, icon_color, retint_icons

DWMWA_USE_IMMERSIVE_DARK_MODE = 20


class CustomTitleBar(QFrame):
    """Synchronous, theme-aware title bar for the frameless main window."""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("appTitleBar")
        self.setFixedHeight(36)
        self._host = host
        self._drag_offset: QPoint | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(6)
        self.title = QLabel(host.windowTitle() or "Math3D Teaching", self)
        self.title.setObjectName("appTitle")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title)
        layout.addStretch(1)
        self.minimize_button = self._window_button("titleBarMinimize", "最小化", "minus")
        self.maximize_button = self._window_button("titleBarMaximize", "最大化", "square")
        self.close_button = self._window_button("titleBarClose", "关闭", "x")
        for button in (self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button)
        self.minimize_button.clicked.connect(host.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximized)
        self.close_button.clicked.connect(host.close)

    @staticmethod
    def _window_button(object_name: str, tooltip: str, icon_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        apply_icon(button, icon_name, icon_color(), icon_size=14, hit_size=32)
        return button

    def set_theme(self, theme: str) -> None:
        retint_icons(self, theme)
        self.title.setText(self._host.windowTitle() or "Math3D Teaching")

    def _toggle_maximized(self) -> None:
        if self._host.isMaximized():
            self._host.showNormal()
        else:
            self._host.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._host.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton and not self._host.isMaximized():
            self._host.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def apply_native_titlebar_theme(window: QWidget, effective_theme: str) -> bool:
    """Apply the Windows immersive title-bar flag when the API is available."""
    if window.property("math3d_custom_titlebar"):
        return False
    if sys.platform != "win32" or effective_theme not in ("light", "dark"):
        return False
    try:
        enabled = ctypes.c_int(1 if effective_theme == "dark" else 0)
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        try:
            set_window_attribute.argtypes = (
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_uint,
            )
            set_window_attribute.restype = ctypes.c_long
        except (AttributeError, TypeError):
            # Python test doubles do not expose ctypes function metadata.
            pass
        result = set_window_attribute(
            ctypes.c_void_p(int(window.winId())),
            ctypes.c_uint(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(enabled),
            ctypes.c_uint(ctypes.sizeof(enabled)),
        )
    except (AttributeError, OSError, OverflowError, TypeError, ValueError, ctypes.ArgumentError):
        return False
    return result == 0


class _TitlebarTracker(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange)
            and isinstance(watched, QWidget)
            and watched.isWindow()
            and not watched.property("math3d_custom_titlebar")
        ):
            app = QApplication.instance()
            theme = app.property("math3d_effective_theme") if app else None
            if theme in ("light", "dark"):
                apply_native_titlebar_theme(watched, theme)
        return False


def install_titlebar_tracker(app: QApplication) -> None:
    """Install one process-wide tracker for top-level window lifecycle events."""
    if app.property("math3d_titlebar_tracker") is None:
        tracker = _TitlebarTracker(app)
        app.setProperty("math3d_titlebar_tracker", tracker)
        app.installEventFilter(tracker)
