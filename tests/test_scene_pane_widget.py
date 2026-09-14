import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QRubberBand, QWidget

from ui.scene_pane_widget import ScenePaneWidget
from ui.scene_pane_manager import ScenePaneManager
from ui.designer_window import MainWindow


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


def test_active_pane_styles_renderer_and_chrome(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    first, second = widget.set_layout(2)
    manager.focus_pane(second)

    assert widget.interactor(second).property("activePane") is True
    assert widget._chromes[second].property("activePane") is True
    assert widget.interactor(first).property("activePane") is False
    assert widget._chromes[first].property("activePane") is False


def test_rename_updates_materialized_pane_chrome(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)

    manager.rename_pane(manager.active_pane_id, "重命名的窗格")

    assert widget._chromes[manager.active_pane_id].title_label.text() == "重命名的窗格"


def test_hiding_pane_clears_selection_band_before_interactor_is_recreated(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    first, second = widget.set_layout(2)
    runtime = manager.pane(second).runtime = SimpleNamespace(
        _selection_band=QRubberBand(QRubberBand.Shape.Rectangle, widget.interactor(second)),
        _selection_start=(1.0, 2.0), _selection_pixel_start=object(),
        _dragging_point_id="P", _drag_start_geometry_state=object(), _drag_moved=True,
    )

    manager.focus_pane(first)
    widget.set_layout(1)
    widget.set_layout(2)

    assert runtime._selection_band is None
    assert runtime._selection_start is None
    assert runtime._selection_pixel_start is None
    assert runtime._dragging_point_id is None
    assert runtime._drag_start_geometry_state is None
    assert runtime._drag_moved is False
    assert widget.interactor(second) is not None


def test_recreated_interactor_invokes_restore_callback(qapp):
    manager = ScenePaneManager()
    restored = []
    renderer_refs = []
    restored_content = []
    def on_created(pane_id, renderer):
        restored.append((pane_id, renderer))
        renderer_refs.append(manager.pane(pane_id).renderer_2d)
        restored_content.append(manager.pane(pane_id).scene_2d.get("objects"))
    widget = ScenePaneWidget(
        manager, interactor_factory=FakeInteractor,
        on_interactor_created=on_created,
    )
    pane_two = widget.set_layout(2)[1]
    old = widget.interactor(pane_two)
    manager.pane(pane_two).scene_2d["objects"] = ["kept"]
    widget.set_layout(1)
    widget.set_layout(2)
    new = widget.interactor(pane_two)
    assert new is not old
    assert restored[-1] == (pane_two, new)
    assert renderer_refs[-1] is new
    assert manager.pane(pane_two).scene_2d["objects"] == ["kept"]
    assert restored_content[-1] == ["kept"]


def test_designer_restore_callback_defers_until_ready():
    window = MainWindow.__new__(MainWindow)
    window._pane_widgets_ready = False
    window._on_pane_interactor_created("pane-1", object())
    assert window._pending_pane_redraws == {"pane-1"}


def test_designer_restore_callback_renders_when_ready(monkeypatch):
    window = MainWindow.__new__(MainWindow)
    window._pane_widgets_ready = True
    window.window = object()
    calls = []
    window._render_scene = lambda: calls.append(True)
    window._using_pane = lambda pane_id: __import__("contextlib").nullcontext()
    window.pane_manager = ScenePaneManager()
    window._on_pane_interactor_created("pane-1", object())
    assert calls == [True]


def test_lecture_and_user_tabs_share_one_container_and_case_chrome_controls(qapp):
    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    container = window.scene_pane_widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    users = container.set_layout(4)
    window.algebra_panel = MagicMock()
    window._sync_scene_controls = lambda: None
    window._set_2d_geometry_tool = lambda _tool: None

    window._load_linear_algebra_topic("ch01.ops.addition")

    cases = window._teaching_case_pane_ids
    # 数学案例流程默认“全部显示”，两个步骤窗格同时存在。
    assert set(container.interactors) == set(cases)
    assert getattr(window, "_teaching_case_pane_grid", None) is None
    container._chromes[cases[1]].hide_requested.emit()
    assert cases[1] not in container.interactors
    container._chromes[cases[0]].fullscreen_requested.emit()
    assert tuple(container.interactors) == (cases[0],)
    window._reveal_algebra_pane(users[-1], 1)
    assert tuple(container.interactors) == (users[-1],)
    assert len(manager.panes) == 6
    container.close()


def test_opening_case_group_at_retained_limit_keeps_first_case_and_ten_panes() -> None:
    from services.scene_commands import CommandPlan

    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    for _ in range(manager.MAX_RETAINED_PANES - 1):
        manager.create_pane()
    cases = tuple(
        SimpleNamespace(id=f"case-{index}", purpose=f"案例 {index}", stage_refs=())
        for index in range(3)
    )
    explanation = SimpleNamespace(case_layout=SimpleNamespace(cases=cases))
    compiled = SimpleNamespace(
        topic_id="ch04.limit",
        plan=CommandPlan(scene="2d", operations=()),
        storyboard=(object(),),
    )
    window._close_teaching_case_panes = lambda: None
    window._sync_layout_buttons = lambda: None
    window.algebra_panel = SimpleNamespace(sync_pane_tabs=lambda: None)

    window._open_teaching_case_panes_impl(explanation, compiled, defer_render=True)

    assert len(manager.panes) == manager.MAX_RETAINED_PANES
    assert len(window._teaching_case_pane_ids) == 1
    pane_id = window._teaching_case_pane_ids[0]
    assert manager.pane(pane_id).source_id == "case-0"
    assert manager.visible_pane_ids() == (pane_id,)


def test_manager_visibility_changes_refresh_retained_case_surfaces(qapp):
    manager = ScenePaneManager()
    container = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    case = manager.register_case("case")
    manager.enter_lecture("case")
    assert tuple(container.interactors) == (case,)
    manager.delete_pane(case)
    assert tuple(container.interactors) == (manager.active_pane_id,)
    container.close()


def test_lazy_case_plan_initializes_only_its_own_renderer_once():
    from services.scene_commands import CommandPlan

    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    case_id = window.pane_manager.register_case("case")
    case = window.pane_manager.pane(case_id)
    case.scene_2d["pending_plan"] = CommandPlan(scene="2d", operations=()).to_dict()
    window._pane_widgets_ready = True
    window.window = object()
    window._render_scene = lambda: None
    calls = []
    def execute(plan, *, pane_id, activate_pane):
        calls.append((pane_id, activate_pane))
        return SimpleNamespace(valid=True)
    window.scene_command_service = SimpleNamespace(execute=execute)

    window._on_pane_interactor_created(case_id, object())
    window._on_pane_interactor_created(case_id, object())

    assert calls == [(case_id, False)]
    assert window.pane_manager.active_pane_id == "pane-1"
    assert "pending_plan" not in case.scene_2d


def test_agent_workspace_refresh_notifies_only_after_runtime_is_restored():
    from models.geometry_2d import Point2D

    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    window._pane_scene().geometry_points = [Point2D("saved", 3, 4)]
    snapshot = window._scene_snapshot_from_current_state()
    window._pane_scene().geometry_points = [Point2D("changed", 8, 9)]
    refreshed = []
    manager.workspace_restored.connect(lambda: refreshed.append(window._pane_scene().geometry_points[0].x))

    window._restore_agent_scene_snapshot(snapshot)

    assert refreshed == [3]
