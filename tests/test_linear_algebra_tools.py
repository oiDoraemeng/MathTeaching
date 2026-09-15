from models.geometry_2d import Linear2D, Point2D
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds
from services.scene_commands import SceneCommandService
from ui.linear_algebra_tools import (
    build_polygon_tool_plan,
    build_transform_tool_plan,
    build_vector_tool_plan,
    parse_matrix,
)


class _FakePlotter:
    def __init__(self) -> None:
        self.actors: dict[str, object] = {}
        self.meshes: dict[str, object] = {}
        self.removed: list[str] = []

    def add_mesh(self, mesh, *, name: str, **_kwargs):
        actor = object()
        self.actors[name] = actor
        self.meshes[name] = mesh
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.removed.append(name)
        self.actors.pop(name, None)
        self.meshes.pop(name, None)


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
    assert parse_matrix("1,0,0;0,1,0") is None
    assert parse_matrix("1,0;bad,1") is None


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
