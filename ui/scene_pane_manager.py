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
    # Emitted after a pane is permanently removed.  UI hosts use this to
    # discard associated tabs/widgets without duplicating deletion logic.
    pane_deleted = Signal(str)

    MIN_PANES = 1
    MAX_PANES = 4  # maximum visible panes; total retained panes is unbounded

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._panes: dict[str, ScenePaneState] = {}
        self._pane_order: list[str] = []
        self._layout_count = 1
        self._visible_ids: list[str] = []
        self._lecture_user_visible: tuple[str, ...] | None = None
        self._lecture_case_ids: tuple[str, ...] = ()
        self._next_pane_id_number = 1
        self._display_numbers: dict[str, int] = {}
        self._undo_stack: list[HistoryEntry] = []
        self._redo_stack: list[HistoryEntry] = []
        self._active_pane_id = self.create_pane()

    @property
    def active_pane_id(self) -> str:
        return self._active_pane_id

    def active_pane(self) -> ScenePaneState:
        """Return the state receiving user tool operations."""
        return self._panes[self._active_pane_id]

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
        for pid in self._pane_order:
            if len(self._visible_ids) >= count:
                break
            if pid not in self._visible_ids:
                self._visible_ids.append(pid)
        visible = tuple(self._visible_ids[:count])
        self._visible_ids = list(visible)
        if self._active_pane_id not in visible:
            self._set_active_pane(visible[0])
        return visible

    def visible_pane_ids(self) -> tuple[str, ...]:
        return tuple(self._visible_ids[: self._layout_count])

    @property
    def user_visible_pane_ids(self) -> tuple[str, ...]:
        return tuple(pid for pid in self._visible_ids if self._panes[pid].source == "user")

    def set_visible_panes(self, pane_ids: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        ids = list(dict.fromkeys(pane_ids))
        if len(ids) > self.MAX_PANES:
            raise ValueError("visible pane count cannot exceed four")
        if any(pid not in self._panes for pid in ids):
            raise ValueError("unknown pane ID")
        # Keep at least one visible pane whenever retained states exist.  A
        # transient empty set (for example while closing the last visible
        # pane) leaves layout and active-focus consumers without a target.
        if not ids and self._pane_order:
            ids = [self._pane_order[0]]
        self._visible_ids = ids
        self._layout_count = max(1, len(ids)) if ids else 1
        if self._active_pane_id not in ids and ids:
            self._set_active_pane(ids[0])
        return tuple(ids)

    def enter_lecture(self, case_id: str, case_ids: tuple[str, ...] | list[str] | None = None) -> tuple[str, ...]:
        self._lecture_user_visible = self.user_visible_pane_ids
        allowed = set(case_ids) if case_ids is not None else None
        cases = [pid for pid in self._pane_order
                 if self._panes[pid].source == "case"
                 and (allowed is None or self._panes[pid].source_id in allowed)]
        self._lecture_case_ids = tuple(cases)
        selected = next((pid for pid in cases if self._panes[pid].source_id == case_id), None)
        return self.set_visible_panes([selected] if selected else [])

    def leave_lecture(self) -> tuple[str, ...]:
        restored = self._lecture_user_visible
        if restored is None:
            # A defensive fallback for callers that leave without entering:
            # retain the current layout's first user pane only.
            restored = tuple(self.user_visible_pane_ids[:1])
        self._lecture_user_visible = None
        self._lecture_case_ids = ()
        return self.set_visible_panes(list(restored))

    def show_all_cases(self) -> tuple[str, ...]:
        return self.set_visible_panes([pid for pid in self._lecture_case_ids if pid in self._panes][: self.MAX_PANES])

    def show_case(self, case_id: str) -> tuple[str, ...]:
        pid = next((pid for pid in self._pane_order if self._panes[pid].source == "case" and self._panes[pid].source_id == case_id), None)
        if pid is None:
            raise ValueError(f"unknown case ID: {case_id}")
        return self.set_visible_panes([pid])

    def register_case(self, case_id: str, *, name: str | None = None) -> str:
        """Register a retained teaching case as a regular pane state."""
        existing = next((pid for pid in self._pane_order if self._panes[pid].source == "case" and self._panes[pid].source_id == case_id), None)
        if existing is not None:
            return existing
        return self.create_pane(source="case", source_id=case_id, name=name or case_id)

    # Callback-friendly aliases used by the teaching-case host.
    open_case = register_case

    def close_case(self, case_id: str) -> None:
        pane_id = next((pid for pid in self._pane_order if self._panes[pid].source == "case" and self._panes[pid].source_id == case_id), None)
        if pane_id is None:
            raise ValueError(f"unknown case ID: {case_id}")
        self.delete_pane(pane_id)

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

    def create_pane(self, *, source: str = "user", source_id: str | None = None, name: str | None = None) -> str:
        """Create a retained, initially hidden-or-visible blank pane state."""
        if source not in {"user", "case"}:
            raise ValueError("source must be user or case")
        pane_id = f"pane-{self._next_pane_id_number}"
        self._next_pane_id_number += 1
        display_number = next(number for number in range(1, len(self._pane_order) + 2) if number not in self._display_numbers.values())
        self._panes[pane_id] = ScenePaneState(pane_id, name or f"窗格 {display_number}", source=source, source_id=source_id)
        self._pane_order.append(pane_id)
        self._display_numbers[pane_id] = display_number
        if not self._visible_ids:
            self._visible_ids.append(pane_id)
        return pane_id

    def delete_pane(self, pane_id: str) -> None:
        """Permanently remove a pane and repair the layout and active focus."""
        if pane_id not in self._panes:
            raise ValueError(f"unknown pane ID: {pane_id}")
        if len(self._pane_order) <= self.MIN_PANES:
            raise RuntimeError("cannot delete the last pane")
        was_active = pane_id == self._active_pane_id
        self._pane_order.remove(pane_id)
        if pane_id in self._visible_ids:
            self._visible_ids.remove(pane_id)
        del self._panes[pane_id]
        del self._display_numbers[pane_id]
        # A deleted pane's callbacks may close over state that no longer
        # exists.  They cannot safely be replayed by global history.
        self._undo_stack = [entry for entry in self._undo_stack if entry.pane_id != pane_id]
        self._redo_stack = [entry for entry in self._redo_stack if entry.pane_id != pane_id]
        self._layout_count = max(1, min(self._layout_count, len(self._visible_ids) or len(self._pane_order)))
        visible = self.visible_pane_ids()
        if not visible and self._pane_order:
            self._visible_ids = [self._pane_order[0]]
            self._layout_count = 1
            visible = self.visible_pane_ids()
        if was_active or self._active_pane_id not in visible:
            self._set_active_pane(visible[0])
        self.pane_deleted.emit(pane_id)

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
        if entry.pane_id in self.visible_pane_ids():
            self._set_active_pane(entry.pane_id)
        entry.undo()
        self._undo_stack.pop()
        self._redo_stack.append(entry)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        entry = self._redo_stack[-1]
        if entry.pane_id in self.visible_pane_ids():
            self._set_active_pane(entry.pane_id)
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
