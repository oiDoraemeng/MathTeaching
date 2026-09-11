"""The closed semantic-primitive to :class:`CommandPlan` vocabulary.

This module is intentionally independent of renderers.  It is the small
boundary used by artifact and contract validation before a plan is compiled.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .palette import ROLE_COLORS


@dataclass(frozen=True)
class SemanticPrimitiveSpec:
    name: str
    command_ops: tuple[str, ...]
    dimensions: tuple[int, ...]
    required_fields: tuple[str, ...]


_COMMON_FIELDS = ("alias", "dimension", "claim_refs", "stage_id", "role", "data")
_SPECS: tuple[SemanticPrimitiveSpec, ...] = (
    SemanticPrimitiveSpec("subspace_family", ("geometry.subspace_region", "geometry.subspace3d"), (2, 3), (*_COMMON_FIELDS, "origin", "basis", "translation")),
    SemanticPrimitiveSpec("domain_image_map", ("geometry.mapping_bundle",), (2, 3), (*_COMMON_FIELDS, "domain_basis", "kernel_basis", "image_basis", "input_vectors", "output_vectors", "relations")),
    SemanticPrimitiveSpec("affine_solution_set", ("geometry.affine_solution",), (2, 3), (*_COMMON_FIELDS, "particular_solution", "nullspace_basis", "translation")),
    SemanticPrimitiveSpec("constraint_intersection", ("geometry.constraint", "geometry.intersection"), (2, 3), (*_COMMON_FIELDS, "constraints", "intersection")),
    SemanticPrimitiveSpec("elimination_tableau", ("geometry.matrix_tableau",), (2, 3), (*_COMMON_FIELDS, "matrix", "rhs", "row_operation", "highlight_rows")),
    SemanticPrimitiveSpec("least_squares_bundle", ("geometry.least_squares",), (2, 3), (*_COMMON_FIELDS, "data_points", "fit_kind", "fit_parameters", "projection_points", "residuals", "orthogonality_pairs")),
    SemanticPrimitiveSpec("basis_coordinate_map", ("geometry.basis_grid", "geometry.coordinate_readout"), (2, 3), (*_COMMON_FIELDS, "basis", "coordinates", "vector")),
    SemanticPrimitiveSpec("eigen_direction", ("geometry.spectrum",), (2, 3), (*_COMMON_FIELDS, "matrix", "roots", "eigenspaces")),
    SemanticPrimitiveSpec("spectral_roots", ("geometry.spectrum",), (2, 3), (*_COMMON_FIELDS, "matrix", "roots", "eigenspaces")),
    SemanticPrimitiveSpec("orthogonalization_bundle", ("geometry.orthogonalization",), (2, 3), (*_COMMON_FIELDS, "input_vectors", "projection_components", "orthogonal_basis")),
    SemanticPrimitiveSpec("quadratic_level_set", ("geometry.quadratic_level_set",), (2, 3), (*_COMMON_FIELDS, "matrix", "linear", "constant", "level", "classification", "principal_axes")),
)
_BY_NAME = {spec.name: spec for spec in _SPECS}
_OPS = {op for spec in _SPECS for op in spec.command_ops}
_ROLES = frozenset(ROLE_COLORS)


def primitive_spec(name: str) -> SemanticPrimitiveSpec:
    """Return the registered specification, or raise for an unknown name."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(f"Unknown semantic primitive: {name}") from None


def all_primitive_specs() -> tuple[SemanticPrimitiveSpec, ...]:
    return _SPECS


def validate_payload_header(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return stable diagnostics for a high-level operation payload header."""
    errors: list[str] = []
    op = payload.get("op")
    if not isinstance(op, str) or op not in _OPS:
        errors.append(f"op: unknown operation {op!r}")

    dimension = payload.get("dimension")
    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension not in (2, 3):
        errors.append(f"dimension: expected integer 2 or 3, got {dimension!r}")

    role = payload.get("role")
    if not isinstance(role, str) or role not in _ROLES:
        errors.append(f"role: unknown role {role!r}")

    claims = payload.get("claim_refs")
    if not isinstance(claims, (list, tuple)) or not claims or any(not isinstance(ref, str) or not ref.strip() for ref in claims):
        errors.append("claim_refs: must contain at least one non-empty reference")

    def visit(value: object, path: str) -> None:
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                errors.append(f"{path}: numeric value must be finite")
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                visit(item, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(payload, "$")
    return tuple(dict.fromkeys(errors))


__all__ = ["SemanticPrimitiveSpec", "primitive_spec", "all_primitive_specs", "validate_payload_header"]
