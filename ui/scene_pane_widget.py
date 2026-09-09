"""Qt container that materializes visible :class:`ScenePaneState` objects."""

from __future__ import annotations

from typing import Callable, Any

from PySide6.QtCore import Qt, QEvent, QTimer, QObject
from PySide6.QtWidgets import QWidget, QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QMessageBox
from PySide6.QtCore import Signal
from shiboken6 import isValid

from ui.scene_pane_manager import ScenePaneManager
from services.scene_clipboard import SceneClipboard, rectangle_select


class PaneChrome(QFrame):
    """Reusable pane frame with title and compact window controls."""

    hide_requested = Signal()
    fullscreen_requested = Signal()
    close_requested = Signal()

    def __init__(self, title: str = "", content: QWidget | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("paneChrome")
        self.setProperty("chrome", True)
        self.title_label = QLabel(str(title), self)
        self.title_label.setObjectName("paneChromeTitle")
        self.hide_button = QToolButton(self); self.hide_button.setText("—"); self.hide_button.setToolTip("隐藏窗格")
        self.fullscreen_button = QToolButton(self); self.fullscreen_button.setText("□"); self.fullscreen_button.setToolTip("全屏窗格")
        self.close_button = QToolButton(self); self.close_button.setText("×"); self.close_button.setToolTip("关闭窗格")
        self.close_button.setObjectName("paneChromeClose")
        bar = QHBoxLayout(); bar.setContentsMargins(8, 2, 4, 2); bar.setSpacing(2)
        bar.addWidget(self.title_label); bar.addStretch(); bar.addWidget(self.hide_button); bar.addWidget(self.fullscreen_button); bar.addWidget(self.close_button)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0); root.addLayout(bar)
        if content is not None: root.addWidget(content, 1)
        self.hide_button.clicked.connect(self.hide_requested)
        self.fullscreen_button.clicked.connect(self.fullscreen_requested)
        self.close_button.clicked.connect(self._confirm_close)

    def _confirm_close(self) -> None:
        answer = QMessageBox.question(self, "关闭窗格", "确定关闭此窗格？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.close_requested.emit()

    def set_title(self, title: str) -> None:
        self.title_label.setText(str(title))

    def enterEvent(self, event):
        return super().enterEvent(event)

    def leaveEvent(self, event):
        return super().leaveEvent(event)


class ScenePaneWidget(QWidget):
    """Own the transient viewport controls for panes while states stay retained.

    An interactor is allocated only while its pane is visible.  The state object
    remains in ``ScenePaneManager`` when a pane is hidden, so restoring a layout
    can recreate the control without losing the scene model.
    """

    def __init__(self, manager: ScenePaneManager, parent: QWidget | None = None,
                 interactor_factory: Callable[[QWidget], Any] | None = None,
                 on_interactor_created: Callable[[str, Any], None] | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._factory = interactor_factory or self._default_factory
        self._on_interactor_created = on_interactor_created
        self._interactors: dict[str, Any] = {}
        self._chromes: dict[str, PaneChrome] = {}
        self._retry_attempts: dict[str, int] = {}
        self._retry_timers: dict[str, QTimer] = {}
        self._refresh_callbacks: dict[str, Callable[[str], None]] = {}
        self._refreshing = False
        self.clipboard = SceneClipboard()
        manager.active_pane_changed.connect(self._on_active_changed)
        manager.pane_renamed.connect(self._on_pane_renamed)
        manager.visible_panes_changed.connect(self.sync_layout)
        manager.workspace_restored.connect(self._restore_workspace)
        self.sync_layout()

    def _restore_workspace(self) -> None:
        for pane_id in tuple(self._interactors):
            self._discard_interactor(pane_id, save_camera=False)
        self.sync_layout()

    def select_rectangle(self, rect, pane_id=None):
        """Return and retain 2-D objects whose anchor lies within rect."""
        pane = self.manager.pane(pane_id or self.manager.active_pane_id)
        runtime = getattr(pane, "runtime", None)
        objects = [] if runtime is None else [*getattr(runtime, "geometry_points", []), *getattr(runtime, "linear_objects", []), *getattr(runtime, "annotations", []), *getattr(runtime, "curve_layers", [])]
        selected = rectangle_select(objects, rect)
        pane.selected_object_ids = [getattr(item, "id", "") for item in selected]
        return selected

    @staticmethod
    def _default_factory(parent: QWidget) -> Any:
        from pyvistaqt import QtInteractor
        return QtInteractor(parent)

    @property
    def interactors(self) -> dict[str, Any]:
        return dict(self._interactors)

    def interactor(self, pane_id: str | None = None) -> Any | None:
        return self._interactors.get(pane_id or self.manager.active_pane_id)

    def sync_layout(self) -> tuple[str, ...]:
        visible = self.manager.visible_pane_ids()
        visible_set = set(visible)
        for pane_id in set(self._interactors) | set(self._retry_attempts):
            if pane_id not in visible_set:
                self._clear_retry(pane_id)
                self._discard_interactor(pane_id)
        self.refresh_visible_panes()
        return visible

    def _discard_interactor(self, pane_id: str, *, save_camera: bool = True) -> None:
        widget = self._interactors.pop(pane_id, None)
        chrome = self._chromes.pop(pane_id, None)
        if pane_id in self.manager.panes:
            state = self.manager.pane(pane_id)
            self._clear_interactor_transients(state.runtime)
            camera = getattr(widget, "camera", None)
            if camera is not None and save_camera:
                try:
                    position = [list(camera.position), list(camera.focal_point), list(camera.up)]
                    saved = {"position": position}
                    if state.scene_mode == "2d":
                        saved["parallel_scale"] = float(camera.parallel_scale)
                        state.camera_2d = saved
                    else:
                        state.camera_3d = saved
                    if state.runtime is not None:
                        if state.scene_mode == "2d":
                            state.runtime._two_d_camera_position = position
                            state.runtime._two_d_parallel_scale = saved["parallel_scale"]
                        else:
                            state.runtime._three_d_camera_position = position
                except (AttributeError, TypeError, ValueError, RuntimeError):
                    pass
            state.renderer_2d = state.renderer_3d = None
        if widget is not None and isValid(widget):
            # Finalize the VTK render window before materializing replacements;
            # deferred Qt deletion alone can keep more than four contexts live.
            widget.close()
        if chrome is not None and isValid(chrome):
            chrome.hide(); chrome.setParent(None); chrome.deleteLater()
        elif widget is not None and isValid(widget):
            try:
                widget.hide()
                widget.close()
            except RuntimeError:
                pass
            if isValid(widget):
                widget.setParent(None)
                widget.deleteLater()

    @staticmethod
    def _clear_interactor_transients(runtime: Any | None) -> None:
        """Drop Qt selection objects and drag state tied to a discarded surface."""
        if runtime is None:
            return
        band = getattr(runtime, "_selection_band", None)
        if band is not None:
            try:
                if isValid(band):
                    band.hide()
            except (RuntimeError, TypeError):
                pass
        for name, value in (
            ("_selection_band", None), ("_selection_start", None),
            ("_selection_pixel_start", None), ("_dragging_point_id", None),
            ("_drag_start_geometry_state", None), ("_drag_moved", False),
        ):
            if hasattr(runtime, name):
                setattr(runtime, name, value)

    def _create_interactor(self, pane_id: str) -> Any:
        chrome = PaneChrome(self.manager.pane(pane_id).name, parent=self)
        widget = self._factory(chrome)
        chrome.layout().addWidget(widget, 1)
        self._chromes[pane_id] = chrome
        chrome.hide_requested.connect(lambda pid=pane_id: self._hide_pane(pid))
        chrome.fullscreen_requested.connect(lambda pid=pane_id: self._fullscreen_pane(pid))
        chrome.close_requested.connect(lambda pid=pane_id: self.delete_pane(pid))
        self._interactors[pane_id] = widget
        widget.setObjectName("scenePane")
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        widget.installEventFilter(self)
        receiver = getattr(widget, "interactor", widget)
        if receiver is not widget:
            receiver.installEventFilter(self)
        state = self.manager.pane(pane_id)
        state.renderer_2d = state.renderer_3d = widget
        if not self._renderer_valid(widget):
            raise RuntimeError("renderer initialization failed")
        if self._on_interactor_created is not None:
            self._on_interactor_created(pane_id, widget)
        return widget

    def _hide_pane(self, pane_id: str) -> None:
        visible = [pid for pid in self.manager.visible_pane_ids() if pid != pane_id]
        if visible:
            self.manager.set_visible_panes(visible); self.sync_layout()

    def _fullscreen_pane(self, pane_id: str) -> None:
        self.manager.set_visible_panes([pane_id]); self.sync_layout()

    @staticmethod
    def _renderer_valid(renderer: Any) -> bool:
        if renderer is None:
            return False
        try:
            if isinstance(renderer, QObject) and not isValid(renderer):
                return False
            if getattr(renderer, "_closed", False) or getattr(renderer, "_deleted", False):
                return False
            # Plain QWidget test renderers need no VTK surface. For real
            # interactors a missing underlying surface means it was finalized.
            missing = object()
            for name in ("interactor", "render_window", "ren_win"):
                owner = getattr(renderer, name, missing)
                if owner is missing:
                    continue
                if owner is None or (isinstance(owner, QObject) and not isValid(owner)):
                    return False
                if getattr(owner, "_deleted", False):
                    return False
            checker = getattr(renderer, "isValid", None)
            if callable(checker):
                return bool(checker())
            checker = getattr(renderer, "is_valid", None)
            if callable(checker):
                return bool(checker())
        except Exception:
            return False
        return True

    def refresh_visible_panes(self, on_refresh: Callable[[str], None] | None = None) -> None:
        """Refresh each surface; recovery failure never prevents sibling redraws."""
        if self._refreshing:
            return
        self._refreshing = True
        try:
            for pane_id in self.manager.visible_pane_ids():
                if on_refresh is not None:
                    self._refresh_callbacks[pane_id] = on_refresh
                if pane_id not in self._retry_timers:
                    # A later show/resize/restore can start a fresh bounded cycle.
                    self._retry_attempts.pop(pane_id, None)
                    self._refresh_pane(pane_id)
            self._update_highlight()
        finally:
            self._refreshing = False

    def _refresh_pane(self, pane_id: str) -> None:
        if pane_id not in self.manager.visible_pane_ids():
            self._clear_retry(pane_id)
            return
        try:
            widget = self._interactors.get(pane_id)
            if not self._renderer_valid(widget):
                self._discard_interactor(pane_id)
                widget = self._create_interactor(pane_id)
            chrome = self._chromes.get(pane_id)
            target = chrome or widget
            target.setGeometry(self.manager.layout_rects(self.size())[pane_id])
            # Hidden/unmapped is expected during minimization; show then render
            # first instead of treating invisibility as context loss.
            target.show(); widget.show()
            widget.update()
            callback = self._refresh_callbacks.get(pane_id)
            if callback is not None:
                callback(pane_id)
            else:
                render = getattr(widget, "render", None)
                if callable(render) and getattr(type(widget), "render", None) is not QWidget.render:
                    render()
        except Exception:
            self._discard_interactor(pane_id)
            self._schedule_retry(pane_id)
        else:
            self._clear_retry(pane_id)
        self._update_highlight()

    def _schedule_retry(self, pane_id: str) -> None:
        if pane_id in self._retry_timers:
            return
        attempt = self._retry_attempts.get(pane_id, 0)
        if attempt >= 4:
            return
        self._retry_attempts[pane_id] = attempt + 1
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(50 * 2 ** attempt)
        self._retry_timers[pane_id] = timer

        def retry() -> None:
            self._retry_timers.pop(pane_id, None)
            timer.deleteLater()
            self._refresh_pane(pane_id)

        timer.timeout.connect(retry)
        timer.start()

    def _clear_retry(self, pane_id: str) -> None:
        timer = self._retry_timers.pop(pane_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        self._retry_attempts.pop(pane_id, None)
        self._refresh_callbacks.pop(pane_id, None)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn):
            for pane_id, widget in self._interactors.items():
                if watched is widget or watched is getattr(widget, "interactor", None):
                    self.manager.focus_pane(pane_id)
                    self._update_highlight()
                    break
        return super().eventFilter(watched, event)

    def _update_highlight(self) -> None:
        active = self.manager.active_pane_id
        for pane_id, widget in self._interactors.items():
            if not isValid(widget):
                continue
            is_active = pane_id == active
            # The visible border is drawn by PaneChrome; keep the renderer
            # property too for backwards-compatible styling and tests.
            for target in (widget, self._chromes.get(pane_id)):
                if target is None or not isValid(target):
                    continue
                target.setProperty("activePane", is_active)
                target.style().unpolish(target)
                target.style().polish(target)

    def delete_pane(self, pane_id: str) -> tuple[str, ...]:
        self.manager.delete_pane(pane_id)
        result = self.sync_layout()
        self.pane_closed.emit(pane_id)
        return result

    def set_layout(self, count: int) -> tuple[str, ...]:
        visible = self.manager.set_layout(count)
        return self.sync_layout()

    def _on_active_changed(self, pane_id: str) -> None:
        widget = self._interactors.get(pane_id)
        if widget is not None and isValid(widget):
            widget.show()
        self._update_highlight()

    def _on_pane_renamed(self, pane_id: str, title: str) -> None:
        chrome = self._chromes.get(pane_id)
        if chrome is not None and isValid(chrome):
            chrome.set_title(title)

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self.refresh_visible_panes()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.refresh_visible_panes()
    pane_closed = Signal(str)
