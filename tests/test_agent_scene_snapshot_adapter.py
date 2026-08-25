from __future__ import annotations

from agent.scene_snapshot import SceneSnapshot
from models.curve_layer import CurveLayer
from models.geometry_2d import Annotation2D, Linear2D, Point2D
from models.scene_mode import SceneMode
from models.surface_layer import SurfaceLayer
from ui.designer_window import MainWindow, _SceneCommandState


def test_designer_scene_snapshot_round_trip_is_json_only() -> None:
    state = _SceneCommandState(
        points=(Point2D("P", 1.0, 2.0),),
        linears=(Linear2D("v", "vector", "p", "q"),),
        annotations=(Annotation2D("note", "hello", 0.0, 1.0),),
        curves=(CurveLayer("f", "explicit", "y=x"),),
        object_order=("P", "v", "note"),
        surfaces=(SurfaceLayer("plane", "explicit", "z=0"),),
        scene_mode=SceneMode.TWO_D,
        points3d=(("A", (1.0, 2.0, 3.0)),),
        areas=(("area", {"op": "area.fill"}),),
    )

    snapshot = MainWindow._scene_snapshot_from_state(state)
    restored = MainWindow._state_from_scene_snapshot(SceneSnapshot.from_dict(snapshot.to_dict()))

    assert restored.scene_mode is SceneMode.TWO_D
    assert restored.points[0].name == "P"
    assert restored.linears[0].kind == "vector"
    assert restored.curves[0].expression == "y=x"
    assert restored.points3d == (("A", (1.0, 2.0, 3.0)),)
