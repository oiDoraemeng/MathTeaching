"""Rank-based finite constraint solution-state compiler."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Literal, Mapping
from ..compiler import CompileIssue, VisualCompileError

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

class ConstraintFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try: classification = classify_constraint_system(payload.get("matrix"), payload.get("rhs"), payload.get("tolerance", 1e-9))
        except (ValueError, TypeError) as error: raise VisualCompileError((CompileIssue("numeric_invalid", "$.constraints", str(error)),)) from error
        dimension = classification.dimension; bounds = payload.get("bounds", [-2,2,-2,2] if dimension == 2 else [-2,2,-2,2,-2,2])
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2*dimension or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)) for v in bounds):
            raise VisualCompileError((CompileIssue("numeric_invalid", "$.bounds", "bounds must be finite and dimension matched"),))
        if any(bounds[i] >= bounds[i+1] for i in range(0,len(bounds),2)): raise VisualCompileError((CompileIssue("invalid_bounds", "$.bounds", "bounds must be ordered"),))
        prefix = str(payload.get("alias_prefix", "constraint")); aliases = [f"{prefix}__intersection"]
        operation = {"op":"geometry.constraint", "alias":prefix, "matrix":payload["matrix"], "rhs":payload["rhs"], "dimension":dimension, "bounds":list(bounds), "solution_state":classification.kind, "intersection_alias":aliases[0], "rank":classification.rank, "augmented_rank":classification.augmented_rank}
        return {"operations": (operation,), "aliases": tuple(aliases), "evidence": classification}

__all__ = ["ConstraintClassification", "ConstraintFamilyCompiler", "classify_constraint_system"]
