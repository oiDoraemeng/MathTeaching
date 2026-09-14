from PySide6.QtCore import QSize
import pytest

from ui.scene_pane_manager import HistoryEntry, ScenePaneManager
from ui.scene_pane_state import ScenePaneState


def test_layouts_have_expected_visible_panes_and_rectangles() -> None:
    manager = ScenePaneManager()
    assert manager.set_layout(1) == ("pane-1",)
    assert manager.layout_rects(QSize(101, 81))["pane-1"].getRect() == (0, 0, 101, 81)

    ids = manager.set_layout(2)
    rects = manager.layout_rects(QSize(101, 81))
    assert ids == ("pane-1", "pane-2")
    assert rects[ids[0]].getRect() == (0, 0, 50, 81)
    assert rects[ids[1]].getRect() == (50, 0, 51, 81)

    ids = manager.set_layout(3)
    rects = manager.layout_rects(QSize(100, 80))
    assert [rects[pane_id].getRect() for pane_id in ids] == [
        (0, 0, 50, 80), (50, 0, 50, 40), (50, 40, 50, 40)
    ]

    ids = manager.set_layout(4)
    rects = manager.layout_rects(QSize(100, 80))
    assert [rects[pane_id].getRect() for pane_id in ids] == [
        (0, 0, 50, 40), (50, 0, 50, 40), (0, 40, 50, 40), (50, 40, 50, 40)
    ]


def test_hiding_preserves_state_and_keeps_active_pane_visible() -> None:
    manager = ScenePaneManager()
    pane_two = manager.set_layout(2)[1]
    manager.pane(pane_two).scene_2d["objects"] = [{"id": "P"}]
    changes: list[str] = []
    manager.active_pane_changed.connect(changes.append)
    manager.focus_pane(pane_two)
    assert changes == [pane_two]

    assert manager.set_layout(1) == (pane_two,)
    assert manager.active_pane_id == pane_two
    assert manager.set_layout(2) == (pane_two, "pane-1")
    assert manager.pane(pane_two).scene_2d["objects"] == [{"id": "P"}]


@pytest.mark.parametrize("active_index", [2, 3])
def test_shrinking_layout_keeps_later_active_pane_visible(active_index: int) -> None:
    manager = ScenePaneManager()
    pane_ids = manager.set_layout(4)
    manager.focus_pane(pane_ids[active_index])

    assert manager.set_layout(1) == (pane_ids[active_index],)
    assert manager.active_pane_id == pane_ids[active_index]


def test_focus_limits_and_delete_repair() -> None:
    manager = ScenePaneManager()
    ids = manager.set_layout(4)
    fifth = manager.create_pane()
    assert fifth not in manager.visible_pane_ids()
    assert len(manager.panes) == 5
    manager.focus_pane(ids[2])
    manager.delete_pane(ids[2])
    assert ids[2] not in manager.panes
    assert manager.visible_pane_ids() == (ids[0], ids[1], ids[3])
    assert manager.active_pane_id == ids[0]
    with pytest.raises(ValueError, match="hidden"):
        manager.focus_pane(manager.create_pane())


def test_replacement_reuses_lowest_available_display_number() -> None:
    manager = ScenePaneManager()
    pane_ids = manager.set_layout(4)
    manager.delete_pane(pane_ids[1])

    replacement = manager.create_pane()
    assert replacement == "pane-5"
    assert manager.pane(replacement).name == "窗格 2"


def test_cannot_delete_last_pane_and_layout_range_is_checked() -> None:
    manager = ScenePaneManager()
    with pytest.raises(RuntimeError, match="last"):
        manager.delete_pane("pane-1")
    for count in (0, 5, True, "2"):
        with pytest.raises(ValueError):
            manager.set_layout(count)


def test_retained_panes_are_capped_at_ten_and_cases_are_evicted_first() -> None:
    manager = ScenePaneManager()
    users = [manager.create_pane() for _ in range(6)]
    cases = [manager.register_case(f"case-{index}") for index in range(3)]
    assert len(manager.panes) == manager.MAX_RETAINED_PANES

    deleted: list[str] = []
    manager.pane_deleted.connect(deleted.append)
    replacement = manager.create_pane()

    assert len(manager.panes) == manager.MAX_RETAINED_PANES
    assert deleted == [cases[0]]
    assert replacement in manager.panes
    assert all(pane_id in manager.panes for pane_id in users)


def test_retained_pane_limit_preserves_active_user_when_no_cases_exist() -> None:
    manager = ScenePaneManager()
    created = [manager.create_pane() for _ in range(9)]
    active = manager.active_pane_id

    replacement = manager.create_pane()

    assert len(manager.panes) == manager.MAX_RETAINED_PANES
    assert active in manager.panes
    assert created[0] not in manager.panes
    assert replacement in manager.panes


def test_workspace_restore_trims_hidden_cases_before_user_panes() -> None:
    manager = ScenePaneManager()
    states = [
        *[manager.pane(manager.active_pane_id)],
        *[
            ScenePaneState(f"user-{index}", f"用户 {index}")
            for index in range(1, 8)
        ],
        *[
            ScenePaneState(f"case-{index}", f"案例 {index}", source="case", source_id=f"case-{index}")
            for index in range(4)
        ],
    ]
    visible = [states[0].pane_id]

    manager.restore_workspace(
        states,
        visible,
        visible[0],
        lecture_case_ids=tuple(state.pane_id for state in states if state.source == "case"),
    )

    assert len(manager.panes) == manager.MAX_RETAINED_PANES
    assert "case-0" not in manager.panes
    assert "case-1" not in manager.panes
    assert all(f"user-{index}" in manager.panes for index in range(1, 8))
    assert manager.workspace_metadata()["lecture_case_ids"] == ["case-2", "case-3"]


def test_deleting_last_visible_pane_promotes_a_retained_sibling() -> None:
    manager = ScenePaneManager()
    first, second = manager.set_layout(2)
    manager.set_visible_panes([first])

    deleted: list[str] = []
    manager.pane_deleted.connect(deleted.append)
    manager.delete_pane(first)

    assert manager.visible_pane_ids() == (second,)
    assert manager.active_pane_id == second
    assert deleted == [first]


def test_global_history_undoes_and_redoes_across_panes() -> None:
    manager = ScenePaneManager()
    first, second = manager.set_layout(2)
    events: list[str] = []
    manager.push(first, lambda: events.append("undo-first"), lambda: events.append("redo-first"))
    manager.push(HistoryEntry(second, lambda: events.append("undo-second"), lambda: events.append("redo-second")))

    assert manager.undo() is True
    assert manager.undo() is True
    assert events == ["undo-second", "undo-first"]
    assert manager.redo() is True
    assert manager.redo() is True
    assert events == ["undo-second", "undo-first", "redo-first", "redo-second"]
    assert manager.undo() is True
    manager.push(first, lambda: None, lambda: None)
    assert manager.redo() is False


def test_history_callback_failure_keeps_source_stack_and_order() -> None:
    manager = ScenePaneManager()
    pane_id = manager.active_pane_id
    failures = [True]
    events: list[str] = []

    def undo_top() -> None:
        if failures[0]:
            raise RuntimeError("undo failed")
        events.append("undo-top")

    manager.push(pane_id, lambda: events.append("undo-bottom"), lambda: events.append("redo-bottom"))
    manager.push(pane_id, undo_top, lambda: events.append("redo-top"))
    with pytest.raises(RuntimeError, match="undo failed"):
        manager.undo()
    failures[0] = False
    assert manager.undo() is True
    assert manager.undo() is True
    assert events == ["undo-top", "undo-bottom"]

    redo_failures = [True]

    def redo_bottom() -> None:
        if redo_failures[0]:
            raise RuntimeError("redo failed")
        events.append("redo-bottom")

    # Redo uses the oldest just-undone entry first.  Replace that behavior in
    # a standalone pair so a failed callback proves it remains retryable.
    manager = ScenePaneManager()
    pane_id = manager.active_pane_id
    manager.push(pane_id, lambda: None, redo_bottom)
    assert manager.undo() is True
    with pytest.raises(RuntimeError, match="redo failed"):
        manager.redo()
    redo_failures[0] = False
    assert manager.redo() is True
    assert events[-1] == "redo-bottom"


def test_deleting_pane_purges_its_undo_and_redo_history() -> None:
    manager = ScenePaneManager()
    first, second = manager.set_layout(2)
    events: list[str] = []
    manager.push(first, lambda: events.append("undo-first"), lambda: events.append("redo-first"))
    manager.push(second, lambda: events.append("undo-second"), lambda: events.append("redo-second"))
    assert manager.undo() is True  # second pane's entry moves to redo

    manager.delete_pane(second)
    assert manager.undo() is True
    assert events == ["undo-second", "undo-first"]
    assert manager.redo() is True
    assert events[-1] == "redo-first"
    assert manager.redo() is False
