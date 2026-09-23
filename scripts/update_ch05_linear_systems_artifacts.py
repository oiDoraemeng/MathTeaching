"""Regenerate and activate the reviewed Chapter 5 sections 5.1--5.5."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.chapter_05 import TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_05


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"


def _sync_topic_digests(resources) -> None:
    path = DATA / "topic-digests.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("topic-digests.json must contain object rows")
    retained = [row for row in rows if not str(row.get("topic_id", "")).startswith("ch05.")]
    retained.extend(
        {
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
        for resource in resources
    )
    retained.sort(key=lambda row: str(row.get("topic_id", "")))
    path.write_text(
        json.dumps(retained, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    payloads = {topic.id: artifact_payload_for(topic.id) for topic in TOPICS}
    resources = compile_chapter_05(reviewed_payloads=payloads)
    _sync_topic_digests(resources)
    print(
        json.dumps(
            {
                "topics": [
                    {
                        "topic_id": resource.topic_id,
                        "stage_count": len(resource.stages),
                        "plan_digest": resource.plan_digest,
                    }
                    for resource in resources
                ]
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
