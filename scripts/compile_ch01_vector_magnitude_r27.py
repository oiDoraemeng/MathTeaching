"""Compile the new ch01.vector.magnitude published revision (r27).

Steps:
  * Load the freshly-written r27 published artifact.
  * Compile it through VisualSemanticsCompiler (uses ch01 contract).
  * Save CompiledSnapshot at ``snapshots/ch01/ch01.vector.magnitude/r27.json``.
  * Save CompiledResource at ``compiled/ch01.vector.magnitude.json``.
  * Refresh the ``index.json`` row (``artifact_digest`` / ``draft_revision``)
    so the runtime witness matches the regenerated artifact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.teaching.store import ArtifactRevision, TeachingArtifactStore
from linear_algebra.teaching.compile_resources import (
    CompiledResource,
    compiled_resource_store,
    compile_published_topic,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.snapshots import (
    CompiledSnapshotStore,
    snapshot_from,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "linear_algebra" / "teaching" / "data"


def main() -> int:
    store = TeachingArtifactStore(DATA)
    topic_id = "ch01.vector.magnitude"
    revision = 27
    stored = store.get(topic_id, revision, "published")
    artifact = stored.artifact
    contract = contract_for(topic_id)
    compiled = VisualSemanticsCompiler().compile(artifact, contract, RenderContext.default(topic_id))

    snapshot_store = CompiledSnapshotStore(DATA / "snapshots")
    snapshot = snapshot_from(artifact, contract, compiled)
    snapshot_store.save(snapshot)
    print(f"snapshot saved at revision {revision}")

    resource = compile_published_topic(topic_id, artifact_store=store)
    if resource.revision != revision:
        raise ValueError(f"compiled resource revision mismatch: expected {revision}, got {resource.revision}")
    compiled_resource_store(DATA / "compiled").save(resource)
    print(f"compiled resource saved at revision {revision}")

    payload = store.upsert_published_topic(
        ArtifactRevision(topic_id=topic_id, revision=revision, state="published"),
        metadata={
            "compiler_version": resource.compiler_version,
            "render_profile": resource.render_profile,
            "plan_digest": resource.plan_digest,
            "stage_count": len(resource.stages),
            "claim_count": resource.claim_count,
            "contract_digest": resource.contract_digest,
            "scene_family": resource.scene_family,
            "draft_revision": 33,
            "reviewed_revision": revision,
        },
    )
    # 按仓库的双空格格式重写索引，保持差异可读。
    (DATA / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("index row refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
