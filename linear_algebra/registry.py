"""Explicit immutable joins for curriculum, explanations, and recipes."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.catalog.model import LessonEntry, LessonNode
from linear_algebra.explanations import explanation_for
from linear_algebra.explanations.model import ExplanationContent
from linear_algebra.teaching.legacy import LegacyTeachingArtifact, adapt_legacy_explanation
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import VisualizationRecipe


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


_REGISTRY: CurriculumRegistry | None = None


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


__all__ = ("CAPABILITIES", "CurriculumRegistry", "catalog_registry")
