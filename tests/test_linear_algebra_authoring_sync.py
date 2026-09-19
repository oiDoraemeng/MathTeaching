from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from linear_algebra.catalog.model import SourceAnchor
from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.teaching.authoring import synchronize_topic
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore


TOPIC_ID = "ch01.ops.addition"


def _add_marker(payload):
    result = deepcopy(payload)
    summary = result["explanation"]["summary"]
    if not summary.endswith("（增量校验）"):
        result["explanation"]["summary"] = summary + "（增量校验）"
    return result


def _seed_store(tmp_path: Path) -> tuple[object, TeachingArtifactStore, LectureSourceRepository]:
    topic = catalog_registry().get_topic(TOPIC_ID)
    source = Path(__file__).parents[1] / ".agents" / "线性代数讲义.md"
    repository = LectureSourceRepository(source)
    bundled = bundled_teaching_store().published(TOPIC_ID)
    assert bundled is not None

    store = TeachingArtifactStore(tmp_path)
    initial = store.save_published(bundled.artifact)
    store.upsert_published_topic(initial)
    return topic, store, repository


def test_unchanged_refinement_performs_no_writes(tmp_path: Path) -> None:
    topic, store, repository = _seed_store(tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json"))

    result = synchronize_topic(topic, store=store, source_repository=repository)

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json"))
    assert result.status == "unchanged"
    assert result.revision == 1
    assert after == before


def test_changed_refinement_publishes_only_one_new_revision(tmp_path: Path) -> None:
    topic, store, repository = _seed_store(tmp_path)

    first = synchronize_topic(
        topic,
        store=store,
        source_repository=repository,
        refiner=_add_marker,
    )
    second = synchronize_topic(
        topic,
        store=store,
        source_repository=repository,
        refiner=_add_marker,
    )

    assert first.status == "published"
    assert first.revision == 2
    assert second.status == "unchanged"
    assert store.published(TOPIC_ID).artifact.revision == 2
    assert [item.revision for item in store.list_revisions(TOPIC_ID, "published")] == [1, 2]
    row = next(item for item in store.index_payload()["topics"] if item["topic_id"] == TOPIC_ID)
    assert row["published_revision"] == 2
    assert row["draft_revision"] == 1
    assert row["reviewed_revision"] == 1
    assert (tmp_path / "snapshots" / "ch01" / TOPIC_ID / "r2.json").is_file()


def test_changed_source_anchor_refreshes_artifact_evidence(tmp_path: Path) -> None:
    topic, store, repository = _seed_store(tmp_path)
    reanchored = replace(
        topic,
        source_path=(
            "第1章 向量与几何测量",
            "1.2 向量的线性运算",
            "1.2.2 向量减法",
        ),
        source_anchor=SourceAnchor(
            (
                "第1章 向量与几何测量",
                "1.2 向量的线性运算",
                "1.2.2 向量减法",
            ),
            4,
        ),
    )
    context = repository.context_for(reanchored)

    result = synchronize_topic(reanchored, store=store, source_repository=repository)

    assert result.status == "published"
    assert result.revision == 2
    published = store.published(TOPIC_ID).artifact
    assert published.source.source_path == context.source_path
    assert published.source.source_hash == context.source_hash
    assert all(claim.source_refs == (context.spans[0].id,) for claim in published.claims)


def test_index_write_failure_leaves_new_revision_inactive(
    tmp_path: Path, monkeypatch,
) -> None:
    topic, store, repository = _seed_store(tmp_path)

    def fail_index(*args, **kwargs):
        raise OSError("index unavailable")

    monkeypatch.setattr(store, "upsert_published_topic", fail_index)
    result = synchronize_topic(
        topic,
        store=store,
        source_repository=repository,
        refiner=_add_marker,
    )

    assert result.status == "rejected"
    assert result.issues == ("index unavailable",)
    assert store.published(TOPIC_ID).artifact.revision == 1
    assert [item.revision for item in store.list_revisions(TOPIC_ID, "published")] == [1, 2]


def test_invalid_refinement_keeps_the_index_on_the_stable_revision(tmp_path: Path) -> None:
    topic, store, repository = _seed_store(tmp_path)

    def remove_visual_evidence(payload):
        result = deepcopy(payload)
        result["visual_semantics"]["entities"] = []
        return result

    result = synchronize_topic(
        topic,
        store=store,
        source_repository=repository,
        refiner=remove_visual_evidence,
    )

    assert result.status == "rejected"
    assert result.issues
    assert store.published(TOPIC_ID).artifact.revision == 1
    assert [item.revision for item in store.list_revisions(TOPIC_ID, "published")] == [1]
    assert store.list_revisions(TOPIC_ID, "draft") == ()
    assert store.list_revisions(TOPIC_ID, "reviewed") == ()
