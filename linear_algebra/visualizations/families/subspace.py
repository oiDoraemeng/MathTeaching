"""Bounded semantic compilers for subspace and domain/image scenes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from ..compiler import CompileIssue, VisualCompileError


@dataclass(frozen=True)
class SubspaceCompileResult:
    operations: tuple[dict[str, Any], ...]
    evidence: Mapping[str, int]
    aliases: tuple[str, ...] = ()


def _numbers(values: object, name: str, dimension: int) -> tuple[float, ...]:
    if not isinstance(values, (list, tuple)) or len(values) != dimension:
        raise VisualCompileError((CompileIssue("invalid_dimension", f"$.{name}", f"invalid_dimension: expected {dimension} values"),))
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise VisualCompileError((CompileIssue("numeric_invalid", f"$.{name}", "numeric_invalid: values must be finite"),))
    return result


def _matrix_rank(matrix: list[list[float]], tolerance: float = 1e-9) -> int:
    rows = [row[:] for row in matrix]
    rank = 0
    for column in range(max((len(row) for row in rows), default=0)):
        pivot = next((index for index in range(rank, len(rows)) if abs(rows[index][column]) > tolerance), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][column]
        rows[rank] = [value / scale for value in rows[rank]]
        for index in range(len(rows)):
            if index != rank:
                factor = rows[index][column]
                rows[index] = [a - factor * b for a, b in zip(rows[index], rows[rank])]
        rank += 1
    return rank


class SubspaceFamilyCompiler:
    primitives = frozenset({"geometry.subspace3d", "geometry.affine_solution", "geometry.mapping_bundle"})

    @classmethod
    def validate(cls, payload: Mapping[str, object]) -> tuple[CompileIssue, ...]:
        issues: list[CompileIssue] = []
        primitive = payload.get("primitive", payload.get("op"))
        if primitive not in cls.primitives:
            issues.append(CompileIssue("unsupported_scene_family", "$.primitive", str(primitive)))
            return tuple(issues)
        dimension = payload.get("dimension", 3)
        if dimension not in (2, 3):
            issues.append(CompileIssue("invalid_dimension", "$.dimension", "dimension must be 2 or 3"))
            return tuple(issues)
        try:
            _numbers(payload.get("origin", [0] * int(dimension)), "origin", int(dimension))
            _numbers(payload.get("affine_offset", [0] * int(dimension)), "affine_offset", int(dimension))
        except VisualCompileError as error:
            issues.extend(error.issues)
        basis = payload.get("basis", [])
        if not isinstance(basis, (list, tuple)) or not basis:
            issues.append(CompileIssue("missing_basis", "$.basis", "basis must be non-empty"))
        else:
            for index, vector in enumerate(basis):
                try:
                    _numbers(vector, f"$.basis[{index}]", int(dimension))
                except VisualCompileError as error:
                    issues.extend(error.issues)
        if payload.get("is_linear", False) and any(abs(value) > 1e-12 for value in _numbers(payload.get("affine_offset", [0] * int(dimension)), "affine_offset", int(dimension))):
            issues.append(CompileIssue("origin_required", "$.affine_offset", "origin_required: linear subspaces must pass through origin"))
        return tuple(issues)

    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> SubspaceCompileResult:
        issues = cls.validate(payload)
        if issues:
            raise VisualCompileError(issues)
        primitive = str(payload.get("primitive", payload.get("op")))
        dimension = int(payload.get("dimension", 3))
        origin = list(_numbers(payload.get("origin", [0] * dimension), "origin", dimension))
        offset = list(_numbers(payload.get("affine_offset", [0] * dimension), "affine_offset", dimension))
        basis = [list(_numbers(vector, "basis", dimension)) for vector in payload["basis"]]  # type: ignore[index]
        if len(basis) > 3:
            raise VisualCompileError((CompileIssue("layout_overflow", "$.basis", "at most three basis vectors are supported"),))
        rank = _matrix_rank(basis)
        domain_dimension = int(payload.get("domain_dimension", len(basis)))
        nullity = max(0, domain_dimension - rank)
        prefix = str(payload.get("alias_prefix", "mapping" if primitive == "geometry.mapping_bundle" else "subspace"))
        op_name = primitive
        operation = {"op": op_name, "alias": prefix, "origin": origin, "basis": basis, "offset": offset,
                     "dimension": dimension, "bounds": list(payload.get("bounds", [-2, 2, -2, 2, -2, 2] if dimension == 3 else [-2, 2, -2, 2]))}
        operations: list[dict[str, Any]] = [operation]
        aliases = [f"{prefix}__domain"]
        if primitive == "geometry.mapping_bundle":
            operations[0] = {**operation, "domain_alias": f"{prefix}__domain", "kernel_alias": f"{prefix}__kernel", "image_alias": f"{prefix}__image"}
            aliases.extend((f"{prefix}__kernel", f"{prefix}__image"))
        return SubspaceCompileResult(tuple(operations), {"rank": rank, "nullity": nullity, "domain_dimension": domain_dimension}, tuple(aliases))


__all__ = ["SubspaceCompileResult", "SubspaceFamilyCompiler"]
