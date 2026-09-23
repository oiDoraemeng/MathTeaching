import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingProfileRecord
from linear_algebra.teaching.profiles import TeachingLevel, profile_for, validate_profile_coverage


def test_every_topic_has_a_teaching_profile() -> None:
    assert validate_profile_coverage() == ()
    assert {topic.id for topic in topic_entries()} == {
        topic.id for topic in topic_entries() if profile_for(topic.id)
    }


def test_matrix_composition_profile_matches_its_two_display_sections() -> None:
    profile = profile_for("ch02.matrix.composition")
    assert profile.minimum_level == TeachingLevel.CALCULATE
    assert profile.required_sections == ("definition", "worked_examples")


def test_matrix_powers_profile_matches_its_two_display_sections() -> None:
    profile = profile_for("ch02.matrix.powers")
    assert profile.minimum_level == TeachingLevel.CALCULATE
    assert profile.required_sections == ("definition", "worked_examples")


def test_profile_serializes_to_the_stable_artifact_record() -> None:
    profile = profile_for("ch02.matrix.composition")
    record = profile.to_record()

    assert isinstance(record, TeachingProfileRecord)
    assert record.minimum_level == TeachingLevel.CALCULATE
    assert "connections" not in record.required_sections
    assert profile.to_dict() == {
        "minimum_level": 2,
        "required_sections": [
            "definition",
            "worked_examples",
        ],
        "requires_analogy_boundary": False,
    }


def test_unknown_topic_has_no_implicit_profile() -> None:
    with pytest.raises(KeyError, match="unknown.topic"):
        profile_for("unknown.topic")
