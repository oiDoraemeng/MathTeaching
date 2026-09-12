"""Explicit visualization recipe registry for the lecture topics."""

from .chapter_01 import RECIPES as CHAPTER_01_RECIPES
from .chapter_02 import RECIPES as CHAPTER_02_RECIPES
from .chapter_03 import RECIPES as CHAPTER_03_RECIPES
from .chapter_04 import RECIPES as CHAPTER_04_RECIPES
from .chapter_05 import RECIPES as CHAPTER_05_RECIPES
from .common import RenderContext, VisualizationRecipe
from .compiler import (
    COMPILER_VERSION,
    CompileIssue,
    CompiledStoryboardStage,
    CompiledVisualization,
    VisualCompileError,
    VisualSemanticsCompiler,
)
from .evidence import ClaimEvidence, EvidenceIssue, EvidenceLedger, build_evidence_ledger
from .palette import ROLE_COLORS, known_role, role_color
from .snapshots import CompiledSnapshot, CompiledSnapshotStore, snapshot_from
from .capability_map import (
    SemanticPrimitiveSpec,
    all_primitive_specs,
    primitive_spec,
    validate_payload_header,
)

_RECIPES: tuple[VisualizationRecipe, ...] = (*CHAPTER_01_RECIPES, *CHAPTER_02_RECIPES, *CHAPTER_03_RECIPES, *CHAPTER_04_RECIPES, *CHAPTER_05_RECIPES)
_BY_ID = {recipe.id: recipe for recipe in _RECIPES}


def recipe_for(visualization_id: str) -> VisualizationRecipe:
    try:
        return _BY_ID[visualization_id]
    except KeyError as error:
        raise KeyError(f"Unknown visualization recipe: {visualization_id}") from error


def recipes_for_topics() -> dict[str, VisualizationRecipe]:
    return dict(_BY_ID)


__all__ = (
    "RenderContext",
    "VisualizationRecipe",
    "recipe_for",
    "recipes_for_topics",
    "COMPILER_VERSION",
    "CompileIssue",
    "CompiledVisualization",
    "CompiledStoryboardStage",
    "VisualCompileError",
    "VisualSemanticsCompiler",
    "ClaimEvidence",
    "EvidenceIssue",
    "EvidenceLedger",
    "build_evidence_ledger",
    "ROLE_COLORS",
    "known_role",
    "role_color",
    "CompiledSnapshot",
    "CompiledSnapshotStore",
    "snapshot_from",
    "SemanticPrimitiveSpec",
    "primitive_spec",
    "all_primitive_specs",
    "validate_payload_header",
)
