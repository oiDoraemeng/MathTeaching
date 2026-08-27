from __future__ import annotations

from agent.capabilities.registry import build_default_registry
from agent.capabilities.scene_index import SceneIndex
from agent.capabilities.contracts import ToolCall
from agent.scene_snapshot import SceneSnapshot


def _index(mode: str = "2d") -> SceneIndex:
    return SceneIndex.from_snapshot(
        SceneSnapshot(
            scene_mode=mode,
            geometry=({"object_type": "point", "agent_alias": "P", "name": "P", "x": 1, "y": 2},),
        )
    )


def _call(name: str, arguments: dict[str, object], index: SceneIndex | None = None):
    return build_default_registry().dispatch(ToolCall("call-1", name, arguments), index)


def test_scene_read_and_edit_handlers_return_detached_data_or_unexecuted_plan() -> None:
    index = _index()

    inspection = _call("scene.inspect", {}, index)
    edit = _call("scene.edit", {"action": "upsert", "object_type": "point", "alias": "Q", "coordinates": [3, 4]}, index)

    assert inspection.data["objects"][0]["alias"] == "P"
    assert edit.plan["operations"] == [{"op": "point.upsert", "alias": "Q", "coordinates": [3, 4]}]
    assert index.find(alias="Q")["objects"] == []


def test_scene_clear_empty_scope_is_no_op_and_unsafe_export_is_rejected() -> None:
    index = _index()

    cleared = _call("scene.clear", {"scope": "surfaces"}, index)
    exported = _call("result.export", {"filename": "../escape.png"}, index)

    assert cleared.status == "no_op"
    assert exported.status == "error"
    assert exported.errors[0].code == "unsafe_export_filename"


def test_scene_clear_checks_the_full_staged_index_not_only_inspection_page() -> None:
    index = SceneIndex.from_snapshot(
        SceneSnapshot(
            scene_mode="3d",
            geometry=tuple({"object_type": "point", "agent_alias": f"P{number}", "x": number, "y": 0} for number in range(51)),
            layers=({"agent_alias": "Zsurface", "kind": "explicit", "expression": "z=x+y"},),
        )
    )

    cleared = _call("scene.clear", {"scope": "surfaces"}, index)

    assert cleared.status == "ok"
    assert cleared.plan["operations"] == [{"op": "scene.clear", "scope": "surfaces"}]


def test_scene_edit_rejects_alias_conflict_and_scope_mismatch() -> None:
    index = _index()

    conflict = _call("scene.edit", {"action": "upsert", "object_type": "curve", "alias": "P", "expression": "y=x", "kind": "explicit"}, index)
    mismatch = _call("scene.edit", {"action": "upsert", "object_type": "surface", "alias": "s", "expression": "z=x+y", "kind": "explicit"}, index)

    assert conflict.errors[0].code == "alias_conflict"
    assert mismatch.errors[0].code == "scene_scope_mismatch"


def test_view_only_supports_mode_and_fit_and_math_handlers_use_controlled_parsers() -> None:
    index = _index()

    view = _call("view.control", {"action": "fit", "padding": 1.2}, index)
    calculation = _call("math.calculate", {"expression": "sin(pi/2)+2"}, index)
    unsafe = _call("math.calculate", {"expression": "__import__('os')"}, index)
    derivative = _call("math.derive", {"action": "tangent", "expression": "y=x^2", "curve_alias": "f", "x": 1, "presentation": "draw"}, index)

    assert view.plan["operations"] == [{"op": "view.fit", "padding": 1.2}]
    assert calculation.data["result"] == "3"
    assert unsafe.errors[0].code == "unsafe_expression"
    assert derivative.plan["operations"][0]["op"] == "calculus.tangent"
