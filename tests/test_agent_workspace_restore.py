"""Request/approval routing and complete workspace restore regressions."""

from types import SimpleNamespace

import pytest

from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore
from models.geometry_2d import Point2D
from models.surface_layer import SurfaceLayer
from services.agent_provider import AgentResponse
from services.agent_worker import RuntimeTurnWorker
from services.scene_commands import CommandPlan, SceneCommandService
from ui.designer_window import MainWindow
from ui.scene_pane_manager import ScenePaneManager


def workspace():
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    return window


def test_workspace_restore_recreates_deleted_panes_removes_extras_and_restores_both_modes():
    window = workspace()
    manager = window.pane_manager
    first, second = manager.set_layout(2)
    manager.pane(first).name = "草稿"
    manager.pane(second).source = "case"
    manager.pane(second).source_id = "addition"
    manager.pane(first).camera_2d = {"position": [[0, 0, 20], [0, 0, 0], [0, 1, 0]], "parallel_scale": 7}
    manager.pane(first).camera_3d = {"position": [[9, 9, 9], [0, 0, 0], [0, 0, 1]]}
    manager.pane(first).selected_object_ids = ["P"]
    manager.pane(first).algebra_model = {"draft": "x^2"}
    runtime = window._pane_scene(first)
    runtime.geometry_points = [Point2D("P", 1, 2)]
    runtime.layers = [SurfaceLayer("surface", "explicit", "z=x+y")]
    manager.pane(second).scene_2d = {"pending_plan": {"operations": [{"op": "view.fit"}]}}
    manager.set_visible_panes([second, first])
    snapshot = SceneSnapshot.from_json(window._scene_snapshot_from_current_state().to_json())
    manager.delete_pane(first)
    extra = manager.create_pane()
    manager.set_visible_panes([extra])

    window._restore_agent_scene_snapshot(snapshot)

    assert list(manager.panes) == [first, second]
    assert manager.visible_pane_ids() == (second, first)
    assert manager.active_pane_id == first
    restored = manager.pane(first)
    assert restored.name == "草稿"
    assert restored.selected_object_ids == ["P"]
    assert restored.algebra_model == {"draft": "x^2"}
    assert restored.camera_2d["parallel_scale"] == 7
    assert restored.camera_3d["position"][0] == [9, 9, 9]
    assert restored.runtime.geometry_points[0].x == 1
    assert restored.runtime.layers[0].expression == "z=x+y"
    assert manager.pane(second).scene_2d["pending_plan"]["operations"][0]["op"] == "view.fit"
    assert manager.pane(second).source == "case"


def test_invalid_workspace_restore_does_not_partially_mutate_manager():
    window = workspace()
    manager = window.pane_manager
    before = manager.active_pane().to_snapshot()
    with pytest.raises(ValueError):
        manager.restore_workspace([manager.active_pane()], ["missing"], "missing")
    assert manager.active_pane().to_snapshot() == before


def test_workspace_restore_restores_or_clears_teaching_case_metadata():
    window = workspace()
    manager = window.pane_manager
    case = manager.register_case("addition-case")
    manager.enter_lecture("addition-case")
    window._teaching_case_pane_ids = [case]
    window._teaching_case_stage_refs = {case: ("stage-1",)}
    window._active_linear_algebra_topic_id = "chapter.addition"
    window._active_linear_algebra_stage_id = "stage-1"
    lecture_snapshot = window._scene_snapshot_from_current_state()

    manager.leave_lecture()
    window._teaching_case_pane_ids = ["stale"]
    window._teaching_case_stage_refs = {"stale": ("bad",)}
    window._active_linear_algebra_topic_id = "stale-topic"
    window._restore_agent_scene_snapshot(lecture_snapshot)
    assert window._teaching_case_pane_ids == [case]
    assert window._teaching_case_stage_refs == {case: ("stage-1",)}
    assert window._active_linear_algebra_topic_id == "chapter.addition"

    manager.leave_lecture()
    ordinary_snapshot = window._scene_snapshot_from_current_state()
    window._teaching_case_pane_ids = [case]
    window._active_linear_algebra_topic_id = "stale-topic"
    window._restore_agent_scene_snapshot(ordinary_snapshot)
    assert window._teaching_case_pane_ids == []
    assert window._active_linear_algebra_topic_id is None


def test_workspace_restore_rebuilds_lecture_compilation_for_stage_routing():
    window = workspace()
    manager = window.pane_manager
    compiled_a = window._resolve_linear_algebra_compiled("ch01.ops.addition")
    compiled_b = window._resolve_linear_algebra_compiled("ch01.vector.coordinate-system")
    assert compiled_a is not None
    assert compiled_b is not None
    stage_a = compiled_a.storyboard[0].id

    case_a = manager.register_case("addition-case")
    manager.enter_lecture("addition-case")
    window._teaching_case_pane_ids = [case_a]
    window._teaching_case_stage_refs = {case_a: (stage_a,)}
    window._active_linear_algebra_topic_id = compiled_a.topic_id
    window._active_linear_algebra_compiled = compiled_a
    window._active_linear_algebra_stage_id = stage_a
    snapshot_a = window._scene_snapshot_from_current_state()

    manager.leave_lecture()
    case_b = manager.register_case("coordinate-system-case")
    manager.enter_lecture("coordinate-system-case")
    window._teaching_case_pane_ids = [case_b]
    window._teaching_case_stage_refs = {case_b: (compiled_b.storyboard[0].id,)}
    window._active_linear_algebra_topic_id = compiled_b.topic_id
    window._active_linear_algebra_compiled = compiled_b

    window._restore_agent_scene_snapshot(snapshot_a)
    window._select_linear_algebra_stage(compiled_a.topic_id, stage_a)

    assert window._active_linear_algebra_compiled is not None
    assert window._active_linear_algebra_compiled.topic_id == compiled_a.topic_id
    assert window._active_linear_algebra_stage_id == stage_a
    assert window._teaching_case_pane_ids == [case_a]
    assert manager.active_pane_id == case_a


@pytest.mark.parametrize("mode", ["Agent", "Ask"])
def test_worker_runtime_and_approval_keep_request_pane_when_focus_changes(tmp_path, mode):
    window = workspace()
    manager = window.pane_manager
    first, second = manager.set_layout(2)
    snapshot = window._scene_snapshot_from_current_state()
    operations = []

    class Host:
        scene_mode = "2d"

        def for_pane(self, pane_id):
            self.pane_id = pane_id
            return self

        def check_scene_fingerprint(self, expected):
            return window.check_scene_fingerprint(expected, self.pane_id)

        def begin_scene_command_transaction(self):
            pass

        def apply_scene_command(self, operation):
            operations.append((self.pane_id, operation))

        def commit_scene_command_transaction(self):
            pass

        def rollback_scene_command_transaction(self):
            pass

    plan = CommandPlan(operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},))
    runtime = AgentRuntime(command_service=SceneCommandService(Host()), session_store=SessionStore(app_root=tmp_path))

    def respond(*args, **kwargs):
        manager.focus_pane(second)
        return AgentResponse("完成", plan)

    runtime.agent = SimpleNamespace(provider=SimpleNamespace(), respond=respond)
    session = runtime.session_store.create_session("test")
    worker = RuntimeTurnWorker(runtime, session.id, "draw", mode=mode, execution_mode="confirm",
                               scene_before=snapshot, pane_id=first)
    results, errors = [], []
    worker.turn_finished.connect(results.append)
    worker.error.connect(errors.append)
    worker.run()
    assert not errors
    result = results[0]
    turn = runtime.session_store.get_turn(result.turn_id)
    assert turn.validation["pane_id"] == first
    if mode == "Ask":
        assert result.status == "approval_required"
        assert not operations
        runtime.execute(plan, pane_id=turn.validation["pane_id"],
                        expected_scene_fingerprint=turn.validation["base_scene_fingerprint"])
    else:
        assert result.status == "completed"
    assert operations and all(pane_id == first for pane_id, _ in operations)
    assert manager.active_pane_id == second


def test_request_fingerprint_ignores_focus_but_detects_target_model_changes():
    window = workspace()
    first, second = window.pane_manager.set_layout(2)
    fingerprint = window._scene_snapshot_from_current_state().fingerprint_for_pane(first)
    window.pane_manager.focus_pane(second)
    assert window.check_scene_fingerprint(fingerprint, first)
    window._pane_scene(first).geometry_points.append(Point2D("P", 2, 3))
    assert not window.check_scene_fingerprint(fingerprint, first)
