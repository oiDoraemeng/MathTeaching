"""Deterministic real spectral evidence."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping
import numpy as np
from ..compiler import CompileIssue, VisualCompileError
from ..limits import validate_budget

@dataclass(frozen=True)
class SpectralRoot:
    value: float
    eigenspace_id: str

@dataclass(frozen=True)
class SpectralEvidence:
    roots: tuple[SpectralRoot, ...]
    eigenspaces: dict[str, tuple[tuple[float, ...], ...]]
    complex_roots: tuple[complex, ...]

def spectral_evidence(matrix: object, tolerance: float = 1e-9) -> SpectralEvidence:
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1] or values.shape[0] not in (2, 3) or not np.isfinite(values).all():
        raise ValueError("matrix must be finite square 2D or 3D")
    roots_raw = np.linalg.eigvals(values)
    real_values = sorted({round(float(root.real), 12) for root in roots_raw if abs(float(root.imag)) <= float(tolerance)})
    roots: list[SpectralRoot] = []
    spaces: dict[str, tuple[tuple[float, ...], ...]] = {}
    for index, value in enumerate(real_values):
        _, _, vh = np.linalg.svd(values - value * np.eye(values.shape[0]))
        rank = int(np.linalg.matrix_rank(values - value * np.eye(values.shape[0]), tol=float(tolerance)))
        vectors = vh[rank:]
        basis = tuple(tuple(float(x) for x in vector) for vector in vectors)
        space_id = f"spectrum__eigenspace_{index}"
        spaces[space_id] = basis
        roots.append(SpectralRoot(value, space_id))
    complex_roots = tuple(complex(root) for root in roots_raw if abs(float(root.imag)) > float(tolerance))
    return SpectralEvidence(tuple(roots), spaces, complex_roots)

class SpectralFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try:
            matrix = np.asarray(payload.get("matrix"), dtype=float)
            if matrix.ndim != 2 or matrix.shape[0] not in (2, 3) or matrix.shape[0] != matrix.shape[1]:
                raise ValueError("matrix must be finite square 2D or 3D")
            dimension = int(matrix.shape[0])
            bounds = tuple(float(value) for value in payload.get("bounds", (-2, 2, -2, 2) if dimension == 2 else (-2, 2, -2, 2, -2, 2)))
            errors = validate_budget("lecture-v1", scene=f"{dimension}d", entity_count=dimension + 2, stage_count=1, sample_count=dimension * dimension, bounds=bounds)
            if errors: raise ValueError("render_budget: " + "; ".join(errors))
            evidence = spectral_evidence(matrix, payload.get("tolerance", 1e-9))
            aliases = ("spectrum__matrix", "spectrum__roots")
            operation = {"op": "geometry.spectrum", "alias": aliases[0], "matrix": tuple(tuple(float(x) for x in row) for row in matrix), "roots": tuple(root.value for root in evidence.roots), "eigenspaces": evidence.eigenspaces, "complex_roots": evidence.complex_roots, "roots_alias": aliases[1], "bounds": bounds, "tolerance": float(payload.get("tolerance", 1e-9))}
            return {"operations": (operation,), "aliases": aliases, "evidence": evidence}
        except (TypeError, ValueError, np.linalg.LinAlgError) as error:
            raise VisualCompileError((CompileIssue("invalid_spectrum", "$.spectrum", str(error)),)) from error

__all__ = ["SpectralRoot", "SpectralEvidence", "spectral_evidence", "SpectralFamilyCompiler"]
