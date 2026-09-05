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
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.contracts import contract_for, validate_contract
from linear_algebra.visualizations.palette import ROLE_COLORS
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, snapshot_from
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from services.scene_commands import CommandPlan
from services.scene_commands import SceneCommandService

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHAPTER = re.compile(r"^第([1-3])章(?:\s|$)")
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
    for capability in topic.required_capabilities:
        expected_operation = registry.capabilities.get(capability)
        if expected_operation is None:
            errors.append(f"{topic.id}: capability_mismatch {capability}: no operation mapping")
        elif expected_operation not in operations:
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
    if Counter(topic.chapter_number for topic in registry.topics) != Counter({1: 24, 2: 15, 3: 15}):
        errors.append("catalog: expected chapter topic counts 24/15/15")
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
