"""Regenerate, compile, and activate the three 3.2 determinant topics."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from linear_algebra.catalog.chapter_03 import TOPICS
from linear_algebra.teaching.compile_resources import CompiledResource, compiled_resource_store
from linear_algebra.teaching.generation import GenerationRequest, generate_draft
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import ArtifactRevision, TeachingArtifactStore, artifact_digest
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
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, contract_digest_for, snapshot_from

import generate_chapter3_local as chapter3


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"
TOPIC_IDS = (
    "ch03.det.basic-properties",
    "ch03.det.multiplicativity",
    "ch03.det.transpose",
)
REMOVED_TOPIC_IDS = {
    "ch03.det.row-swap",
    "ch03.det.scaling",
    "ch03.det.shear",
}


def _sync_topic_digest(resource: CompiledResource) -> None:
    path = DATA / "topic-digests.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("topic-digests.json must contain object rows")
    replacement = {
        "topic_id": resource.topic_id,
        "revision": resource.revision,
        "source_hash": resource.source_hash,
        "artifact_digest": resource.artifact_digest,
        "compiler_version": resource.compiler_version,
        "render_profile": resource.render_profile,
        "plan_digest": resource.plan_digest,
        "stage_count": len(resource.stages),
        "claim_count": resource.claim_count,
    }
    updated = [row for row in rows if row.get("topic_id") != resource.topic_id]
    updated.append(replacement)
    updated.sort(key=lambda row: str(row.get("topic_id", "")))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def compile_and_activate(
    store: TeachingArtifactStore,
    topic_id: str,
    *,
    published_revision: int,
    draft_revision: int,
    reviewed_revision: int,
) -> CompiledResource:
    artifact = store.get(topic_id, published_revision, "published").artifact
    contract = contract_for(topic_id)
    compiled = VisualSemanticsCompiler().compile(artifact, contract, RenderContext.default(topic_id))
    CompiledSnapshotStore(DATA / "snapshots").save(snapshot_from(artifact, contract, compiled))
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
        topic_id=topic_id,
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
        ArtifactRevision(topic_id, published_revision, "published"),
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
    _sync_topic_digest(resource)
    return resource


def _write_index_without_removed_topics(store: TeachingArtifactStore) -> None:
    payload = store.index_payload()
    topics = [
        row
        for row in payload.get("topics", [])
        if isinstance(row, dict) and str(row.get("topic_id", "")) not in REMOVED_TOPIC_IDS
    ]
    payload["topics"] = sorted(topics, key=lambda row: str(row.get("topic_id", "")))
    payload["topic_count"] = len(payload["topics"])
    (DATA / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    repo = LectureSourceRepository(ROOT / ".agents" / "线性代数讲义.md")
    store = TeachingArtifactStore(DATA)
    agent = chapter3.LocalChapterThreeAgent()
    summaries: list[dict[str, object]] = []
    for topic_id in TOPIC_IDS:
        topic = next(item for item in TOPICS if item.id == topic_id)
        context = repo.context_for(topic)
        draft = generate_draft(agent, GenerationRequest(context, topic, profile_for(topic.id)))
        draft_revision = store.save_draft(draft.artifact, raw_reply=draft.raw_reply)
        reviewed_revision = store.review_draft(topic.id, draft_revision.revision, "local-math-review")
        reviewed = store.get(topic.id, reviewed_revision.revision, "reviewed").artifact
        issues = (
            *validate_source_evidence(reviewed, context, topic),
            *validate_closed_references(reviewed),
            *validate_claim_bindings(reviewed),
            *validate_teaching_depth(reviewed),
            *validate_worked_examples(reviewed),
            *validate_contract(reviewed, contract_for(topic.id)),
        )
        if issues:
            raise ValueError(f"{topic_id}: " + "; ".join(f"{issue.code}:{issue.path}" for issue in issues))
        published = store.publish(reviewed, source_context=context, topic=topic, raw_reply=draft.raw_reply)
        if not published.ok or published.revision is None:
            raise ValueError(f"{topic_id}: " + "; ".join(issue.code for issue in published.issues))
        resource = compile_and_activate(
            store,
            topic_id,
            published_revision=published.revision.revision,
            draft_revision=draft_revision.revision,
            reviewed_revision=reviewed_revision.revision,
        )
        summaries.append(
            {
                "topic_id": topic_id,
                "draft_revision": draft_revision.revision,
                "reviewed_revision": reviewed_revision.revision,
                "published_revision": published.revision.revision,
                "source_hash": context.source_hash,
                "stage_count": len(resource.stages),
                "plan_digest": resource.plan_digest,
            }
        )
    _write_index_without_removed_topics(store)
    print(json.dumps({"topics": summaries}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
