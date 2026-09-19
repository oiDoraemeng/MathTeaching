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


def test_fullscreen_control_toggles_back_to_the_previous_layout(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    first, second = widget.set_layout(2)
    chrome = widget._chromes[first]
    assert chrome.fullscreen_button.toolTip() == "全屏窗格"

    chrome.fullscreen_button.click()
    assert manager.visible_pane_ids() == (first,)
    assert chrome.fullscreen_button.toolTip() == "还原窗格"

    chrome.fullscreen_button.click()
    assert manager.visible_pane_ids() == (first, second)
    assert chrome.fullscreen_button.toolTip() == "全屏窗格"


def test_hiding_the_fullscreen_pane_restores_the_other_panes(qapp):
    manager = ScenePaneManager()
    widget = ScenePaneWidget(manager, interactor_factory=FakeInteractor)
    first, second = widget.set_layout(2)

    widget._chromes[first].fullscreen_button.click()
    assert manager.visible_pane_ids() == (first,)

    widget._chromes[first].hide_requested.emit()
    assert manager.visible_pane_ids() == (second,)


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
        _dragging_point_id="P", _dragging_annotation_id="A",
        _drag_start_geometry_state=object(), _drag_moved=True,
        _dragging_3d_annotation_alias="mark-1",
        _dragging_3d_annotation_moved=True,
        _drag_start_3d_annotation_state=object(),
    )

    manager.focus_pane(first)
    widget.set_layout(1)
    widget.set_layout(2)

    assert runtime._selection_band is None
    assert runtime._selection_start is None
    assert runtime._selection_pixel_start is None
    assert runtime._dragging_point_id is None
    assert runtime._dragging_annotation_id is None
    assert runtime._drag_start_geometry_state is None
    assert runtime._drag_moved is False
    assert runtime._dragging_3d_annotation_alias is None
    assert runtime._dragging_3d_annotation_moved is False
    assert runtime._drag_start_3d_annotation_state is None
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


def test_pane_viewport_changed_fires_after_geometry_is_assigned(qapp):
    """窗格拿到真实几何后必须通知所有者，否则屏幕定尺寸图形会沿用默认视口。"""
    notified = []
    manager = ScenePaneManager()
    widget = ScenePaneWidget(
        manager, interactor_factory=FakeInteractor,
        on_pane_viewport_changed=notified.append,
    )
    first, second = widget.set_layout(2)
    assert set(notified) == {first, second}

    notified.clear()
    third = widget.set_layout(3)[2]
    # 布局变化会重新分配所有可见窗格的几何，已有的窗格也要再次通知。
    assert set(notified) == {first, second, third}


def test_pane_viewport_change_rebuilds_3d_arrow_heads(qapp):
    """4.1/4.2 三维案例窗格的箭头必须按布局后的真实视口重算头部尺寸。"""
    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    case_id = manager.register_case("case")
    case = manager.pane(case_id)
    case.scene_mode = "3d"
    rendered = []
    case.renderer_3d = SimpleNamespace(render=lambda: rendered.append(True))
    refreshed = []
    case.runtime = SimpleNamespace(
        geometry3d_controller=SimpleNamespace(refresh_vector_heads=lambda: refreshed.append(True))
    )
    window._pane_widgets_ready = True

    window._on_pane_viewport_changed(case_id)
    # 第一遍在回调内同步完成：首帧绘制之前头部就已修正，不再闪烁。
    assert refreshed == [True]
    assert rendered == []
    for _ in range(5):
        qapp.processEvents()
    # 延迟的第二遍复测并渲染（真实控制器里数值未变会被跳过）。
    assert refreshed == [True, True]
    assert rendered == [True]

    # 刷新挂起期间的重复通知会被合并：延迟遍只调度一次、只渲染一次。
    rendered.clear()
    window._on_pane_viewport_changed(case_id)
    window._on_pane_viewport_changed(case_id)
    for _ in range(5):
        qapp.processEvents()
    assert rendered == [True]


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


def test_clear_pending_plans_keeps_the_token_of_panes_without_a_renderer() -> None:
    """多窗格案例逐个物化：还没绑定渲染器的窗格必须保住自己的 hand-off token。"""
    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    materialized = manager.register_case("case-0")
    staged = manager.register_case("case-1")
    for pane_id in (materialized, staged):
        pane = manager.pane(pane_id)
        pane.scene_mode = "3d"
        pane.scene_3d["pending_plan"] = {"scene": "3d", "operations": []}
    # 已物化的窗格拥有渲染器；等待中的窗格可能已经有 runtime（案例向量绑定会
    # 提前创建），但还没有渲染器，所以令牌必须留下。
    manager.pane(materialized).renderer_3d = object()
    manager.pane(staged).runtime = SimpleNamespace()
    window._teaching_case_pane_ids = [materialized, staged]

    window._clear_pending_curriculum_plans()

    assert "pending_plan" not in manager.pane(materialized).scene_3d
    assert "pending_plan" in manager.pane(staged).scene_3d


def test_reopening_a_case_group_rebuilds_retained_panes_from_current_artifacts() -> None:
    """案例窗格会带着上一次载入的图形被保留，重新载入必须换成新产物。"""
    from services.scene_commands import CommandPlan

    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    stale = manager.register_case("case-0")
    manager.pane(stale).scene_3d["geometry3d"] = {"stale": True}
    manager.pane(stale).runtime = SimpleNamespace(_agent_geometry3d={"stale": {}})
    cases = (SimpleNamespace(id="case-0", purpose="案例", stage_refs=()),)
    explanation = SimpleNamespace(case_layout=SimpleNamespace(cases=cases, default_pane_count=1))
    compiled = SimpleNamespace(topic_id="ch04.limit", plan=CommandPlan(scene="3d", operations=()), storyboard=())
    window._close_teaching_case_panes = lambda: None
    window._sync_layout_buttons = lambda: None
    window.algebra_panel = SimpleNamespace(sync_pane_tabs=lambda: None)
    window.scene_pane_widget = None

    window._open_teaching_case_panes_impl(explanation, compiled, defer_render=True)

    rebuilt = window._teaching_case_pane_ids[0]
    assert rebuilt != stale and stale not in manager.panes
    pane = manager.pane(rebuilt)
    assert pane.runtime is None
    assert "geometry3d" not in pane.scene_3d
    assert "pending_plan" in pane.scene_3d


@pytest.mark.parametrize("host_executed", [False, True])
def test_case_pane_materializes_its_own_staged_plan_and_masks_it(host_executed: bool) -> None:
    """每个案例窗格都要执行自己的计划，再套自己的舞台掩码（否则窗口是空的）。"""
    from services.scene_commands import CommandPlan

    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    host_pane = manager.register_case("case-0")
    other_pane = manager.register_case("case-1")
    plan = CommandPlan(scene="3d", operations=())
    for pane_id in (host_pane, other_pane):
        pane = manager.pane(pane_id)
        pane.scene_mode = "3d"
        pane.scene_3d["pending_plan"] = plan.to_dict()
    window._teaching_case_pane_ids = [host_pane, other_pane]
    window._teaching_case_stage_refs = {host_pane: ("stage.a",), other_pane: ("stage.b",)}
    window._pane_widgets_ready = True
    window.window = object()
    window._render_scene = lambda: None
    window._using_pane = lambda _pane_id: __import__("contextlib").nullcontext()
    window._pending_curriculum_transaction = None
    window._pending_curriculum_host_executed = host_executed
    executed: list[tuple[str, tuple]] = []
    window.scene_command_service = SimpleNamespace(
        execute=lambda pending_plan, pane_id=None, activate_pane=True: (
            executed.append((pane_id, tuple(pending_plan.operations))),
            SimpleNamespace(valid=True, messages=()),
        )[1]
    )
    masked: list[bool] = []
    window._apply_linear_algebra_storyboard_visibility = lambda *args, **kwargs: masked.append(True)

    window._on_pane_interactor_created(other_pane, object())

    # host_pane 已经物化（可能已提交主题事务），other_pane 仍要自己物化。
    assert executed == [(other_pane, ())]
    assert masked == [True]
    assert "pending_plan" not in manager.pane(other_pane).scene_3d


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
