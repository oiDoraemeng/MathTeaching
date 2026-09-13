import json
from pathlib import Path

import pytest

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.teaching.compile_resources import compiled_resource_store
from services.scene_commands import SceneCommandService


NEW_TOPICS = tuple(topic.id for topic in catalog_registry().topics if topic.chapter_number >= 4)


@pytest.mark.parametrize("topic_id", NEW_TOPICS)
def test_every_new_topic_compiles_replays_and_matches_published_resource(topic_id: str) -> None:
    bundle = catalog_registry().resolve_bundle(topic_id, artifact_store=bundled_teaching_store())
    assert bundle.artifact is not None
    assert bundle.compiled is not None
    assert bundle.snapshot is not None
    validation = SceneCommandService().validate(bundle.compiled.plan)
    assert validation.valid, validation.messages
    resource = compiled_resource_store(Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "compiled").get(topic_id)
    assert resource.plan_digest == bundle.compiled.plan_digest
    assert tuple(stage["id"] for stage in resource.stages) == tuple(stage.id for stage in bundle.compiled.storyboard)


def test_integration_matrix_has_exact_new_topic_distribution() -> None:
    chapters = {chapter: sum(topic.chapter_number == chapter for topic in catalog_registry().topics) for chapter in range(4, 9)}
    assert chapters == {4: 16, 5: 8, 6: 3, 7: 6, 8: 6}
