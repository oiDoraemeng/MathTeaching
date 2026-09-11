"""Small deterministic chapter publish/rollback acceptance fixtures."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ChapterReleaseFixture:
    chapter: int
    topic_id: str
    published_revision: int
    stale_revision: int
    previous_topic_id: str


_FIXTURES = (
    ChapterReleaseFixture(4, "ch04.space.subspace", 1, 0, "ch03.subspace.column"),
    ChapterReleaseFixture(5, "ch05.systems.gaussian", 1, 0, "ch04.space.subspace"),
    ChapterReleaseFixture(6, "ch06.least-squares.projection", 1, 0, "ch05.systems.gaussian"),
    ChapterReleaseFixture(7, "ch07.eigen.spectrum", 1, 0, "ch06.least-squares.projection"),
    ChapterReleaseFixture(8, "ch08.quadratic.level-set", 1, 0, "ch07.eigen.spectrum"),
)


def chapter_release_fixtures() -> tuple[ChapterReleaseFixture, ...]:
    return _FIXTURES


def assert_previous_chapters_unchanged(before: Mapping[str, object], after: Mapping[str, object]) -> None:
    """Assert chapter 1-3 rows and their serialized values are unchanged."""
    def prior_rows(payload: Mapping[str, object]) -> dict[str, object]:
        rows = payload.get("topics", ())
        return {
            str(row["topic_id"]): row
            for row in rows
            if isinstance(row, Mapping) and str(row.get("topic_id", "")).startswith(("ch01.", "ch02.", "ch03."))
        }

    before_rows = prior_rows(before)
    after_rows = prior_rows(after)
    if before_rows != after_rows:
        raise AssertionError("chapter 1-3 index entries changed")


__all__ = ["ChapterReleaseFixture", "chapter_release_fixtures", "assert_previous_chapters_unchanged"]
