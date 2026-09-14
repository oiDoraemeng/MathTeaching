"""Incrementally publish changed teaching artifacts with the local quality adapter."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.authoring import synchronize_topic
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    source = Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md"
    if not source.is_file():
        source = Path(__file__).resolve().parents[1] / ".agents" / "绾挎€т唬鏁拌涔?md"
    repository = LectureSourceRepository(source)
    store = TeachingArtifactStore(root)
    updated = 0
    rejected = 0
    for topic in topic_entries():
        result = synchronize_topic(topic, store=store, source_repository=repository)
        if result.status == "published":
            updated += 1
        elif result.status == "rejected":
            rejected += 1
        print(json.dumps({
            "topic_id": topic.id,
            "status": result.status,
            "revision": result.revision,
            "issues": list(result.issues),
        }, ensure_ascii=False))
    print(json.dumps({"updated": updated, "rejected": rejected}, ensure_ascii=False))
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
