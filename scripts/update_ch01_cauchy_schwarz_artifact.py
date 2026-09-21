"""Publish and compile the lecture-grounded Cauchy-Schwarz teaching artifact."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.compile_resources import (
    CompiledResource,
    compiled_resource_store,
)
from linear_algebra.teaching.generation import GenerationRequest, generate_draft
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import (
    ArtifactRevision,
    TeachingArtifactStore,
    artifact_digest,
)
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for, validate_contract
from linear_algebra.visualizations.snapshots import (
    CompiledSnapshotStore,
    contract_digest_for,
    snapshot_from,
)
from scripts.generate_chapter1_local import LocalChapterOneAgent


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"
TOPIC_ID = "ch01.inner.cauchy-schwarz"


def compile_and_activate(
    store: TeachingArtifactStore,
    *,
    published_revision: int,
    draft_revision: int,
    reviewed_revision: int,
) -> CompiledResource:
    revision = ArtifactRevision(TOPIC_ID, published_revision, "published")
    artifact = store.get(TOPIC_ID, published_revision, "published").artifact
    contract = contract_for(TOPIC_ID)
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract,
        RenderContext.default(TOPIC_ID),
    )
    CompiledSnapshotStore(DATA / "snapshots").save(
        snapshot_from(artifact, contract, compiled)
    )

    stages = tuple(
        {
            "id": stage.id,
            "title": stage.title,
            "caption": stage.caption,
            "layout": stage.layout,
            "visible_refs": list(stage.visible_refs),
            "visible_aliases": list(stage.visible_aliases),
            "anchor": list(stage.anchor),
        }
        for stage in compiled.storyboard
    )
    resource = CompiledResource(
        topic_id=TOPIC_ID,
        revision=artifact.revision,
        artifact_digest=artifact_digest(artifact),
        source_hash=artifact.source.source_hash,
        compiler_version=compiled.compiler_version,
        render_profile=compiled.render_profile,
        plan_digest=compiled.plan_digest,
        plan=compiled.plan.to_dict(),
        stages=stages,
        read_guide=artifact.explanation.read_guide,
        claim_count=len(artifact.claims),
        contract_digest=contract_digest_for(contract),
        scene_family=artifact.visual_semantics.scene_family,
    )
    compiled_resource_store(DATA / "compiled").save(resource)
    store.upsert_published_topic(
        revision,
        metadata={
            "compiler_version": resource.compiler_version,
            "render_profile": resource.render_profile,
            "plan_digest": resource.plan_digest,
            "stage_count": len(resource.stages),
            "claim_count": resource.claim_count,
            "contract_digest": resource.contract_digest,
            "scene_family": resource.scene_family,
            "draft_revision": draft_revision,
            "reviewed_revision": reviewed_revision,
        },
    )
    return resource


def main() -> int:
    topic = next(item for item in topic_entries() if item.id == TOPIC_ID)
    source_repo = LectureSourceRepository(ROOT / ".agents" / "线性代数讲义.md")
    context = source_repo.context_for(topic)
    request = GenerationRequest(context, topic, profile_for(topic.id))
    store = TeachingArtifactStore(DATA)

    draft = generate_draft(LocalChapterOneAgent(), request)
    draft_revision = store.save_draft(draft.artifact, raw_reply=draft.raw_reply)
    reviewed_revision = store.review_draft(
        topic.id,
        draft_revision.revision,
        "local-math-review",
    )
    reviewed = store.get(
        topic.id,
        reviewed_revision.revision,
        "reviewed",
    ).artifact

    issues = (
        *validate_source_evidence(reviewed, context, topic),
        *validate_closed_references(reviewed),
        *validate_claim_bindings(reviewed),
        *validate_teaching_depth(reviewed),
        *validate_worked_examples(reviewed),
        *validate_contract(reviewed, contract_for(topic.id)),
    )
    if issues:
        details = "; ".join(
            f"{issue.code}:{getattr(issue, 'path', getattr(issue, 'detail', ''))}"
            for issue in issues
        )
        raise ValueError(f"{topic.id}: {details}")

    compiler = VisualSemanticsCompiler()
    compiler.compile(reviewed, contract_for(topic.id), RenderContext.default(topic.id))
    published = store.publish(reviewed, source_context=context, topic=topic)
    if not published.ok or published.revision is None:
        raise ValueError(
            f"{topic.id}: "
            + "; ".join(issue.code for issue in published.issues)
        )

    compile_and_activate(
        store,
        published_revision=published.revision.revision,
        draft_revision=draft_revision.revision,
        reviewed_revision=reviewed_revision.revision,
    )

    print(
        f"{topic.id}: draft r{draft_revision.revision}, "
        f"reviewed r{reviewed_revision.revision}, "
        f"published r{published.revision.revision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
