"""Regenerate and activate the text-only Chapter 3 sections 3.3--3.6."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from linear_algebra.catalog.chapter_03 import TOPICS
from linear_algebra.teaching.generation import GenerationRequest, generate_draft
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.contracts import contract_for, validate_contract

import generate_chapter3_local as chapter3
from update_ch03_determinant_core_artifacts import compile_and_activate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"
TOPIC_IDS = (
    "ch03.cramer.area-ratio",
    "ch03.inverse.undo",
    "ch03.adjugate.matrix",
    "ch03.det.zero.equivalence",
)
REMOVED_TOPIC_IDS = {
    "ch03.inverse.formula",
    "ch03.inverse.examples",
}


def _remove_retired_topic_resources(topic_id: str) -> None:
    targets = (
        DATA / "compiled" / f"{topic_id}.json",
        DATA / "drafts" / "ch03" / topic_id,
        DATA / "revieweds" / "ch03" / topic_id,
        DATA / "published" / "ch03" / topic_id,
        DATA / "published" / "ch03" / f"{topic_id}.json",
        DATA / "audit" / "ch03" / topic_id,
        DATA / "audit" / "reviews" / "ch03" / topic_id,
        DATA / "snapshots" / "ch03" / topic_id,
    )
    data_root = DATA.resolve()
    for target in targets:
        resolved = target.resolve()
        if not resolved.is_relative_to(data_root):
            raise ValueError(f"refusing to remove out-of-store path: {resolved}")
        if resolved.is_dir():
            shutil.rmtree(resolved)
        elif resolved.exists():
            resolved.unlink()


def _remove_retired_index_rows(store: TeachingArtifactStore) -> None:
    payload = store.index_payload()
    rows = [
        row
        for row in payload.get("topics", [])
        if isinstance(row, dict) and str(row.get("topic_id", "")) not in REMOVED_TOPIC_IDS
    ]
    payload["topics"] = sorted(rows, key=lambda row: str(row.get("topic_id", "")))
    payload["topic_count"] = len(payload["topics"])
    (DATA / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    digest_path = DATA / "topic-digests.json"
    digests = json.loads(digest_path.read_text(encoding="utf-8"))
    digests = [row for row in digests if row.get("topic_id") not in REMOVED_TOPIC_IDS]
    digest_path.write_text(
        json.dumps(digests, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
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
            raise ValueError(
                f"{topic_id}: "
                + "; ".join(
                    f"{issue.code}:{getattr(issue, 'path', getattr(issue, 'detail', ''))}"
                    for issue in issues
                )
            )
        published = store.publish(
            reviewed,
            source_context=context,
            topic=topic,
            raw_reply=draft.raw_reply,
        )
        if not published.ok or published.revision is None:
            raise ValueError(
                f"{topic_id}: "
                + "; ".join(f"{issue.code}:{issue.path}" for issue in published.issues)
            )
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

    for topic_id in REMOVED_TOPIC_IDS:
        _remove_retired_topic_resources(topic_id)
    _remove_retired_index_rows(store)
    print(json.dumps({"topics": summaries}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
