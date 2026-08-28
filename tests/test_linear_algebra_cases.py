from models.linear_algebra_cases import linear_algebra_case, linear_algebra_cases
from services.scene_commands import SceneCommandService


def test_vector_case_catalog_has_five_unique_entries() -> None:
    cases = linear_algebra_cases()
    assert [item.name for item in cases] == ["向量加法", "向量减法", "向量数乘", "向量内积", "向量外积"]
    assert len({item.id for item in cases}) == 5
    assert all(item.category == "向量" for item in cases)


def test_each_case_has_explanation_and_valid_2d_plan() -> None:
    validator = SceneCommandService()
    for item in linear_algebra_cases():
        assert item.formula and item.steps and item.conclusion
        validation = validator.validate(item.plan)
        assert validation.valid, validation.messages
        assert item.plan.scene == "2d"


def test_unknown_case_returns_none() -> None:
    assert linear_algebra_case("missing") is None
