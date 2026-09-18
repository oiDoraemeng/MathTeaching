from linear_algebra.catalog import topic_entries
from linear_algebra.explanations import explanation_for


def test_all_chapter_4_to_8_topics_have_grounded_explanations():
    topics = [topic for topic in topic_entries() if 4 <= topic.chapter_number <= 8]
    assert len(topics) == 37
    for topic in topics:
        content = explanation_for(topic.id)
        assert content.id == f"explain.{topic.id}"
        assert all((getattr(content, field) or "").strip() for field in ("title", "summary", "formula", "geometric_meaning", "conclusion"))
        assert len(content.steps) >= 2
        assert len(content.searchable_text) >= 4
        assert any(char in content.formula for char in "=\\")


def test_unknown_chapter_topic_is_rejected():
    try:
        explanation_for("ch08.unknown")
    except KeyError as error:
        assert "ch08.unknown" in str(error)
    else:
        raise AssertionError("unknown topic was accepted")
