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
