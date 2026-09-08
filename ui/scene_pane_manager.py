"""Layout, focus, and global history management for ordinary scene panes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, QRect, QSize, Signal

from ui.scene_pane_state import ScenePaneState


@dataclass(frozen=True)
class HistoryEntry:
    """One reversible operation, kept in the order it occurred globally."""

    pane_id: str
    undo: Callable[[], Any]
    redo: Callable[[], Any]
    description: str = ""


class ScenePaneManager(QObject):
    """Own runtime pane states and the visible layout without owning widgets."""

    active_pane_changed = Signal(str)
    # A descriptive alias for consumers which prefer signal names that mirror
    # the property they observe.
    active_pane_id_changed = Signal(str)

    MIN_PANES = 1
    MAX_PANES = 4

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._panes: dict[str, ScenePaneState] = {}
        self._pane_order: list[str] = []
        self._layout_count = 1
        self._next_pane_id_number = 1
        self._display_numbers: dict[str, int] = {}
        self._undo_stack: list[HistoryEntry] = []
        self._redo_stack: list[HistoryEntry] = []
        self._active_pane_id = self.create_pane()

    @property
    def active_pane_id(self) -> str:
        return self._active_pane_id

    @property
    def panes(self) -> dict[str, ScenePaneState]:
        """The live pane-state mapping (keyed by stable pane ID)."""
        return self._panes

    @property
    def history(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._undo_stack)

    def pane(self, pane_id: str) -> ScenePaneState:
        try:
            return self._panes[pane_id]
        except KeyError as error:
            raise ValueError(f"unknown pane ID: {pane_id}") from error

    def set_layout(self, count: int) -> tuple[str, ...]:
        """Show *count* panes, allocating blank states as needed.

        Reducing a layout only hides states: it never discards their contents.
        """
        if type(count) is not int or not self.MIN_PANES <= count <= self.MAX_PANES:
            raise ValueError("layout count must be an integer from 1 to 4")
        while len(self._pane_order) < count:
            self.create_pane()
        self._layout_count = count
        visible = self.visible_pane_ids()
        if self._active_pane_id not in visible:
            self._set_active_pane(visible[0])
        return visible

    def visible_pane_ids(self) -> tuple[str, ...]:
        return tuple(self._pane_order[: self._layout_count])

    def layout_count_for_pane(self, pane_id: str) -> int:
        """Return the smallest layout that includes this pane in scene order."""
        self.pane(pane_id)
        return self._pane_order.index(pane_id) + 1

    def focus_pane(self, pane_id: str) -> str:
        """Make a visible pane active and notify listeners when it changes."""
        if pane_id not in self._panes:
            raise ValueError(f"unknown pane ID: {pane_id}")
        if pane_id not in self.visible_pane_ids():
            raise ValueError(f"cannot focus hidden pane: {pane_id}")
        self._set_active_pane(pane_id)
        return pane_id

    def activate_for_tool(self, pane_id: str | None = None) -> str:
        """Activate the pane receiving a tool command (or keep current)."""
        return self.focus_pane(pane_id or self._active_pane_id)

    def create_pane(self) -> str:
        """Create a retained, initially hidden-or-visible blank pane state."""
        if len(self._pane_order) >= self.MAX_PANES:
            raise RuntimeError("cannot create more than four panes")
        pane_id = f"pane-{self._next_pane_id_number}"
        self._next_pane_id_number += 1
        display_number = next(
            number for number in range(1, self.MAX_PANES + 1)
            if number not in self._display_numbers.values()
        )
        self._panes[pane_id] = ScenePaneState(pane_id, f"窗格 {display_number}")
        self._pane_order.append(pane_id)
        self._display_numbers[pane_id] = display_number
        return pane_id

    def delete_pane(self, pane_id: str) -> None:
        """Permanently remove a pane and repair the layout and active focus."""
        if pane_id not in self._panes:
            raise ValueError(f"unknown pane ID: {pane_id}")
        if len(self._pane_order) <= self.MIN_PANES:
            raise RuntimeError("cannot delete the last pane")
        was_active = pane_id == self._active_pane_id
        self._pane_order.remove(pane_id)
        del self._panes[pane_id]
        del self._display_numbers[pane_id]
        # A deleted pane's callbacks may close over state that no longer
        # exists.  They cannot safely be replayed by global history.
        self._undo_stack = [entry for entry in self._undo_stack if entry.pane_id != pane_id]
        self._redo_stack = [entry for entry in self._redo_stack if entry.pane_id != pane_id]
        self._layout_count = min(self._layout_count, len(self._pane_order))
        visible = self.visible_pane_ids()
        if was_active or self._active_pane_id not in visible:
            self._set_active_pane(visible[0])

    def layout_rects(self, size: QSize) -> dict[str, QRect]:
        """Return each visible pane's rectangle for the requested viewport size."""
        if not isinstance(size, QSize):
            raise TypeError("size must be a QSize")
        width, height = size.width(), size.height()
        left_width, top_height = width // 2, height // 2
        right_width, bottom_height = width - left_width, height - top_height
        ids = self.visible_pane_ids()
        if len(ids) == 1:
            return {ids[0]: QRect(0, 0, width, height)}
        if len(ids) == 2:
            return {
                ids[0]: QRect(0, 0, left_width, height),
                ids[1]: QRect(left_width, 0, right_width, height),
            }
        if len(ids) == 3:
            return {
                ids[0]: QRect(0, 0, left_width, height),
                ids[1]: QRect(left_width, 0, right_width, top_height),
                ids[2]: QRect(left_width, top_height, right_width, bottom_height),
            }
        return {
            ids[0]: QRect(0, 0, left_width, top_height),
            ids[1]: QRect(left_width, 0, right_width, top_height),
            ids[2]: QRect(0, top_height, left_width, bottom_height),
            ids[3]: QRect(left_width, top_height, right_width, bottom_height),
        }

    def push(self, entry: HistoryEntry | str, undo: Callable[[], Any] | None = None,
             redo: Callable[[], Any] | None = None, description: str = "") -> HistoryEntry:
        """Push a global history entry and invalidate redo history.

        The expanded arguments make simple callers convenient while accepting a
        pre-built :class:`HistoryEntry` for richer command layers.
        """
        if isinstance(entry, HistoryEntry):
            history_entry = entry
        else:
            if entry not in self._panes:
                raise ValueError(f"unknown pane ID: {entry}")
            if not callable(undo) or not callable(redo):
                raise TypeError("undo and redo must be callable")
            history_entry = HistoryEntry(entry, undo, redo, description)
        if history_entry.pane_id not in self._panes:
            raise ValueError(f"unknown pane ID: {history_entry.pane_id}")
        self._undo_stack.append(history_entry)
        self._redo_stack.clear()
        return history_entry

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        entry = self._undo_stack[-1]
        entry.undo()
        self._undo_stack.pop()
        self._redo_stack.append(entry)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        entry = self._redo_stack[-1]
        entry.redo()
        self._redo_stack.pop()
        self._undo_stack.append(entry)
        return True

    def _set_active_pane(self, pane_id: str) -> None:
        if pane_id == self._active_pane_id:
            return
        self._active_pane_id = pane_id
        self.active_pane_changed.emit(pane_id)
        self.active_pane_id_changed.emit(pane_id)
