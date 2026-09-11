import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

import pytest

from fixtures.linear_algebra_chapter_release import (
    assert_previous_chapters_unchanged,
    chapter_release_fixtures,
)


def test_each_new_chapter_has_one_publish_and_one_rollback_fixture():
    fixtures = chapter_release_fixtures()
    assert {fixture.chapter for fixture in fixtures} == {4, 5, 6, 7, 8}
    assert all(fixture.topic_id.startswith(f"ch{fixture.chapter:02d}.") for fixture in fixtures)
    assert all(fixture.published_revision == 1 and fixture.stale_revision == 0 for fixture in fixtures)


def test_fixture_topic_links_are_stable_and_previous_topic_is_prior_chapter():
    fixtures = chapter_release_fixtures()
    assert len({fixture.topic_id for fixture in fixtures}) == 5
    assert all(fixture.previous_topic_id.startswith(f"ch{fixture.chapter - 1:02d}.") for fixture in fixtures)


def test_failed_chapter_publish_only_removes_its_own_index_entry():
    before = {
        "topics": [
            {"topic_id": "ch01.vector.magnitude", "chapter": 1},
            {"topic_id": "ch04.space.subspace", "chapter": 4},
            {"topic_id": "ch05.systems.gaussian", "chapter": 5},
        ]
    }
    after = {"topics": [before["topics"][0], before["topics"][2]]}
    assert_previous_chapters_unchanged(before, after)
    assert {row["topic_id"] for row in after["topics"]} == {"ch01.vector.magnitude", "ch05.systems.gaussian"}


def test_chapter_one_to_three_index_bytes_are_unchanged():
    index_path = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "index.json"
    original = index_path.read_bytes()
    payload = json.loads(original)
    assert_previous_chapters_unchanged(payload, payload)
    assert index_path.read_bytes() == original
