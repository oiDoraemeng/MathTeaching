"""Deterministic, renderer-independent examples for chapter 4-8 scene families."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SceneFamilyFixture:
    family: str
    case: str
    payload: dict[str, object]
    expected: dict[str, object]


def scene_family_fixtures() -> tuple[SceneFamilyFixture, ...]:
    return (
        SceneFamilyFixture("subspace_structure", "normal", {"dimension": 3, "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}, {"rank": "full"}),
        SceneFamilyFixture("subspace_structure", "boundary", {"dimension": 3, "basis": [[1, 0, 0], [2, 0, 0], [0, 0, 0]]}, {"rank": "deficient"}),
        SceneFamilyFixture("subspace_structure", "failure", {"dimension": 3, "basis": [[1, 0], [0, 1]]}, {"classification": "invalid_dimension"}),
        SceneFamilyFixture("constraint_solution", "normal", {"dimension": 2, "matrix": [[1, 0], [0, 1]], "rhs": [2, -1]}, {"classification": "unique"}),
        SceneFamilyFixture("constraint_solution", "boundary", {"dimension": 2, "matrix": [[1, 1], [2, 2]], "rhs": [1, 2]}, {"classification": "infinite"}),
        SceneFamilyFixture("constraint_solution", "failure", {"dimension": 2, "matrix": [[1, 1], [2, 2]], "rhs": [1, 3]}, {"classification": "none"}),
        SceneFamilyFixture("basis_coordinate", "normal", {"dimension": 2, "basis": [[1, 0], [0, 1]], "vector": [2, 3]}, {"classification": "invertible"}),
        SceneFamilyFixture("basis_coordinate", "boundary", {"dimension": 2, "basis": [[1, 2], [2, 4]], "vector": [2, 4]}, {"classification": "singular"}),
        SceneFamilyFixture("basis_coordinate", "failure", {"dimension": 3, "basis": [[1, 0], [0, 1]], "vector": [1, 2, 3]}, {"classification": "invalid_dimension"}),
        SceneFamilyFixture("spectral_orthogonal", "normal", {"dimension": 2, "matrix": [[2, 0], [0, 3]], "roots": [2, 3]}, {"classification": "distinct_real_roots"}),
        SceneFamilyFixture("spectral_orthogonal", "boundary", {"dimension": 2, "matrix": [[2, 0], [0, 2]], "roots": [2, 2]}, {"classification": "repeated_roots"}),
        SceneFamilyFixture("spectral_orthogonal", "failure", {"dimension": 2, "matrix": [[0, -1], [1, 0]], "roots": ["i", "-i"]}, {"classification": "complex_roots"}),
        SceneFamilyFixture("quadratic_shape", "normal", {"dimension": 2, "matrix": [[2, 0], [0, 3]], "level": 1}, {"classification": "positive_definite"}),
        SceneFamilyFixture("quadratic_shape", "boundary", {"dimension": 2, "matrix": [[1, 0], [0, 0]], "level": 1}, {"classification": "degenerate"}),
        SceneFamilyFixture("quadratic_shape", "failure", {"dimension": 3, "matrix": [[1, 0, 0], [0, -1, 0], [0, 0, 1]], "level": 1}, {"classification": "indefinite"}),
    )


__all__ = ["SceneFamilyFixture", "scene_family_fixtures"]
