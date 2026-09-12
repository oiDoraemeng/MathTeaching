"""Validated quadratic-form classification and bounded level-set payloads."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping
import numpy as np
from ..compiler import CompileIssue, VisualCompileError
from ..limits import validate_budget

@dataclass(frozen=True)
class QuadraticEvidence:
    eigenvalues: tuple[float, ...]
    principal_axes: tuple[tuple[float, ...], ...]
    signature: tuple[int, int, int]
    classification: str

def classify_quadratic(matrix: object, tolerance: float = 1e-9) -> QuadraticEvidence:
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.shape[0] not in (2, 3) or values.shape[0] != values.shape[1] or not np.isfinite(values).all():
        raise ValueError("matrix must be finite square 2D or 3D")
    if not np.allclose(values, values.T, atol=float(tolerance), rtol=0):
        raise ValueError("matrix must be symmetric")
    eigenvalues, eigenvectors = np.linalg.eigh(values)
    axes = []
    for index in range(values.shape[0]):
        axis = eigenvectors[:, index]
        first = next((x for x in axis if abs(x) > float(tolerance)), 1.0)
        if first < 0: axis = -axis
        axes.append(tuple(float(x) for x in axis))
    positive = int(np.sum(eigenvalues > float(tolerance))); negative = int(np.sum(eigenvalues < -float(tolerance))); zero = values.shape[0] - positive - negative
    classification = "indefinite" if positive and negative else ("positive_definite" if positive == values.shape[0] else ("negative_definite" if negative == values.shape[0] else ("semidefinite" if positive or negative else "degenerate")))
    return QuadraticEvidence(tuple(float(x) for x in eigenvalues), tuple(axes), (positive, negative, zero), classification)

class QuadraticFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try:
            values = np.asarray(payload.get("matrix"), dtype=float)
            if values.ndim != 2 or values.shape[0] not in (2, 3) or values.shape[0] != values.shape[1]: raise ValueError("matrix must be finite square 2D or 3D")
            dimension = int(values.shape[0]); bounds = tuple(float(x) for x in payload.get("bounds", (-2, 2, -2, 2) if dimension == 2 else (-2, 2, -2, 2, -2, 2)))
            sample_count = int(payload.get("sample_count", 128 * 128 if dimension == 2 else 64 * 64 * 64))
            errors = validate_budget("lecture-v1", scene=f"{dimension}d", entity_count=3, stage_count=3, sample_count=sample_count, bounds=bounds)
            if errors: raise ValueError("render_budget: " + "; ".join(errors))
            evidence = classify_quadratic(values, payload.get("tolerance", 1e-9)); aliases = ("quadratic__original", "quadratic__principal", "quadratic__standard")
            if dimension == 2:
                angles = np.linspace(0.0, 2.0 * math.pi, min(128, max(16, int(math.sqrt(sample_count)))), endpoint=False)
                contour = []; source_indices = []
                for source_index, angle in enumerate(angles):
                    direction = np.array([math.cos(float(angle)), math.sin(float(angle))])
                    denominator = float(direction @ values @ direction)
                    if denominator <= float(payload.get("tolerance", 1e-9)):
                        continue
                    radius = 1.0 / math.sqrt(denominator)
                    point = direction * radius
                    if bounds[0] <= point[0] <= bounds[1] and bounds[2] <= point[1] <= bounds[3]:
                        contour.append((float(point[0]), float(point[1])))
                        source_indices.append(source_index)
                segments = [(i,i+1) for i in range(len(contour)-1) if source_indices[i+1] == source_indices[i]+1]
                if len(contour)>1 and source_indices[0] == 0 and source_indices[-1] == len(angles)-1:
                    segments.append((len(contour)-1,0))
                geometry = {"contour_vertices": tuple(contour), "contour_segments": tuple(segments)}
            else:
                grid = min(32, max(4, int(round(sample_count ** (1 / 3)))))
                vertices = tuple((float(x), float(y), float(z)) for x in np.linspace(bounds[0], bounds[1], grid) for y in np.linspace(bounds[2], bounds[3], grid) for z in np.linspace(bounds[4], bounds[5], grid) if abs(float(np.array((x, y, z)) @ values @ np.array((x, y, z))) - 1.0) <= 0.15)
                geometry = {"mesh_vertices": vertices, "mesh_faces": tuple((index, index + 1, index + 2) for index in range(0, max(0, len(vertices) - 2), 3))}
            operation = {"op": "geometry.quadratic_level_set", "alias": aliases[0], "matrix": tuple(tuple(float(x) for x in row) for row in values), "eigenvalues": evidence.eigenvalues, "principal_axes": evidence.principal_axes, "signature": evidence.signature, "classification": evidence.classification, "aliases": aliases, "bounds": bounds, "sample_count": sample_count, "tolerance": float(payload.get("tolerance", 1e-9)), "axis_segments": tuple((tuple(0.0 for _ in range(dimension)), axis) for axis in evidence.principal_axes), **geometry}
            return {"operations": (operation,), "aliases": aliases, "evidence": evidence}
        except (TypeError, ValueError, np.linalg.LinAlgError) as error:
            raise VisualCompileError((CompileIssue("invalid_quadratic", "$.quadratic", str(error)),)) from error

__all__ = ["QuadraticEvidence", "classify_quadratic", "QuadraticFamilyCompiler"]
