from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.explanations import explanation_for


def test_every_topic_has_independent_explanation_content() -> None:
    for item in topic_entries():
        content = explanation_for(item.id)
        assert content.id == item.explanation_id
        assert content.title and content.summary and content.formula
        assert 2 <= len(content.steps) <= 12
        # geometric_meaning 和 conclusion 视讲义是否提供对应小节而定：
        # 讲义 1.1.1 只有定义/记法/约定/模与例，没有这两小节，不应强制要求。
        assert content.searchable_text

