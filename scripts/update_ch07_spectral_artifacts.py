"""Regenerate and activate the reviewed Chapter 7 sections 7.1--7.4."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.chapter_07 import TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_07


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"


def _sync_topic_digests(resources) -> None:
    path = DATA / "topic-digests.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    retained = [row for row in rows if not str(row.get("topic_id", "")).startswith("ch07.")]
    retained.extend({
        "topic_id": resource.topic_id,
        "revision": resource.revision,
        "source_hash": resource.source_hash,
        "artifact_digest": resource.artifact_digest,
        "plan_digest": resource.plan_digest,
        "contract_digest": resource.contract_digest,
        "compiler_version": resource.compiler_version,
        "render_profile": resource.render_profile,
        "scene_family": resource.scene_family,
    } for resource in resources)
    path.write_text(json.dumps(retained, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    payloads = {topic.id: artifact_payload_for(topic.id) for topic in TOPICS}
    resources = compile_chapter_07(reviewed_payloads=payloads)
    _sync_topic_digests(resources)
    print(f"released {len(resources)} Chapter 7 reviewed and compiled resources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
