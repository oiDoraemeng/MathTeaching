"""Regenerate, compile and activate one Chapter 2 topic artifact.

Topic: ch02.matrix.additive-distributivity (讲义 2.4 矩阵加法与矩阵数乘).

This reuses the local Chapter 2 adapter exactly like generate_chapter2_local.py,
but regenerates and makes runtime-visible only a single topic so the remaining
Chapter 2 topics keep their current published revisions.

Unlike a bare ``store.publish`` call, this follows the Cauchy-Schwarz
precedent (``scripts/update_ch01_cauchy_schwarz_artifact.py``): the published
artifact is compiled into a fresh ``CompiledResource`` (snapshot + compiled
resource on disk) and the index row is written with the real compiler metadata,
so ``stage_count`` / ``reviewed_revision`` never inherit stale values.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.chapter_02 import TOPICS
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

import generate_chapter2_local as chapter2


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"
TOPIC_ID = "ch02.matrix.additive-distributivity"


def _sync_chapter_and_digest_indexes(resource: CompiledResource) -> None:
    chapter_path = DATA / "index-ch02.json"
    chapter_payload = json.loads(chapter_path.read_text(encoding="utf-8"))
    chapter_rows = chapter_payload.get("topics") if isinstance(chapter_payload, dict) else None
    if not isinstance(chapter_rows, list) or not all(isinstance(row, dict) for row in chapter_rows):
        raise ValueError("index-ch02.json must contain object topic rows")
    replacement_row = {
        "topic_id": resource.topic_id,
        "revision": resource.revision,
        "source_hash": resource.source_hash,
    }
    updated_chapter_rows = [
        row for row in chapter_rows if row.get("topic_id") != resource.topic_id
    ]
    updated_chapter_rows.append(replacement_row)
    chapter_payload["topics"] = sorted(
        updated_chapter_rows,
        key=lambda row: str(row.get("topic_id", "")),
    )
    chapter_temporary = chapter_path.with_suffix(chapter_path.suffix + ".tmp")
    chapter_temporary.write_text(
        json.dumps(chapter_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    chapter_temporary.replace(chapter_path)

    digest_path = DATA / "topic-digests.json"
    rows = json.loads(digest_path.read_text(encoding="utf-8"))
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
    temporary = digest_path.with_suffix(digest_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(digest_path)


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
    _sync_chapter_and_digest_indexes(resource)
    return resource


def main() -> int:
    repo = LectureSourceRepository(ROOT / ".agents" / "线性代数讲义.md")
    store = TeachingArtifactStore(DATA)
    agent = chapter2.LocalChapterTwoAgent()

    topic = next(item for item in TOPICS if item.id == TOPIC_ID)
    context = repo.context_for(topic)
    request = GenerationRequest(context, topic, profile_for(topic.id))
    draft = generate_draft(agent, request)
    draft_revision = store.save_draft(draft.artifact, raw_reply=draft.raw_reply)
    reviewed_revision = store.review_draft(topic.id, draft_revision.revision, "local-math-review")
    artifact = store.get(topic.id, reviewed_revision.revision, "reviewed").artifact

    issues = (
        *validate_source_evidence(artifact, context, topic),
        *validate_closed_references(artifact),
        *validate_claim_bindings(artifact),
        *validate_teaching_depth(artifact),
        *validate_worked_examples(artifact),
        *validate_contract(artifact, contract_for(topic.id)),
    )
    if issues:
        raise ValueError(f"{topic.id}: " + "; ".join(f"{issue.code}:{issue.path}" for issue in issues))

    VisualSemanticsCompiler().compile(artifact, contract_for(topic.id), RenderContext.default(topic.id))
    published = store.publish(artifact, source_context=context, topic=topic, raw_reply=draft.raw_reply)
    if not published.ok or published.revision is None:
        raise ValueError(f"{topic.id}: " + "; ".join(issue.code for issue in published.issues))

    resource = compile_and_activate(
        store,
        published_revision=published.revision.revision,
        draft_revision=draft_revision.revision,
        reviewed_revision=reviewed_revision.revision,
    )

    print(
        json.dumps(
            {
                "topic_id": topic.id,
                "draft_revision": draft_revision.revision,
                "reviewed_revision": reviewed_revision.revision,
                "published_revision": published.revision.revision,
                "source_hash": context.source_hash,
                "stage_count": len(resource.stages),
                "artifact_digest": resource.artifact_digest,
                "plan_digest": resource.plan_digest,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - direct script invocation
    raise SystemExit(main())
