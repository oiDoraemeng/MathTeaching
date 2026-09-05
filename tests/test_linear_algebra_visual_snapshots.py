"""Published compiled snapshot tests."""

from dataclasses import replace

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import VisualContract
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, snapshot_from
from tests.teaching_fixtures import composition_artifact_payload


def test_published_snapshot_contains_digest_but_not_scene_operations(tmp_path) -> None:
    artifact = replace(
        TeachingArtifact.from_dict(composition_artifact_payload()),
        status="published",
    )
    contract = VisualContract(artifact.topic_id, (), (), (), (), 1)
    compiled = VisualSemanticsCompiler().compile(
        artifact, contract, RenderContext.default(artifact.topic_id)
    )
    snapshot = snapshot_from(artifact, contract, compiled)
    store = CompiledSnapshotStore(tmp_path)
    path = store.save(snapshot)
    loaded = store.load(artifact.topic_id, artifact.revision)

    assert path.name == "r1.json"
    assert loaded == snapshot
    assert "operations" not in path.read_text(encoding="utf-8")
