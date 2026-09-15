from pathlib import Path
from types import SimpleNamespace

import pytest

from linear_algebra.registry import catalog_registry, runtime_teaching_store
from linear_algebra.teaching.source import LectureSourceRepository
from services.scene_commands import CommandPlan
from ui.teaching_case_panes import case_pane_layout, case_pane_placement, case_plan
from ui.scene_pane_widget import PaneChrome
from ui.teaching_case_panes import TeachingCasePane


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


def test_case_pane_uses_shared_pane_chrome():
    """Case viewports keep the shared title/control chrome contract."""
    assert issubclass(TeachingCasePane, PaneChrome)


def test_case_plan_drops_capability_evidence_from_every_step():
    """能力证据（cap__*）不进案例窗格。

    向量减法声明 projection_2d，编译器补出的投影残差正好从 B 连到 A；若不过滤，
    第一步窗格也会出现把 A、B 连起来的线段。
    """

    compiled = catalog_registry().resolve_bundle(
        "ch01.ops.subtraction",
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled

    operands = case_plan(compiled, "stage.subtraction.operands")
    assert {
        str(operation["alias"]) for operation in operands.operations if operation.get("alias")
    } == {
        "sem__a__origin",
        "sem__a__end",
        "sem__a",
        "sem__b__origin",
        "sem__b__end",
        "sem__b",
    }
    assert not any(
        str(value).startswith("cap__")
        for operation in operands.operations
        for value in operation.values()
        if isinstance(value, str)
    )

    difference = case_plan(compiled, "stage.subtraction.difference")
    aliases = {
        str(operation["alias"]) for operation in difference.operations if operation.get("alias")
    }
    assert "sem__rel.subtraction.endpoints" in aliases
    assert not any(alias.startswith("cap__") for alias in aliases)


@pytest.mark.parametrize(
    "topic_id, grid_bounds, cases",
    [
        (
            "ch02.matrix.transformed-grid",
            [-12.0, 12.0, -12.0, 12.0],
            (
                ([[1.0, 0.0], [0.0, 1.0]], None),
                ([[2.0, 1.0], [1.0, 2.0]], "A=[[2,1],[1,2]]"),
                # 第三步只画输入与它的像：变形网格已经在第二步给出。
                (None, None),
            ),
        ),
        (
            "ch02.matrix.stretch-rotate-scale",
            [-12.0, 12.0, -12.0, 12.0],
            (
                ([[1.0, 0.0], [0.0, 1.0]], None),
                ([[2.0, 0.0], [0.0, 1.0]], "A=[[2,0],[0,1]]"),
                ([[0.0, -1.0], [1.0, 0.0]], "R=[[0,-1],[1,0]]"),
                ([[0.0, -1.0], [2.0, 0.0]], "B=[[0,-1],[2,0]]"),
            ),
        ),
    ],
)
def test_matrix_vector_case_panes_use_the_matrix_transform_feature(topic_id, grid_bounds, cases):
    """2.5 的矩阵案例窗格用软件已有的矩阵变换功能：网格、样本点的像与矩阵标注。"""

    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled

    assert len(compiled.storyboard) == len(cases)
    for stage, (matrix, label) in zip(compiled.storyboard, cases):
        operations = case_plan(compiled, stage.id).operations
        grid_ops = [op for op in operations if op.get("op") == "geometry.transformed_grid"]
        staged_ops = [op for op in operations if op.get("op") == "geometry.staged_transform"]
        label_ops = [op for op in operations if op.get("op") == "annotation.upsert"]
        if matrix is None:
            assert (grid_ops, staged_ops, label_ops) == ([], [], [])
            continue
        assert [op["matrix"] for op in grid_ops] == [matrix]
        # 取样范围远大于窗格视野：网格铺满窗格并由视口裁切，而不是一小块悬浮网格。
        assert [op["bounds"] for op in grid_ops] == [grid_bounds]
        # 样本点取标准基：它们在变换后的位置正是讲义所说的两列。
        assert [op["matrices"] for op in staged_ops] == [[matrix]]
        assert [op["points"] for op in staged_ops] == [[[1.0, 0.0], [0.0, 1.0]]]
        assert [op["text"] for op in label_ops] == ([] if label is None else [label])
