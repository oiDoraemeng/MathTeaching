"""Optional native title-bar theming with safe platform fallbacks."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget

from ui.icons import apply_icon, icon_color, retint_icons

DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# 最大化按钮随窗口状态切换为 Windows 风格的还原图标。
_MAXIMIZE_ICON = "square"
_RESTORE_ICON = "copy"


class _HostStateSync(QObject):
    """Re-sync title-bar controls after the host window changes state."""

    def __init__(self, callback, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowStateChange:
            self._callback()
        return False



class CustomTitleBar(QFrame):
    """Synchronous, theme-aware title bar for the frameless main window."""

    right_panel_toggle_requested = Signal()

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("appTitleBar")
        self.setFixedHeight(36)
        self._host = host
        self._theme = "light"
        self._drag_offset: QPoint | None = None
        self._maximized_shown: bool | None = None
        self._pending_maximized: bool | None = None
        self._state_settle_timer = QTimer(self)
        self._state_settle_timer.setSingleShot(True)
        self._state_settle_timer.timeout.connect(self._release_window_state_transition)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(6)
        self.title = QLabel(host.windowTitle() or "Math3D Teaching", self)
        self.title.setObjectName("appTitle")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title)
        layout.addStretch(1)
        self.right_panel_button = self._window_button(
            "titleBarRightPanel",
            "展开右侧面板",
            "panel-right-open",
        )
        self.minimize_button = self._window_button("titleBarMinimize", "最小化", "minus")
        self.maximize_button = self._window_button("titleBarMaximize", "最大化", _MAXIMIZE_ICON)
        self.close_button = self._window_button("titleBarClose", "关闭", "x")
        for button in (self.right_panel_button, self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button)
        self.right_panel_button.clicked.connect(self.right_panel_toggle_requested)
        self.minimize_button.clicked.connect(self._request_minimized)
        self.maximize_button.clicked.connect(self._toggle_maximized)
        self.close_button.clicked.connect(host.close)
        self._state_sync = _HostStateSync(self._sync_maximize_button, self)
        host.installEventFilter(self._state_sync)
        self._sync_maximize_button(force=True)

    def _window_button(self, object_name: str, tooltip: str, icon_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        apply_icon(button, icon_name, icon_color(self._theme), icon_size=14, hit_size=32)
        return button

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in ("light", "dark") else "light"
        retint_icons(self, self._theme)
        self._sync_maximize_button(force=True)
        self.title.setText(self._host.windowTitle() or "Math3D Teaching")

    def set_right_panel_expanded(self, expanded: bool) -> None:
        """Reflect the right sidebar state with a VS Code-like title-bar glyph."""
        is_expanded = bool(expanded)
        label = "折叠右侧面板" if is_expanded else "展开右侧面板"
        icon_name = "panel-right-close" if is_expanded else "panel-right-open"
        self.right_panel_button.setToolTip(label)
        self.right_panel_button.setAccessibleName(label)
        apply_icon(self.right_panel_button, icon_name, icon_color(self._theme), icon_size=14, hit_size=32)

    def _sync_maximize_button(self, *, force: bool = False) -> None:
        """Mirror the maximize control's glyph and tooltip to the window state."""
        maximized = bool(self._host.isMaximized())
        if maximized == self._maximized_shown and not force:
            self._finish_window_state_transition_if_settled(maximized)
            return
        self._maximized_shown = maximized
        icon_name = _RESTORE_ICON if maximized else _MAXIMIZE_ICON
        label = "还原" if maximized else "最大化"
        self.maximize_button.setToolTip(label)
        self.maximize_button.setAccessibleName(label)
        apply_icon(self.maximize_button, icon_name, icon_color(self._theme), icon_size=14, hit_size=32)
        self._finish_window_state_transition_if_settled(maximized)

    def _finish_window_state_transition_if_settled(self, maximized: bool) -> None:
        if self._pending_maximized is None or maximized != self._pending_maximized:
            return
        self._pending_maximized = None
        self._state_settle_timer.stop()
        self.minimize_button.setEnabled(True)
        self.maximize_button.setEnabled(True)

    def _release_window_state_transition(self) -> None:
        """Never leave the chrome disabled if the window manager drops an event."""
        self._pending_maximized = None
        self.minimize_button.setEnabled(True)
        self.maximize_button.setEnabled(True)
        self._sync_maximize_button(force=True)

    def _begin_window_state_transition(self, expected_maximized: bool) -> bool:
        if self._pending_maximized is not None:
            return False
        self._pending_maximized = expected_maximized
        self.minimize_button.setEnabled(False)
        self.maximize_button.setEnabled(False)
        self._state_settle_timer.start(500)
        return True

    def _request_minimized(self) -> None:
        """Serialize minimize with a pending maximize/restore request."""
        if not self._begin_window_state_transition(bool(self._host.isMaximized())):
            return
        self._host.showMinimized()

    def _toggle_maximized(self) -> None:
        # 窗口状态提交有延迟，图标只以 WindowStateChange 为准。
        target_maximized = not (self._host.isMaximized() or self._host.isFullScreen())
        if not self._begin_window_state_transition(target_maximized):
            return
        if target_maximized:
            self._host.showMaximized()
        else:
            self._host.showNormal()

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
            # Python 测试替身没有 ctypes 函数元数据。
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
