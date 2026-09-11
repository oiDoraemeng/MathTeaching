import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures.linear_algebra_chapters_4_8 import scene_family_fixtures


def _numeric_leaves(value):
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [number for item in value.values() for number in _numeric_leaves(item)]
    if isinstance(value, (list, tuple)):
        return [number for item in value for number in _numeric_leaves(item)]
    return []


def test_each_scene_family_has_normal_boundary_and_failure_fixture():
    fixtures = scene_family_fixtures()
    grouped = {(item.family, item.case) for item in fixtures}
    expected_families = {
        "subspace_structure", "constraint_solution", "basis_coordinate",
        "spectral_orthogonal", "quadratic_shape",
    }
    for family in expected_families:
        assert {(family, kind) for kind in ("normal", "boundary", "failure")} <= grouped


def test_fixtures_are_finite_bounded_and_two_or_three_dimensional():
    fixtures = scene_family_fixtures()
    assert len(fixtures) == 15
    for fixture in fixtures:
        assert fixture.payload["dimension"] in (2, 3)
        numbers = _numeric_leaves(fixture.payload)
        assert all(math.isfinite(float(number)) for number in numbers)
        assert len(numbers) <= 256


def test_expected_classifications_cover_required_boundary_cases():
    fixtures = scene_family_fixtures()
    by_key = {(item.family, item.case): item for item in fixtures}
    assert by_key[("subspace_structure", "normal")].expected["rank"] == "full"
    assert by_key[("subspace_structure", "boundary")].expected["rank"] == "deficient"
    assert by_key[("constraint_solution", "normal")].expected["classification"] == "unique"
    assert by_key[("constraint_solution", "boundary")].expected["classification"] in {"none", "infinite"}
    assert by_key[("basis_coordinate", "normal")].expected["classification"] == "invertible"
    assert by_key[("basis_coordinate", "boundary")].expected["classification"] == "singular"
    assert by_key[("spectral_orthogonal", "boundary")].expected["classification"] == "repeated_roots"
    assert by_key[("spectral_orthogonal", "failure")].expected["classification"] == "complex_roots"
    assert by_key[("quadratic_shape", "normal")].expected["classification"] == "positive_definite"
    assert by_key[("quadratic_shape", "boundary")].expected["classification"] == "degenerate"
    assert by_key[("quadratic_shape", "failure")].expected["classification"] == "indefinite"
