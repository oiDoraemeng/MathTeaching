"""Atomic review and publication gates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.model import TeachingArtifact, WorkedExample, WorkedExampleCheck
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.teaching_fixtures import composition_artifact_payload


def _topic_context():
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    return topic, context


def _reviewed_valid_artifact() -> TeachingArtifact:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    example = WorkedExample(
        kind="matrix_transform",
        given=([[0, -1], [1, 0]], [1, 2]),
        calculation=("Bx = (-2, 1)",),
        result=(-2.0, 1.0),
        checks=(WorkedExampleCheck(name="result", expected=(-2.0, 1.0)),),
    )
    explanation = replace(
        artifact.explanation,
        definition="AB 表示先做 B 再做 A。",
        formula="(AB)x=A(Bx)",
        derivation=("先算 Bx", "再算 A(Bx)"),
        worked_examples=(example,),
        geometric_meaning="变换按从右到左的顺序串联。",
        pitfalls=("不能把 AB 当作先做 A。",),
        invariants=("复合顺序不变。",),
        connections=("矩阵与基",),
        transfer_note="比较 BA 可检验非交换性。",
    )
    return replace(artifact, explanation=explanation, status="reviewed")


def test_publish_replaces_index_only_after_all_validation_passes(tmp_path: Path) -> None:
    topic, context = _topic_context()
    store = TeachingArtifactStore(tmp_path)
    old_result = store.publish(_reviewed_valid_artifact(), source_context=context, topic=topic)
    assert old_result.ok and old_result.revision is not None
    old = store.published(topic.id)
    assert old is not None

    broken = _reviewed_valid_artifact()
    bad_example = replace(
        broken.explanation.worked_examples[0],
        checks=(WorkedExampleCheck(name="result", expected=(9.0, 9.0)),),
    )
    broken = replace(broken, explanation=replace(broken.explanation, worked_examples=(bad_example,)))
    result = store.publish(broken, source_context=context, topic=topic)

    assert result.ok is False
    current = store.published(topic.id)
    assert current is not None
    assert current.artifact.generated.artifact_digest == old.artifact.generated.artifact_digest


def test_publish_rejects_a_valid_but_unreviewed_draft(tmp_path: Path) -> None:
    topic, context = _topic_context()
    store = TeachingArtifactStore(tmp_path)
    draft = replace(_reviewed_valid_artifact(), status="draft")

    result = store.publish(draft, source_context=context, topic=topic)

    assert result.ok is False
    assert result.issues[0].code == "review_required"


def test_review_draft_is_explicit_transition(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    draft = store.save_draft(artifact, raw_reply="raw")

    reviewed = store.review_draft(artifact.topic_id, draft.revision, "teacher")

    assert reviewed.state == "reviewed"
    assert store.get(artifact.topic_id, reviewed.revision, "reviewed").artifact.status == "reviewed"
