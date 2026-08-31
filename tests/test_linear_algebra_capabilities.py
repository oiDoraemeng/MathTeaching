from services.scene_commands import CommandPlan, SceneCommandService


def test_new_linear_algebra_operation_families_are_validated() -> None:
    validator = SceneCommandService()
    plans = (
        CommandPlan(scene="2d", operations=(
            {"op": "geometry.polygon", "alias": "area", "vertices": [[0, 0], [2, 0], [1, 1]], "opacity": 0.25},
            {"op": "geometry.angle_arc", "alias": "angle", "vertex": [0, 0], "first": [1, 0], "second": [0, 1], "radius": 0.4},
            {"op": "geometry.right_angle_marker", "alias": "right", "vertex": [0, 0], "first": [1, 0], "second": [0, 1], "size": 0.2},
            {"op": "geometry.projection", "vector": [3, 2], "direction": [2, 1], "result_alias": "proj", "foot_alias": "H", "residual_alias": "residual"},
            {"op": "geometry.transformed_grid", "matrix": [[1, 1], [0, 1]], "bounds": [-2, 2, -2, 2], "step": 1},
            {"op": "geometry.subspace_region", "basis": [[1, 2]], "bounds": [-2, 2, -2, 2], "opacity": 0.2},
            {"op": "geometry.staged_transform", "matrices": [[[1, 0], [0, 1]]], "points": [[1, 2]], "aliases": ["p"]},
            {"op": "geometry.oriented_area", "alias": "signed", "vectors": [[2, 0], [0, 3]]},
            {"op": "annotation.formula", "alias": "formula", "text": "det(A)=1", "position": [1, 1]},
        )),
        CommandPlan(scene="3d", operations=(
            {"op": "linear3d.upsert", "alias": "v", "start": [0, 0, 0], "end": [2, 1, 3], "kind": "vector"},
            {"op": "plane3d.upsert", "alias": "plane", "origin": [0, 0, 0], "normal": [0, 0, 1], "size": 2},
            {"op": "geometry.parallelogram3d", "alias": "face", "origin": [0, 0, 0], "vectors": [[1, 0, 0], [0, 2, 0]]},
            {"op": "geometry.parallelepiped", "alias": "box", "origin": [0, 0, 0], "vectors": [[1, 0, 0], [0, 2, 0], [0, 0, 3]]},
            {"op": "geometry.oriented_volume", "alias": "volume", "origin": [0, 0, 0], "vectors": [[1, 0, 0], [0, 2, 0], [0, 0, 3]]},
            {"op": "annotation.formula", "alias": "formula", "text": "V=6", "position": [0, 0, 0]},
        )),
    )
    for plan in plans:
        validation = validator.validate(plan)
        assert validation.valid, validation.messages


def test_new_operations_reject_wrong_scene_scope() -> None:
    validator = SceneCommandService()
    invalid_2d = validator.validate(CommandPlan(scene="2d", operations=(
        {"op": "linear3d.upsert", "alias": "v", "start": [0, 0, 0], "end": [1, 1, 1], "kind": "vector"},
    )))
    invalid_3d = validator.validate(CommandPlan(scene="3d", operations=(
        {"op": "geometry.polygon", "alias": "face", "vertices": [[0, 0], [1, 0], [0, 1]]},
    )))
    invalid_staged_3d = validator.validate(CommandPlan(scene="3d", operations=(
        {"op": "geometry.staged_transform", "matrices": [[[1, 0], [0, 1]]], "points": [[1, 0]], "aliases": ["p"]},
    )))
    assert not invalid_2d.valid
    assert not invalid_3d.valid
    assert not invalid_staged_3d.valid


def test_new_operations_reject_degenerate_geometry() -> None:
    validator = SceneCommandService()
    polygon = validator.validate(CommandPlan(scene="2d", operations=(
        {"op": "geometry.polygon", "alias": "face", "vertices": [[0, 0], [1, 0]]},
    )))
    volume = validator.validate(CommandPlan(scene="3d", operations=(
        {"op": "geometry.oriented_volume", "alias": "V", "origin": [0, 0, 0], "vectors": [[1, 0, 0], [0, 1, 0]]},
    )))
    collinear_polygon = validator.validate(CommandPlan(scene="2d", operations=(
        {"op": "geometry.polygon", "alias": "flat", "vertices": [[0, 0], [1, 0], [2, 0]]},
    )))
    assert not polygon.valid
    assert not volume.valid
    assert not collinear_polygon.valid
