import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingProfileRecord
from linear_algebra.teaching.profiles import TeachingLevel, profile_for, validate_profile_coverage


def test_every_topic_has_a_teaching_profile() -> None:
    assert validate_profile_coverage() == ()
    assert {topic.id for topic in topic_entries()} == {
        topic.id for topic in topic_entries() if profile_for(topic.id)
    }


def test_bridge_and_analogy_profiles_are_explicit() -> None:
    assert profile_for("ch02.matrix.composition").minimum_level >= TeachingLevel.EXPLAIN
    analogy = profile_for("ch03.det.high-dimensional-volume")
    assert analogy.minimum_level == TeachingLevel.EXPLAIN
    assert analogy.requires_analogy_boundary is True


def test_profile_serializes_to_the_stable_artifact_record() -> None:
    profile = profile_for("ch02.matrix.composition")
    record = profile.to_record()

    assert isinstance(record, TeachingProfileRecord)
    assert record.minimum_level == TeachingLevel.TRANSFER
    assert "connections" in record.required_sections
    assert profile.to_dict() == {
        "minimum_level": 4,
        "required_sections": [
            "definition",
            "formula",
            "derivation",
            "worked_examples",
            "geometric_meaning",
            "pitfalls",
            "connections",
        ],
        "requires_analogy_boundary": False,
    }


def test_unknown_topic_has_no_implicit_profile() -> None:
    with pytest.raises(KeyError, match="unknown.topic"):
        profile_for("unknown.topic")
