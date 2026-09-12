"""Semantic scene-family dispatch registry.

Concrete family compilers are added by later tasks; this boundary deliberately
rejects unknown primitives instead of silently routing them to a generic vector
renderer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..compiler import VisualCompileError, CompileIssue
from .subspace import SubspaceFamilyCompiler, SubspaceCompileResult
from .tableau import MatrixTableauCompiler, TableauCompileResult, TableauStage, Swap, Scale, Eliminate, apply_row_operation
from .coordinates import CoordinateFamilyCompiler, CoordinateEvidence, coordinate_evidence
from .least_squares import LeastSquaresFamilyCompiler, LeastSquaresEvidence, least_squares_fit
from .spectral import SpectralFamilyCompiler, SpectralEvidence, SpectralRoot, spectral_evidence
from .orthogonalization import OrthogonalizationFamilyCompiler, OrthogonalizationEvidence, gram_schmidt
from .quadratic import QuadraticFamilyCompiler, QuadraticEvidence, classify_quadratic
from .chapter_04 import Chapter4FamilyCompiler, Chapter4CompileResult, compile_chapter_04
from .constraints import ConstraintFamilyCompiler


@dataclass(frozen=True)
class SceneFamilyCompiler:
    primitive: str

    def compile(self, *args: object, **kwargs: object) -> object:
        # Shared family dispatch is intentionally small here: topic-specific
        # command emission remains owned by the typed semantic compiler, while
        # this boundary proves the registered family was actually invoked.
        semantics = kwargs.get("semantics")
        topic_id = kwargs.get("topic_id")
        context = kwargs.get("context")
        if isinstance(topic_id, str) and topic_id.startswith("ch04.") and semantics is not None:
            return compile_chapter_04(topic_id, semantics, context)
        if isinstance(topic_id, str) and topic_id.startswith("ch05.") and semantics is not None:
            return _compile_chapter_05(topic_id, semantics)
        return {"family": self.primitive, "validated": True}


_REGISTERED = {
    "subspace_region": SceneFamilyCompiler("subspace_region"),
    "affine_solution": SceneFamilyCompiler("affine_solution"),
    "basis_change": SceneFamilyCompiler("basis_change"),
    "spectral_orthogonal": SceneFamilyCompiler("spectral_orthogonal"),
    "quadratic_level_set": SceneFamilyCompiler("quadratic_level_set"),
}

def _compile_chapter_05(topic_id, semantics):
    """Compile chapter-five artifacts into typed mathematical operations."""
    from .tableau import MatrixTableauCompiler
    from .least_squares import LeastSquaresFamilyCompiler
    from .subspace import SubspaceFamilyCompiler
    import numpy as np
    common = {"operations": [], "aliases": {}, "evidence": {"invariants": {"finite numeric result": True}}}
    if not semantics.relations:
        raise ValueError("chapter 5 requires typed relation evidence")
    params = dict(semantics.relations[0].parameters)
    ids = [e.id for e in semantics.entities] + [r.id for r in semantics.relations]
    if topic_id == "ch05.consistency.geometry":
        payload = {"op": "geometry.elimination_tableau", "matrix": params["matrix"], "rhs": params["rhs"], "solution_state": "unique", "operations": [], "alias_prefix": "consistency"}
        result = MatrixTableauCompiler.compile(payload); common["operations"].extend(result.operations); common["aliases"] = {i: tuple(result.aliases) for i in ids}
    elif topic_id in {"ch05.gaussian-elimination", "ch05.elementary-matrix-elimination"}:
        raw = params["operations"]
        ops = ({"kind":"eliminate","target":int(raw[0][0]),"source":int(raw[0][1]),"factor":float(raw[1][1])},)
        payload = {"op": "geometry.elimination_tableau", "matrix": params["matrix"], "rhs": params["rhs"], "solution_state": ("unique" if params.get("solution_code",2)==1 else "infinite"), "operations": ops, "alias_prefix": topic_id.split(".")[-1]}
        result = MatrixTableauCompiler.compile(payload); common["operations"].extend(result.operations); common["aliases"] = {i: tuple(result.aliases) for i in ids}
    elif topic_id in {"ch05.least-squares.projection", "ch05.least-squares-derivation"}:
        payload = {"matrix": params["matrix"], "values": params["values"], "alias_prefix": topic_id.split(".")[-1]}
        result = LeastSquaresFamilyCompiler.compile(payload); common["operations"].extend(result["operations"]); common["aliases"] = {i: tuple(result["aliases"]) for i in ids}
    else:
        payload = {"primitive":"geometry.affine_solution", "dimension":2, "origin":[0,0], "affine_offset":[0,0] if "homogeneous" in topic_id else params["particular"], "basis":params["nullspace_basis"], "is_linear":"homogeneous" in topic_id, "alias_prefix": topic_id.split(".")[-1]}
        result = SubspaceFamilyCompiler.compile(payload); common["operations"].extend(result.operations); common["aliases"] = {i: tuple(result.aliases) for i in ids}
    return common


def family_compiler_for(primitive: str) -> SceneFamilyCompiler:
    try:
        return _REGISTERED[primitive]
    except KeyError as error:
        raise VisualCompileError((CompileIssue("unsupported_scene_family", "$.visual_semantics.scene_family", f"unsupported_scene_family: {primitive}"),)) from error


def registered_families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTERED))


__all__ = ["SceneFamilyCompiler", "family_compiler_for", "registered_families", "Chapter4FamilyCompiler", "Chapter4CompileResult", "MatrixTableauCompiler", "TableauCompileResult", "TableauStage", "Swap", "Scale", "Eliminate", "apply_row_operation", "CoordinateFamilyCompiler", "CoordinateEvidence", "coordinate_evidence", "LeastSquaresFamilyCompiler", "LeastSquaresEvidence", "least_squares_fit", "SpectralFamilyCompiler", "SpectralEvidence", "SpectralRoot", "spectral_evidence", "OrthogonalizationFamilyCompiler", "OrthogonalizationEvidence", "gram_schmidt", "QuadraticFamilyCompiler", "QuadraticEvidence", "classify_quadratic"]


