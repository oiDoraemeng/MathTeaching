import numpy as np
import pytest

from linear_algebra.visualizations.families.orthogonalization import OrthogonalizationFamilyCompiler, gram_schmidt
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService


def test_gram_schmidt_outputs_orthonormal_basis():
    evidence = gram_schmidt([[1, 1, 0], [1, 0, 1]], 1e-9)
    np.testing.assert_allclose(evidence.basis @ evidence.basis.T, np.eye(2), atol=1e-9)


def test_gram_schmidt_rejects_dependent_vectors():
    with pytest.raises(VisualCompileError, match="dependent"):
        OrthogonalizationFamilyCompiler.compile({"vectors": [[1, 0, 0], [2, 0, 0]]})


def test_orthogonalization_compiler_emits_stages_and_command_gate():
    result = OrthogonalizationFamilyCompiler.compile({"vectors": [[1, 0, 0], [1, 1, 0]], "bounds": [-2, 2, -2, 2, -2, 2]})
    assert result["aliases"] == ("orthogonalization__input", "orthogonalization__projection", "orthogonalization__residual", "orthogonalization__normalized")
    assert SceneCommandService().validate(CommandPlan(scene="3d", operations=result["operations"])).valid
