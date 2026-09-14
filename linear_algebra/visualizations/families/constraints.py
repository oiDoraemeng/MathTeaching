"""Rank-based finite constraint solution-state compiler."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Literal, Mapping

import numpy as np

from ..compiler import CompileIssue, VisualCompileError
from ..limits import validate_budget

ConstraintKind = Literal["unique", "none", "infinite"]

@dataclass(frozen=True)
class ConstraintClassification:
    kind: ConstraintKind
    rank: int
    augmented_rank: int
    dimension: int

def _rank(matrix: list[list[float]], tolerance: float) -> int:
    rows = [row[:] for row in matrix]; rank = 0
    for col in range(max((len(row) for row in rows), default=0)):
        pivot = next((i for i in range(rank, len(rows)) if abs(rows[i][col]) > tolerance), None)
        if pivot is None: continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][col]; rows[rank] = [v / scale for v in rows[rank]]
        for i in range(len(rows)):
            if i != rank:
                factor = rows[i][col]; rows[i] = [a - factor*b for a,b in zip(rows[i], rows[rank])]
        rank += 1
    return rank

def classify_constraint_system(matrix: object, rhs: object, tolerance: float = 1e-9) -> ConstraintClassification:
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be a positive finite number")
    if not isinstance(matrix, (list, tuple)) or not matrix or not all(isinstance(row, (list, tuple)) for row in matrix):
        raise ValueError("matrix must be a non-empty rectangular array")
    dimension = len(matrix[0]); rows: list[list[float]] = []
    if dimension not in (2, 3) or any(len(row) != dimension for row in matrix): raise ValueError("matrix dimension is invalid")
    if not isinstance(rhs, (list, tuple)) or len(rhs) != len(matrix): raise ValueError("rhs dimension mismatch")
    try:
        rows = [[float(v) for v in row] for row in matrix]; vector = [float(v) for v in rhs]
    except (TypeError, ValueError, OverflowError) as error: raise ValueError("numeric_invalid") from error
    if not all(math.isfinite(v) for row in rows for v in row) or not all(math.isfinite(v) for v in vector): raise ValueError("numeric_invalid")
    tol = float(tolerance); rank = _rank(rows, tol); augmented = _rank([row + [b] for row,b in zip(rows, vector)], tol)
    kind: ConstraintKind = "none" if augmented > rank else ("unique" if rank == dimension else "infinite")
    return ConstraintClassification(kind, rank, augmented, dimension)


def _strict_budget_count(payload: Mapping[str, object], key: str, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VisualCompileError((CompileIssue("invalid_budget_count", f"$.{key}", f"invalid_budget_count: {key} must be a non-negative integer"),))
    return value


def _line_endpoints(
    particular: np.ndarray,
    direction: np.ndarray,
    bounds: tuple[float, ...],
) -> tuple[list[float], list[float]]:
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        raise ValueError("constraint nullspace direction is degenerate")
    unit = direction / norm
    span = max(bounds[index + 1] - bounds[index] for index in range(0, len(bounds), 2))
    radius = max(span, 1.0)
    return (
        [float(value) for value in particular - radius * unit],
        [float(value) for value in particular + radius * unit],
    )


def _solution_geometry(
    matrix: object,
    rhs: object,
    classification: ConstraintClassification,
    bounds: tuple[float, ...],
    tolerance: float,
    state_alias: str,
) -> dict[str, object]:
    dimension = classification.dimension
    center = [
        (bounds[index] + bounds[index + 1]) / 2.0
        for index in range(0, len(bounds), 2)
    ]
    if classification.kind == "none":
        return {
            "op": "annotation.upsert" if dimension == 2 else "annotation.formula",
            "alias": state_alias,
            "text": "无交集",
            "position": center,
        }

    values = np.asarray(matrix, dtype=float)
    vector = np.asarray(rhs, dtype=float)
    if classification.kind == "unique":
        point = np.linalg.solve(values, vector)
        return {
            "op": "point.upsert" if dimension == 2 else "point3d.upsert",
            "alias": state_alias,
            "coordinates": [float(value) for value in point],
        }

    particular, _, _, _ = np.linalg.lstsq(values, vector, rcond=None)
    _, _, vh = np.linalg.svd(values)
    solution_dimension = dimension - classification.rank
    if solution_dimension == 1:
        direction = vh[classification.rank]
        start, end = _line_endpoints(particular, direction, bounds)
        return {
            "op": "linear.upsert" if dimension == 2 else "linear3d.upsert",
            "alias": state_alias,
            "kind": "line" if dimension == 2 else "segment",
            "start": start,
            "end": end,
        }
    if dimension == 3 and solution_dimension == 2:
        nonzero_row = next((row for row in values if np.linalg.norm(row) > tolerance), None)
        if nonzero_row is None:
            return {"op": "annotation.formula", "alias": state_alias, "text": "全空间 R^3", "position": center}
        normal = nonzero_row / np.linalg.norm(nonzero_row)
        return {
            "op": "plane3d.upsert",
            "alias": state_alias,
            "origin": [float(value) for value in particular],
            "normal": [float(value) for value in normal],
            "size": max(bounds[index + 1] - bounds[index] for index in range(0, len(bounds), 2)),
        }
    return {
        "op": "annotation.upsert" if dimension == 2 else "annotation.formula",
        "alias": state_alias,
        "text": "全平面" if dimension == 2 else "全空间 R^3",
        "position": center,
    }

class ConstraintFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try: classification = classify_constraint_system(payload.get("matrix"), payload.get("rhs"), payload.get("tolerance", 1e-9))
        except (ValueError, TypeError, np.linalg.LinAlgError) as error: raise VisualCompileError((CompileIssue("numeric_invalid", "$.constraints", str(error)),)) from error
        dimension = classification.dimension; bounds = payload.get("bounds", [-2,2,-2,2] if dimension == 2 else [-2,2,-2,2,-2,2])
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2*dimension or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)) for v in bounds):
            raise VisualCompileError((CompileIssue("numeric_invalid", "$.bounds", "bounds must be finite and dimension matched"),))
        if any(bounds[i] >= bounds[i+1] for i in range(0,len(bounds),2)): raise VisualCompileError((CompileIssue("invalid_bounds", "$.bounds", "bounds must be ordered"),))
        stage_count = _strict_budget_count(payload, "stage_count", 1)
        sample_count = _strict_budget_count(payload, "sample_count", len(payload.get("matrix", [])))
        budget_errors = validate_budget("lecture-v1", scene="3d" if dimension == 3 else "2d", entity_count=1, stage_count=stage_count, sample_count=sample_count, bounds=tuple(float(value) for value in bounds))
        if budget_errors:
            raise VisualCompileError(tuple(CompileIssue("render_budget", "$.constraints", error) for error in budget_errors))
        prefix = str(payload.get("alias_prefix", "constraint")); aliases = [f"{prefix}__intersection"]
        solution_dimension = dimension - classification.rank if classification.kind == "infinite" else 0
        if classification.kind == "none":
            state_name = "empty"
        elif classification.kind == "unique":
            state_name = "point"
        elif dimension == 3 and solution_dimension >= 3:
            state_name = "space"
        elif solution_dimension == 0:
            state_name = "plane"
        elif solution_dimension == 1:
            state_name = "line"
        else:
            state_name = "plane"
        state_alias = f"{prefix}__{state_name}"
        aliases.append(state_alias)
        try:
            geometry_op = _solution_geometry(payload["matrix"], payload["rhs"], classification, tuple(float(value) for value in bounds), float(payload.get("tolerance", 1e-9)), state_alias)
        except (ValueError, np.linalg.LinAlgError) as error:
            raise VisualCompileError((CompileIssue("numeric_invalid", "$.constraints", str(error)),)) from error
        operation = {"op":"geometry.constraint", "alias":prefix, "matrix":payload["matrix"], "rhs":payload["rhs"], "dimension":dimension, "bounds":list(bounds), "solution_state":classification.kind, "intersection_alias":aliases[0], "state_alias": state_alias, "rank":classification.rank, "augmented_rank":classification.augmented_rank, "stage_count":stage_count, "sample_count":sample_count, "solution_geometry": geometry_op}
        return {"operations": (operation,), "aliases": tuple(aliases), "evidence": classification}

__all__ = ["ConstraintClassification", "ConstraintFamilyCompiler", "classify_constraint_system"]
