"""Explicit chapter-4 semantic mappings shared by catalog and artifacts."""
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True)
class Chapter4Semantic:
    family: str
    primitive: str
    relation: str
    capabilities: tuple[str, ...]
    operation: str
    roles: tuple[str, ...]
    invariants: tuple[str, ...]

_MAPPING = {
    "ch04.space.closure": Chapter4Semantic("subspace_region", "vector", "spans", ("subspace_region",), "geometry.polygon", ("vector_a", "vector_b", "sum", "scaled"), ("additive_closure", "scalar_closure")),
    "ch04.subspace.classification": Chapter4Semantic("subspace_region", "region", "spans", ("polygon_2d",), "geometry.polygon", ("origin", "line", "plane", "whole_space", "affine_counterexample"), ("origin_contains", "affine_not_subspace")),
    "ch04.subspace.intersection": Chapter4Semantic("subspace_region", "region", "spans", ("polygon_2d",), "geometry.polygon", ("subspace_u", "subspace_v", "intersection", "union_counterexample"), ("intersection_closed", "union_not_closed")),
    "ch04.subspace.col-null": Chapter4Semantic("subspace_region", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("domain", "codomain", "kernel", "column_space"), ("diag_1_0", "kernel_to_zero", "image_x_axis")),
    "ch04.span.dimension": Chapter4Semantic("subspace_region", "vector", "spans", ("polygon_2d",), "geometry.polygon", ("span_1d", "span_2d", "span_3d"), ("rank_equals_dimension",)),
    "ch04.dependence.redundancy": Chapter4Semantic("basis_change", "vector", "spans", ("polygon_2d",), "geometry.polygon", ("dependent_set", "independent_set", "zero_combination"), ("nonzero_coefficients_sum_zero",)),
    "ch04.nullspace.test": Chapter4Semantic("basis_change", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("columns", "null_vector", "trivial_nullspace"), ("Ax_zero", "nonzero_null_solution")),
    "ch04.rank.collapse": Chapter4Semantic("basis_change", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("rank_two", "rank_one", "rank_zero"), ("rank_collapse_sequence",)),
    "ch04.basis.span": Chapter4Semantic("subspace_region", "basis", "spans", ("polygon_2d",), "geometry.polygon", ("independent_basis", "spanning_set", "too_few", "too_many"), ("independent_and_spanning",)),
    "ch04.dimension.ladder": Chapter4Semantic("subspace_region", "region", "spans", ("polygon_2d",), "geometry.polygon", ("point", "line", "plane", "volume"), ("nested_dimensions",)),
    "ch04.coordinates.readout": Chapter4Semantic("basis_change", "basis", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("standard_basis", "oblique_basis", "same_vector"), ("coordinate_reconstruction",)),
    "ch04.linear-map.definition": Chapter4Semantic("basis_change", "matrix", "maps_to", ("transformed_grid",), "linear_algebra.matrix_transform", ("map_T", "sum_test", "homogeneity_test", "origin"), ("origin_fixed", "additivity", "homogeneity")),
    "ch04.linear-map.compare": Chapter4Semantic("basis_change", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("linear_case", "translation", "square_map", "constant_shift"), ("nonlinear_diagnostics",)),
    "ch04.linear-map.matrix-columns": Chapter4Semantic("basis_change", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("standard_e1", "standard_e2", "column_1", "column_2"), ("Tej_equals_column_j",)),
    "ch04.kernel-image": Chapter4Semantic("subspace_region", "region", "spans", ("polygon_2d",), "geometry.polygon", ("domain", "kernel_direction", "zero", "image"), ("kernel_maps_zero", "image_reachable")),
    "ch04.rank-nullity": Chapter4Semantic("subspace_region", "matrix", "batch_maps_to", ("transformed_grid",), "geometry.transformed_grid", ("domain", "rank", "nullity", "preserved", "collapsed"), ("rank_plus_nullity_equals_domain")),
}
TOPIC_SEMANTICS: Mapping[str, Chapter4Semantic] = MappingProxyType(_MAPPING)
def semantic_for(topic_id: str) -> Chapter4Semantic:
    try:
        item = TOPIC_SEMANTICS[topic_id]
        roles = tuple(dict.fromkeys(("vector_a", "transformed_a", *item.roles)))
        return Chapter4Semantic(item.family, item.primitive, item.relation, item.capabilities, item.operation, roles, item.invariants)
    except KeyError as error: raise KeyError(f"unknown chapter 4 semantic mapping: {topic_id}") from error
__all__ = ["Chapter4Semantic", "TOPIC_SEMANTICS", "semantic_for"]
