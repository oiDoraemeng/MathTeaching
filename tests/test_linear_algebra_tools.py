from models.geometry_2d import Linear2D, Point2D
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds
from services.scene_commands import SceneCommandService
from ui.linear_algebra_tools import (
    build_matrix_grid_tool_plan,
    build_polygon_tool_plan,
    build_transform_tool_plan,
    build_vector_tool_plan,
    parse_matrix,
    parse_matrix_expression,
)


class _FakePlotter:
    def __init__(self) -> None:
        self.actors: dict[str, object] = {}
        self.meshes: dict[str, object] = {}
        self.styles: dict[str, dict[str, object]] = {}
        self.labels: dict[str, tuple[tuple[object, ...], tuple[str, ...], dict[str, object]]] = {}
        self.removed: list[str] = []

    def add_mesh(self, mesh, *, name: str, **kwargs):
        actor = object()
        self.actors[name] = actor
        self.meshes[name] = mesh
        self.styles[name] = dict(kwargs)
        return actor

    def add_point_labels(self, points, labels, *, name: str, **kwargs):
        actor = object()
        self.actors[name] = actor
        self.labels[name] = (tuple(points), tuple(labels), dict(kwargs))
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.removed.append(name)
        self.actors.pop(name, None)
        self.meshes.pop(name, None)
        self.styles.pop(name, None)
        self.labels.pop(name, None)


def _vectors() -> tuple[tuple[Linear2D, Linear2D], dict[str, Point2D]]:
    points = {
        "o": Point2D("O", 0, 0),
        "a": Point2D("A", 3, 0),
        "b": Point2D("B", 0, 4),
    }
    return (
        Linear2D("v₁", "vector", "o", "a"),
        Linear2D("v₂", "vector", "o", "b"),
    ), points


def test_parse_matrix_accepts_common_forms_and_rejects_invalid_input() -> None:
    assert parse_matrix("1,0;0,2") == ((1.0, 0.0), (0.0, 2.0))
    assert parse_matrix("[1 0; 0 2]") == ((1.0, 0.0), (0.0, 2.0))
    assert parse_matrix(
        r"\begin{pmatrix}1&0\\0&2\end{pmatrix}"
    ) == ((1.0, 0.0), (0.0, 2.0))
    assert parse_matrix(
        r"\begin{bmatrix}\frac{1}{2}&-1\\0&2.5\end{bmatrix}"
    ) == ((0.5, -1.0), (0.0, 2.5))
    assert parse_matrix("1,0,0;0,1,0") is None
    assert parse_matrix("1,0;bad,1") is None


def test_parse_matrix_expression_evaluates_a_chain_of_standard_latex_matrices() -> None:
    expression = parse_matrix_expression(
        r"A=\begin{pmatrix}1&2\\0&1\end{pmatrix}"
        r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}"
        r"\cdot\begin{pmatrix}1&1\\0&1\end{pmatrix}"
    )

    assert expression is not None
    assert expression.result == ((2.0, 8.0), (0.0, 3.0))
    assert expression.input_latex.endswith(
        r"\cdot\begin{pmatrix}1&1\\0&1\end{pmatrix}"
    )
    assert expression.result_latex == r"\begin{pmatrix}2&8\\0&3\end{pmatrix}"
    assert expression.display_latex.endswith(
        r" = \begin{pmatrix}2&8\\0&3\end{pmatrix}"
    )


def test_parse_matrix_expression_recomputes_an_outdated_displayed_result() -> None:
    expression = parse_matrix_expression(
        r"A=\begin{pmatrix}2&0\\0&1\end{pmatrix}"
        r"\cdot\begin{pmatrix}3&0\\0&1\end{pmatrix}"
        r"=\begin{pmatrix}1&0\\0&1\end{pmatrix}"
    )

    assert expression is not None
    assert expression.result == ((6.0, 0.0), (0.0, 1.0))
    assert expression.result_latex == r"\begin{pmatrix}6&0\\0&1\end{pmatrix}"


def test_parse_matrix_expression_rejects_nonstandard_forms_and_times() -> None:
    assert parse_matrix_expression("A=[1 0;0 1]") is None
    assert parse_matrix_expression(
        r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}"
        r"\times\begin{pmatrix}1&0\\0&1\end{pmatrix}"
    ) is None
    assert parse_matrix_expression(
        r"A=\begin{pmatrix}1&0\\0&1&2\end{pmatrix}"
    ) is None


def test_vector_tool_plans_keep_math_explanation_with_drawing() -> None:
    vectors, points = _vectors()
    bounds = ViewportBounds((-5, 5), (-5, 5))

    angle = build_vector_tool_plan("angle", vectors, points, bounds, "la_tool_angle_1")
    assert angle is not None
    assert [operation["op"] for operation in angle.operations] == [
        "geometry.angle_arc",
        "annotation.formula",
    ]
    assert angle.operations[1]["text"] == "θ=90.0°"

    area = build_vector_tool_plan("area", vectors, points, bounds, "la_tool_area_1")
    assert area is not None
    assert area.operations[1]["text"] == "det=12.00"


def test_vector_tool_plans_preserve_a_nonzero_vector_origin() -> None:
    points = {
        "o": Point2D("O", 2, 3),
        "a": Point2D("A", 5, 3),
        "b": Point2D("B", 2, 7),
    }
    vectors = (
        Linear2D("v₁", "vector", "o", "a"),
        Linear2D("v₂", "vector", "o", "b"),
    )
    bounds = ViewportBounds((-5, 5), (-5, 5))

    for tool in ("projection", "subspace", "area"):
        plan = build_vector_tool_plan(tool, vectors, points, bounds, f"la_tool_{tool}_1")
        assert plan is not None
        assert plan.operations[0]["origin"] == [2, 3]


def test_dependent_vectors_are_rendered_as_a_one_dimensional_subspace() -> None:
    points = {
        "o": Point2D("O", 0, 0),
        "a": Point2D("A", 2, 0),
        "b": Point2D("B", 4, 0),
    }
    vectors = (
        Linear2D("v₁", "vector", "o", "a"),
        Linear2D("v₂", "vector", "o", "b"),
    )
    plan = build_vector_tool_plan("subspace", vectors, points, ViewportBounds((-5, 5), (-5, 5)), "la_tool_subspace_1")
    assert plan is not None
    assert plan.operations[0]["basis"] == [[2, 0]]
    assert plan.operations[1]["text"] == "span(v₁)"


def test_transform_plan_uses_distinct_aliases_for_grid_and_stages() -> None:
    plan = build_transform_tool_plan(
        ((1.0, 0.0), (0.0, 2.0)),
        ((1.0, 0.0), (0.0, 1.0)),
        ViewportBounds((-3, 3), (-3, 3)),
        "la_tool_transform_1",
    )
    assert [operation["op"] for operation in plan.operations] == [
        "geometry.transformed_grid",
        "geometry.staged_transform",
        "annotation.formula",
    ]
    assert plan.operations[0]["alias"] == "la_tool_transform_1_grid"
    assert plan.operations[1]["alias"] == "la_tool_transform_1_staged"


def test_matrix_grid_tool_plan_stays_in_the_current_coordinate_plane() -> None:
    plan = build_matrix_grid_tool_plan(
        ((2.0, 1.0), (0.0, 1.0)), 5.0, "la_tool_transform"
    )

    assert [operation["op"] for operation in plan.operations] == [
        "geometry.transformed_grid"
    ]
    operation = plan.operations[0]
    assert operation["bounds"] == [-5.0, 5.0, -5.0, 5.0]
    assert operation["show_source_grid"] is False
    assert operation["show_basis"] is True


def test_matrix_grid_marks_the_transformed_basis_in_distinct_colors() -> None:
    plotter = _FakePlotter()
    controller = GeometrySceneController(plotter, ViewportBounds((-3, 3), (-3, 3)))

    controller.add_teaching_transformed_grid(
        ((2.0, 1.0), (0.5, 3.0)),
        (-2, 2, -2, 2),
        alias="la_tool_transform_grid",
        color="#2f7ebd",
        show_source_grid=False,
        show_basis=True,
    )

    grid_name = "geometry:teaching:grid:la_tool_transform_grid:transformed"
    e1_name = "geometry:teaching:grid:la_tool_transform_grid:basis:e1"
    e2_name = "geometry:teaching:grid:la_tool_transform_grid:basis:e2"
    assert plotter.styles[e1_name]["color"] != plotter.styles[grid_name]["color"]
    assert plotter.styles[e2_name]["color"] != plotter.styles[grid_name]["color"]
    assert plotter.styles[e1_name]["color"] != plotter.styles[e2_name]["color"]
    assert tuple(plotter.meshes[e1_name].points[2][:2]) == (2.0, 0.5)
    assert tuple(plotter.meshes[e2_name].points[2][:2]) == (1.0, 3.0)
    assert set(plotter.labels) == {f"{e1_name}:label", f"{e2_name}:label"}


def test_transformed_grid_can_skip_the_source_grid_overlay() -> None:
    """案例窗格只画变形后的网格，不再把灰色原始网格叠在原坐标系上。"""

    plotter = _FakePlotter()
    controller = GeometrySceneController(plotter, ViewportBounds((-3, 3), (-3, 3)))

    controller.add_teaching_transformed_grid(
        ((2.0, 0.0), (0.0, 1.0)),
        (-2, 2, -2, 2),
        alias="case_grid",
    )
    assert set(plotter.actors) == {
        "geometry:teaching:grid:case_grid:original",
        "geometry:teaching:grid:case_grid:transformed",
    }

    controller.add_teaching_transformed_grid(
        ((2.0, 0.0), (0.0, 1.0)),
        (-2, 2, -2, 2),
        alias="case_grid",
        show_source_grid=False,
    )
    assert set(plotter.actors) == {"geometry:teaching:grid:case_grid:transformed"}
    assert set(controller._teaching_actors) == {"geometry:teaching:grid:case_grid:transformed"}


def test_skipping_an_uncreated_source_grid_does_not_remove_an_unknown_actor() -> None:
    """A new case pane may omit the source grid before any actor exists."""

    plotter = _FakePlotter()
    controller = GeometrySceneController(plotter, ViewportBounds((-3, 3), (-3, 3)))

    controller.add_teaching_transformed_grid(
        ((2.0, 0.0), (0.0, 1.0)),
        (-2, 2, -2, 2),
        alias="case_grid",
        show_source_grid=False,
    )

    assert plotter.removed == []
    assert set(plotter.actors) == {"geometry:teaching:grid:case_grid:transformed"}


def test_teaching_actor_prefix_can_be_cleared_without_touching_other_actors() -> None:
    plotter = _FakePlotter()
    controller = GeometrySceneController(plotter, ViewportBounds((-3, 3), (-3, 3)))
    controller.add_teaching_transformed_grid(
        ((1.0, 0.0), (0.0, 1.0)),
        (-2, 2, -2, 2),
        alias="la_tool_transform_1_grid",
    )
    controller.add_teaching_subspace_region(
        ((1.0, 0.0),),
        (-2, 2, -2, 2),
        alias="la_tool_subspace_1",
    )
    controller.add_teaching_polygon(
        "lecture_polygon",
        ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    )

    controller.clear_teaching_prefix("la_tool_")

    assert not any("la_tool_" in name for name in plotter.actors)
    assert "geometry:teaching:polygon:lecture_polygon" in plotter.actors


def test_two_independent_basis_vectors_fill_the_visible_subspace() -> None:
    plotter = _FakePlotter()
    controller = GeometrySceneController(plotter, ViewportBounds((-3, 3), (-3, 3)))
    controller.add_teaching_subspace_region(
        ((1.0, 0.0), (0.0, 1.0)),
        (-2, 2, -3, 3),
        alias="plane",
    )

    bounds = plotter.meshes["geometry:teaching:subspace:plane"].bounds
    assert (bounds.x_min, bounds.x_max, bounds.y_min, bounds.y_max) == (-2, 2, -3, 3)


def test_all_specialized_tool_plans_pass_the_scene_command_protocol() -> None:
    vectors, points = _vectors()
    bounds = ViewportBounds((-5, 5), (-5, 5))
    plans = [
        build_vector_tool_plan(tool, vectors, points, bounds, f"la_tool_{tool}_1")
        for tool in ("angle", "projection", "subspace", "area")
    ]
    plans.extend(
        [
            build_polygon_tool_plan(tuple(points.values()), "la_tool_polygon_1"),
            build_transform_tool_plan(
                ((1.0, 0.0), (0.0, 2.0)),
                ((1.0, 0.0), (0.0, 1.0)),
                bounds,
                "la_tool_transform_1",
            ),
        ]
    )

    validator = SceneCommandService()
    for plan in plans:
        assert plan is not None
        validation = validator.validate(plan)
        assert validation.valid, validation.messages
