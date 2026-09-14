import pytest
from linear_algebra.visualizations.families.constraints import ConstraintFamilyCompiler, classify_constraint_system
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService

@pytest.mark.parametrize("matrix,rhs,expected", [([[1,0],[0,1]],[1,2],"unique"), ([[1,0],[1,0]],[1,2],"none"), ([[1,0],[2,0]],[1,2],"infinite")])
def test_constraint_solution_classification(matrix, rhs, expected):
    assert classify_constraint_system(matrix, rhs).kind == expected

def test_constraint_compile_preserves_state_and_intersection_alias():
    result = ConstraintFamilyCompiler.compile({"matrix":[[1,0],[0,1]],"rhs":[1,2]})
    assert result["evidence"].kind == "unique"
    assert result["operations"][0]["intersection_alias"] in result["aliases"]
    assert result["operations"][0]["state_alias"] == "constraint__point"


@pytest.mark.parametrize(
    "scene,matrix,rhs,solution_op,state_alias",
    [
        ("2d", [[1, 0], [0, 1]], [1, 2], "point.upsert", "constraint__point"),
        ("2d", [[1, 0], [2, 0]], [1, 2], "linear.upsert", "constraint__line"),
        ("3d", [[1, 0, 0], [0, 1, 0], [0, 0, 0]], [1, 2, 0], "linear3d.upsert", "constraint__line"),
        ("3d", [[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 0, 0], "plane3d.upsert", "constraint__plane"),
        ("3d", [[0, 0, 0], [0, 0, 0], [0, 0, 0]], [0, 0, 0], "annotation.formula", "constraint__space"),
    ],
)
def test_compiled_constraint_is_scene_valid_and_rank_specific(scene, matrix, rhs, solution_op, state_alias):
    operation = ConstraintFamilyCompiler.compile({"matrix": matrix, "rhs": rhs})["operations"][0]
    assert operation["state_alias"] == state_alias
    assert operation["solution_geometry"]["op"] == solution_op
    validation = SceneCommandService().validate(CommandPlan(scene=scene, operations=(operation,)))
    assert validation.valid, validation.messages


@pytest.mark.parametrize("matrix,rhs,state_alias", [([[1,0],[1,0]],[1,2], "constraint__empty"), ([[1,0],[2,0]],[1,2], "constraint__line")])
def test_constraint_states_emit_dimension_specific_geometry(matrix, rhs, state_alias):
    result = ConstraintFamilyCompiler.compile({"matrix": matrix, "rhs": rhs})
    assert result["operations"][0]["state_alias"] == state_alias
    assert result["operations"][0]["solution_geometry"]["op"] in {"annotation.upsert", "linear.upsert"}

@pytest.mark.parametrize("payload", [{"matrix":[[1,0],[0,1]],"rhs":[1,2],"bounds":[1,-1,-2,2]}, {"matrix":[[1,0],[0,1]],"rhs":[1,2],"tolerance":0}])
def test_constraint_rejects_invalid_numeric_or_bounds(payload):
    with pytest.raises(VisualCompileError): ConstraintFamilyCompiler.compile(payload)


@pytest.mark.parametrize("key", ["stage_count", "sample_count"])
@pytest.mark.parametrize("value", [True, 1.5, "2", -1])
def test_constraint_rejects_non_integer_budget_counts(key, value):
    with pytest.raises(VisualCompileError, match="invalid_budget_count"):
        ConstraintFamilyCompiler.compile({"matrix": [[1, 0], [0, 1]], "rhs": [1, 2], key: value})


@pytest.mark.parametrize("operation", [
    {"op": "geometry.constraint", "matrix": [[1, 0]], "rhs": [1], "solution_state": "unique", "rank": 1, "augmented_rank": 1, "bounds": [-1, 1, -1, 1]},
    {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "bad", "rank": 2, "augmented_rank": 2, "bounds": [-1, 1, -1, 1]},
    {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "unique", "rank": 3, "augmented_rank": 2, "bounds": [-1, 1, -1, 1]},
    {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "unique", "rank": 2, "augmented_rank": 2, "tolerance": 0, "bounds": [-1, 1, -1, 1]},
    {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "unique", "rank": 2, "augmented_rank": 2, "bounds": [1, -1, -1, 1]},
])
def test_scene_command_service_rejects_invalid_constraint_gates(operation):
    result = SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,)))
    assert not result.valid


@pytest.mark.parametrize(
    "scene,operation",
    [
        ("2d", {"op": "geometry.constraint", "dimension": 3, "matrix": [[1, 0], [0, 1]], "rhs": [1, 2]}),
        ("3d", {"op": "geometry.constraint", "dimension": 2, "matrix": [[1, 0], [0, 1]], "rhs": [1, 2]}),
        ("2d", {"op": "geometry.constraint", "dimension": True, "matrix": [[1, 0], [0, 1]], "rhs": [1, 2]}),
    ],
)
def test_scene_command_service_rejects_constraint_dimension_mismatch(scene, operation):
    result = SceneCommandService().validate(CommandPlan(scene=scene, operations=(operation,)))
    assert not result.valid


def test_scene_command_service_rejects_constraint_budget_before_host_mutation():
    operation = {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "unique", "rank": 2, "augmented_rank": 2, "bounds": [-1e9, 1e9, -1, 1]}
    result = SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,)))
    assert not result.valid


def test_scene_command_service_3d_constraint_budget_reports_budget_error():
    operation = {"op": "geometry.constraint", "scene": "3d", "matrix": [[1,0,0],[0,1,0],[0,0,1]], "rhs": [1,2,3], "solution_state": "unique", "rank": 3, "augmented_rank": 3, "entity_count": 33, "stage_count": 7, "sample_count": 64 * 64 * 64 + 1, "bounds": [-2,2,-2,2,-2,2]}
    result = SceneCommandService().validate(CommandPlan(scene="3d", operations=(operation,)))
    assert not result.valid
    assert any("render_budget" in message or "budget" in message for message in result.messages)
