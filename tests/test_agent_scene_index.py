from __future__ import annotations

import importlib

from agent.capabilities.scene_index import SceneIndex
from agent.scene_snapshot import SceneSnapshot


def _snapshot() -> SceneSnapshot:
    return SceneSnapshot(
        scene_mode="2d",
        curves=({"agent_alias": "f", "name": "f", "kind": "explicit", "expression": "y=x^2"},),
        geometry=(
            {"object_type": "point", "agent_alias": "P", "name": "P", "x": 1, "y": 2},
            {"object_type": "linear", "agent_alias": "v", "name": "v", "kind": "vector", "start_point_id": "P", "end_point_id": "Q"},
        ),
        layers=({"agent_alias": "s", "name": "s", "kind": "explicit", "expression": "z=x+y"},),
        annotations=({"agent_alias": "note", "text": "hello"},),
        metadata={"points3d": [["A", [1, 2, 3]]]},
    )


def test_scene_index_inspects_and_finds_snapshot_objects_in_stable_order() -> None:
    index = SceneIndex.from_snapshot(_snapshot())

    inspection = index.inspect()
    found = index.find(alias="P")

    assert inspection["scene_mode"] == "2d"
    assert [item["alias"] for item in inspection["objects"]] == ["A", "P", "f", "note", "s", "v"]
    assert found["objects"] == [{"alias": "P", "object_type": "point", "coordinates": [1, 2]}]


def test_scene_index_reads_staged_operations_without_mutating_source_snapshot() -> None:
    snapshot = _snapshot()
    index = SceneIndex.from_snapshot(snapshot)
    staged = index.clone()

    staged.apply_operations((
        {"op": "point.upsert", "alias": "Q", "coordinates": [3, 4]},
        {"op": "linear.upsert", "alias": "w", "kind": "vector", "start": "P", "end": "Q"},
    ))

    assert staged.find(alias="Q")["objects"][0]["coordinates"] == [3, 4]
    assert index.find(alias="Q")["objects"] == []
    assert snapshot.geometry[0]["agent_alias"] == "P"


def test_scene_index_recognizes_main_window_points3d_snapshot_records() -> None:
    index = SceneIndex.from_snapshot(SceneSnapshot(scene_mode="3d", metadata={"points3d": [{"alias": "A", "kind": "point3d", "coordinates": [1, 2, 3]}]}))

    assert index.find(alias="A")["objects"] == [{"alias": "A", "object_type": "point3d", "coordinates": [1, 2, 3], "kind": "point3d"}]


def test_scene_index_recognizes_main_window_area_metadata() -> None:
    index = SceneIndex.from_snapshot(SceneSnapshot(metadata={"areas": [["area", {"op": "area.fill", "expression": "y=x", "interval": [0, 1]}]]}))

    assert index.find(alias="area")["objects"][0]["object_type"] == "area"


def test_scene_index_uses_bounded_results_without_selection_fallback() -> None:
    index = SceneIndex.from_snapshot(
        SceneSnapshot(geometry=tuple({"object_type": "point", "agent_alias": f"P{number}", "x": number, "y": 0} for number in range(60)))
    )

    inspection = index.inspect()
    found = index.find(object_types=["point"], limit=100)

    assert len(inspection["objects"]) == 50
    assert inspection["truncated"] is True
    assert len(found["objects"]) == 20
    assert found["truncated"] is True


def test_scene_index_does_not_import_renderer_or_ui_modules() -> None:
    module = importlib.import_module("agent.capabilities.scene_index")

    assert "PySide6" not in module.__dict__
    assert "pyvista" not in module.__dict__
    assert "ui" not in module.__dict__
