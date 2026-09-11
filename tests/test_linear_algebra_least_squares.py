import numpy as np
import pytest

from linear_algebra.visualizations.families.least_squares import LeastSquaresFamilyCompiler, least_squares_fit
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService


def test_least_squares_residual_is_orthogonal_to_columns():
    evidence = least_squares_fit([[1, 0], [1, 1], [1, 2]], [1, 2, 2], 1e-9)
    np.testing.assert_allclose(evidence.design_matrix.T @ evidence.residual, [0, 0], atol=1e-9)


def test_least_squares_preserves_fit_projection_residual_aliases():
    result = LeastSquaresFamilyCompiler.compile({"matrix": [[1, 0], [1, 1], [1, 2]], "values": [1, 2, 2]})
    assert result["aliases"] == ("least_squares__data", "least_squares__fit", "least_squares__projection", "least_squares__residual")
    assert SceneCommandService().validate(CommandPlan(scene="2d", operations=result["operations"])).valid


def test_least_squares_rejects_nonfinite_and_singular_tolerance():
    with pytest.raises(VisualCompileError):
        LeastSquaresFamilyCompiler.compile({"matrix": [[1, 0], [1, 1]], "values": [1, float("nan")]})
    with pytest.raises(ValueError, match="tolerance"):
        least_squares_fit([[1], [2]], [1, 2], 0)


def test_least_squares_budget_rejects_before_lstsq(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("lstsq must not run")
    monkeypatch.setattr(np.linalg, "lstsq", fail)
    with pytest.raises(VisualCompileError, match="render_budget"):
        LeastSquaresFamilyCompiler.compile({"matrix": [[1, 0]] * 20000, "values": [1] * 20000})
