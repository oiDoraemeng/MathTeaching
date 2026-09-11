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


@pytest.mark.parametrize("matrix,rhs,state_alias", [([[1,0],[1,0]],[1,2], "constraint__empty"), ([[1,0],[2,0]],[1,2], "constraint__line")])
def test_constraint_states_emit_dimension_specific_geometry(matrix, rhs, state_alias):
    result = ConstraintFamilyCompiler.compile({"matrix": matrix, "rhs": rhs})
    assert result["operations"][0]["state_alias"] == state_alias
    assert result["operations"][0]["solution_geometry"]["op"] in {"annotation.upsert", "linear.upsert"}

@pytest.mark.parametrize("payload", [{"matrix":[[1,0],[0,1]],"rhs":[1,2],"bounds":[1,-1,-2,2]}, {"matrix":[[1,0],[0,1]],"rhs":[1,2],"tolerance":0}])
def test_constraint_rejects_invalid_numeric_or_bounds(payload):
    with pytest.raises(VisualCompileError): ConstraintFamilyCompiler.compile(payload)


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


def test_scene_command_service_rejects_constraint_budget_before_host_mutation():
    operation = {"op": "geometry.constraint", "matrix": [[1, 0], [0, 1]], "rhs": [1, 2], "solution_state": "unique", "rank": 2, "augmented_rank": 2, "bounds": [-1e9, 1e9, -1, 1]}
    result = SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,)))
    assert not result.valid
