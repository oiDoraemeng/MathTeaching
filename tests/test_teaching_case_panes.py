from pathlib import Path
from types import SimpleNamespace

import pytest
import ui.teaching_case_panes as teaching_case_panes

from linear_algebra.registry import catalog_registry, runtime_teaching_store
from linear_algebra.teaching.source import LectureSourceRepository
from services.scene_commands import CommandPlan
from models.geometry_2d import Annotation2D
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds
from ui.teaching_case_panes import (
    _apply_planned_view_fit,
    case_pane_layout,
    case_pane_placement,
    case_plan,
)
from ui.scene_pane_widget import PaneChrome
from ui.scene_pane_manager import ScenePaneManager
from ui.teaching_case_panes import TeachingCasePane


@pytest.mark.parametrize("count, expected", [(1, (1, 1)), (2, (1, 2)), (3, (2, 2)), (4, (2, 2))])
def test_case_pane_layout_is_bounded(count, expected):
    assert case_pane_layout(count) == expected


def test_case_pane_layout_rejects_other_counts():
    with pytest.raises(ValueError):
        case_pane_layout(5)


def test_vector_addition_uses_shared_plan_bounds_at_the_pane_aspect_ratio():
    plotter = SimpleNamespace(
        interactor=SimpleNamespace(width=lambda: 400, height=lambda: 600),
        camera=SimpleNamespace(focal_point=(0.0, 0.0, 0.0), parallel_scale=6.5),
    )

    applied = _apply_planned_view_fit(
        plotter,
        ({"op": "view.fit", "padding": 1.15, "bounds": [0.0, 4.0, 0.0, 3.0]},),
    )

    assert applied is True
    assert plotter.camera.focal_point == (2.0, 1.5, 0.0)
    assert plotter.camera.parallel_scale == pytest.approx(3.45)


def test_vector_addition_first_pane_uses_the_same_bounds_without_sum_geometry():
    compiled = catalog_registry().resolve_bundle(
        "ch01.ops.addition",
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled

    first = case_plan(compiled, "stage.flow.objects")
    second = case_plan(compiled, "stage.flow.parallelogram")
    first_fit = next(operation for operation in first.operations if operation.get("op") == "view.fit")
    second_fit = next(operation for operation in second.operations if operation.get("op") == "view.fit")

    assert first_fit == second_fit == {
        "op": "view.fit",
        "padding": 1.15,
        "bounds": [0.0, 4.0, 0.0, 3.0],
    }
    first_aliases = {
        str(operation["alias"])
        for operation in first.operations
        if operation.get("alias")
    }
    assert first_aliases == {
        "sem__flow_a__origin",
        "sem__flow_a__end",
        "sem__flow_a",
        "sem__flow_b__origin",
        "sem__flow_b__end",
        "sem__flow_b",
    }
    assert [operation.get("op") for operation in first.operations] == [
        "scene.set_mode",
        "point.upsert",
        "point.upsert",
        "linear.upsert",
        "point.upsert",
        "point.upsert",
        "linear.upsert",
        "view.fit",
    ]
    assert not any(
        operation.get("op") in {"geometry.polygon", "geometry.vector_addition"}
        for operation in first.operations
    )
    assert not any(
        "flow_sum" in str(operation.get("alias", ""))
        or "addition" in str(operation.get("alias", ""))
        for operation in first.operations
    )


def test_basis_definition_case_panes_use_the_shared_wide_view():
    compiled = catalog_registry().resolve_bundle(
        "ch04.basis.definition",
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled

    fits = [
        next(operation for operation in case_plan(compiled, stage_id).operations if operation.get("op") == "view.fit")
        for stage_id in (
            "stage.ch04.basis.definition.standard",
            "stage.ch04.basis.definition.oblique",
        )
    ]

    assert fits[0] == fits[1] == {
        "op": "view.fit",
        "padding": 1.15,
        "bounds": [-5.0, 5.0, -5.0, 5.0],
    }


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


def test_case_label_drag_persists_its_annotation_position():
    class FakeInteractor:
        cursor = None

        @staticmethod
        def width() -> int:
            return 100

        @staticmethod
        def height() -> int:
            return 100

        def setCursor(self, cursor):
            self.cursor = cursor

    class FakePlotter:
        def __init__(self) -> None:
            self.interactor = FakeInteractor()
            self.camera = SimpleNamespace(focal_point=(0.0, 0.0, 0.0), parallel_scale=5.0)
            self.render_count = 0

        def remove_actor(self, *_args, **_kwargs) -> None:
            pass

        def render(self) -> None:
            self.render_count += 1

    class MouseEvent:
        def __init__(self, x: float, y: float) -> None:
            self._position = SimpleNamespace(x=lambda: x, y=lambda: y)
            self.accepted = False

        @staticmethod
        def button():
            from PySide6.QtCore import Qt
            return Qt.MouseButton.LeftButton

        def position(self):
            return self._position

        def accept(self) -> None:
            self.accepted = True

    manager = ScenePaneManager()
    pane = TeachingCasePane.__new__(TeachingCasePane)
    pane.plotter = FakePlotter()
    pane.bounds = ViewportBounds((-5.0, 5.0), (-5.0, 5.0))
    pane.geometry = GeometrySceneController(pane.plotter, pane.bounds, annotation_font_size=13)
    pane.pane_manager = manager
    pane.pane_id = manager.active_pane_id
    pane._dragging_label = None
    pane._annotation_positions = {}
    pane._linear_label_offsets = {}
    annotation = Annotation2D("案例标签", "说明", 0.0, 0.0, agent_alias="case_label", editable=True)
    pane.geometry.add_annotation(annotation)

    assert pane._begin_label_drag(MouseEvent(50.0, 50.0))
    assert pane._handle_label_mouse_move(MouseEvent(70.0, 40.0))
    assert pane._finish_label_drag(MouseEvent(70.0, 40.0))

    assert (annotation.x, annotation.y) == (2.0, 1.0)
    assert manager.pane(pane.pane_id).scene_2d["label_positions"] == {
        "annotations": {"case_label": [2.0, 1.0]},
        "linears": {},
    }


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
            [-2.0, 2.0, -2.0, 2.0],
            (
                # 第一步只画标准基向量，不画网格。
                (None, None),
                ([[2.0, 0.0], [0.0, 1.0]], r"$A=\left[\genfrac{}{}{0}{}{2\quad 0}{0\quad 1}\right]$"),
                ([[0.0, -1.0], [1.0, 0.0]], r"$R=\left[\genfrac{}{}{0}{}{0\quad -1}{1\quad \ 0}\right]$"),
                ([[2.0, 1.0], [1.0, 2.0]], r"$A=\left[\genfrac{}{}{0}{}{2\quad 1}{1\quad 2}\right]$"),
            ),
        ),
        (
            "ch02.matrix.basis",
            [-5.0, 5.0, -5.0, 5.0],
            (
                # 第一步：标准基下的旋转与同一输入向量。
                ([[0.0, -1.0], [1.0, 0.0]], r"$A=\left[\genfrac{}{}{0}{}{0\quad -1}{1\quad \ 0}\right]$"),
                # 第二步：换一组基 b1=(1,0)、b2=(1,1)，同一个旋转的矩阵变成 B。
                ([[-1.0, -2.0], [1.0, 1.0]], r"$B=\left[\genfrac{}{}{0}{}{-1\quad -2}{\ 1\quad \ 1}\right]$"),
            ),
        ),
    ],
)
def test_matrix_vector_case_panes_use_the_matrix_transform_feature(topic_id, grid_bounds, cases):
    """2.5、2.7 的矩阵案例窗格用软件已有的矩阵变换功能：网格、样本点的像与矩阵标注。"""

    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled

    assert len(compiled.storyboard) == len(cases)
    for stage, (matrix, label) in zip(compiled.storyboard, cases):
        operations = case_plan(compiled, stage.id).operations
        grid_ops = [op for op in operations if op.get("op") == "geometry.transformed_grid"]
        coordinate_ops = [op for op in operations if op.get("op") == "linear_algebra.coordinate_transform"]
        staged_ops = [op for op in operations if op.get("op") == "geometry.staged_transform"]
        label_ops = [op for op in operations if op.get("op") == "annotation.upsert"]
        if topic_id == "ch02.matrix.basis":
            assert not coordinate_ops
            assert not staged_ops
            assert [op["matrix"] for op in grid_ops] == [matrix]
            assert [op["bounds"] for op in grid_ops] == [grid_bounds]
            assert grid_ops[0]["show_source_grid"] is False
            assert grid_ops[0]["show_basis"] is True
            assert [op["text"] for op in label_ops] == [label]
            continue
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


def test_matrix_powers_case_panes_reuse_toolbar_grids_with_one_shared_scale() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch02.matrix.powers",
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled
    expected = (
        (
            [[1.0, 2.0], [3.0, 4.0]],
            "#2F6BFF",
            r"$A=\left[\genfrac{}{}{0}{}{1\quad 2}{3\quad 4}\right]$",
        ),
        (
            [[7.0, 10.0], [15.0, 22.0]],
            "#F08A24",
            r"$A^{2}=\left[\genfrac{}{}{0}{}{\ 7\quad 10}{15\quad 22}\right]$",
        ),
    )

    assert len(compiled.storyboard) == 2
    for stage, (matrix, color, label) in zip(compiled.storyboard, expected):
        operations = case_plan(compiled, stage.id).operations
        grids = [op for op in operations if op.get("op") == "geometry.transformed_grid"]
        labels = [op for op in operations if op.get("op") == "annotation.upsert"]
        fits = [op for op in operations if op.get("op") == "view.fit"]

        assert len(grids) == 1
        assert grids[0]["matrix"] == matrix
        assert grids[0]["bounds"] == [-1.0, 1.0, -1.0, 1.0]
        assert grids[0]["show_source_grid"] is False
        assert grids[0]["show_basis"] is True
        assert grids[0]["color"] == color
        assert [op["text"] for op in labels] == [label]
        assert fits == [
            {"op": "view.fit", "padding": 1.15, "bounds": [-18.0, 18.0, -38.0, 38.0]}
        ]
        assert not any("invariant:" in str(op.get("text", "")) for op in operations)


@pytest.mark.parametrize(
    "topic_id",
    (
        "ch03.det.basic-properties",
        "ch03.det.multiplicativity",
        "ch03.det.transpose",
    ),
)
def test_determinant_core_defers_grids_to_the_matrix_workspace(
    monkeypatch,
    topic_id: str,
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled
    calls: list[tuple[object, float, str]] = []
    original = teaching_case_panes.build_matrix_grid_tool_plan

    def capture(matrix, grid_range, alias):
        calls.append((matrix, grid_range, alias))
        return original(matrix, grid_range, alias)

    monkeypatch.setattr(teaching_case_panes, "build_matrix_grid_tool_plan", capture)
    for stage in compiled.storyboard:
        operations = case_plan(compiled, stage.id).operations
        assert not any(
            operation.get("op") == "geometry.transformed_grid"
            for operation in operations
        )
        assert any(operation.get("op") == "view.fit" for operation in operations)

    assert calls == []


@pytest.mark.parametrize(
    "topic_id, expected_bounds",
    [
        ("ch02.matrix.additive-distributivity", [-3.0, 3.0, -3.0, 3.0]),
        ("ch02.matrix.transformed-grid", [-2.0, 2.0, -2.0, 2.0]),
        ("ch02.matrix.composition", [-3.0, 3.0, -3.0, 3.0]),
        ("ch02.matrix.basis", [-5.0, 5.0, -5.0, 5.0]),
    ],
)
def test_chapter_two_matrix_cases_share_toolbar_grid_contract(
    topic_id: str,
    expected_bounds: list[float],
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled
    grids = []
    fits = []
    for stage in compiled.storyboard:
        operations = case_plan(compiled, stage.id).operations
        grids.extend(
            operation
            for operation in operations
            if operation.get("op") == "geometry.transformed_grid"
        )
        fits.extend(
            operation
            for operation in operations
            if operation.get("op") == "view.fit"
        )

    assert grids
    assert all(operation["show_source_grid"] is False for operation in grids)
    assert all(operation["show_basis"] is True for operation in grids)
    assert all(operation["color"] == "#2f7ebd" for operation in grids)
    assert all(operation["bounds"] == expected_bounds for operation in grids)
    assert fits
    assert all(operation["bounds"] == expected_bounds for operation in fits)
    assert all(operation["padding"] == 1.15 for operation in fits)


def test_chapter_four_matrix_cases_reuse_toolbar_only_for_linear_witnesses() -> None:
    basis = catalog_registry().resolve_bundle(
        "ch04.basis.definition",
        artifact_store=runtime_teaching_store(),
    ).compiled
    expected_basis = (
        [[1.0, 0.0], [0.0, 1.0]],
        [[1.0, 1.0], [1.0, -1.0]],
    )
    for stage, expected_matrix in zip(basis.storyboard, expected_basis):
        operations = case_plan(basis, stage.id).operations
        grids = [
            operation
            for operation in operations
            if operation.get("op") == "geometry.transformed_grid"
        ]
        assert len(grids) == 1
        assert grids[0]["matrix"] == expected_matrix
        assert grids[0]["bounds"] == [-5.0, 5.0, -5.0, 5.0]
        assert grids[0]["show_source_grid"] is False
        assert grids[0]["show_basis"] is True
        assert grids[0]["color"] == "#2f7ebd"

    linear_map = catalog_registry().resolve_bundle(
        "ch04.linear-map.definition",
        artifact_store=runtime_teaching_store(),
    ).compiled
    stretch = case_plan(linear_map, linear_map.storyboard[0].id).operations
    translation = case_plan(linear_map, linear_map.storyboard[1].id).operations
    stretch_grid = next(
        operation
        for operation in stretch
        if operation.get("op") == "geometry.transformed_grid"
    )
    translation_grid = next(
        operation
        for operation in translation
        if operation.get("op") == "geometry.transformed_grid"
    )
    assert stretch_grid["matrix"] == [[2.0, 0.0], [0.0, 1.0]]
    assert stretch_grid["show_source_grid"] is False
    assert stretch_grid["show_basis"] is True
    assert translation_grid["origin"] == [1, 0]
    assert translation_grid.get("show_basis", False) is False


@pytest.mark.parametrize(
    "topic_id",
    (
        "ch06.basis-change.coordinates",
        "ch06.similarity-transform",
    ),
)
def test_chapter_six_matrix_cases_use_default_five_and_fit_transformed_grid(
    topic_id: str,
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled

    for stage in compiled.storyboard:
        operations = case_plan(compiled, stage.id).operations
        grids = [
            operation
            for operation in operations
            if operation.get("op") == "geometry.transformed_grid"
        ]
        fit = next(operation for operation in operations if operation.get("op") == "view.fit")

        assert len(grids) == 1
        assert grids[0]["bounds"] == [-5.0, 5.0, -5.0, 5.0]
        assert fit["bounds"] == [-8.0, 8.0, -8.0, 8.0]
        assert fit["padding"] == 1.0
