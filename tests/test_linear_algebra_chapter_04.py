from linear_algebra.catalog.chapter_04 import TOPICS
from linear_algebra.visualizations.chapter_04 import RECIPES
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService

def test_chapter_four_has_16_complete_topic_recipes_and_validated_plans():
    assert len(TOPICS) == len(RECIPES) == 16
    for recipe in RECIPES:
        plan = recipe.builder(RenderContext.default(recipe.id))
        assert SceneCommandService().validate(plan).valid
        assert any(operation["op"].startswith("geometry.") for operation in plan.operations)
