"""Explicit immutable joins for curriculum, explanations, and recipes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.catalog.model import LessonEntry, LessonNode
from linear_algebra.explanations import explanation_for
from linear_algebra.explanations.model import ExplanationContent
from linear_algebra.teaching.legacy import LegacyTeachingArtifact, adapt_legacy_explanation
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import RenderContext, VisualizationRecipe
from linear_algebra.visualizations.compiler import CompiledVisualization, VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import VisualContract, contract_for
from linear_algebra.visualizations.snapshots import CompiledSnapshot, CompiledSnapshotStore, snapshot_from


CAPABILITIES: Mapping[str, str] = MappingProxyType({
    "vector_2d": "linear.upsert",
    "vector_3d": "linear3d.upsert",
    "annotation_formula": "annotation.formula",
    "polygon_2d": "geometry.polygon",
    "angle_2d": "geometry.angle_arc",
    "right_angle_2d": "geometry.right_angle_marker",
    "projection_2d": "geometry.projection",
    "right_hand_3d": "linear3d.upsert",
    "parallelepiped_3d": "geometry.parallelepiped",
    "oriented_volume_3d": "geometry.oriented_volume",
    "batch_inner_product": "linear.upsert",
    "transformed_grid": "geometry.transformed_grid",
    "staged_transform": "geometry.staged_transform",
    "subspace_region": "geometry.subspace_region",
    "oriented_area_2d": "geometry.oriented_area",
})


@dataclass(frozen=True)
class CurriculumBundle:
    """One topic's source catalog entry and optional published teaching graph."""

    topic: LessonEntry
    artifact: TeachingArtifact | None
    contract: VisualContract
    recipe: VisualizationRecipe
    compiled: CompiledVisualization | None
    snapshot: CompiledSnapshot | None


@dataclass(frozen=True)
class CurriculumRegistry:
    nodes: tuple[LessonNode, ...]
    topics: tuple[LessonEntry, ...]
    explanations: Mapping[str, ExplanationContent]
    recipes: Mapping[str, VisualizationRecipe]
    capabilities: Mapping[str, str]

    def get_topic(self, topic_id: str) -> LessonEntry:
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        raise KeyError(f"Unknown linear algebra topic: {topic_id}")

    def get_explanation(self, explanation_id: str) -> ExplanationContent:
        try:
            return self.explanations[explanation_id]
        except KeyError as error:
            raise KeyError(f"Unknown linear algebra explanation: {explanation_id}") from error

    def get_recipe(self, visualization_id: str) -> VisualizationRecipe:
        try:
            return self.recipes[visualization_id]
        except KeyError as error:
            raise KeyError(f"Unknown linear algebra visualization: {visualization_id}") from error

    def get_legacy_explanation(self, topic_id: str) -> LegacyTeachingArtifact:
        topic = self.get_topic(topic_id)
        return adapt_legacy_explanation(topic, self.get_explanation(topic.explanation_id))

    def resolve_bundle(
        self,
        topic_id: str,
        *,
        artifact_store: TeachingArtifactStore | None = None,
        snapshot_store: CompiledSnapshotStore | None = None,
        context: RenderContext | None = None,
    ) -> CurriculumBundle:
        """Resolve all topic-owned teaching surfaces without executing a plan."""

        topic = self.get_topic(topic_id)
        contract = contract_for(topic_id)
        recipe = self.get_recipe(topic.visualization_id)
        if artifact_store is None:
            configured_root = os.environ.get("MATH3D_TEACHING_ARTIFACT_ROOT", "").strip()
            if configured_root:
                artifact_store = TeachingArtifactStore(configured_root)
        artifact: TeachingArtifact | None = None
        if artifact_store is not None:
            stored = artifact_store.published(topic_id)
            if stored is not None:
                artifact = stored.artifact
        compiled: CompiledVisualization | None = None
        snapshot: CompiledSnapshot | None = None
        if artifact is not None:
            render_context = context or RenderContext.default(topic_id)
            compiled = VisualSemanticsCompiler().compile(artifact, contract, render_context)
            snapshot = (
                snapshot_store.load(topic_id, artifact.revision)
                if snapshot_store is not None
                else snapshot_from(artifact, contract, compiled)
            )
        return CurriculumBundle(topic, artifact, contract, recipe, compiled, snapshot)


_REGISTRY: CurriculumRegistry | None = None


def bundled_teaching_store() -> TeachingArtifactStore:
    """Return the checked-in teaching artifact store used by the application."""

    return TeachingArtifactStore(Path(__file__).resolve().parent / "teaching" / "data")


def runtime_teaching_store() -> TeachingArtifactStore:
    """Resolve the store for runtime readers, honoring test/pack overrides."""

    configured_root = os.environ.get("MATH3D_TEACHING_ARTIFACT_ROOT", "").strip()
    return TeachingArtifactStore(configured_root) if configured_root else bundled_teaching_store()


def catalog_registry() -> CurriculumRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        topics = topic_entries()
        explanations = {topic.explanation_id: explanation_for(topic.id) for topic in topics}
        recipes = {topic.visualization_id: recipe_for(topic.visualization_id) for topic in topics}
        _REGISTRY = CurriculumRegistry(
            nodes=lecture_manifest(),
            topics=topics,
            explanations=MappingProxyType(explanations),
            recipes=MappingProxyType(recipes),
            capabilities=CAPABILITIES,
        )
    return _REGISTRY


__all__ = ("CAPABILITIES", "CurriculumBundle", "CurriculumRegistry", "bundled_teaching_store", "runtime_teaching_store", "catalog_registry")
