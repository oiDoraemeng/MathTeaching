"""Development validators for the checked-in linear algebra curriculum."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Iterable

from linear_algebra.catalog.model import LessonEntry
from linear_algebra.registry import CurriculumRegistry, catalog_registry
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore, artifact_digest
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
from linear_algebra.teaching.compile_resources import compiled_resource_store
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_placeholder_explanations,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.contracts import contract_for, validate_contract
from linear_algebra.visualizations.palette import ROLE_COLORS
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, snapshot_from, contract_digest_for
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from services.scene_commands import CommandPlan
from services.scene_commands import SceneCommandService

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHAPTER = re.compile(r"^第(\d+)章(?:\s|[^A-Za-z0-9]|$)")
_SECTION = re.compile(r"^\d+\.\d+(?:\s|$)")
_EXCLUDED = ("自检", "练习", "挑战")


@dataclass(frozen=True)
class HeadingRecord:
    path: tuple[str, ...]
    level: int
    occurrence: int
    line_number: int


@dataclass(frozen=True)
class TeachingValidationSummary:
    """Machine-readable summary emitted by the full artifact audit."""

    topic_count: int
    chapter_counts: tuple[tuple[int, int], ...]
    published_count: int
    claim_count: int
    stale_count: int
    plan_digests: tuple[tuple[str, str], ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "topic_count": self.topic_count,
            "chapter_counts": {str(chapter): count for chapter, count in self.chapter_counts},
            "published_count": self.published_count,
            "claim_count": self.claim_count,
            "stale_count": self.stale_count,
            "plan_digests": {topic_id: digest for topic_id, digest in self.plan_digests},
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class ValidationReport:
    """Layered curriculum validation suitable for CI and editor diagnostics."""

    topic_count_by_chapter: dict[int, int]
    source_errors: tuple[str, ...] = ()
    content_errors: tuple[str, ...] = ()
    semantic_errors: tuple[str, ...] = ()
    execution_errors: tuple[str, ...] = ()
    topic_records: tuple["TopicValidationRecord", ...] = ()
    issues: tuple["TopicValidationIssue", ...] = ()

    @property
    def chapter_counts(self) -> dict[int, int]:
        """Return the stable chapter distribution used by release gates."""

        return dict(sorted(self.topic_count_by_chapter.items()))

    @property
    def topic_count(self) -> int:
        return sum(self.topic_count_by_chapter.values())

    @property
    def plan_digests(self) -> dict[str, str]:
        return {
            record.topic_id: record.plan_digest
            for record in self.topic_records
            if record.plan_digest
        }

    @property
    def errors(self) -> tuple[str, ...]:
        layered = (*self.source_errors, *self.content_errors, *self.semantic_errors, *self.execution_errors)
        return (*layered, *(str(issue) for issue in self.issues))


@dataclass(frozen=True)
class TopicValidationIssue:
    """A deterministic, machine-readable issue for one curriculum topic."""

    chapter: int
    topic_id: str
    category: str
    path: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"chapter:{self.chapter} topic:{self.topic_id} {self.category}:{self.code} {self.path}: {self.message}"


@dataclass(frozen=True)
class TopicValidationRecord:
    """Release evidence captured for one validated topic."""

    topic_id: str
    chapter: int
    source_hash: str = ""
    artifact_revision: int | None = None
    artifact_status: str = ""
    published_revision: int | None = None
    contract_digest: str = ""
    compiler_version: str = ""
    plan_digest: str = ""
    stage_ids: tuple[str, ...] = ()
    operation_names: tuple[str, ...] = ()


def validate_curriculum(
    registry: CurriculumRegistry | None = None,
    *,
    source_path: Path | None = None,
    artifact_store: TeachingArtifactStore | None = None,
    require_published: bool = False,
) -> ValidationReport:
    """Run source/content/semantic/execution checks without mutating resources.

    With no artifact store this validates the legacy catalog and source anchors;
    callers that provide a store can opt into strict published-resource coverage.
    """

    registry = registry or catalog_registry()
    counts = Counter(topic.chapter_number for topic in registry.topics)
    source_errors = list(validate_lecture_source(source_path or Path(__file__).parents[1] / ".agents" / "线性代数讲义.md", registry.topics))
    content_errors: list[str] = []
    semantic_errors: list[str] = []
    execution_errors: list[str] = []
    repository = LectureSourceRepository(source_path or Path(__file__).parents[1] / ".agents" / "线性代数讲义.md")
    compiler = VisualSemanticsCompiler()
    command_validator = SceneCommandService()
    if artifact_store is not None:
        for topic in registry.topics:
            stored = artifact_store.published(topic.id)
            if stored is None:
                if require_published:
                    content_errors.append(f"content:{topic.id}: missing published artifact")
                continue
            artifact = stored.artifact
            try:
                context = repository.context_for(topic)
                source_errors.extend(
                    f"source:{topic.id}: {issue.code} {issue.path}: {issue.message}"
                    for issue in validate_source_evidence(artifact, context, topic)
                )
            except (OSError, ValueError) as error:
                source_errors.append(f"source:{topic.id}: {error}")
            content_errors.extend(
                f"content:{topic.id}: {issue.code} {issue.path}: {issue.message}"
                for issue in (
                    *validate_closed_references(artifact),
                    *validate_claim_bindings(artifact),
                    *validate_teaching_depth(artifact),
                    *validate_placeholder_explanations(artifact),
                    *validate_worked_examples(artifact),
                )
            )
            contract = contract_for(topic.id)
            semantic_errors.extend(
                f"semantic:{topic.id}: {issue.code}: {issue.detail}"
                for issue in validate_contract(artifact, contract)
            )
            try:
                compiled = compiler.compile(artifact, contract, RenderContext.default(topic.id))
            except VisualCompileError as error:
                semantic_errors.append(f"semantic:{topic.id}: visual compilation failed: {error}")
                continue
            result = command_validator.validate(compiled.plan)
            if not result.valid:
                execution_errors.extend(
                    f"execution:{topic.id}: {message}" for message in result.messages
                )
    return ValidationReport(
        topic_count_by_chapter=dict(sorted(counts.items())),
        source_errors=tuple(source_errors),
        content_errors=tuple(content_errors),
        semantic_errors=tuple(semantic_errors),
        execution_errors=tuple(execution_errors),
    )


def _course_paths(root: Path) -> tuple[Path, Path]:
    """Resolve a project root and lecture path from either form of input."""

    root = root.resolve()
    if root.is_file():
        return root.parents[1] if root.parent.name == ".agents" else root.parent, root
    source = root / ".agents" / "线性代数讲义.md"
    if source.is_file():
        return root, source
    # Accept ``linear_algebra/teaching/data`` as a convenient fixture root.
    if root.name == "data" and root.parent.name == "teaching":
        project = root.parents[2]
        return project, project / ".agents" / "线性代数讲义.md"
    return root, source


def _issue(
    issues: list[TopicValidationIssue],
    topic: LessonEntry,
    category: str,
    path: str,
    code: str,
    message: str,
) -> None:
    issues.append(TopicValidationIssue(topic.chapter_number, topic.id, category, path, code, message))


def validate_all_topics(
    repository_root: Path,
    *,
    registry: CurriculumRegistry | None = None,
    artifact_root: Path | None = None,
    snapshot_root: Path | None = None,
) -> ValidationReport:
    """Validate the complete 88-topic release surface deterministically.

    Chapter 1--3 artifacts are read from the published store.  Chapters 4--8
    are currently represented by reviewed fixtures plus their checked-in
    compiled resources; the chapter index is the publication witness for both
    forms.  No files are modified by this function.
    """

    project_root, source_path = _course_paths(Path(repository_root))
    registry = registry or catalog_registry()
    data_root = Path(artifact_root).resolve() if artifact_root is not None else project_root / "linear_algebra" / "teaching" / "data"
    store = TeachingArtifactStore(data_root)
    compiler_store = compiled_resource_store(data_root / "compiled")
    snapshot_store = CompiledSnapshotStore(snapshot_root) if snapshot_root is not None else None
    issues: list[TopicValidationIssue] = []
    records: list[TopicValidationRecord] = []
    expected_counts = {1: 19, 2: 15, 3: 15, 4: 16, 5: 8, 6: 3, 7: 6, 8: 6}
    counts = Counter(topic.chapter_number for topic in registry.topics)
    if counts != Counter(expected_counts):
        # Keep the issue topic-neutral so consumers can still render all rows.
        issues.append(TopicValidationIssue(0, "", "catalog", "chapter_counts", "chapter_count_mismatch", f"expected {expected_counts}, got {dict(sorted(counts.items()))}"))
    ids = [topic.id for topic in registry.topics]
    for duplicate in sorted({topic_id for topic_id in ids if ids.count(topic_id) > 1}):
        issues.append(TopicValidationIssue(0, duplicate, "catalog", "topic_id", "duplicate_topic_id", "topic ID is not unique"))

    index_rows: dict[str, dict[str, object]] = {}
    index_path = data_root / "index.json"
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        rows = payload.get("topics", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            raise ValueError("topics must be an array")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("topic_id"), str):
                issues.append(TopicValidationIssue(0, "", "published", "index.json", "invalid_index_row", "topic index row must contain topic_id"))
                continue
            topic_id = str(row["topic_id"])
            if topic_id in index_rows:
                issues.append(TopicValidationIssue(0, topic_id, "published", "index.json", "duplicate_index_topic", "topic appears more than once"))
            index_rows[topic_id] = row
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(TopicValidationIssue(0, "", "published", "index.json", "invalid_index", str(error)))

    try:
        reviewed_payloads = load_reviewed_artifacts(data_root / "revieweds")
    except (FileNotFoundError, OSError, ValueError):
        reviewed_payloads = {}
    repository = LectureSourceRepository(source_path)
    compiler = VisualSemanticsCompiler()
    command_validator = SceneCommandService()
    for topic in registry.topics:
        row = index_rows.get(topic.id)
        published_revision: int | None = None
        if row is None:
            _issue(issues, topic, "published", "index.json", "missing_index_entry", "topic is absent from the published index")
        else:
            # Legacy rows use ``revision`` while chapter 4--8 release rows
            # expose the explicit ``published_revision`` witness.
            revision_field = "published_revision" if "published_revision" in row else "revision"
            value = row.get(revision_field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                _issue(issues, topic, "published", revision_field, "invalid_published_revision", "published revision must be a positive integer")
            else:
                published_revision = value

        artifact = None
        try:
            stored = store.published(topic.id)
            artifact = stored.artifact if stored is not None else None
        except (FileNotFoundError, OSError, ValueError, KeyError) as error:
            _issue(issues, topic, "artifact", "published", "invalid_artifact", str(error))
        if artifact is None and topic.chapter_number >= 4:
            raw = reviewed_payloads.get(topic.id)
            if raw is not None:
                try:
                    artifact = TeachingArtifact.from_dict(raw)
                except (TypeError, ValueError, KeyError) as error:
                    _issue(issues, topic, "artifact", "reviewed", "invalid_artifact", str(error))
            else:
                _issue(issues, topic, "artifact", "reviewed", "missing_artifact", "no published or reviewed artifact resource")
        if artifact is None:
            if topic.chapter_number < 4:
                _issue(issues, topic, "artifact", "published", "missing_artifact", "no published artifact resource")
            records.append(TopicValidationRecord(topic.id, topic.chapter_number, published_revision=published_revision))
            continue

        if artifact.topic_id != topic.id:
            _issue(issues, topic, "artifact", "topic_id", "topic_id_mismatch", f"expected {topic.id!r}, got {artifact.topic_id!r}")
        if artifact.status not in {"published", "reviewed"}:
            _issue(issues, topic, "artifact", "status", "invalid_status", f"unsupported artifact status {artifact.status!r}")
        # The legacy index is intentionally frozen at its original revision;
        # only an explicit extended ``published_revision`` is authoritative.
        if published_revision is not None and artifact.revision != published_revision and row is not None and "published_revision" in row:
            _issue(issues, topic, "published", "published_revision", "revision_mismatch", f"index={published_revision}, artifact={artifact.revision}")
        if row is not None and row.get("source_hash") not in (None, artifact.source.source_hash):
            _issue(issues, topic, "published", "source_hash", "index_source_mismatch", "index source hash differs from artifact")

        try:
            context = repository.context_for(topic)
            if artifact.source.source_hash != context.source_hash:
                _issue(issues, topic, "source", "source_hash", "stale_source", "artifact source hash differs from lecture source")
            for source_issue in validate_source_evidence(artifact, context, topic):
                _issue(issues, topic, "source", source_issue.path, source_issue.code, source_issue.message)
        except (OSError, ValueError, KeyError) as error:
            _issue(issues, topic, "source", "context", "source_context_invalid", str(error))

        contract = contract_for(topic.id)
        contract_digest = contract_digest_for(contract)
        for contract_issue in validate_contract(artifact, contract):
            _issue(issues, topic, "contract", contract_issue.detail, contract_issue.code, contract_issue.detail)
        compiled = None
        try:
            compiled = compiler.compile(artifact, contract, RenderContext.default(topic.id))
        except Exception as error:
            _issue(issues, topic, "compiled", "compiler", "compile_failed", str(error))
        if compiled is None:
            records.append(TopicValidationRecord(topic.id, topic.chapter_number, artifact.source.source_hash, artifact.revision, artifact.status, published_revision, contract_digest))
            continue
        validation = command_validator.validate(compiled.plan)
        if not validation.valid:
            _issue(issues, topic, "plan", "operations", "invalid_plan", "; ".join(validation.messages))
        operation_names = tuple(sorted({str(operation.get("op")) for operation in validation.expanded_operations}))
        for expected_operation in contract.expected_operations:
            if expected_operation not in operation_names:
                _issue(issues, topic, "plan", "operations", "missing_expected_operation", f"expected operation {expected_operation!r} is absent")

        resource = None
        try:
            resource = compiler_store.get(topic.id)
        except (FileNotFoundError, OSError, ValueError, KeyError) as error:
            _issue(issues, topic, "compiled", "resource", "missing_compiled_resource", str(error))
        if resource is not None:
            comparisons = (
                ("topic_id", resource.topic_id, topic.id),
                ("revision", resource.revision, artifact.revision),
                ("source_hash", resource.source_hash, artifact.source.source_hash),
                ("artifact_digest", resource.artifact_digest, artifact_digest(artifact)),
                ("plan_digest", resource.plan_digest, compiled.plan_digest),
                ("contract_digest", resource.contract_digest, contract_digest),
            )
            for field, actual, expected in comparisons:
                if field == "contract_digest" and not contract.expected_operations and not resource.contract_digest:
                    continue
                if actual != expected:
                    _issue(issues, topic, "compiled", field, "compiled_resource_mismatch", f"expected {expected!r}, got {actual!r}")
            expected_stages = tuple(stage.id for stage in compiled.storyboard)
            resource_stages = tuple(str(stage.get("id")) for stage in resource.stages)
            if resource_stages != expected_stages:
                _issue(issues, topic, "compiled", "stages", "compiled_stage_mismatch", "compiled stage IDs differ from compiler output")
        if snapshot_store is not None:
            snapshot = snapshot_store.load(topic.id, artifact.revision)
            if snapshot is None:
                _issue(issues, topic, "compiled", "snapshot", "missing_snapshot", "published snapshot is missing")
            else:
                expected_snapshot = snapshot_from(artifact, contract, compiled)
                if snapshot != expected_snapshot:
                    _issue(issues, topic, "compiled", "snapshot", "snapshot_mismatch", "snapshot differs from compiled output")

        records.append(TopicValidationRecord(
            topic.id, topic.chapter_number, artifact.source.source_hash, artifact.revision,
            artifact.status, published_revision, contract_digest, compiled.compiler_version,
            compiled.plan_digest, tuple(stage.id for stage in compiled.storyboard), operation_names,
        ))

    issues.sort(key=lambda item: (item.chapter, item.topic_id, item.category, item.path, item.code, item.message))
    return ValidationReport(
        topic_count_by_chapter=dict(sorted(counts.items())),
        issues=tuple(issues),
        topic_records=tuple(records),
    )


def validate_visual_role_palette(registry: CurriculumRegistry) -> tuple[str, ...]:
    """Check legacy recipe output uses the shared teaching-role palette."""

    errors: list[str] = []
    palette = set(ROLE_COLORS.values())
    allowed_roles = {"primary", "construction", "result"}
    validator = SceneCommandService()
    for topic in registry.topics:
        try:
            plan = registry.get_recipe(topic.visualization_id).builder(RenderContext.default(topic.id))
        except Exception as error:
            errors.append(f"{topic.id}: cannot inspect role palette: {error}")
            continue
        validation = validator.validate(plan)
        if not validation.valid:
            continue
        for index, operation in enumerate(validation.expanded_operations):
            color = operation.get("color")
            if isinstance(color, str) and color.startswith("#") and color not in palette:
                errors.append(f"{topic.id}: operation {index + 1} uses unknown teaching color {color}")
            role = operation.get("role")
            if role is not None and role not in allowed_roles:
                errors.append(f"{topic.id}: operation {index + 1} uses unknown scene role {role!r}")
    return tuple(errors)


def validate_capability_plan(
    registry: CurriculumRegistry,
    topic: LessonEntry,
    plan: CommandPlan,
) -> tuple[str, ...]:
    """Ensure every declared topic capability has evidence in the compiled plan."""

    operations = {str(operation.get("op")) for operation in plan.operations}
    errors: list[str] = []
    declarative_skips = {
        "vector_3d": "topic storyboard is 2d; 3d analogy is retained in explanation semantics",
        # The n-dimensional determinant topic is rendered as a 3D volume.
        # Its catalog also names the 2D oriented-area primitive to preserve the
        # area -> volume analogy, but a 2D command cannot be placed in a 3D
        # CommandPlan.  The signed-area bridge remains in the artifact prose
        # and typed 3D volume evidence.
        "oriented_area_2d": "topic storyboard is 3d; 2d area is retained as the explanation analogy",
        "transformed_grid": "topic storyboard is 3d; transformed grid is retained as the explanation analogy",
        "subspace_region": "topic storyboard is 3d; subspace region is retained as the explanation analogy",
    }
    for capability in topic.required_capabilities:
        expected_operation = registry.capabilities.get(capability)
        if expected_operation is None:
            errors.append(f"{topic.id}: capability_mismatch {capability}: no operation mapping")
        elif expected_operation not in operations:
            if (
                (capability == "vector_3d" and plan.scene == "2d")
                or (capability == "oriented_area_2d" and plan.scene == "3d")
                or (capability in {"transformed_grid", "subspace_region"} and plan.scene == "3d")
            ):
                continue
            errors.append(
                f"{topic.id}: capability_mismatch {capability}: expected operation "
                f"{expected_operation!r} is absent; no declared skip reason"
            )
    return tuple(errors)


def audit_published_artifacts(
    registry: CurriculumRegistry,
    store: TeachingArtifactStore,
    source_path: Path,
    *,
    snapshot_store: CompiledSnapshotStore | None = None,
) -> TeachingValidationSummary:
    """Validate every published artifact and return stable aggregate metrics.

    The audit is deliberately opt-in: repositories without generated artifacts
    continue to use the legacy catalog validator, while CI can pass an artifact
    root and require all 54 topics to be published and replayable.
    """

    errors: list[str] = []
    chapters = Counter(topic.chapter_number for topic in registry.topics)
    published_count = 0
    claim_count = 0
    stale_count = 0
    plan_digests: list[tuple[str, str]] = []
    repository = LectureSourceRepository(source_path)
    compiler = VisualSemanticsCompiler()
    for topic in registry.topics:
        stored = store.published(topic.id)
        if stored is None:
            errors.append(f"{topic.id}: missing published artifact")
            continue
        published_count += 1
        artifact = stored.artifact
        claim_count += len(artifact.claims)
        if artifact.status != "published":
            errors.append(f"{topic.id}: artifact status is {artifact.status!r}, expected 'published'")
        if artifact.revision < 1:
            errors.append(f"{topic.id}: artifact revision must be positive")
        if artifact.generated.source_hash != artifact.source.source_hash:
            errors.append(f"{topic.id}: generated source_hash differs from artifact source_hash")
        try:
            context = repository.context_for(topic)
        except (OSError, ValueError) as error:
            errors.append(f"{topic.id}: source context failed: {error}")
            context = None
        if context is not None:
            for issue in validate_source_evidence(artifact, context, topic):
                errors.append(f"{topic.id}: {issue.code} {issue.path}: {issue.message}")
            if artifact.source.source_hash != context.source_hash:
                stale_count += 1
        for issue in (
            *validate_closed_references(artifact),
            *validate_claim_bindings(artifact),
            *validate_teaching_depth(artifact),
            *validate_placeholder_explanations(artifact),
            *validate_worked_examples(artifact),
        ):
            errors.append(f"{topic.id}: {issue.code} {issue.path}: {issue.message}")
        contract = contract_for(topic.id)
        for issue in validate_contract(artifact, contract):
            errors.append(f"{topic.id}: {issue.code}: {issue.detail}")
        try:
            compiled = compiler.compile(artifact, contract, RenderContext.default(topic.id))
        except VisualCompileError as error:
            errors.append(f"{topic.id}: visual compilation failed: {error}")
            continue
        errors.extend(validate_capability_plan(registry, topic, compiled.plan))
        plan_digests.append((topic.id, compiled.plan_digest))
        snapshot = snapshot_store.load(topic.id, artifact.revision) if snapshot_store is not None else snapshot_from(artifact, contract, compiled)
        if snapshot is None:
            errors.append(f"{topic.id}: missing compiled snapshot for revision {artifact.revision}")
            continue
        if snapshot.source_hash != artifact.source.source_hash:
            errors.append(f"{topic.id}: snapshot source_hash differs from artifact")
        if snapshot.plan_digest != compiled.plan_digest:
            errors.append(f"{topic.id}: snapshot plan_digest differs from compiler output")
        if snapshot.stage_ids != tuple(stage.id for stage in compiled.storyboard):
            errors.append(f"{topic.id}: snapshot stage_ids differ from compiler output")
    return TeachingValidationSummary(
        topic_count=len(registry.topics),
        chapter_counts=tuple(sorted(chapters.items())),
        published_count=published_count,
        claim_count=claim_count,
        stale_count=stale_count,
        plan_digests=tuple(sorted(plan_digests)),
        errors=tuple(errors),
    )


def validate_registry(registry: CurriculumRegistry) -> tuple[str, ...]:
    errors: list[str] = []
    topic_ids = [topic.id for topic in registry.topics]
    if len(topic_ids) != len(set(topic_ids)):
        errors.append("catalog: duplicate topic IDs")
    expected_counts = Counter({1: 19, 2: 15, 3: 15, 4: 16, 5: 8, 6: 3, 7: 6, 8: 6})
    if Counter(topic.chapter_number for topic in registry.topics) != expected_counts:
        errors.append("catalog: expected chapter topic counts 19/15/15/16/8/3/6/6")
    node_ids = [node.id for node in registry.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("catalog: duplicate node IDs")
    validator = SceneCommandService()
    for topic in registry.topics:
        try:
            explanation = registry.get_explanation(topic.explanation_id)
        except KeyError as error:
            errors.append(f"{topic.id}: {error}")
        else:
            if explanation.id != topic.explanation_id:
                errors.append(f"{topic.id}: explanation ID mismatch: {explanation.id}")
        try:
            recipe = registry.get_recipe(topic.visualization_id)
        except KeyError as error:
            errors.append(f"{topic.id}: {error}")
            continue
        missing = sorted(set(topic.required_capabilities) - set(registry.capabilities))
        if missing:
            errors.append(f"{topic.id}: missing capabilities: {', '.join(missing)}")
        if recipe.required_capabilities != topic.required_capabilities:
            errors.append(f"{topic.id}: recipe capability declaration differs from catalog")
        try:
            plan = recipe.builder(RenderContext.default(topic.id))
        except Exception as error:
            errors.append(f"{topic.id}: recipe build failed: {error}")
            continue
        result = validator.validate(plan)
        if not result.valid:
            errors.append(f"{topic.id}: invalid command plan: {'; '.join(result.messages)}")
    expected_explanations = {topic.explanation_id for topic in registry.topics}
    expected_recipes = {topic.visualization_id for topic in registry.topics}
    for orphan in sorted(set(registry.explanations) - expected_explanations):
        errors.append(f"orphan explanation: {orphan}")
    for orphan in sorted(set(registry.recipes) - expected_recipes):
        errors.append(f"orphan recipe: {orphan}")
    return tuple(errors)


def validate_lecture_source(path: Path, entries: Iterable[LessonEntry]) -> tuple[str, ...]:
    if not path.is_file():
        return (f"lecture source does not exist: {path}",)
    records = _heading_records(path.read_text(encoding="utf-8"))
    by_key = {(record.path, record.level, record.occurrence): record for record in records}
    errors: list[str] = []
    last_line = 0
    for entry in entries:
        if any(word in " / ".join(entry.source_path) for word in _EXCLUDED):
            errors.append(f"{entry.id}: excluded source path: {' / '.join(entry.source_path)}")
            continue
        anchor = entry.source_anchor
        key = (anchor.heading_path, anchor.heading_level, anchor.occurrence)
        record = by_key.get(key)
        if record is None:
            errors.append(
                f"{entry.id}: missing source anchor level {anchor.heading_level}: "
                f"{' / '.join(anchor.heading_path)} (occurrence {anchor.occurrence})"
            )
            continue
        if record.line_number < last_line:
            errors.append(f"{entry.id}: source anchor is out of lecture order")
        last_line = max(last_line, record.line_number)
    return tuple(errors)


def _heading_records(source: str) -> tuple[HeadingRecord, ...]:
    active_chapter: str | None = None
    stack: list[tuple[int, str]] = []
    counts: Counter[tuple[str, ...]] = Counter()
    records: list[HeadingRecord] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = _HEADING.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if _CHAPTER.match(title):
            active_chapter = title
            # The source occasionally uses a second-level heading for a section.
            # Keep the active chapter at a synthetic root level so those headings
            # remain children of the chapter in the conceptual curriculum path.
            stack = [(1, title)]
        elif active_chapter is None:
            continue
        else:
            if level <= 3 and _SECTION.match(title):
                stack = [(1, active_chapter)]
            else:
                stack = [(item_level, item_title) for item_level, item_title in stack if item_level < level]
            if not stack or stack[0][1] != active_chapter:
                stack.insert(0, (1, active_chapter))
            stack.append((level, title))
        path = tuple(item[1] for item in stack)
        counts[path] += 1
        records.append(HeadingRecord(path, level, counts[path], line_number))
    return tuple(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the linear algebra lecture curriculum")
    parser.add_argument("source", nargs="?", type=Path, default=Path(__file__).parents[1] / ".agents" / "线性代数讲义.md")
    parser.add_argument("--artifact-root", type=Path, default=None, help="require and audit published teaching artifacts")
    parser.add_argument("--snapshot-root", type=Path, default=None, help="load compiled snapshots from this root")
    parser.add_argument("--summary-output", type=Path, default=None, help="write the JSON audit summary to this path")
    args = parser.parse_args(argv)
    registry = catalog_registry()
    errors = [
        *validate_registry(registry),
        *validate_lecture_source(args.source, registry.topics),
        *validate_visual_role_palette(registry),
    ]
    summary: TeachingValidationSummary | None = None
    artifact_root = args.artifact_root
    if artifact_root is None:
        configured_root = os.environ.get("MATH3D_TEACHING_ARTIFACT_ROOT", "").strip()
        artifact_root = Path(configured_root) if configured_root else None
    if artifact_root is None and args.snapshot_root is None:
        report = validate_all_topics(args.source)
        if report.errors:
            for error in report.errors:
                print(error)
            return 1
        print(f"{report.topic_count} topics validated")
        return 0
    if artifact_root is not None:
        snapshot_store = CompiledSnapshotStore(args.snapshot_root) if args.snapshot_root is not None else None
        summary = audit_published_artifacts(
            registry,
            TeachingArtifactStore(artifact_root),
            args.source,
            snapshot_store=snapshot_store,
        )
        errors.extend(summary.errors)
        if args.summary_output is not None:
            args.summary_output.parent.mkdir(parents=True, exist_ok=True)
            args.summary_output.write_text(
                json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    if errors:
        for error in errors:
            print(error)
        return 1
    if summary is None:
        print(f"{len(registry.topics)} topics validated")
    else:
        print(json.dumps(summary.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
