from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService


def test_every_topic_has_a_recipe_that_validates() -> None:
    validator = SceneCommandService()
    for topic in topic_entries():
        recipe = recipe_for(topic.visualization_id)
        first = recipe.builder(RenderContext.default(topic.id))
        second = recipe.builder(RenderContext.default(topic.id))
        assert first == second
        assert first.operations and first.operations[-1]["op"] == "view.fit"
        aliases = [str(operation["alias"]) for operation in first.operations if "alias" in operation]
        assert len(aliases) == len(set(aliases)), (topic.id, aliases)
        result = validator.validate(first)
        assert result.valid, (topic.id, result.messages)


def test_3d_topics_use_3d_scene() -> None:
    for topic in topic_entries():
        plan = recipe_for(topic.visualization_id).builder(RenderContext.default(topic.id))
        operation_names = {str(operation["op"]) for operation in plan.operations}
        if any(name.startswith("linear3d") or name.startswith("plane3d") for name in operation_names):
            assert plan.scene == "3d"
