import numpy as np
import pytest
from linear_algebra.visualizations.families.quadratic import QuadraticFamilyCompiler, classify_quadratic
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService

@pytest.mark.parametrize("matrix,expected", [([[2,0],[0,1]], "positive_definite"), ([[1,0],[0,-1]], "indefinite"), ([[1,0],[0,0]], "semidefinite")])
def test_quadratic_classification(matrix, expected):
    assert classify_quadratic(matrix, 1e-9).classification == expected

def test_principal_axes_are_stable_across_compilations():
    assert classify_quadratic([[3,1],[1,2]], 1e-9).principal_axes == classify_quadratic([[3,1],[1,2]], 1e-9).principal_axes

def test_quadratic_compiler_emits_bounded_level_set_and_stage_aliases():
    result = QuadraticFamilyCompiler.compile({"matrix": [[2,0],[0,1]], "bounds": [-2,2,-2,2]})
    assert result["aliases"] == ("quadratic__original", "quadratic__principal", "quadratic__standard")
    assert SceneCommandService().validate(CommandPlan(scene="2d", operations=result["operations"])).valid

def test_quadratic_rejects_nonsymmetric_and_over_budget():
    with pytest.raises(VisualCompileError, match="symmetric"):
        QuadraticFamilyCompiler.compile({"matrix": [[1,2],[0,1]]})
    with pytest.raises(VisualCompileError, match="budget"):
        QuadraticFamilyCompiler.compile({"matrix": [[1,0],[0,1]], "sample_count": 128 * 128 + 1})
