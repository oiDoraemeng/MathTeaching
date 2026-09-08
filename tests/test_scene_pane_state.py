import pytest

from ui.scene_pane_state import ScenePaneState


def test_pane_state_instances_are_isolated() -> None:
    first = ScenePaneState("pane-1", "窗格 1")
    second = ScenePaneState("pane-2", "窗格 2")

    first.scene_2d["objects"] = [{"id": "P", "x": 1}]
    first.scene_mode = "3d"
    first.camera_3d["position"] = [1, 2, 3]
    first.selected_object_ids.append("P")
    first.algebra_model["expression"] = "x+y"

    assert second.scene_2d == {}
    assert second.scene_mode == "2d"
    assert second.camera_3d == {}
    assert second.selected_object_ids == []
    assert second.algebra_model == {}


def test_snapshot_round_trip_is_detached_and_excludes_renderers() -> None:
    state = ScenePaneState("pane-1", "主窗格")
    state.scene_2d = {"objects": [{"id": "P", "coordinates": [1, 2]}]}
    state.scene_3d = {"surfaces": [{"id": "S", "equation": "z=x"}]}
    state.camera_2d = {"center": [0, 0], "zoom": 2}
    state.selected_object_ids = ["P"]
    state.algebra_model = {"rows": [{"expression": "x^2"}]}
    state.renderer_2d = object()

    restored = ScenePaneState.from_snapshot(state.to_snapshot())
    assert restored.name == state.name
    assert restored.scene_2d == state.scene_2d
    assert restored.scene_3d == state.scene_3d
    assert restored.camera_2d == state.camera_2d
    assert restored.selected_object_ids == state.selected_object_ids
    assert restored.algebra_model == state.algebra_model
    assert restored.renderer_2d is None

    restored.scene_2d["objects"][0]["id"] = "changed"
    assert state.scene_2d["objects"][0]["id"] == "P"


def test_snapshot_rejects_invalid_ids_modes_and_non_json_values() -> None:
    with pytest.raises(ValueError):
        ScenePaneState("", "窗格")
    with pytest.raises(ValueError):
        ScenePaneState("pane", "窗格", scene_mode="invalid")

    state = ScenePaneState("pane", "窗格")
    state.scene_2d["renderer"] = object()
    with pytest.raises(ValueError, match="JSON-safe"):
        state.to_snapshot()

    with pytest.raises(ValueError):
        ScenePaneState.from_snapshot({"version": 1, "pane_id": "pane"})

