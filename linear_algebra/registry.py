"""Explicit immutable joins for curriculum, explanations, and recipes."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.catalog.model import LessonEntry, LessonNode
from linear_algebra.explanations import explanation_for
from linear_algebra.explanations.model import ExplanationContent
from linear_algebra.teaching.legacy import LegacyTeachingArtifact, adapt_legacy_explanation
from linear_algebra.teaching.source import LectureSourceRepository, SourceContext
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import RenderContext, VisualizationRecipe
from linear_algebra.visualizations.compiler import CompiledVisualization, VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import VisualContract, contract_for
from linear_algebra.visualizations.snapshots import CompiledSnapshot, CompiledSnapshotStore, snapshot_from
from linear_algebra.teaching.load_states import LoadPhase, LoadTransaction

if TYPE_CHECKING:
    from services.scene_commands import SceneCommandService


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
    "quadratic_level_set": "geometry.quadratic_level_set",
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
    source_context: SourceContext | None = None
    source_diagnostic: tuple[str, str, str] | None = None
    bundle_diagnostic: tuple[str, str, str] | None = None

    @property
    def is_extended(self) -> bool:
        """Whether this bundle belongs to the published chapter 4–8 surface."""

        return self.topic.chapter_number >= 4

    @property
    def explanation(self) -> object:
        """Return the structured explanation used by the UI transaction."""

        return self.artifact.explanation if self.artifact is not None else None


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
        source_repository: LectureSourceRepository | None = None,
        context: RenderContext | None = None,
    ) -> CurriculumBundle:
        """Resolve all topic-owned teaching surfaces without executing a plan."""

        topic = self.get_topic(topic_id)
        contract = contract_for(topic_id)
        recipe = self.get_recipe(topic.visualization_id)
        source_context: SourceContext | None = None
        source_diagnostic: tuple[str, str, str] | None = None
        bundle_diagnostic: tuple[str, str, str] | None = None
        if artifact_store is None:
            configured_root = os.environ.get("MATH3D_TEACHING_ARTIFACT_ROOT", "").strip()
            if configured_root:
                artifact_store = TeachingArtifactStore(configured_root)
        artifact: TeachingArtifact | None = None
        if artifact_store is not None:
            if source_repository is not None:
                try:
                    source_context = source_repository.context_for(topic)
                    loaded = artifact_store.load_published(topic_id, current_context=source_context)
                    if loaded is not None:
                        artifact = loaded.artifact
                        source_diagnostic = loaded.diagnostic
                except (ValueError, OSError, KeyError) as error:
                    bundle_diagnostic = ("source_invalid", "source", str(error))
            else:
                try:
                    stored = artifact_store.published(topic_id)
                    if stored is not None:
                        artifact = stored.artifact
                except (ValueError, OSError, KeyError) as error:
                    bundle_diagnostic = ("artifact_invalid", "artifact", str(error))
        # Chapter 4–8 release scripts keep their reviewed payload and the
        # compiled resource/index as the checked-in release unit.  Materialise
        # that immutable payload as the runtime's published view when a
        # filesystem ``published`` directory is absent; this keeps runtime
        # lookup one-to-one without making the UI understand release layout.
        if artifact is None and topic.chapter_number >= 4:
            try:
                from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts

                reviewed = load_reviewed_artifacts().get(topic_id)
                if reviewed is not None:
                    artifact = replace(TeachingArtifact.from_dict(reviewed), status="published")
                    if source_repository is not None:
                        source_context = source_repository.context_for(topic)
                        if artifact.source.source_hash != source_context.source_hash:
                            source_diagnostic = ("stale_source", artifact.source.source_hash, source_context.source_hash)
            except (FileNotFoundError, ValueError, OSError) as error:
                artifact = None
                bundle_diagnostic = ("artifact_invalid", "artifact", str(error))
        compiled: CompiledVisualization | None = None
        snapshot: CompiledSnapshot | None = None
        if artifact is not None:
            render_context = context or RenderContext.default(topic_id)
            try:
                compiled = VisualSemanticsCompiler().compile(artifact, contract, render_context)
                expected_snapshot = snapshot_from(artifact, contract, compiled)
                if snapshot_store is not None:
                    try:
                        snapshot = snapshot_store.load(topic_id, artifact.revision)
                    except (ValueError, OSError, KeyError) as error:
                        snapshot = None
                        bundle_diagnostic = ("snapshot_invalid", "snapshot", str(error))
                    if snapshot is None:
                        bundle_diagnostic = bundle_diagnostic or ("missing_snapshot", "snapshot", "published snapshot is missing")
                    elif snapshot != expected_snapshot:
                        bundle_diagnostic = ("snapshot_mismatch", "snapshot", "published snapshot differs from compiled output")
                else:
                    snapshot = expected_snapshot
                # The checked-in compiled resource is the release witness for
                # chapter 4–8 when no separate snapshot store is configured.
                if topic.chapter_number >= 4 and artifact_store is not None:
                    from linear_algebra.teaching.compile_resources import compiled_resource_store
                    try:
                        resource = compiled_resource_store(Path(artifact_store.root) / "compiled").get(topic_id)
                        if resource.topic_id != topic_id or resource.revision != artifact.revision:
                            bundle_diagnostic = ("compiled_mismatch", "compiled", "published resource identity differs")
                        elif resource.source_hash != artifact.source.source_hash or resource.plan_digest != compiled.plan_digest:
                            bundle_diagnostic = ("compiled_mismatch", "compiled", "published resource digest differs")
                    except (FileNotFoundError, ValueError, OSError) as error:
                        bundle_diagnostic = ("missing_compiled", "compiled", str(error))
            except Exception as error:
                compiled = None
                snapshot = None
                bundle_diagnostic = ("compiled_invalid", "compiled", str(error))
        if artifact is not None:
            if artifact.topic_id != topic.id:
                bundle_diagnostic = bundle_diagnostic or (
                    "artifact_invalid", "artifact.topic_id",
                    f"expected {topic.id!r}, got {artifact.topic_id!r}",
                )
            if recipe.id != topic.visualization_id:
                bundle_diagnostic = bundle_diagnostic or (
                    "artifact_invalid", "recipe.id",
                    f"expected {topic.visualization_id!r}, got {recipe.id!r}",
                )
            if compiled is not None and compiled.topic_id != topic.id:
                bundle_diagnostic = bundle_diagnostic or (
                    "compiled_invalid", "compiled.topic_id",
                    f"expected {topic.id!r}, got {compiled.topic_id!r}",
                )
            if snapshot is not None and snapshot.topic_id != topic.id:
                bundle_diagnostic = bundle_diagnostic or (
                    "snapshot_invalid", "snapshot.topic_id",
                    f"expected {topic.id!r}, got {snapshot.topic_id!r}",
                )
        # Preserve a diagnostic-bearing bundle so the loader can reject it
        # without mutating a host or throwing an unstructured exception.
        return CurriculumBundle(topic, artifact, contract, recipe, compiled, snapshot, source_context, source_diagnostic, bundle_diagnostic)

    def commit_curriculum_bundle(
        self,
        bundle: CurriculumBundle,
        *,
        pane_id: str | None = None,
        scene_service: "SceneCommandService | None" = None,
        expected_scene_fingerprint: str | None = None,
        previous_scene_fingerprint: str | None = None,
        previous_explanation_fingerprint: str | None = None,
    ) -> LoadTransaction:
        """Validate and stage a complete topic before one optional host commit.

        Resolution is intentionally side-effect free.  This method performs
        the state-machine checks and attaches the explanation and scene plan to
        one ``LoadTransaction``.  When ``scene_service`` is supplied its
        ``execute`` method is called only after ``STAGED``; the service owns
        the host transaction and rollback.
        """

        topic = bundle.topic
        previous_revision = bundle.artifact.revision if bundle.artifact is not None else None
        transaction = LoadTransaction(topic.id, previous_revision=previous_revision)
        transaction.previous_scene_fingerprint = previous_scene_fingerprint
        transaction.previous_explanation_fingerprint = previous_explanation_fingerprint
        transaction.advance(LoadPhase.RESOLVING)

        def reject(code: str, field: str, message: str) -> LoadTransaction:
            transaction.reject(code, transaction.phase, field, message)
            return transaction

        transaction.advance(LoadPhase.SOURCE_CHECKED)
        if bundle.bundle_diagnostic is not None:
            code, field, message = bundle.bundle_diagnostic
            code_map = {
                "source_invalid": "source_stale",
                "artifact_invalid": "missing_artifact",
                "compiled_invalid": "numeric_invalid",
                "compiled_mismatch": "bundle_mismatch",
                "snapshot_invalid": "bundle_mismatch",
                "snapshot_mismatch": "bundle_mismatch",
                "missing_snapshot": "missing_snapshot",
                "missing_compiled": "missing_compiled",
            }
            return reject(code_map.get(code, "bundle_mismatch"), field, message)
        if bundle.source_diagnostic is not None:
            return reject("source_stale", "source_hash", "published source hash no longer matches the lecture")

        artifact = bundle.artifact
        if topic.chapter_number >= 4 and artifact is None:
            return reject("missing_artifact", "artifact", "extended topics require a published TeachingArtifact")
        if artifact is not None:
            if artifact.status != "published":
                return reject("missing_artifact", "artifact.status", "artifact is not published")
            if artifact.topic_id != topic.id:
                return reject("bundle_mismatch", "artifact.topic_id", f"expected {topic.id!r}")
            if artifact.source.source_path != topic.source_path:
                return reject("bundle_mismatch", "artifact.source.source_path", "source path does not match topic")
        transaction.advance(LoadPhase.ARTIFACT_CHECKED)

        if bundle.contract.topic_id != topic.id:
            return reject("bundle_mismatch", "contract.topic_id", f"expected {topic.id!r}")
        if bundle.recipe.id != topic.visualization_id:
            return reject("bundle_mismatch", "recipe.id", f"expected {topic.visualization_id!r}")
        if artifact is not None and artifact.visual_semantics.scene_kind != bundle.recipe.scene:
            return reject("unsupported_scene_family", "visual_semantics.scene_kind", "recipe and artifact scene differ")
        transaction.advance(LoadPhase.CONTRACT_CHECKED)

        compiled = bundle.compiled
        if compiled is None:
            if topic.chapter_number >= 4:
                return reject("missing_compiled", "compiled", "extended topics require a compiled visualization")
            plan = bundle.recipe.builder(RenderContext.default(topic.id))
        else:
            if compiled.topic_id != topic.id:
                return reject("bundle_mismatch", "compiled.topic_id", f"expected {topic.id!r}")
            plan = compiled.plan
        transaction.advance(LoadPhase.COMPILED)

        from services.scene_commands import SceneCommandService

        validation = SceneCommandService().validate(plan)
        if not validation.valid:
            return reject("plan_invalid", "compiled.plan", "；".join(validation.messages))
        if topic.chapter_number >= 4 and bundle.snapshot is None:
            return reject("missing_snapshot", "snapshot", "extended topics require a compiled snapshot")
        if bundle.snapshot is not None:
            if bundle.snapshot.topic_id != topic.id:
                return reject("bundle_mismatch", "snapshot.topic_id", f"expected {topic.id!r}")
            if compiled is not None and bundle.snapshot.plan_digest != compiled.plan_digest:
                return reject("bundle_mismatch", "snapshot.plan_digest", "snapshot and compiled plan differ")
        transaction.advance(LoadPhase.PLAN_VALIDATED)

        explanation = artifact.explanation if artifact is not None else self.get_explanation(topic.explanation_id)
        transaction.stage(
            bundle=bundle,
            plan=plan,
            explanation=explanation,
            pane_id=pane_id,
            previous_scene_fingerprint=previous_scene_fingerprint,
            previous_explanation_fingerprint=previous_explanation_fingerprint,
        )
        if scene_service is not None:
            transaction.commit_host(
                scene_service.execute,
                expected_scene_fingerprint=expected_scene_fingerprint,
            )
        return transaction


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


def commit_curriculum_bundle(
    bundle: CurriculumBundle,
    *,
    pane_id: str | None = None,
    scene_service: "SceneCommandService | None" = None,
    expected_scene_fingerprint: str | None = None,
    previous_scene_fingerprint: str | None = None,
    previous_explanation_fingerprint: str | None = None,
) -> LoadTransaction:
    """Convenience wrapper for callers that already hold a resolved bundle."""

    return catalog_registry().commit_curriculum_bundle(
        bundle,
        pane_id=pane_id,
        scene_service=scene_service,
        expected_scene_fingerprint=expected_scene_fingerprint,
        previous_scene_fingerprint=previous_scene_fingerprint,
        previous_explanation_fingerprint=previous_explanation_fingerprint,
    )


__all__ = ("CAPABILITIES", "CurriculumBundle", "CurriculumRegistry", "bundled_teaching_store", "runtime_teaching_store", "catalog_registry", "commit_curriculum_bundle")
