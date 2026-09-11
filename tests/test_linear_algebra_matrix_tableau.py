import pytest

from linear_algebra.visualizations.families.tableau import (
    Eliminate,
    MatrixTableauCompiler,
    Scale,
    Swap,
    apply_row_operation,
)
from services.scene_commands import CommandPlan, SceneCommandService


def test_eliminate_row_operation_has_exact_next_tableau():
    matrix, rhs = apply_row_operation(
        [[1, 2], [3, 4]], [5, 6], Eliminate(target=1, source=0, factor=3)
    )
    assert matrix == [[1, 2], [0, -2]]
    assert rhs == [5, -9]


def test_typed_row_operations_are_immutable_and_apply_exactly():
    assert apply_row_operation([[1, 2], [3, 4]], [5, 6], Swap(first=0, second=1)) == ([[3, 4], [1, 2]], [6, 5])
    assert apply_row_operation([[1, 2], [3, 4]], [5, 6], Scale(row=1, factor=2)) == ([[1, 2], [6, 8]], [5, 12])
    with pytest.raises(ValueError, match="factor"):
        apply_row_operation([[1, 2]], [5], Scale(row=0, factor=0))


def test_matrix_tableau_compiler_emits_immutable_stages_aliases_and_invariants():
    result = MatrixTableauCompiler.compile({
        "matrix": [[1, 2], [3, 4]], "rhs": [5, 6],
        "operations": [Eliminate(target=1, source=0, factor=3)],
        "solution_state": "unique", "rank": 2, "augmented_rank": 2,
        "alias_prefix": "elim",
    })
    assert len(result.stages) == 2
    assert result.stages[1].matrix == ((1.0, 2.0), (0.0, -2.0))
    assert result.stages[1].rhs == (5.0, -9.0)
    assert result.stages[1].highlight_rows == (1, 0)
    assert result.stages[1].alias == "elim__stage_1"
    assert result.stages[1].solution_state == "unique"
    assert result.stages[1].rank == result.stages[0].rank == 2


def test_matrix_tableau_command_is_validated_before_host_mutation():
    operation = {
        "op": "geometry.matrix_tableau", "matrix": [[1, 2], [3, 4]], "rhs": [5, 6],
        "stages": [{"matrix": [[1, 2], [0, -2]], "rhs": [5, -9], "alias": "stage_1", "highlight_rows": [1]}],
        "solution_state": "unique", "rank": 2, "augmented_rank": 2,
    }
    result = SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,)))
    assert result.valid
    assert result.expanded_operations[1]["op"] == "geometry.matrix_tableau"
