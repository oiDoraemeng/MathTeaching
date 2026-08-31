from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.validation import validate_lecture_source


def test_repository_lecture_source_matches_all_topic_anchors() -> None:
    source = Path(__file__).parents[1] / ".agents" / "线性代数讲义.md"
    errors = validate_lecture_source(source, catalog_registry().topics)
    assert errors == ()
