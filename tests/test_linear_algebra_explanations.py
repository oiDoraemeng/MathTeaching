from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.explanations import explanation_for


def test_every_topic_has_independent_explanation_content() -> None:
    for item in topic_entries():
        content = explanation_for(item.id)
        assert content.id == item.explanation_id
        assert content.title and content.summary and content.formula
        assert 2 <= len(content.steps) <= 12
        assert content.geometric_meaning and content.conclusion
        assert content.searchable_text

