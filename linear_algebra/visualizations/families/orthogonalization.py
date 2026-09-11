"""Gram-Schmidt projection and residual evidence."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping
import numpy as np
from ..compiler import CompileIssue, VisualCompileError
from ..limits import validate_budget

@dataclass(frozen=True)
class OrthogonalizationEvidence:
    basis: np.ndarray
    projection_components: tuple[np.ndarray, ...]
    residuals: tuple[np.ndarray, ...]
    stages: tuple[dict[str, object], ...]

def gram_schmidt(vectors: object, tolerance: float = 1e-9) -> OrthogonalizationEvidence:
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    values = np.asarray(vectors, dtype=float)
    if values.ndim != 2 or values.shape[0] not in (1, 2, 3) or values.shape[1] not in (2, 3) or not np.isfinite(values).all():
        raise ValueError("vectors must be finite bounded 2D/3D vectors")
    orthogonal: list[np.ndarray] = []; components: list[np.ndarray] = []; residuals: list[np.ndarray] = []; stages: list[dict[str, object]] = []
    for index, vector in enumerate(values):
        projection = np.zeros(values.shape[1]); residual = vector.copy()
        for prior in orthogonal:
            component = float(np.dot(vector, prior)) * prior
            projection += component; residual -= component
        norm = float(np.linalg.norm(residual))
        if norm <= float(tolerance): raise ValueError("dependent vector below tolerance")
        normalized = residual / norm; orthogonal.append(normalized); components.append(projection); residuals.append(residual)
        stages.append({"id": f"orthogonalization__stage_{index}", "input": tuple(float(x) for x in vector), "projection": tuple(float(x) for x in projection), "residual": tuple(float(x) for x in residual), "normalized": tuple(float(x) for x in normalized), "highlight_rows": (index,)})
    return OrthogonalizationEvidence(np.asarray(orthogonal), tuple(components), tuple(residuals), tuple(stages))

class OrthogonalizationFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try:
            raw = np.asarray(payload.get("vectors"), dtype=float)
            if raw.ndim != 2 or raw.shape[1] not in (2, 3): raise ValueError("vectors dimension must be 2D or 3D")
            bounds = tuple(float(value) for value in payload.get("bounds", (-2, 2, -2, 2, -2, 2) if raw.shape[1] == 3 else (-2, 2, -2, 2)))
            errors = validate_budget("lecture-v1", scene=f"{raw.shape[1]}d", entity_count=raw.shape[0] * 4, stage_count=raw.shape[0], sample_count=raw.shape[0], bounds=bounds)
            if errors: raise ValueError("render_budget: " + "; ".join(errors))
            evidence = gram_schmidt(raw, payload.get("tolerance", 1e-9)); aliases = ("orthogonalization__input", "orthogonalization__projection", "orthogonalization__residual", "orthogonalization__normalized")
            operation = {"op": "geometry.orthogonalization", "alias": aliases[0], "vectors": tuple(tuple(float(x) for x in row) for row in raw), "stages": evidence.stages, "aliases": aliases, "bounds": bounds, "tolerance": float(payload.get("tolerance", 1e-9))}
            return {"operations": (operation,), "aliases": aliases, "evidence": evidence}
        except (TypeError, ValueError, np.linalg.LinAlgError) as error:
            raise VisualCompileError((CompileIssue("invalid_orthogonalization", "$.orthogonalization", str(error)),)) from error

__all__ = ["OrthogonalizationEvidence", "gram_schmidt", "OrthogonalizationFamilyCompiler"]
