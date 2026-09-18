import hashlib
import json
from pathlib import Path

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for, load_draft_artifacts, load_reviewed_artifacts
from linear_algebra.teaching.validation import validate_artifact_payload


def test_all_39_chapter_artifacts_are_deterministic_and_reviewed_only():
    payloads = load_reviewed_artifacts()
    assert len(payloads) == 37
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


def test_materialized_resources_and_receipts_are_digestable():
    drafts = load_draft_artifacts()
    reviewed = load_reviewed_artifacts()
    assert len(drafts) == len(reviewed) == 37
    for topic_id, payload in reviewed.items():
        assert payload["status"] == "reviewed"
        assert drafts[topic_id]["status"] == "draft"
        assert (Path("linear_algebra/teaching/data/revieweds") / topic_id[:4] / topic_id / "r1.json").is_file()
        receipt = payload["generated"]
        assert str(receipt["raw_reply_digest"]).startswith("sha256:")
        assert str(receipt["artifact_digest"]).startswith("sha256:")
        assert receipt["source_hash"] == payload["source"]["source_hash"]
