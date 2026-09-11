import math

import pytest

from linear_algebra.visualizations.capability_map import (
    all_primitive_specs,
    primitive_spec,
    validate_payload_header,
)


def test_all_extended_primitives_have_command_mapping() -> None:
    names = {item.name for item in all_primitive_specs()}
    expected = {
        "subspace_family", "domain_image_map", "affine_solution_set",
        "constraint_intersection", "elimination_tableau", "least_squares_bundle",
        "basis_coordinate_map", "eigen_direction", "spectral_roots",
        "orthogonalization_bundle", "quadratic_level_set",
    }
    assert expected <= names
    assert primitive_spec("quadratic_level_set").command_ops == ("geometry.quadratic_level_set",)


@pytest.mark.parametrize("payload, field", [
    ({"op": "geometry.unknown", "dimension": 2, "role": "vector_a", "claim_refs": ["c"]}, "op"),
    ({"op": "geometry.spectrum", "dimension": 4, "role": "vector_a", "claim_refs": ["c"]}, "dimension"),
    ({"op": "geometry.spectrum", "dimension": 2.0, "role": "vector_a", "claim_refs": ["c"]}, "dimension"),
    ({"op": "geometry.spectrum", "dimension": 2, "role": "unknown", "claim_refs": ["c"]}, "role"),
    ({"op": "geometry.spectrum", "dimension": 2, "role": "vector_a", "claim_refs": []}, "claim_refs"),
    ({"op": "geometry.spectrum", "dimension": 2, "role": "vector_a", "claim_refs": ["c"], "value": math.inf}, "finite"),
])
def test_payload_header_rejects_invalid_values(payload: dict[str, object], field: str) -> None:
    errors = validate_payload_header(payload)
    assert field in " ".join(errors)
