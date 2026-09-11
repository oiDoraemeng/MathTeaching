"""Least-squares fit and residual evidence for bounded 2D scenes."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np

from ..compiler import CompileIssue, VisualCompileError
from ..limits import validate_budget


@dataclass(frozen=True)
class LeastSquaresEvidence:
    design_matrix: np.ndarray
    values: np.ndarray
    coefficients: np.ndarray
    fit: np.ndarray
    projection: np.ndarray
    residual: np.ndarray


def least_squares_fit(matrix: object, values: object, tolerance: float = 1e-9) -> LeastSquaresEvidence:
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    try:
        design = np.asarray(matrix, dtype=float)
        target = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("matrix and values must contain finite numbers") from error
    if design.ndim != 2 or target.ndim != 1 or design.shape[0] != target.shape[0] or design.shape[0] < design.shape[1] or design.shape[1] > 3 or not np.isfinite(design).all() or not np.isfinite(target).all():
        raise ValueError("matrix and values dimensions or finite values are invalid")
    coefficients, _, _, _ = np.linalg.lstsq(design, target, rcond=float(tolerance))
    fit = design @ coefficients
    residual = target - fit
    projection = fit.copy()
    if not np.allclose(design.T @ residual, 0.0, atol=max(float(tolerance) * 10, 1e-9)):
        raise ValueError("residual is not orthogonal to design columns")
    return LeastSquaresEvidence(design.copy(), target.copy(), coefficients, fit, projection, residual)


class LeastSquaresFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try:
            raw_matrix = payload.get("matrix")
            if not isinstance(raw_matrix, (list, tuple)) or not raw_matrix or len(raw_matrix) > 128:
                raise ValueError("render_budget: matrix rows exceed bounded limit")
            if not isinstance(raw_matrix[0], (list, tuple)) or len(raw_matrix[0]) not in (1, 2, 3):
                raise ValueError("matrix columns must be 1, 2, or 3")
            dimension = len(raw_matrix[0])
            bounds = tuple(float(value) for value in payload.get("bounds", (-2, 2, -2, 2)))
            if len(bounds) != 4 or any(not math.isfinite(value) for value in bounds) or bounds[0] >= bounds[1] or bounds[2] >= bounds[3] or any(abs(value) > 100.0 for value in bounds):
                raise ValueError("render_budget: least-squares bounds are invalid or exceed teaching extent")
            budget_errors = validate_budget("lecture-v1", scene="2d", entity_count=dimension + 4, stage_count=1, sample_count=len(raw_matrix), bounds=bounds)
            if budget_errors:
                raise ValueError("render_budget: " + "; ".join(budget_errors))
            evidence = least_squares_fit(raw_matrix, payload.get("values"), payload.get("tolerance", 1e-9))
            prefix = str(payload.get("alias_prefix", "least_squares")) or "least_squares"
            aliases = (f"{prefix}__data", f"{prefix}__fit", f"{prefix}__projection", f"{prefix}__residual")
            operation = {"op": "geometry.least_squares", "alias": aliases[0], "matrix": tuple(tuple(float(x) for x in row) for row in evidence.design_matrix), "values": tuple(float(x) for x in evidence.values), "coefficients": tuple(float(x) for x in evidence.coefficients), "fit": tuple(float(x) for x in evidence.fit), "projection": tuple(float(x) for x in evidence.projection), "residual": tuple(float(x) for x in evidence.residual), "data_alias": aliases[0], "fit_alias": aliases[1], "projection_alias": aliases[2], "residual_alias": aliases[3], "bounds": bounds, "tolerance": float(payload.get("tolerance", 1e-9)), "entity_count": dimension + 4, "sample_count": int(evidence.design_matrix.shape[0])}
            return {"operations": (operation,), "aliases": aliases, "evidence": evidence}
        except (TypeError, ValueError, np.linalg.LinAlgError) as error:
            raise VisualCompileError((CompileIssue("invalid_least_squares", "$.least_squares", str(error)),)) from error


__all__ = ["LeastSquaresEvidence", "least_squares_fit", "LeastSquaresFamilyCompiler"]
