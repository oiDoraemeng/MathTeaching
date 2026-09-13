from types import SimpleNamespace

import pytest

from services.scene_commands import CommandPlan
from ui.designer_window import MainWindow
from ui.scene_pane_manager import ScenePaneManager
from ui.teaching_case_panes import StoryboardVisibilityController


def compiled(*stages):
    return SimpleNamespace(topic_id="ch08.principal-axis", storyboard=tuple(stages), plan=CommandPlan(scene="2d", operations=()))


def stage(stage_id, aliases, *, title="阶段", caption="说明", layout="sequence"):
    return SimpleNamespace(
        id=stage_id,
        title=title,
        caption=caption,
        layout=layout,
        visible_aliases=tuple(aliases),
        anchor=(0.0, 0.0),
    )


def test_controller_consumes_compiled_stage_ids_and_exposes_metadata():
    value = compiled(stage("matrix", ("matrix", "relation"), title="矩阵表", caption="保留矩阵"))
    selection = StoryboardVisibilityController(value).select("matrix")
    assert selection.stage_id == "matrix"
    assert selection.title == "矩阵表"
    assert selection.caption == "保留矩阵"
    assert selection.controlled_aliases == ("matrix", "relation")
    assert selection.visible_aliases == ("matrix", "relation")
    assert selection.hidden_aliases == ()


def test_unknown_stage_rejects_before_runtime_visibility_changes():
    value = compiled(
        stage("first", ("one",)),
        stage("second", ("two",)),
    )
    calls = []

    class Geometry:
        def set_agent_alias_visible(self, *args):
            calls.append(args)

        def set_teaching_visible(self, *args):
            calls.append(args)

    runtime = SimpleNamespace(geometry_controller=Geometry(), geometry3d_controller=None)
    with pytest.raises(ValueError, match="unknown storyboard stage"):
        StoryboardVisibilityController(value).apply(runtime, "missing")
    assert calls == []


@pytest.mark.parametrize(
    "topic, stage_id, visible, hidden",
    [
        ("ch05.gaussian-elimination", "tableau", ("tableau", "relation"), ("other",)),
        ("ch06.basis-change.coordinates", "mapping", ("domain", "image"), ("kernel",)),
        ("ch08.principal-axis", "quadratic", ("quadratic", "axes"), ("original",)),
    ],
)
def test_matrix_mapping_and_quadratic_use_the_same_visibility_controller(topic, stage_id, visible, hidden):
    value = SimpleNamespace(
        topic_id=topic,
        storyboard=(stage(stage_id, visible), stage("other", hidden)),
    )
    selection = StoryboardVisibilityController(value).select(stage_id)
    assert selection.visible_aliases == visible
    assert selection.hidden_aliases == hidden
    assert selection.controlled_aliases == (*visible, *hidden)


def test_controller_updates_existing_2d_and_3d_actors_without_commands():
    value = compiled(stage("matrix", ("matrix",)), stage("axes", ("axes",)))
    calls = []

    class Geometry:
        def set_agent_alias_visible(self, alias, visible):
            calls.append(("2d-agent", alias, visible))

        def set_teaching_visible(self, alias, visible):
            calls.append(("2d-teaching", alias, visible))

    class Geometry3D:
        def set_visible(self, alias, visible):
            calls.append(("3d", alias, visible))

    runtime = SimpleNamespace(geometry_controller=Geometry(), geometry3d_controller=Geometry3D())
    StoryboardVisibilityController(value).apply(runtime, "axes", render=False)
    assert calls == [
        ("2d-agent", "matrix", False),
        ("2d-teaching", "matrix", False),
        ("3d", "matrix", False),
        ("2d-agent", "axes", True),
        ("2d-teaching", "axes", True),
        ("3d", "axes", True),
    ]


def test_main_window_stage_switch_keeps_pane_identity_and_session_state():
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    pane_id = window.pane_manager.register_case("case", name="案例")
    window.pane_manager.set_visible_panes([pane_id])
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {pane_id: ("first", "second")}
    window._active_linear_algebra_compiled = compiled(
        stage("first", ("one",)), stage("second", ("two",))
    )
    window._active_linear_algebra_topic_id = window._active_linear_algebra_compiled.topic_id
    window._active_linear_algebra_stage_id = "first"
    window._hidden_linear_algebra_aliases = set()
    window._agent_session_store = object()
    pane_before = tuple(window.pane_manager.panes)
    refs_before = dict(window._teaching_case_stage_refs)
    session_before = window._agent_session_store

    window._select_linear_algebra_stage(window._active_linear_algebra_compiled.topic_id, "second")

    assert tuple(window.pane_manager.panes) == pane_before
    assert window.pane_manager.visible_pane_ids() == (pane_id,)
    assert window._teaching_case_stage_refs == refs_before
    assert window._agent_session_store is session_before
    assert window._active_linear_algebra_stage_id == "second"
    assert window._hidden_linear_algebra_aliases == {"one"}


def test_main_window_unknown_stage_leaves_current_selection_untouched():
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._active_linear_algebra_compiled = compiled(stage("first", ("one",)))
    window._active_linear_algebra_topic_id = window._active_linear_algebra_compiled.topic_id
    window._active_linear_algebra_stage_id = "first"
    window._hidden_linear_algebra_aliases = {"old-hidden"}
    window._select_linear_algebra_stage(window._active_linear_algebra_compiled.topic_id, "missing")
    assert window._active_linear_algebra_stage_id == "first"
    assert window._hidden_linear_algebra_aliases == {"old-hidden"}
