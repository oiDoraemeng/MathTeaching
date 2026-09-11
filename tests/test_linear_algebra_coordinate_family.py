import numpy as np
import pytest

from linear_algebra.visualizations.families.coordinates import CoordinateFamilyCompiler, coordinate_evidence
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService


def test_alternate_coordinates_round_trip_to_same_vector():
    evidence = coordinate_evidence([[1, 1], [0, 1]], [2, 3])
    np.testing.assert_allclose(evidence.basis_matrix @ evidence.alternate_coordinates, evidence.standard_vector)


def test_coordinate_readout_rejects_singular_basis():
    with pytest.raises(VisualCompileError, match="singular"):
        CoordinateFamilyCompiler.compile({"primitive": "geometry.coordinate_readout", "basis_matrix": [[1, 2], [2, 4]], "standard_vector": [1, 2]})


def test_coordinate_compiler_emits_stable_aliases_and_command_is_validated():
    result = CoordinateFamilyCompiler.compile({"primitive": "geometry.basis_grid", "basis_matrix": [[1, 0], [0, 1]], "standard_vector": [2, 3], "alias_prefix": "coords"})
    assert result["aliases"] == ("coords__basis_grid", "coords__standard", "coords__alternate")
    operation = result["operations"][0]
    assert SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,))).valid


def test_coordinate_budget_rejects_before_solve(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("solve must not run")
    monkeypatch.setattr(np.linalg, "solve", fail)
    with pytest.raises(VisualCompileError, match="render_budget"):
        CoordinateFamilyCompiler.compile({"primitive": "geometry.basis_grid", "basis_matrix": [[1, 0], [0, 1]], "standard_vector": [2, 3], "bounds": [-1000, 1000, -2, 2]})
