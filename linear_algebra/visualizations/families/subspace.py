"""Bounded semantic compilers for subspace and domain/image scenes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from ..compiler import CompileIssue, VisualCompileError
from ..limits import limits_for, validate_budget


@dataclass(frozen=True)
class SubspaceCompileResult:
    operations: tuple[dict[str, Any], ...]
    evidence: Mapping[str, int]
    aliases: tuple[str, ...] = ()


def _numbers(values: object, name: str, dimension: int) -> tuple[float, ...]:
    if not isinstance(values, (list, tuple)) or len(values) != dimension:
        raise VisualCompileError((CompileIssue("invalid_dimension", f"$.{name}", f"invalid_dimension: expected {dimension} values"),))
    try:
        result = tuple(float(value) for value in values)
    except (TypeError, ValueError, OverflowError) as error:
        raise VisualCompileError((CompileIssue("numeric_invalid", f"$.{name}", "numeric_invalid: values must be finite numbers"),)) from error
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
            _numbers(payload.get("origin", [0] * dimension), "origin", dimension)
            _numbers(payload.get("affine_offset", [0] * dimension), "affine_offset", dimension)
        except VisualCompileError as error:
            issues.extend(error.issues)
        basis = payload.get("basis", [])
        if not isinstance(basis, (list, tuple)) or not basis:
            issues.append(CompileIssue("missing_basis", "$.basis", "basis must be non-empty"))
        else:
            for index, vector in enumerate(basis):
                try:
                    _numbers(vector, f"basis[{index}]", dimension)
                except VisualCompileError as error:
                    issues.extend(error.issues)
        if payload.get("is_linear", False) and any(abs(value) > 1e-12 for value in _numbers(payload.get("affine_offset", [0] * dimension), "affine_offset", dimension)):
            issues.append(CompileIssue("origin_required", "$.affine_offset", "origin_required: linear subspaces must pass through origin"))
        bounds = payload.get("bounds", [-2, 2, -2, 2, -2, 2] if dimension == 3 else [-2, 2, -2, 2])
        expected = 2 * dimension
        if not isinstance(bounds, (list, tuple)) or len(bounds) != expected:
            issues.append(CompileIssue("invalid_bounds", "$.bounds", f"invalid_bounds: expected {expected} finite values"))
        else:
            try:
                numeric_bounds = tuple(float(value) for value in bounds)
            except (TypeError, ValueError, OverflowError):
                numeric_bounds = ()
            if len(numeric_bounds) != expected or not all(math.isfinite(value) for value in numeric_bounds):
                issues.append(CompileIssue("numeric_invalid", "$.bounds", "numeric_invalid: bounds must be finite numbers"))
            elif any(numeric_bounds[index] >= numeric_bounds[index + 1] for index in range(0, expected, 2)):
                issues.append(CompileIssue("invalid_bounds", "$.bounds", "invalid_bounds: lower bound must be less than upper bound"))
            elif any(abs(value) > 100.0 for value in numeric_bounds):
                issues.append(CompileIssue("render_budget", "$.bounds", "render_budget: bounds exceed teaching extent"))
        if primitive == "geometry.mapping_bundle":
            domain_dimension = payload.get("domain_dimension", len(basis) if isinstance(basis, (list, tuple)) else 0)
            if isinstance(domain_dimension, bool) or not isinstance(domain_dimension, int) or domain_dimension < 1 or domain_dimension > 3:
                issues.append(CompileIssue("invalid_dimension", "$.domain_dimension", "domain_dimension must be an integer from 1 to 3"))
            elif isinstance(basis, (list, tuple)):
                try:
                    checked_basis = [list(_numbers(vector, f"basis[{index}]", dimension)) for index, vector in enumerate(basis)]
                    if domain_dimension < _matrix_rank(checked_basis):
                        issues.append(CompileIssue("invalid_dimension", "$.domain_dimension", "domain_dimension must be at least rank"))
                except VisualCompileError as error:
                    issues.extend(error.issues)
            input_dimension = payload.get("input_dimension", domain_dimension)
            if input_dimension != domain_dimension:
                issues.append(CompileIssue("invalid_dimension", "$.input_dimension", "input_dimension must match domain_dimension"))
        if isinstance(basis, (list, tuple)) and len(basis) > limits_for("lecture-v1").max_entities_3d:
            issues.append(CompileIssue("layout_overflow", "$.basis", "layout_overflow: basis exceeds render budget"))
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2 * dimension:
            scene = "3d" if dimension == 3 else "2d"
            for error in validate_budget("lecture-v1", scene=scene, entity_count=len(basis), stage_count=1, sample_count=len(basis), bounds=tuple(float(value) for value in bounds)):
                if "bounds" in error:
                    issues.append(CompileIssue("render_budget", "$.bounds", error))
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
        domain_dimension = payload.get("domain_dimension", len(basis))
        if isinstance(domain_dimension, bool) or not isinstance(domain_dimension, int):
            raise VisualCompileError((CompileIssue("invalid_dimension", "$.domain_dimension", "domain_dimension must be an integer"),))
        nullity = domain_dimension - rank
        prefix = str(payload.get("alias_prefix", "mapping" if primitive == "geometry.mapping_bundle" else "subspace"))
        op_name = primitive
        operation = {"op": op_name, "alias": prefix, "origin": origin, "basis": basis, "offset": offset,
                     "dimension": dimension, "bounds": list(payload.get("bounds", [-2, 2, -2, 2, -2, 2] if dimension == 3 else [-2, 2, -2, 2]))}
        operations: list[dict[str, Any]] = [operation]
        aliases = [f"{prefix}__domain"]
        if primitive == "geometry.mapping_bundle":
            operations[0] = {**operation, "domain_alias": f"{prefix}__domain", "kernel_alias": f"{prefix}__kernel", "image_alias": f"{prefix}__image",
                              "domain_basis": payload.get("domain_basis", basis), "kernel_basis": payload.get("kernel_basis", []),
                              "image_basis": payload.get("image_basis", basis), "lanes": {
                                  "domain": {"alias": f"{prefix}__domain", "basis": payload.get("domain_basis", basis)},
                                  "kernel": {"alias": f"{prefix}__kernel", "basis": payload.get("kernel_basis", [])},
                                  "image": {"alias": f"{prefix}__image", "basis": payload.get("image_basis", basis)},
                              }, "rank": rank, "nullity": nullity}
            aliases.extend((f"{prefix}__kernel", f"{prefix}__image"))
        return SubspaceCompileResult(tuple(operations), {"rank": rank, "nullity": nullity, "domain_dimension": domain_dimension}, tuple(aliases))


__all__ = ["SubspaceCompileResult", "SubspaceFamilyCompiler"]
