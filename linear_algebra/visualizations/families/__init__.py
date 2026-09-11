"""Semantic scene-family dispatch registry.

Concrete family compilers are added by later tasks; this boundary deliberately
rejects unknown primitives instead of silently routing them to a generic vector
renderer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..compiler import VisualCompileError, CompileIssue


@dataclass(frozen=True)
class SceneFamilyCompiler:
    primitive: str

    def compile(self, *args: object, **kwargs: object) -> object:
        raise VisualCompileError((CompileIssue("unsupported_scene_family", "$.visual_semantics.scene_family", self.primitive),))


_REGISTERED = {
    "subspace_region": SceneFamilyCompiler("subspace_region"),
    "affine_solution": SceneFamilyCompiler("affine_solution"),
    "basis_change": SceneFamilyCompiler("basis_change"),
    "spectral_orthogonal": SceneFamilyCompiler("spectral_orthogonal"),
    "quadratic_level_set": SceneFamilyCompiler("quadratic_level_set"),
}


def family_compiler_for(primitive: str) -> SceneFamilyCompiler:
    try:
        return _REGISTERED[primitive]
    except KeyError as error:
        raise VisualCompileError((CompileIssue("unsupported_scene_family", "$.visual_semantics.scene_family", f"unsupported_scene_family: {primitive}"),)) from error


def registered_families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTERED))


__all__ = ["SceneFamilyCompiler", "family_compiler_for", "registered_families"]
