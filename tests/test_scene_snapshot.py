from __future__ import annotations

import pytest

from agent.scene_snapshot import SceneSnapshot


def test_snapshot_round_trip_preserves_scene_state() -> None:
    snapshot = SceneSnapshot(
        version=1,
        scene_mode="2d",
        curves=({"alias": "f", "expression": "y=x^2"},),
        geometry=({"alias": "P", "coordinates": [1, 2]},),
        layers=(),
        annotations=(),
        camera={"parallel_scale": 10.0},
    )

    assert SceneSnapshot.from_json(snapshot.to_json()) == snapshot


def test_snapshot_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="version"):
        SceneSnapshot.from_dict({"version": 99})


def test_snapshot_emits_json_compatible_primitives() -> None:
    snapshot = SceneSnapshot(
        scene_mode="3d",
        geometry=({"alias": "P", "coordinates": [1, 2, 3]},),
    )

    payload = snapshot.to_dict()

    assert payload["version"] == 1
    assert isinstance(payload["geometry"], list)
    assert payload["geometry"][0]["coordinates"] == [1, 2, 3]


def test_snapshot_round_trip_preserves_multi_pane_extension_and_legacy_fields() -> None:
    snapshot = SceneSnapshot(
        scene_mode="2d",
        geometry=({"alias": "active"},),
        active_pane_id="pane-2",
        panes=(
            {"pane_id": "pane-1", "visible": False, "snapshot": {"scene_mode": "2d"}},
            {"pane_id": "pane-2", "visible": True, "snapshot": {"scene_mode": "3d"}},
        ),
    )
    restored = SceneSnapshot.from_dict(snapshot.to_dict())
    assert restored.active_pane_id == "pane-2"
    assert len(restored.panes) == 2
    # Existing consumers still receive the active-pane legacy projection.
    assert restored.geometry == ({"alias": "active"},)


def test_snapshot_rejects_invalid_active_pane_id() -> None:
    with pytest.raises(ValueError, match="active_pane_id"):
        SceneSnapshot(active_pane_id=" ")


def test_snapshot_rejects_pane_without_id() -> None:
    with pytest.raises(ValueError, match="pane_id"):
        SceneSnapshot(panes=({"visible": True},))
