"""Closed mathematical witnesses and stage contracts for Chapter 6."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from linear_algebra.chapter_04_semantics import (
    EntityDescriptor,
    RelationDescriptor,
    StageDescriptor,
)


@dataclass(frozen=True)
class Ch6Spec:
    topic: str
    entities: tuple[EntityDescriptor, ...]
    relations: tuple[RelationDescriptor, ...]
    stages: tuple[StageDescriptor, ...]
    invariants: tuple[str, ...]
    formula: str
    operations: tuple[str, ...]

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(entity.role for entity in self.entities)

    @property
    def relation(self) -> str:
        return self.relations[0].kind


def _entity(role: str, value: object, kind: str = "vector") -> EntityDescriptor:
    return EntityDescriptor(role, kind, 2, value, role)


def _map(
    name: str,
    source: str,
    target: str,
    matrix: object,
    input_value: object,
    output: object,
    *,
    kind: str = "maps_to",
) -> RelationDescriptor:
    return RelationDescriptor(
        name,
        kind,
        source,
        target,
        (("matrix", matrix), ("input", input_value), ("output", output)),
    )


def _basis_change() -> Ch6Spec:
    identity = ((1.0, 0.0), (0.0, 1.0))
    basis = ((1.0, -1.0), (1.0, 1.0))
    inverse = ((0.5, 0.5), (-0.5, 0.5))
    invariants = (
        "P inverse P = I",
        "P c = x",
        "P inverse x = c",
        "standard basis change matrix is I",
    )
    entities = (
        _entity("standard_basis", identity, "matrix"),
        _entity("basis_matrix", basis, "matrix"),
        _entity("inverse_basis", inverse, "matrix"),
        _entity("forward_coordinates", (2.0, 3.0)),
        _entity("forward_vector", (-1.0, 5.0)),
        _entity("inverse_vector", (4.0, 2.0)),
        _entity("inverse_coordinates", (3.0, -1.0)),
        _entity("identity_basis", identity, "matrix"),
    )
    relations = (
        _map("forward", "forward_coordinates", "forward_vector", basis, (2.0, 3.0), (-1.0, 5.0)),
        _map("backward", "inverse_vector", "inverse_coordinates", inverse, (4.0, 2.0), (3.0, -1.0)),
        _map("identity", "standard_basis", "identity_basis", identity, identity, identity, kind="coordinate_equivalence"),
    )
    stages = (
        StageDescriptor("forward", "新坐标变成标准坐标", "overlay", ("basis_matrix", "forward_coordinates"), ("forward_vector",), ("forward",), invariants),
        StageDescriptor("backward", "标准坐标变成新坐标", "overlay", ("basis_matrix", "inverse_vector"), ("inverse_coordinates",), ("backward",), invariants),
        StageDescriptor("identity", "标准基到标准基", "overlay", ("standard_basis",), ("identity_basis",), ("identity",), invariants),
    )
    return Ch6Spec(
        "ch06.basis-change.coordinates",
        entities,
        relations,
        stages,
        invariants,
        r"\boldsymbol x=\boldsymbol P\boldsymbol c,\quad \boldsymbol c=\boldsymbol P^{-1}\boldsymbol x",
        ("geometry.transformed_grid", "linear.upsert"),
    )


def _similarity() -> Ch6Spec:
    identity = ((1.0, 0.0), (0.0, 1.0))
    basis = ((1.0, -1.0), (1.0, 1.0))
    inverse = ((0.5, 0.5), (-0.5, 0.5))
    operator = ((2.0, 1.0), (1.0, 2.0))
    similar = ((3.0, 0.0), (0.0, 1.0))
    invariants = (
        "B = P inverse A P",
        "A v1 = 3 v1",
        "A v2 = v2",
        "similarity preserves determinant rank trace and spectrum",
    )
    entities = (
        _entity("standard_basis", identity, "matrix"),
        _entity("basis_matrix", basis, "matrix"),
        _entity("inverse_basis", inverse, "matrix"),
        _entity("operator", operator, "matrix"),
        _entity("similar_operator", similar, "matrix"),
        _entity("basis_v1", (1.0, 1.0)),
        _entity("basis_v2", (-1.0, 1.0)),
        _entity("image_v1", (3.0, 3.0)),
        _entity("image_v2", (-1.0, 1.0)),
    )
    relations = (
        RelationDescriptor("similarity", "composition_order", "operator", "similar_operator", (("basis_matrix", basis), ("inverse_basis", inverse), ("operator", operator), ("similar_operator", similar))),
        _map("apply_v1", "basis_v1", "image_v1", operator, (1.0, 1.0), (3.0, 3.0)),
        _map("apply_v2", "basis_v2", "image_v2", operator, (-1.0, 1.0), (-1.0, 1.0)),
    )
    stages = (
        StageDescriptor("change_basis", "P：翻译为标准坐标", "sequence", ("basis_matrix",), ("standard_basis",), ("similarity",), invariants),
        StageDescriptor("apply_operator", "A：执行线性变换", "sequence", ("basis_v1", "basis_v2", "operator"), ("image_v1", "image_v2"), ("apply_v1", "apply_v2"), invariants),
        StageDescriptor("change_basis_back", "P⁻¹：翻译回新基", "sequence", ("inverse_basis", "operator"), ("similar_operator",), ("similarity",), invariants),
    )
    return Ch6Spec(
        "ch06.similarity-transform",
        entities,
        relations,
        stages,
        invariants,
        r"\boldsymbol B=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P",
        ("geometry.transformed_grid", "linear.upsert"),
    )


_SPECS = MappingProxyType(
    {
        "ch06.basis-change.coordinates": _basis_change(),
        "ch06.similarity-transform": _similarity(),
    }
)


def spec_for(topic: str) -> Ch6Spec:
    return _SPECS[topic if topic.startswith("ch06.") else f"ch06.{topic}"]


def specs() -> tuple[Ch6Spec, ...]:
    return tuple(_SPECS.values())


__all__ = ["Ch6Spec", "spec_for", "specs"]
