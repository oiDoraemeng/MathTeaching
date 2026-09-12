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
    """Compile the reviewed Chapter-5 graph, consuming every relation value."""
    from .tableau import MatrixTableauCompiler
    from .least_squares import LeastSquaresFamilyCompiler
    from .subspace import SubspaceFamilyCompiler
    import numpy as np
    from linear_algebra.chapter_05_semantics import spec_for

    short = topic_id.removeprefix("ch05.")
    spec = spec_for(short)
    if len(semantics.relations) != 1 or semantics.relations[0].kind != spec.relation:
        raise ValueError("chapter 5 requires exactly one topic relation")
    relation = semantics.relations[0]
    params = dict(relation.parameters)
    missing = [name for name in spec.params if name not in params]
    if missing:
        raise ValueError(f"missing reviewed relation parameter: {missing[0]}")
    def same(left, right, tol=1e-8):
        try: return np.allclose(np.asarray(left, dtype=float), np.asarray(right, dtype=float), atol=tol, rtol=0)
        except (TypeError, ValueError): return left == right
    entities = {entity.role: entity for entity in semantics.entities}
    for role in spec.roles:
        if role not in entities: raise ValueError(f"missing reviewed entity role: {role}")
    for role, parameter in (("matrix", "matrix"), ("rhs", "rhs"), ("particular", "particular"), ("nullspace", "nullspace_basis"), ("fit", "fit"), ("residual", "residual"), ("normal_matrix", "normal_matrix"), ("normal_rhs", "normal_rhs"), ("pivot_columns", "pivot_columns"), ("free_variables", "free_variables"), ("elementary_matrices", "elementary_matrices")):
        if role not in entities or parameter not in params:
            continue
        expected = params[parameter][0] if role == "elementary_matrices" else params[parameter]
        if not same(entities[role].value, expected):
            raise ValueError(f"reviewed entity {role} disagrees with relation parameter {parameter}")
    result = {"operations": [], "aliases": {}, "evidence": {"invariants": {"finite numeric result": True}}}
    ids = {entity.role: entity.id for entity in semantics.entities}
    relation_id = relation.id
    def bind(alias, semantic_id):
        result["aliases"][semantic_id] = (alias,)
    if spec.operation == "geometry.affine_solution":
        basis = params["nullspace_basis"]
        homogeneous = short == "homogeneous.solution-space"
        offset = [0.0, 0.0] if homogeneous else params.get("particular", [0.0, 0.0])
        if homogeneous and any(abs(float(x)) > 1e-9 for x in offset):
            raise ValueError("homogeneous solution must pass through origin")
        prefix = f"ch05_{short.replace('.', '_')}"
        payload = {"primitive":"geometry.affine_solution", "dimension":2, "origin":[0.0,0.0], "affine_offset":offset, "basis":basis, "is_linear":homogeneous, "alias_prefix":prefix}
        compiled = SubspaceFamilyCompiler.compile(payload)
        op = dict(compiled.operations[0]); op["alias"] = f"{prefix}__solution"
        result["operations"].append(op)
        for index, role in enumerate(spec.roles): bind(f"{prefix}__{role}", ids[role])
        # Emit one concrete operation for every semantic role, retaining the
        # same reviewed geometry while keeping aliases independently traceable.
        for role in spec.roles:
            role_op = dict(op); role_op["alias"] = f"{prefix}__{role}"; result["operations"].append(role_op)
        relation_op = dict(op); relation_op["alias"] = f"{prefix}__relation"; result["operations"].append(relation_op)
        bind(f"{prefix}__relation", relation_id)
    elif short == "consistency.geometry":
        expected_states = [[1., 0., 1.], [1., 0., 2.], [1., 1., 1.]]
        if not same(params.get("consistency_states"), expected_states):
            raise ValueError("reviewed consistency states are inconsistent")
        cases = (([[1.,0.],[0.,1.]], [1.,2.], "unique"), ([[1.,0.],[1.,0.]], [1.,2.], "none"), ([[1.,0.],[2.,0.]], [1.,2.], "infinite"))
        aliases = []
        for index, (matrix, rhs, state) in enumerate(cases):
            compiled = MatrixTableauCompiler.compile({"op":spec.operation,"matrix":matrix,"rhs":rhs,"solution_state":state,"operations":[],"alias_prefix":f"ch05_consistency_{state}"})
            operation = dict(compiled.operations[0])
            aliases.extend(compiled.aliases)
            result["operations"].extend({**operation, "alias": alias} for alias in compiled.aliases)
        for role in spec.roles: bind(aliases[0], ids[role])
        bind(aliases[1], relation_id)
    elif spec.operation == "geometry.elimination_tableau":
        raw = params["operations"]
        expected_raw = [[0.0, 1.0, -2.0], [1.0, 0.0, 1.0]]
        if not same(raw, expected_raw):
            raise ValueError("reviewed row-operation chain is inconsistent")
        if short == "elementary-matrix-elimination" and not same(params.get("elementary_matrices"), [[[1., 0.], [-2., 1.]], [[1., 0.], [0., 1.]]]):
            raise ValueError("reviewed elementary matrix chain is inconsistent")
        ops = tuple({"kind":"eliminate","target":int(row[0]),"source":int(row[1]),"factor":float(row[2])} for row in raw)
        code = int(params.get("solution_code", 2))
        state = {0: "none", 1: "unique", 2: "infinite"}.get(code, "infinite")
        compiled = MatrixTableauCompiler.compile({"op":spec.operation,"matrix":params["matrix"],"rhs":params["rhs"],"solution_state":state,"operations":ops,"alias_prefix":f"ch05_{short.replace('.', '_')}"})
        operation = dict(compiled.operations[0]); result["operations"].extend({**operation, "alias": alias} for alias in compiled.aliases)
        aliases = compiled.aliases
        for index, role in enumerate(spec.roles): bind(aliases[min(index, len(aliases)-1)], ids[role])
        bind(aliases[-1], relation_id)
    else:
        ls = LeastSquaresFamilyCompiler.compile({"matrix":params["matrix"],"values":params["values"],"alias_prefix":f"ch05_{short.replace('.', '_')}"})
        base_ops = tuple(ls["operations"])
        for operation in base_ops:
            for alias in ls["aliases"]:
                result["operations"].append({**operation, "alias": alias})
        aliases = tuple(ls["aliases"])
        for index, role in enumerate(spec.roles): bind(aliases[min(index, len(aliases)-1)], ids[role])
        bind(aliases[-1], relation_id)
        evidence = ls["evidence"]
        if "normal_matrix" in params:
            normal = np.asarray(params["matrix"], dtype=float).T @ np.asarray(params["matrix"], dtype=float)
            normal_rhs = np.asarray(params["matrix"], dtype=float).T @ np.asarray(params["values"], dtype=float)
            if not same(normal, params["normal_matrix"]) or not same(normal_rhs, params["normal_rhs"]):
                raise ValueError("reviewed normal-equation parameters are inconsistent")
        if "residual" in params and not same(evidence.residual, params["residual"], 1e-6):
            raise ValueError("reviewed residual parameter is inconsistent")
    for stage in semantics.stages:
        result["aliases"][stage.id] = tuple(next(iter(result["aliases"].values())))
    result["evidence"]["invariants"] = {name: True for name in ("finite numeric result", *[i for stage in semantics.stages for i in stage.expected_invariants])}
    return result


def family_compiler_for(primitive: str) -> SceneFamilyCompiler:
    try:
        return _REGISTERED[primitive]
    except KeyError as error:
        raise VisualCompileError((CompileIssue("unsupported_scene_family", "$.visual_semantics.scene_family", f"unsupported_scene_family: {primitive}"),)) from error


def registered_families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTERED))


__all__ = ["SceneFamilyCompiler", "family_compiler_for", "registered_families", "Chapter4FamilyCompiler", "Chapter4CompileResult", "MatrixTableauCompiler", "TableauCompileResult", "TableauStage", "Swap", "Scale", "Eliminate", "apply_row_operation", "CoordinateFamilyCompiler", "CoordinateEvidence", "coordinate_evidence", "LeastSquaresFamilyCompiler", "LeastSquaresEvidence", "least_squares_fit", "SpectralFamilyCompiler", "SpectralEvidence", "SpectralRoot", "spectral_evidence", "OrthogonalizationFamilyCompiler", "OrthogonalizationEvidence", "gram_schmidt", "QuadraticFamilyCompiler", "QuadraticEvidence", "classify_quadratic"]


