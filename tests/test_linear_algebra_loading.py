from types import SimpleNamespace
from unittest.mock import MagicMock

from linear_algebra.catalog.manifest import topic_entries
from models.geometry_2d import Point2D
from models.scene_mode import SceneMode
from services.scene_commands import CommandPlan
from ui.scene_pane_manager import ScenePaneManager
from ui.designer_window import MainWindow


def test_every_topic_is_wrapped_in_one_clear_and_load_plan() -> None:
    for topic in topic_entries():
        plan = MainWindow._linear_algebra_lesson_plan(topic.id)
        assert isinstance(plan, CommandPlan)
        assert plan.operations[0] == {"op": "scene.clear", "scope": "all"}
        assert plan.scene in {"2d", "3d"}
        assert plan.operations[-1]["op"] == "view.fit"


def test_unknown_topic_reports_error_without_executing() -> None:
    statuses: list[tuple[str, bool]] = []
    executed: list[CommandPlan] = []
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window.algebra_panel = SimpleNamespace(set_status=lambda text, is_error=False: statuses.append((text, is_error)))
    window.scene_command_service = SimpleNamespace(execute=executed.append)

    window._load_linear_algebra_topic("missing-topic")

    assert executed == []
    assert statuses and statuses[-1][1] is True
    assert "线性代数主题" in statuses[-1][0]


def test_linear_algebra_toolbar_context_tracks_loaded_topic() -> None:
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.TWO_D
    window._active_linear_algebra_topic_id = "ch01.ops.addition"
    assert window._is_linear_algebra_context() is True

    window._active_linear_algebra_topic_id = "ch04.subspace.col-null"
    assert window._is_linear_algebra_context() is False

    window._active_linear_algebra_topic_id = None
    assert window._is_linear_algebra_context() is True


def test_opening_linear_algebra_enters_2d_workspace_and_reveals_tools() -> None:
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.THREE_D
    window._active_linear_algebra_topic_id = "ch04.subspace.col-null"
    window.algebra_panel = SimpleNamespace(
        set_status=MagicMock(),
    )
    window._save_current_view_state = MagicMock()
    window._close_scene_settings = MagicMock()
    window._render_scene = MagicMock()

    window._enter_linear_algebra_workspace()

    assert window._pane_scene().scene_mode is SceneMode.TWO_D
    window._render_scene.assert_called_once_with()
    window.algebra_panel.set_status.assert_called_once_with("已打开线性代数讲义目录")


def test_loading_a_2d_topic_activates_the_visible_select_tool() -> None:
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.TWO_D
    window.algebra_panel = SimpleNamespace(set_status=lambda *_args, **_kwargs: None)
    window.scene_command_service = SimpleNamespace(execute=lambda _plan: None)
    window._set_2d_geometry_tool = MagicMock()
    window._sync_scene_controls = MagicMock()
    window.two_d_geometry_toolbar = MagicMock()

    window._load_linear_algebra_topic("ch01.ops.addition")

    assert window._active_linear_algebra_topic_id == "ch01.ops.addition"
    window._set_2d_geometry_tool.assert_called_once_with("select")
    window.two_d_geometry_toolbar.set_active_tool.assert_called_once_with(
        "select",
        emit_signal=False,
    )


def test_focusing_the_second_case_pane_keeps_the_shared_select_tool_active() -> None:
    """A point in the second vector-addition pane must be selectable too."""

    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    first = window.pane_manager.register_case("case.addition.objects")
    second = window.pane_manager.register_case("case.addition.parallelogram")
    window.pane_manager.enter_lecture("case.addition.objects", [
        "case.addition.objects",
        "case.addition.parallelogram",
    ])
    window.pane_manager.show_all_cases()
    window._active_linear_algebra_topic_id = "ch01.ops.addition"
    window._pane_scene(first).scene_mode = SceneMode.TWO_D
    window._pane_scene(second).scene_mode = SceneMode.TWO_D
    # The first pane receives the select tool during topic finalization; the
    # second pane used to retain the runtime default (no tool).
    window._pane_scene(first)._active_2d_tool = "select"
    window._pane_scene(second)._active_2d_tool = None
    window._pane_scene(second)._active_linear_algebra_tool = None
    point_c = Point2D("C", 4.0, 3.0)
    second_runtime = window._pane_scene(second)
    second_runtime.geometry_points = [point_c]
    second_runtime.linear_objects = []
    second_runtime.annotations = []
    second_runtime.curve_layers = []
    second_runtime._agent_teaching_2d = {}
    second_runtime._vector_additions = []
    second_runtime.geometry_controller = SimpleNamespace(
        points={point_c.id: point_c},
        linears={},
        annotations={},
        selected_id=None,
        hit_test=lambda *_args: point_c.id,
        set_selected=lambda object_id: setattr(second_runtime.geometry_controller, "selected_id", object_id),
    )
    second_runtime.pane.renderer_2d = SimpleNamespace(
        interactor=SimpleNamespace(setCursor=lambda *_args: None),
        render=lambda: None,
    )
    window.two_d_geometry_toolbar = SimpleNamespace(_active_tool="select")
    window.algebra_panel = SimpleNamespace(
        set_pane_id=lambda *_args: None,
        set_scene_mode=lambda *_args: None,
        set_layers=lambda *_args: None,
        set_selected_layer=lambda *_args: None,
    )
    window._two_d_panel_layers = lambda: []
    window._hit_tolerance = lambda: 0.25

    window.pane_manager.focus_pane(second)
    window._on_algebra_pane_focus_changed(second)

    assert window._pane_scene(second)._active_2d_tool == "select"
    assert window._pane_scene(second)._active_linear_algebra_tool is None
    assert window._begin_select_or_drag(4.0, 3.0) is True
    assert second_runtime.geometry_controller.selected_id == point_c.id


def test_loading_a_text_only_topic_does_not_create_case_panes() -> None:
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.TWO_D
    window.algebra_panel = SimpleNamespace(set_status=lambda *_args, **_kwargs: None)
    window.scene_command_service = SimpleNamespace(execute=lambda _plan: None)
    window._set_2d_geometry_tool = MagicMock()
    window._sync_scene_controls = MagicMock()
    window.two_d_geometry_toolbar = MagicMock()

    window._load_linear_algebra_topic("ch03.adjugate.matrix")

    assert window._active_linear_algebra_topic_id == "ch03.adjugate.matrix"
    assert window._teaching_case_pane_ids == []
    assert all(pane.source == "user" for pane in window.pane_manager.panes.values())


def test_linear_algebra_source_repository_is_reused_for_topic_switches() -> None:
    window = MainWindow.__new__(MainWindow)

    first = window._linear_algebra_source_repository()
    second = window._linear_algebra_source_repository()

    assert first is second


def test_live_window_defers_scene_materialization_after_explanation_preview(monkeypatch) -> None:
    window = MainWindow.__new__(MainWindow)
    window.window = object()
    window.agent_panel = object()
    window._linear_algebra_load_generation = 3
    previewed = []
    continued = []
    window._publish_linear_algebra_explanation_preview = lambda *args: previewed.append(args)
    window._continue_linear_algebra_topic_load = lambda request: continued.append(request)

    assert window._can_defer_linear_algebra_scene_load() is False

    monkeypatch.setattr("ui.designer_window.QApplication.instance", lambda: object())
    monkeypatch.setattr("ui.designer_window.QWidget", object)
    assert window._can_defer_linear_algebra_scene_load() is True


def test_only_the_current_explanation_preview_can_start_scene_materialization() -> None:
    window = MainWindow.__new__(MainWindow)
    window._linear_algebra_load_generation = 8
    request = {"generation": 8, "topic": SimpleNamespace(id="ch01.ops.addition")}
    window._pending_linear_algebra_scene_request = request
    continued = []
    window._continue_linear_algebra_topic_load = continued.append

    window._start_deferred_linear_algebra_scene_load("ch01.ops.addition", "7")
    assert continued == []

    window._start_deferred_linear_algebra_scene_load("ch01.ops.addition", "8")
    assert continued == [request]
    assert window._pending_linear_algebra_scene_request is None


def test_opening_lecture_retains_user_content_and_shows_the_whole_case_flow():
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    user_ids = window.pane_manager.set_layout(4)
    user = window.pane_manager.pane(user_ids[-1])
    user.scene_2d = {"objects": [{"id": "user-point", "x": 7}]}
    window.pane_manager.focus_pane(user.pane_id)
    runtime = window._pane_scene()
    runtime._active_2d_tool = "vector"
    window.algebra_panel = MagicMock()
    executed = []
    window.scene_command_service = SimpleNamespace(execute=lambda plan, **kw: executed.append((plan, kw)))
    window._sync_scene_controls = MagicMock()

    window._load_linear_algebra_topic("ch01.ops.addition")

    assert user.scene_2d == {"objects": [{"id": "user-point", "x": 7}]}
    assert runtime._active_2d_tool == "vector"
    assert executed == []  # hidden case plans are initialized only when materialized
    assert len(window.pane_manager.panes) == 6
    visible = window.pane_manager.visible_pane_ids()
    # 数学案例流程的 default_pane_count 为 2：首屏即“全部显示”。
    assert len(visible) == 2
    assert all(window.pane_manager.pane(pane_id).source == "case" for pane_id in visible)
    window._set_teaching_case_pane_count(1)
    assert len(window.pane_manager.visible_pane_ids()) == 1
    assert not set(user_ids).intersection(window.pane_manager.visible_pane_ids())
    old_case_ids = set(window._teaching_case_pane_ids)

    window._load_linear_algebra_topic("ch01.ops.scalar")

    assert not old_case_ids.intersection(window.pane_manager.panes)
    assert all(pane.source == "user" or pane.pane_id in window._teaching_case_pane_ids
               for pane in window.pane_manager.panes.values())


def test_selecting_a_geometric_example_does_not_filter_user_scene_aliases() -> None:
    calls: list[tuple[str, str, bool]] = []
    renders: list[bool] = []

    class GeometryController:
        def set_agent_alias_visible(self, alias: str, visible: bool) -> None:
            calls.append(("regular", alias, visible))

        def set_teaching_visible(self, alias: str, visible: bool) -> None:
            calls.append(("teaching", alias, visible))

    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.TWO_D
    window._pane_scene().geometry_controller = GeometryController()
    window._pane_scene().geometry3d_controller = None
    window._pane().renderer_2d = window._pane().renderer_3d = SimpleNamespace(render=lambda: renders.append(True))
    window._active_linear_algebra_compiled = SimpleNamespace(
        topic_id="ch01.ops.addition",
        storyboard=(
            SimpleNamespace(
                id="stage.triangle",
                visible_aliases=("sem__a", "sem__addition_triangle"),
            ),
            SimpleNamespace(
                id="stage.parallelogram",
                visible_aliases=("sem__a", "sem__addition_parallelogram"),
            ),
        ),
    )
    window._hidden_linear_algebra_aliases = set()

    window._select_linear_algebra_stage("ch01.ops.addition", "stage.parallelogram")

    assert window._active_linear_algebra_stage_id == "stage.parallelogram"
    assert window._hidden_linear_algebra_aliases == {"sem__addition_triangle"}
    assert calls == []
    assert renders == []


def test_switching_a_flow_step_keeps_each_case_pane_on_its_own_step() -> None:
    """流程窗格各显示自己那一步：切换步骤不能把所有窗格刷成同一张图。

    向量减法两步分别是「a、b」与「从 b 的终点指向 a 的终点的 a-b」。面板上点
    第二步时，仅第二步窗格显示 a-b，第一步窗格必须保持原样。
    """

    window = MainWindow.__new__(MainWindow)
    window._active_linear_algebra_topic_id = "ch01.ops.subtraction"
    window.pane_manager = ScenePaneManager()
    first = window.pane_manager.register_case("case.subtraction.operands", name="第一步：向量 a、b")
    second = window.pane_manager.register_case(
        "case.subtraction.difference", name="第二步：a-b 的终点关系"
    )
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: ("stage.subtraction.operands",),
        second: ("stage.subtraction.difference",),
    }
    window._active_linear_algebra_compiled = SimpleNamespace(
        topic_id="ch01.ops.subtraction",
        storyboard=(
            SimpleNamespace(id="stage.subtraction.operands", visible_aliases=("sem__a", "sem__b")),
            SimpleNamespace(
                id="stage.subtraction.difference",
                visible_aliases=("sem__a", "sem__b", "sem__rel.subtraction.endpoints"),
            ),
        ),
    )
    window._hidden_linear_algebra_aliases = set()
    applied: dict[str, list[tuple[str, bool]]] = {}

    for pane_id in (first, second):
        calls: list[tuple[str, bool]] = []
        applied[pane_id] = calls
        pane = window.pane_manager.pane(pane_id)
        pane.scene_mode = SceneMode.TWO_D
        pane.renderer_2d = pane.renderer_3d = SimpleNamespace(render=lambda: None)
        pane.runtime = SimpleNamespace(
            geometry_controller=SimpleNamespace(
                set_agent_alias_visible=lambda alias, visible, sink=calls: sink.append((alias, visible))
            ),
            geometry3d_controller=None,
            _vector_additions=(),
        )

    window._select_linear_algebra_stage("ch01.ops.subtraction", "stage.subtraction.difference")

    relation = "sem__rel.subtraction.endpoints"
    assert (relation, False) in applied[first]
    assert (relation, True) in applied[second]
    assert window._active_linear_algebra_stage_id == "stage.subtraction.difference"
    # 第二步是超集，选它本身不隐藏任何别名；关键是第一步窗格仍按自己的步骤取掩码。
    assert window._hidden_linear_algebra_aliases == set()


def test_extended_case_panes_still_follow_the_selected_stage() -> None:
    """绑定多个步骤的案例窗格仍随选中阶段切换（4–8 章的逐步讲解）。"""

    window = MainWindow.__new__(MainWindow)
    window._active_linear_algebra_topic_id = "ch04.subspace.col-null"
    window.pane_manager = ScenePaneManager()
    pane_id = window.pane_manager.register_case("case.closure", name="案例")
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {pane_id: ("stage.closure.one", "stage.closure.two")}
    window._active_linear_algebra_compiled = SimpleNamespace(
        topic_id="ch04.subspace.col-null",
        storyboard=(
            SimpleNamespace(id="stage.closure.one", visible_aliases=("sem__one",)),
            SimpleNamespace(id="stage.closure.two", visible_aliases=("sem__one", "sem__two")),
        ),
    )
    calls: list[tuple[str, bool]] = []
    pane = window.pane_manager.pane(pane_id)
    pane.scene_mode = SceneMode.TWO_D
    pane.renderer_2d = pane.renderer_3d = SimpleNamespace(render=lambda: None)
    pane.runtime = SimpleNamespace(
        geometry_controller=SimpleNamespace(
            set_agent_alias_visible=lambda alias, visible, sink=calls: sink.append((alias, visible))
        ),
        geometry3d_controller=None,
        _vector_additions=(),
    )

    window._select_linear_algebra_stage("ch04.subspace.col-null", "stage.closure.two")

    assert ("sem__one", True) in calls
    assert ("sem__two", True) in calls


def test_lecture_vector_addition_binds_only_the_pane_that_shows_the_sum() -> None:
    """数学案例流程的第一步只画 a、b，不能替它补出和向量与平行四边形。

    否则第一步与第二步两个窗格会变得一模一样。
    """
    from contextlib import contextmanager

    window = MainWindow.__new__(MainWindow)
    window._active_linear_algebra_topic_id = "ch01.ops.addition"
    window.pane_manager = SimpleNamespace(panes={"p1": object(), "p2": object()})
    window._teaching_case_pane_ids = ["p1", "p2"]
    scenes = {
        "p1": SimpleNamespace(
            linear_objects=[
                SimpleNamespace(agent_alias="sem__flow_a"),
                SimpleNamespace(agent_alias="sem__flow_b"),
            ],
            _vector_additions=[],
        ),
        "p2": SimpleNamespace(
            linear_objects=[
                SimpleNamespace(agent_alias="sem__flow_a"),
                SimpleNamespace(agent_alias="sem__flow_b"),
                SimpleNamespace(agent_alias="sem__flow_sum"),
            ],
            _vector_additions=[],
        ),
    }
    current = {"pane": "p1"}

    @contextmanager
    def using_pane(pane_id=None):
        previous = current["pane"]
        current["pane"] = pane_id or previous
        try:
            yield
        finally:
            current["pane"] = previous

    window._using_pane = using_pane
    window._pane_scene = lambda pane_id=None: scenes[current["pane"]]
    registered: list[dict] = []
    window._command_register_vector_addition = registered.append

    window._register_linear_algebra_case_vector_additions()

    assert [operation["result_vector"] for operation in registered] == ["sem__flow_sum"]


def test_vector_addition_refresh_is_pinned_to_its_own_case_pane() -> None:
    """Refreshing step two must not create derived vectors in step one."""
    window = MainWindow.__new__(MainWindow)
    manager = window.pane_manager = ScenePaneManager()
    first = manager.register_case("case.addition.objects")
    second = manager.register_case("case.addition.parallelogram")
    manager.enter_lecture("case.addition.objects", [
        "case.addition.objects",
        "case.addition.parallelogram",
    ])
    manager.show_all_cases()
    first_stage = SimpleNamespace(
        id="stage.flow.objects",
        title="第一步",
        caption="",
        layout="overlay",
        visible_aliases=("sem__flow_a", "sem__flow_b"),
        visible_refs=("flow_a", "flow_b"),
        anchor=(0.0, 0.0),
    )
    second_stage = SimpleNamespace(
        id="stage.flow.parallelogram",
        title="第二步",
        caption="",
        layout="overlay",
        visible_aliases=("sem__flow_a", "sem__flow_b", "sem__flow_sum"),
        visible_refs=("flow_a", "flow_b", "flow_sum"),
        anchor=(0.0, 0.0),
    )
    window._active_linear_algebra_compiled = SimpleNamespace(
        topic_id="ch01.ops.addition",
        storyboard=(first_stage, second_stage),
        aliases=(),
    )
    window._active_linear_algebra_stage_id = None
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: (first_stage.id,),
        second: (second_stage.id,),
    }
    manager.pane(first).runtime = SimpleNamespace(
        geometry_controller=None,
        geometry3d_controller=None,
        _vector_additions=[],
    )
    relation = {"alias": "dynamic__sem__rel.addition.flow"}
    manager.pane(second).runtime = SimpleNamespace(
        geometry_controller=None,
        geometry3d_controller=None,
        _vector_additions=[relation],
    )
    window._sync_teaching_matrix_grid = lambda *_args, **_kwargs: None
    refreshed: list[str] = []
    window._refresh_vector_addition = lambda *_args, **_kwargs: refreshed.append(
        window._pane().pane_id
    )

    window._apply_linear_algebra_storyboard_visibility()

    assert manager.active_pane_id == first
    assert refreshed == [second]
