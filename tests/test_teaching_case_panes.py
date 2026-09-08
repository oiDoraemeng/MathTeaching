from types import SimpleNamespace

import pytest

from services.scene_commands import CommandPlan
from ui.teaching_case_panes import case_pane_layout, case_pane_placement, case_plan


@pytest.mark.parametrize("count, expected", [(1, (1, 1)), (2, (1, 2)), (3, (2, 2)), (4, (2, 2))])
def test_case_pane_layout_is_bounded(count, expected):
    assert case_pane_layout(count) == expected


def test_case_pane_layout_rejects_other_counts():
    with pytest.raises(ValueError):
        case_pane_layout(5)


def test_three_case_panes_use_one_left_pane_and_two_stacked_right_panes():
    assert [case_pane_placement(3, index) for index in range(3)] == [
        (0, 0, 2, 1),
        (0, 1, 1, 1),
        (1, 1, 1, 1),
    ]


def test_case_plan_filters_stage_aliases_and_capability_polygon():
    compiled = SimpleNamespace(
        topic_id="ch01.ops.addition",
        plan=CommandPlan(
            scene="2d",
            operations=(
                {"op": "point.upsert", "alias": "sem__a", "coordinates": [0, 0], "name": "a"},
                {"op": "geometry.polygon", "alias": "cap__polygon", "vertices": [[0, 0], [1, 0], [0, 1]]},
                {"op": "geometry.polygon", "alias": "sem__addition_triangle", "vertices": [[0, 0], [1, 0], [1, 1]]},
                {"op": "geometry.polygon", "alias": "sem__addition_parallelogram", "vertices": [[0, 0], [1, 0], [2, 1], [1, 1]]},
            ),
        ),
        storyboard=(
            SimpleNamespace(id="triangle", visible_aliases=("sem__a", "sem__addition_triangle")),
            SimpleNamespace(id="parallelogram", visible_aliases=("sem__a", "sem__addition_parallelogram")),
        ),
    )
    plan = case_plan(compiled, "triangle")
    aliases = {operation.get("alias") for operation in plan.operations}
    assert "sem__a" in aliases
    assert "sem__addition_triangle" in aliases
    assert "sem__addition_parallelogram" not in aliases
    assert "cap__polygon" not in aliases
