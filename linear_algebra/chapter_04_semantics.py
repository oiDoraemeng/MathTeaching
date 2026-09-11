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

_MAPPING = {
    "ch04.space.closure": Chapter4Semantic("subspace_region", "subspace_region", "spans", ("subspace_region",)),
    "ch04.subspace.classification": Chapter4Semantic("subspace_region", "subspace_region", "compare", ("polygon_2d",)),
    "ch04.subspace.intersection": Chapter4Semantic("subspace_region", "subspace_region", "projects_to", ("projection_2d",)),
    "ch04.subspace.col-null": Chapter4Semantic("subspace_region", "subspace_region", "collapses_to", ("vector_2d",)),
    "ch04.span.dimension": Chapter4Semantic("subspace_region", "subspace_region", "spans", ("polygon_2d",)),
    "ch04.dependence.redundancy": Chapter4Semantic("subspace_region", "subspace_region", "orientation", ("angle_2d",)),
    "ch04.nullspace.test": Chapter4Semantic("subspace_region", "subspace_region", "collapses_to", ("transformed_grid",)),
    "ch04.rank.collapse": Chapter4Semantic("subspace_region", "subspace_region", "batch_maps_to", ("transformed_grid",)),
    "ch04.basis.span": Chapter4Semantic("basis_change", "basis_change", "spans", ("polygon_2d",)),
    "ch04.dimension.ladder": Chapter4Semantic("basis_change", "basis_change", "composition_order", ("staged_transform",)),
    "ch04.coordinates.readout": Chapter4Semantic("basis_change", "basis_change", "compare", ("transformed_grid",)),
    "ch04.linear-map.definition": Chapter4Semantic("basis_change", "basis_change", "maps_to", ()),
    "ch04.linear-map.compare": Chapter4Semantic("basis_change", "basis_change", "composition_order", ("staged_transform",)),
    "ch04.linear-map.matrix-columns": Chapter4Semantic("basis_change", "basis_change", "batch_maps_to", ("transformed_grid",)),
    "ch04.kernel-image": Chapter4Semantic("affine_solution", "affine_solution", "spans", ("subspace_region",)),
    "ch04.rank-nullity": Chapter4Semantic("affine_solution", "affine_solution", "compare", ("vector_2d",)),
}
TOPIC_SEMANTICS: Mapping[str, Chapter4Semantic] = MappingProxyType(_MAPPING)
def semantic_for(topic_id: str) -> Chapter4Semantic:
    try: return TOPIC_SEMANTICS[topic_id]
    except KeyError as error: raise KeyError(f"unknown chapter 4 semantic mapping: {topic_id}") from error
__all__ = ["Chapter4Semantic", "TOPIC_SEMANTICS", "semantic_for"]
