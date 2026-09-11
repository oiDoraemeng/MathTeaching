from linear_algebra.teaching.chapter_artifacts import artifact_payload_for, load_reviewed_artifacts
from linear_algebra.teaching.validation import validate_artifact_payload


def test_all_39_chapter_artifacts_are_deterministic_and_reviewed_only():
    payloads = load_reviewed_artifacts()
    assert len(payloads) == 39
    assert all(payload["status"] == "reviewed" for payload in payloads.values())
    for topic_id, payload in payloads.items():
        assert artifact_payload_for(topic_id) == artifact_payload_for(topic_id)
        artifact = validate_artifact_payload(payload)
        assert artifact.topic_id == topic_id
        assert artifact.status == "reviewed"


def test_artifacts_have_closed_source_and_visual_graphs():
    for topic_id in load_reviewed_artifacts():
        artifact = validate_artifact_payload(artifact_payload_for(topic_id))
        assert artifact.claims[0].source_refs[0] in {span.id for span in artifact.source.spans}
        assert artifact.visual_semantics.scene_family
        assert artifact.generated.source_hash == artifact.source.source_hash
