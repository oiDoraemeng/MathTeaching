import pytest
from PySide6.QtWidgets import QApplication, QWidget

from ui.scene_pane_widget import ScenePaneWidget
from ui.scene_pane_manager import ScenePaneManager


class FakeInteractor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.interactor = self


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_visible_panes_get_independent_interactors_and_restore_state(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    first = widget.interactor()
    manager.pane(manager.active_pane_id).scene_2d["objects"] = ["A"]
    widget.set_layout(3)
    ids = manager.visible_pane_ids()
    assert len(widget.interactors) == 3
    assert len({id(value) for value in widget.interactors.values()}) == 3
    assert manager.pane(ids[1]).scene_2d == {}
    widget.set_layout(1)
    assert len(widget.interactors) == 1
    widget.set_layout(3)
    assert manager.pane(ids[0]).scene_2d["objects"] == ["A"]
    assert widget.interactor(ids[1]) is not None
    assert widget.interactor(ids[0]) is first


def test_delete_repairs_layout_and_active_focus(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    ids = widget.set_layout(3)
    manager.focus_pane(ids[1])
    widget.delete_pane(ids[1])
    assert manager.visible_pane_ids() == (ids[0], ids[2])
    assert manager.active_pane_id == ids[0]
    assert ids[1] not in widget.interactors


def test_recreated_interactor_invokes_restore_callback(qapp):
    manager = ScenePaneManager()
    restored = []
    widget = ScenePaneWidget(
        manager, interactor_factory=FakeInteractor,
        on_interactor_created=lambda pane_id, renderer: restored.append((pane_id, renderer)),
    )
    pane_two = widget.set_layout(2)[1]
    old = widget.interactor(pane_two)
    manager.pane(pane_two).scene_2d["objects"] = ["kept"]
    widget.set_layout(1)
    widget.set_layout(2)
    new = widget.interactor(pane_two)
    assert new is not old
    assert restored[-1] == (pane_two, new)
    assert manager.pane(pane_two).scene_2d["objects"] == ["kept"]
