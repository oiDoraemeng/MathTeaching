"""Re-review existing published teaching artifacts with the local quality adapter."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.quality import refine_payload
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    source = Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md"
    if not source.is_file():
        source = Path(__file__).resolve().parents[1] / ".agents" / "绾挎€т唬鏁拌涔?md"
    repository = LectureSourceRepository(source)
    store = TeachingArtifactStore(root)
    updated = 0
    for topic in topic_entries():
        stored = store.published(topic.id)
        if stored is None:
            continue
        context = repository.context_for(topic)
        payload = refine_payload(stored.artifact.to_dict())
        payload["status"] = "draft"
        payload["revision"] = 1
        generated = payload.setdefault("generated", {})
        generated["raw_reply_digest"] = "sha256:pending"
        generated["artifact_digest"] = "sha256:pending"
        artifact = TeachingArtifact.from_dict(payload)
        raw_reply = json.dumps(artifact.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        issues = (
            *validate_source_evidence(artifact, context, topic),
            *validate_closed_references(artifact),
            *validate_claim_bindings(artifact),
            *validate_teaching_depth(artifact),
            *validate_worked_examples(artifact),
        )
        if issues:
            details = "; ".join(f"{item.code}:{item.path}" for item in issues)
            raise ValueError(f"{topic.id}: {details}")
        draft = store.save_draft(artifact, raw_reply=raw_reply)
        reviewed = store.review_draft(topic.id, draft.revision, "codex-math-explanation-review")
        reviewed_artifact = store.get(topic.id, reviewed.revision, "reviewed").artifact
        published = store.publish(reviewed_artifact, source_context=context, topic=topic, raw_reply=raw_reply)
        if not published.ok:
            details = "; ".join(f"{item.code}:{item.path}" for item in published.issues)
            raise ValueError(f"{topic.id}: {details}")
        updated += 1
        print(json.dumps({"topic_id": topic.id, "published_revision": published.revision.revision}, ensure_ascii=False))
    print(json.dumps({"updated": updated}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
