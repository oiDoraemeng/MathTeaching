"""Incrementally materialize trusted local teaching refinements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Literal, Mapping

from linear_algebra.catalog.model import LessonEntry
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for, validate_contract
from linear_algebra.visualizations.snapshots import (
    CompiledSnapshotStore,
    contract_digest_for,
    snapshot_from,
)

from .quality import refine_payload
from .model import TeachingArtifact
from .source import LectureSourceRepository, SourceContext
from .store import TeachingArtifactStore, artifact_digest
from .validation import (
    ArtifactValidationError,
    validate_artifact_payload,
    validate_claim_bindings,
    validate_placeholder_explanations,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)


SyncStatus = Literal["unchanged", "published", "rejected", "unavailable"]
PayloadRefiner = Callable[[Mapping[str, object]], dict[str, object]]


@dataclass(frozen=True)
class AuthoringSyncResult:
    topic_id: str
    status: SyncStatus
    revision: int | None = None
    issues: tuple[str, ...] = ()


def synchronize_topic(
    topic: LessonEntry,
    *,
    store: TeachingArtifactStore,
    source_repository: LectureSourceRepository,
    refiner: PayloadRefiner = refine_payload,
    reviewer: str = "local-math-review",
) -> AuthoringSyncResult:
    """Publish one changed local refinement through the normal release gates.

    The current index remains authoritative until schema, source, mathematical,
    visual-contract and compiler validation all succeed.  An invalid edit can
    therefore never displace the last stable runtime revision.
    """

    stored = store.published(topic.id)
    if stored is None:
        return AuthoringSyncResult(topic.id, "unavailable")

    current = stored.artifact
    try:
        source_context = source_repository.context_for(topic)
        refined_payload = refiner(current.to_dict())
        if _source_anchor_changed(current, source_context):
            _refresh_source_evidence(refined_payload, source_context)
        refined = validate_artifact_payload(refined_payload)
    except (ArtifactValidationError, TypeError, ValueError) as error:
        return AuthoringSyncResult(topic.id, "rejected", current.revision, _error_details(error))

    if artifact_digest(refined) == artifact_digest(current):
        return AuthoringSyncResult(topic.id, "unchanged", current.revision)

    try:
        draft_payload = refined.to_dict()
        draft_payload["status"] = "draft"
        draft_payload["revision"] = 1
        generated = draft_payload.get("generated")
        if not isinstance(generated, dict):
            raise ValueError("$.generated: expected object")
        generated["generated_at"] = _utc_timestamp()
        generated["raw_reply_digest"] = "sha256:pending"
        generated["artifact_digest"] = "sha256:pending"
        candidate = validate_artifact_payload(draft_payload)

        issues = (
            *validate_source_evidence(candidate, source_context, topic),
            *validate_claim_bindings(candidate),
            *validate_teaching_depth(candidate),
            *validate_placeholder_explanations(candidate),
            *validate_worked_examples(candidate),
        )
        contract = contract_for(topic.id)
        contract_issues = validate_contract(candidate, contract)
        if issues or contract_issues:
            details = tuple(
                sorted(
                    [f"{item.code}:{item.path}:{item.message}" for item in issues]
                    + [f"{item.code}:{contract.topic_id}:{item.detail}" for item in contract_issues]
                )
            )
            return AuthoringSyncResult(topic.id, "rejected", current.revision, details)

        compiled = VisualSemanticsCompiler().compile(
            candidate,
            contract,
            RenderContext.default(topic.id),
        )
    except (ArtifactValidationError, VisualCompileError, OSError, KeyError, TypeError, ValueError) as error:
        return AuthoringSyncResult(topic.id, "rejected", current.revision, _error_details(error))

    try:
        raw_reply = json.dumps(
            candidate.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        draft_revision = store.save_draft(candidate, raw_reply=raw_reply)
        reviewed_revision = store.review_draft(topic.id, draft_revision.revision, reviewer)
        reviewed = store.get(topic.id, reviewed_revision.revision, "reviewed").artifact
        published = store.publish(
            reviewed,
            source_context=source_context,
            topic=topic,
            raw_reply=raw_reply,
        )
        if not published.ok or published.revision is None:
            details = tuple(
                f"{item.code}:{item.path}:{item.message}" for item in published.issues
            )
            return AuthoringSyncResult(topic.id, "rejected", current.revision, details)

        published_artifact = store.get(
            topic.id, published.revision.revision, "published"
        ).artifact
        snapshot = snapshot_from(published_artifact, contract, compiled)
        CompiledSnapshotStore(store.root / "snapshots").save(snapshot)
        store.upsert_published_topic(
            published.revision,
            metadata={
                "draft_revision": draft_revision.revision,
                "reviewed_revision": reviewed_revision.revision,
                "compiler_version": compiled.compiler_version,
                "render_profile": compiled.render_profile,
                "contract_digest": contract_digest_for(contract),
                "scene_family": published_artifact.visual_semantics.scene_family,
                "plan_digest": compiled.plan_digest,
                "stage_count": len(compiled.storyboard),
                "claim_count": len(published_artifact.claims),
            },
        )
        return AuthoringSyncResult(topic.id, "published", published.revision.revision)
    except (ArtifactValidationError, VisualCompileError, OSError, KeyError, TypeError, ValueError) as error:
        return AuthoringSyncResult(topic.id, "rejected", current.revision, _error_details(error))


def workspace_authoring_available(*, store: TeachingArtifactStore) -> bool:
    """Return whether this process is running from the writable source checkout."""

    project_root = Path(__file__).resolve().parents[2]
    bundled_root = Path(__file__).resolve().with_name("data")
    return (
        (project_root / ".git").exists()
        and (project_root / ".agents" / "线性代数讲义.md").is_file()
        and store.root == bundled_root.resolve()
    )


def _refresh_source_evidence(
    payload: dict[str, object], context: SourceContext
) -> None:
    """Replace an artifact's source witness when its catalog anchor changes."""

    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("artifact payload is missing a source object")

    spans = [
        {
            "id": span.id,
            "heading_path": list(span.heading_path),
            "start_line": span.start_line,
            "end_line": span.end_line,
            "fingerprint": span.fingerprint,
            "text": span.text,
        }
        for span in context.spans
    ]
    source.update(
        {
            "source_path": list(context.source_path),
            "heading_path": list(context.heading_path),
            "heading_level": context.heading_level,
            "occurrence": context.occurrence,
            "excerpt": context.excerpt,
            "source_hash": context.source_hash,
            "spans": spans,
            "neighboring_titles": list(context.neighboring_titles),
        }
    )

    source_refs = [span.id for span in context.spans]
    claims = payload.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict):
                claim["source_refs"] = source_refs

    generated = payload.get("generated")
    if isinstance(generated, dict):
        generated["source_hash"] = context.source_hash


def _source_anchor_changed(
    artifact: TeachingArtifact, context: SourceContext
) -> bool:
    """Return whether a catalog source anchor now identifies a new section."""

    source = artifact.source
    return (
        source.source_path != context.source_path
        or source.heading_path != context.heading_path
        or source.heading_level != context.heading_level
        or source.occurrence != context.occurrence
    )


def _error_details(error: BaseException) -> tuple[str, ...]:
    issues = getattr(error, "issues", None)
    if issues:
        return tuple(
            f"{getattr(item, 'code', type(error).__name__)}:"
            f"{getattr(item, 'path', '$')}:"
            f"{getattr(item, 'message', str(item))}"
            for item in issues
        )
    return (str(error),)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "AuthoringSyncResult",
    "synchronize_topic",
    "workspace_authoring_available",
]
