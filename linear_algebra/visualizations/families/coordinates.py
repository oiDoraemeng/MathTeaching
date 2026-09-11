"""Coordinate systems and alternate-basis visual evidence."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np

from ..compiler import CompileIssue, VisualCompileError


@dataclass(frozen=True)
class CoordinateEvidence:
    basis_matrix: np.ndarray
    standard_vector: np.ndarray
    alternate_coordinates: np.ndarray


def _finite_array(value: object, shape: tuple[int, ...] | None = None, name: str = "value") -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain finite numbers") from error
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} has invalid dimension")
    if array.ndim not in (1, 2) or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{name} must contain finite numbers")
    return array


def coordinate_evidence(basis_matrix: object, standard_vector: object, tolerance: float = 1e-9) -> CoordinateEvidence:
    basis = _finite_array(basis_matrix, name="basis_matrix")
    vector = _finite_array(standard_vector, name="standard_vector")
    if basis.ndim != 2 or basis.shape[0] != basis.shape[1] or vector.shape != (basis.shape[0],):
        raise ValueError("basis_matrix and standard_vector dimensions mismatch")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or tolerance <= 0:
        raise ValueError("tolerance must be positive and finite")
    if abs(float(np.linalg.det(basis))) <= float(tolerance):
        raise ValueError("singular basis_matrix cannot support bidirectional readout")
    alternate = np.linalg.solve(basis, vector)
    return CoordinateEvidence(basis.copy(), vector.copy(), alternate)


class CoordinateFamilyCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> dict[str, object]:
        try:
            primitive = str(payload.get("primitive", payload.get("op", "geometry.basis_grid")))
            if primitive not in {"geometry.basis_grid", "geometry.coordinate_readout"}:
                raise ValueError("unsupported coordinate primitive")
            evidence = coordinate_evidence(payload.get("basis_matrix"), payload.get("standard_vector"), payload.get("tolerance", 1e-9))
            prefix = str(payload.get("alias_prefix", "coords")) or "coords"
            aliases = (f"{prefix}__basis_grid", f"{prefix}__standard", f"{prefix}__alternate")
            operation = {"op": primitive, "alias": aliases[0], "basis_matrix": tuple(tuple(float(x) for x in row) for row in evidence.basis_matrix), "standard_vector": tuple(float(x) for x in evidence.standard_vector), "alternate_coordinates": tuple(float(x) for x in evidence.alternate_coordinates), "basis_alias": aliases[0], "standard_alias": aliases[1], "alternate_alias": aliases[2], "bounds": tuple(payload.get("bounds", (-2, 2, -2, 2)))}
            return {"operations": (operation,), "aliases": aliases, "evidence": evidence}
        except (TypeError, ValueError, np.linalg.LinAlgError) as error:
            code = "singular_basis" if "singular" in str(error) else "invalid_coordinate"
            raise VisualCompileError((CompileIssue(code, "$.coordinates", str(error)),)) from error


__all__ = ["CoordinateEvidence", "coordinate_evidence", "CoordinateFamilyCompiler"]
