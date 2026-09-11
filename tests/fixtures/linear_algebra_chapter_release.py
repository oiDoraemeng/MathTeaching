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
    source_id: str
    artifact_id: str
    contract_id: str
    recipe_id: str
    snapshot_id: str
    prior_published_revision: int = 1
    prior_artifact_id: str = ""


_FIXTURES = (
    ChapterReleaseFixture(4, "ch04.space.subspace", 1, 0, "ch03.subspace.column", "source:ch04.space.subspace", "artifact:ch04.space.subspace:r1", "contract:ch04.space.subspace", "recipe:ch04.space.subspace", "snapshot:ch04.space.subspace:r1", 1, "artifact:ch04.space.subspace:r1"),
    ChapterReleaseFixture(5, "ch05.systems.gaussian", 1, 0, "ch04.space.subspace", "source:ch05.systems.gaussian", "artifact:ch05.systems.gaussian:r1", "contract:ch05.systems.gaussian", "recipe:ch05.systems.gaussian", "snapshot:ch05.systems.gaussian:r1", 1, "artifact:ch05.systems.gaussian:r1"),
    ChapterReleaseFixture(6, "ch06.least-squares.projection", 1, 0, "ch05.systems.gaussian", "source:ch06.least-squares.projection", "artifact:ch06.least-squares.projection:r1", "contract:ch06.least-squares.projection", "recipe:ch06.least-squares.projection", "snapshot:ch06.least-squares.projection:r1", 1, "artifact:ch06.least-squares.projection:r1"),
    ChapterReleaseFixture(7, "ch07.eigen.spectrum", 1, 0, "ch06.least-squares.projection", "source:ch07.eigen.spectrum", "artifact:ch07.eigen.spectrum:r1", "contract:ch07.eigen.spectrum", "recipe:ch07.eigen.spectrum", "snapshot:ch07.eigen.spectrum:r1", 1, "artifact:ch07.eigen.spectrum:r1"),
    ChapterReleaseFixture(8, "ch08.quadratic.level-set", 1, 0, "ch07.eigen.spectrum", "source:ch08.quadratic.level-set", "artifact:ch08.quadratic.level-set:r1", "contract:ch08.quadratic.level-set", "recipe:ch08.quadratic.level-set", "snapshot:ch08.quadratic.level-set:r1", 1, "artifact:ch08.quadratic.level-set:r1"),
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
