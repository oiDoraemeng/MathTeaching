from __future__ import annotations

from agent.capabilities.contracts import ToolCall
from agent.capabilities.orchestrator import (
    MAX_MUTATING_CALLS,
    MAX_TOOL_CALLS,
    CapabilityOrchestrator,
)
from agent.capabilities.scene_index import SceneIndex
from agent.scene_snapshot import SceneSnapshot


def _snapshot(mode: str = "2d") -> SceneSnapshot:
    return SceneSnapshot(scene_mode=mode)


def test_mutations_are_staged_and_reads_see_previous_edits() -> None:
    orchestrator = CapabilityOrchestrator()
    calls = [
        ToolCall("edit-1", "scene.edit", {"action": "upsert", "object_type": "point", "alias": "Q", "coordinates": [3, 4]}),
        ToolCall("find-1", "scene.find", {"alias": "Q"}),
    ]

    turn = orchestrator.run_calls(calls, _snapshot())

    assert turn.error is None
    assert turn.results[1].data["objects"][0]["alias"] == "Q"
    assert turn.plan is not None
    assert turn.plan.scene == "2d"
    assert [item["op"] for item in turn.plan.operations] == ["scene.set_mode", "point.upsert"]
    assert turn.index.find(alias="Q")["objects"]


def test_conflicting_target_scenes_return_error_without_composed_plan() -> None:
    orchestrator = CapabilityOrchestrator()
    calls = [
        ToolCall("mode-1", "view.control", {"action": "set_mode", "mode": "2d"}),
        ToolCall("mode-2", "view.control", {"action": "set_mode", "mode": "3d"}),
    ]

    turn = orchestrator.run_calls(calls, _snapshot())

    assert turn.plan is None
    assert turn.error is not None
    assert turn.error.errors[0].code == "scene_conflict"
    assert turn.index.scene_mode == "2d"


def test_call_and_mutation_limits_are_terminal_and_leave_staged_index_intact() -> None:
    orchestrator = CapabilityOrchestrator()
    read_calls = [ToolCall(str(i), "scene.find", {"limit": i + 1}) for i in range(MAX_TOOL_CALLS + 1)]
    turn = orchestrator.run_calls(read_calls, _snapshot())
    assert turn.error is not None
    assert turn.error.errors[0].code == "tool_call_limit"
    assert turn.index.inspect()["objects"] == []

    mutating = [
        ToolCall(str(i), "scene.edit", {"action": "upsert", "object_type": "point", "alias": f"P{i}", "coordinates": [i, i]})
        for i in range(MAX_MUTATING_CALLS + 1)
    ]
    turn = CapabilityOrchestrator().run_calls(mutating, _snapshot())
    assert turn.error is not None
    assert turn.error.errors[0].code == "mutation_limit"
    assert turn.index.get(f"P{MAX_MUTATING_CALLS}") is None
    assert turn.index.get("P0") is not None


def test_third_identical_call_is_rejected_using_canonical_arguments() -> None:
    call = ToolCall("provider-a", "scene.find", {"limit": 2})
    turn = CapabilityOrchestrator().run_calls([call, ToolCall("provider-b", "scene.find", {"limit": 2}), ToolCall("provider-c", "scene.find", {"limit": 2})], _snapshot())

    assert turn.error is not None
    assert turn.error.errors[0].code == "tool_loop_detected"
