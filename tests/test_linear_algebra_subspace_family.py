import pytest

from linear_algebra.visualizations.compiler import VisualCompileError
from linear_algebra.visualizations.families.subspace import SubspaceFamilyCompiler


def test_mapping_bundle_emits_kernel_and_image_with_rank_nullity():
    result = SubspaceFamilyCompiler.compile({
        "primitive": "geometry.mapping_bundle", "dimension": 3,
        "origin": [0, 0, 0], "basis": [[1, 0, 0], [0, 1, 0]],
        "affine_offset": [0, 0, 0], "domain_dimension": 3,
    })
    assert {item["op"] for item in result.operations} >= {"geometry.mapping_bundle"}
    assert result.evidence["rank"] + result.evidence["nullity"] == result.evidence["domain_dimension"]
    assert {"mapping__domain", "mapping__kernel", "mapping__image"} == set(result.aliases)


def test_affine_line_is_rejected_when_marked_as_linear_subspace():
    with pytest.raises(VisualCompileError, match="origin_required"):
        SubspaceFamilyCompiler.compile({
            "primitive": "geometry.subspace3d", "dimension": 3,
            "origin": [0, 0, 0], "basis": [[1, 0, 0]], "affine_offset": [1, 0, 0], "is_linear": True,
        })


def test_nonfinite_basis_is_rejected_before_scene_mutation():
    with pytest.raises(VisualCompileError, match="numeric_invalid"):
        SubspaceFamilyCompiler.compile({"primitive": "geometry.subspace3d", "dimension": 3, "basis": [[float("nan"), 0, 0]]})


@pytest.mark.parametrize("bounds", ([2, -2, -1, 1, -1, 1], [0, 1, 0, 1], [0, float("nan"), 0, 1, 0, 1]))
def test_bounds_are_finite_dimension_matched_and_ordered(bounds):
    with pytest.raises(VisualCompileError):
        SubspaceFamilyCompiler.compile({"primitive": "geometry.subspace3d", "dimension": 3, "basis": [[1, 0, 0]], "bounds": bounds})


def test_mapping_bundle_emits_consumable_lane_payload():
    domain_basis = [[1, 0, 0], [0, 1, 0]]
    kernel_basis = [[0, 0, 1]]
    image_basis = [[2, 0, 0], [0, 2, 0]]
    result = SubspaceFamilyCompiler.compile({"primitive": "geometry.mapping_bundle", "dimension": 3, "basis": domain_basis, "domain_basis": domain_basis, "kernel_basis": kernel_basis, "image_basis": image_basis, "domain_dimension": 3, "input_dimension": 3})
    payload = result.operations[0]
    assert payload["domain_basis"] and payload["image_basis"]
    assert payload["rank"] + payload["nullity"] == 3
    assert set(payload["lanes"]) == {"domain", "kernel", "image"}
    assert all(payload["lanes"][lane]["alias"] in result.aliases for lane in payload["lanes"])
    assert payload["lanes"]["domain"]["basis"] == domain_basis
    assert payload["lanes"]["kernel"]["basis"] == kernel_basis
    assert payload["lanes"]["image"]["basis"] == image_basis


def test_string_bounds_are_numeric_invalid():
    with pytest.raises(VisualCompileError, match="numeric_invalid"):
        SubspaceFamilyCompiler.compile({"primitive": "geometry.subspace3d", "dimension": 3, "basis": [[1, 0, 0]], "bounds": ["bad", 1, -1, 1, -1, 1]})


def test_over_budget_bounds_are_rejected_before_operation_emission():
    with pytest.raises(VisualCompileError, match="render_budget"):
        SubspaceFamilyCompiler.compile({"primitive": "geometry.subspace3d", "dimension": 3, "basis": [[1, 0, 0]], "bounds": [-1e9, 1e9, -1, 1, -1, 1]})
