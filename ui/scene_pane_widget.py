"""Qt container that materializes visible :class:`ScenePaneState` objects."""

from __future__ import annotations

from typing import Callable, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ui.scene_pane_manager import ScenePaneManager


class ScenePaneWidget(QWidget):
    """Own the transient viewport controls for panes while states stay retained.

    An interactor is allocated only while its pane is visible.  The state object
    remains in ``ScenePaneManager`` when a pane is hidden, so restoring a layout
    can recreate the control without losing the scene model.
    """

    def __init__(self, manager: ScenePaneManager, parent: QWidget | None = None,
                 interactor_factory: Callable[[QWidget], Any] | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._factory = interactor_factory or self._default_factory
        self._interactors: dict[str, Any] = {}
        self._layout = None
        manager.active_pane_changed.connect(self._on_active_changed)
        self.sync_layout()

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
        for pane_id in tuple(self._interactors):
            if pane_id not in visible_set:
                widget = self._interactors.pop(pane_id)
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
                if pane_id in self.manager.panes:
                    state = self.manager.pane(pane_id)
                    state.renderer_2d = state.renderer_3d = None
        for pane_id in visible:
            if pane_id not in self._interactors:
                widget = self._factory(self)
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                self._interactors[pane_id] = widget
            state = self.manager.pane(pane_id)
            state.renderer_2d = state.renderer_3d = self._interactors[pane_id]
        self._arrange()
        return visible

    def delete_pane(self, pane_id: str) -> tuple[str, ...]:
        self.manager.delete_pane(pane_id)
        return self.sync_layout()

    def set_layout(self, count: int) -> tuple[str, ...]:
        visible = self.manager.set_layout(count)
        return self.sync_layout()

    def _on_active_changed(self, pane_id: str) -> None:
        widget = self._interactors.get(pane_id)
        if widget is not None:
            widget.show()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self._arrange()

    def _arrange(self) -> None:
        rects = self.manager.layout_rects(self.size())
        for pane_id, widget in self._interactors.items():
            if pane_id in rects:
                widget.setGeometry(rects[pane_id])
                widget.show()
