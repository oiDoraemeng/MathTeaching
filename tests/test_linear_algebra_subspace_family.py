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
