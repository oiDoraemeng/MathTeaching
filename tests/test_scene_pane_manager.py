from PySide6.QtCore import QSize
import pytest

from ui.scene_pane_manager import HistoryEntry, ScenePaneManager


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


def test_hiding_preserves_state_and_repairs_hidden_focus() -> None:
    manager = ScenePaneManager()
    pane_two = manager.set_layout(2)[1]
    manager.pane(pane_two).scene_2d["objects"] = [{"id": "P"}]
    changes: list[str] = []
    manager.active_pane_changed.connect(changes.append)
    manager.focus_pane(pane_two)
    assert changes == [pane_two]

    assert manager.set_layout(1) == ("pane-1",)
    assert manager.active_pane_id == "pane-1"
    assert manager.set_layout(2)[1] == pane_two
    assert manager.pane(pane_two).scene_2d["objects"] == [{"id": "P"}]


def test_focus_limits_and_delete_repair() -> None:
    manager = ScenePaneManager()
    ids = manager.set_layout(4)
    with pytest.raises(RuntimeError, match="four"):
        manager.create_pane()
    manager.focus_pane(ids[2])
    manager.delete_pane(ids[2])
    assert ids[2] not in manager.panes
    assert manager.visible_pane_ids() == (ids[0], ids[1], ids[3])
    assert manager.active_pane_id == ids[0]
    with pytest.raises(ValueError, match="hidden"):
        manager.focus_pane(manager.create_pane())


def test_cannot_delete_last_pane_and_layout_range_is_checked() -> None:
    manager = ScenePaneManager()
    with pytest.raises(RuntimeError, match="last"):
        manager.delete_pane("pane-1")
    for count in (0, 5, True, "2"):
        with pytest.raises(ValueError):
            manager.set_layout(count)


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
