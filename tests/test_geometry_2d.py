"""二维点线几何模型与渲染器测试。"""

import unittest

from models.geometry_2d import Annotation2D, Linear2D, Point2D, geometry_latex
from rendering.geometry_scene import GeometrySceneController, linear_mesh
from rendering.ticks import ViewportBounds


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


class FakePlotter:
    def __init__(self) -> None:
        self.actors: dict[str, FakeActor] = {}
        self.meshes: dict[str, object] = {}
        self.mesh_kwargs: dict[str, dict[str, object]] = {}

    def add_mesh(self, mesh, *, name: str, **_kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        self.meshes[name] = mesh
        self.mesh_kwargs[name] = dict(_kwargs)
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.actors.pop(name, None)
        self.meshes.pop(name, None)
        self.mesh_kwargs.pop(name, None)


class Geometry2DTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bounds = ViewportBounds((-5.0, 5.0), (-5.0, 5.0))
        self.first = Point2D("A", -1.0, -1.0)
        self.second = Point2D("B", 1.0, 1.0)

    def test_line_and_ray_extend_to_the_current_viewport(self) -> None:
        line = linear_mesh("line", self.first, self.second, self.bounds)
        ray = linear_mesh("ray", self.first, self.second, self.bounds)

        self.assertEqual({tuple(point[:2]) for point in line.points}, {(-5.0, -5.0), (5.0, 5.0)})
        self.assertEqual({tuple(point[:2]) for point in ray.points}, {(-1.0, -1.0), (5.0, 5.0)})

    def test_vector_has_a_stem_line_and_a_filled_triangle_arrowhead(self) -> None:
        vector = linear_mesh("vector", self.first, self.second, self.bounds)

        # 一条杆线段 + 一个三角形面，共 5 个顶点。
        self.assertEqual(vector.n_points, 5)
        self.assertEqual(vector.n_lines, 1)
        self.assertEqual(vector.n_faces, 1)
        # 箭头尖端应落在终点上。
        self.assertIn((1.0, 1.0), {tuple(point[:2]) for point in vector.points})

    def test_dashed_segment_mesh_contains_multiple_dash_pieces(self) -> None:
        dashed = linear_mesh("segment", self.first, self.second, self.bounds, style="dashed")

        self.assertGreater(dashed.n_lines, 1)
        self.assertEqual(dashed.n_faces, 0)

    def test_dashed_vector_has_a_dashed_stem_and_a_filled_arrowhead(self) -> None:
        dashed = linear_mesh("vector", self.first, self.second, self.bounds, style="dashed")

        self.assertGreater(dashed.n_lines, 1)
        self.assertEqual(dashed.n_faces, 1)
        self.assertIn((1.0, 1.0), {tuple(point[:2]) for point in dashed.points})

    def test_geometry_controller_updates_actor_visibility_and_bounds(self) -> None:
        plotter = FakePlotter()
        controller = GeometrySceneController(plotter, self.bounds)
        linear = Linear2D("a", "line", self.first.id, self.second.id)

        controller.add_point(self.first)
        controller.add_point(self.second)
        controller.add_linear(linear)
        actor_name = controller.linear_actor_name(linear.id)
        # 演员为持久化对象，全程复用同一个实例以避免闪烁。
        persistent_actor = plotter.actors[actor_name]
        persistent_mesh = plotter.meshes[actor_name]

        controller.set_visible(linear.id, False)
        controller.set_bounds(ViewportBounds((-10.0, 10.0), (-10.0, 10.0)))

        # 不可见时演员保留但被隐藏，且内部对象标记为不可见。
        self.assertIn(actor_name, plotter.actors)
        self.assertFalse(plotter.actors[actor_name].visibility)
        self.assertFalse(linear.visible)
        # 恢复可见后应就地更新几何为新视口范围，而不重建演员。
        controller.set_visible(linear.id, True)
        self.assertIs(plotter.actors[actor_name], persistent_actor)
        self.assertIs(plotter.meshes[actor_name], persistent_mesh)
        self.assertTrue(plotter.actors[actor_name].visibility)
        self.assertEqual(
            {tuple(point[:2]) for point in plotter.meshes[actor_name].points},
            {(-10.0, -10.0), (10.0, 10.0)},
        )

    def test_point_render_size_stays_fixed_when_bounds_change(self) -> None:
        plotter = FakePlotter()
        controller = GeometrySceneController(plotter, self.bounds)

        controller.add_point(self.first)
        actor_name = controller.point_actor_name(self.first.id)
        first_kwargs = plotter.mesh_kwargs[actor_name]

        controller.set_bounds(ViewportBounds((-50.0, 50.0), (-50.0, 50.0)))
        second_kwargs = plotter.mesh_kwargs[actor_name]

        self.assertEqual(first_kwargs["point_size"], second_kwargs["point_size"])
        self.assertEqual(first_kwargs["point_size"], 11.0)
        self.assertTrue(second_kwargs["render_points_as_spheres"])

    def test_collinear_vector_labels_keep_their_own_colors(self) -> None:
        """共线向量（a 与 2a）的标签按各自线段的颜色绘制。

        两个向量叠在同一条射线上、标签又紧挨在一起；若共用一个颜色，读者分不清
        哪个标签属于哪个向量。
        """

        class LabelPlotter(FakePlotter):
            def __init__(self) -> None:
                super().__init__()
                self.label_calls: list[dict[str, object]] = []

            def add_point_labels(self, points, labels, *, name: str, **kwargs) -> FakeActor:
                actor = FakeActor()
                self.actors[name] = actor
                self.label_calls.append(
                    {
                        "name": name,
                        "labels": list(labels),
                        "positions": [tuple(point) for point in points],
                        "text_color": kwargs.get("text_color"),
                    }
                )
                return actor

        plotter = LabelPlotter()
        controller = GeometrySceneController(plotter, self.bounds)
        origin = Point2D("O", 0.0, 0.0)
        first_end = Point2D("A", 1.0, 0.0)
        second_end = Point2D("", 2.0, 0.0)
        for point in (origin, first_end, second_end):
            controller.add_point(point)
        controller.add_linear(
            Linear2D("a", "vector", origin.id, first_end.id, color="#2F6BFF", label="a")
        )
        doubled = Linear2D("2a", "vector", origin.id, second_end.id, color="#6B7280", label="2a")
        controller.add_linear(doubled)

        def annotation_calls() -> list[dict[str, object]]:
            return [
                call
                for call in plotter.label_calls
                if str(call["name"]).startswith("geometry:annotations")
            ]

        def annotation_actor_names() -> set[str]:
            return {name for name in plotter.actors if name.startswith("geometry:annotations")}

        def labels_of(actor_name: str) -> list[str]:
            return next(
                call["labels"] for call in reversed(annotation_calls()) if call["name"] == actor_name
            )

        by_label = {label: call for call in annotation_calls() for label in call["labels"]}
        self.assertEqual(set(by_label), {"a", "2a"})
        self.assertEqual(by_label["a"]["text_color"], "#2F6BFF")
        self.assertEqual(by_label["2a"]["text_color"], "#6B7280")
        blue_actor = str(by_label["a"]["name"])
        gray_actor = str(by_label["2a"]["name"])
        self.assertNotEqual(blue_actor, gray_actor)
        self.assertEqual(annotation_actor_names(), {blue_actor, gray_actor})

        # 标签落在线段中点下方，不再压在箭杆与轴线上。
        a_positions = next(
            call["positions"] for call in reversed(annotation_calls()) if call["name"] == blue_actor
        )
        self.assertEqual(a_positions[0][0], 0.5)
        self.assertLess(a_positions[0][1], 0.0)

        # 隐藏一个向量时，它的标签随之消失；恢复后标签回来。
        controller.set_visible(doubled.id, False)
        self.assertEqual(annotation_actor_names(), {blue_actor})
        self.assertEqual(labels_of(blue_actor), ["a"])

        controller.set_visible(doubled.id, True)
        self.assertEqual(annotation_actor_names(), {blue_actor, gray_actor})
        self.assertEqual(labels_of(gray_actor), ["2a"])

        # 移除向量同样带走它的标签演员，不留旧标签。
        controller.remove_object(doubled.id)
        self.assertEqual(annotation_actor_names(), {blue_actor})
        self.assertEqual(labels_of(blue_actor), ["a"])

    def test_vector_endpoint_never_expands_to_a_coordinate_label(self) -> None:
        plotter = FakePlotter()
        controller = GeometrySceneController(plotter, self.bounds)
        controller.add_point(self.first)
        controller.add_point(self.second)
        controller.add_linear(Linear2D("a", "vector", self.first.id, self.second.id, label="a"))

        controller.set_hover(self.first.id)

        self.assertEqual(controller._point_label_text(self.first), "A")

    def test_annotation_and_linear_label_positions_are_independently_movable(self) -> None:
        class LabelPlotter(FakePlotter):
            def __init__(self) -> None:
                super().__init__()
                self.label_calls: list[dict[str, object]] = []

            def add_point_labels(self, _points, _labels, *, name: str, **kwargs) -> FakeActor:
                actor = FakeActor()
                self.actors[name] = actor
                self.label_calls.append({"name": name, **kwargs})
                return actor

        plotter = LabelPlotter()
        controller = GeometrySceneController(plotter, self.bounds, annotation_font_size=13)
        annotation = Annotation2D("说明", "可移动", 0.0, 0.0, editable=True)
        linear = Linear2D("a", "vector", self.first.id, self.second.id, label="a")
        controller.add_point(self.first)
        controller.add_point(self.second)
        controller.add_annotation(annotation)
        controller.add_linear(linear)

        self.assertEqual(controller.hit_test_label(0.0, 0.0, 0.1), ("annotation", annotation.id))
        self.assertEqual(controller.hit_test_label(0.0, -0.2, 0.2), ("linear", linear.id))
        controller.move_annotation(annotation.id, 2.0, 3.0)
        controller.move_linear_label(linear.id, 4.0, 5.0)

        self.assertEqual((annotation.x, annotation.y), (2.0, 3.0))
        self.assertEqual(controller.linear_label_position(linear.id), (4.0, 5.0))
        self.assertEqual(plotter.label_calls[-1]["font_size"], 13)

        controller.set_hover(linear.id)
        self.assertEqual(plotter.label_calls[-1]["shape"], "rounded_rect")

    def test_teaching_angle_arc_is_one_polyline_with_all_samples(self) -> None:
        plotter = FakePlotter()
        controller = GeometrySceneController(plotter, self.bounds)

        controller.add_teaching_angle_arc(
            "theta", (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), radius=0.5
        )

        mesh = plotter.meshes["geometry:teaching:arc:theta"]
        self.assertEqual(mesh.n_lines, 1)
        self.assertEqual(mesh.n_points, 32)

    def test_geometry_latex_uses_coordinates_and_endpoint_symbols(self) -> None:
        line = Linear2D("a", "line", self.first.id, self.second.id)
        segment = Linear2D("s_1", "segment", self.first.id, self.second.id)

        self.assertEqual(geometry_latex(self.first, {self.first.id: self.first}), "A=(-1, -1)")
        self.assertEqual(
            geometry_latex(segment, {self.first.id: self.first, self.second.id: self.second}),
            r"s_1=\overline{AB}",
        )
        self.assertIn("a:", geometry_latex(line, {self.first.id: self.first, self.second.id: self.second}))

    def test_vector_addition_result_uses_visible_endpoint_names(self) -> None:
        origin = Point2D("A", 0.0, 0.0)
        generated_origin = Point2D("", 0.0, 0.0)
        endpoint = Point2D("D", 3.0, 2.0)
        result = Linear2D(
            "sum",
            "vector",
            generated_origin.id,
            endpoint.id,
            role="result",
            label="a+b",
            display_start_name="A",
            display_end_name="D",
        )

        self.assertEqual(
            geometry_latex(
                result,
                {endpoint.id: endpoint},
            ),
            r"\vec{a}+\vec{b}=\overrightarrow{AD}",
        )

    def test_geometry_latex_never_exposes_missing_endpoint_ids(self) -> None:
        vector = Linear2D("a", "vector", "internal-start-id", "internal-end-id", label="a")

        self.assertEqual(geometry_latex(vector, {}), r"\vec{a}")

    def test_vector_expression_keeps_scalar_terms_as_separate_vectors(self) -> None:
        result = Linear2D(
            "combination",
            "vector",
            self.first.id,
            self.second.id,
            label="2a-b",
        )

        self.assertEqual(
            geometry_latex(result, {self.first.id: self.first, self.second.id: self.second}),
            r"2\vec{a}-\vec{b}=\overrightarrow{AB}",
        )

    def test_vector_labels_keep_matrix_factors_outside_vector_glyphs(self) -> None:
        cases = {
            "Ax": r"A\vec{x}=\overrightarrow{AB}",
            "ABx": r"AB\vec{x}=\overrightarrow{AB}",
            "(A+B)x": r"(A+B)\vec{x}=\overrightarrow{AB}",
            "Ax+Bx": r"A\vec{x}+B\vec{x}=\overrightarrow{AB}",
        }

        for label, expected in cases.items():
            with self.subTest(label=label):
                vector = Linear2D(
                    label,
                    "vector",
                    self.first.id,
                    self.second.id,
                    label=label,
                )
                self.assertEqual(
                    geometry_latex(
                        vector,
                        {self.first.id: self.first, self.second.id: self.second},
                    ),
                    expected,
                )

    def test_numbered_vector_labels_use_subscripts(self) -> None:
        vector = Linear2D(
            "e1",
            "vector",
            self.first.id,
            self.second.id,
            label="e1",
        )

        self.assertEqual(
            geometry_latex(vector, {self.first.id: self.first, self.second.id: self.second}),
            r"\vec{e}_{1}=\overrightarrow{AB}",
        )

    def test_unlabeled_vector_uses_endpoint_not_empty_vector_equation(self) -> None:
        result = Linear2D(
            "",
            "vector",
            self.first.id,
            self.second.id,
        )

        self.assertEqual(
            geometry_latex(result, {self.first.id: self.first, self.second.id: self.second}),
            r"\overrightarrow{AB}",
        )

    def test_missing_segment_endpoint_never_emits_question_mark_placeholder(self) -> None:
        segment = Linear2D("", "segment", self.first.id, "missing-end")

        self.assertEqual(geometry_latex(segment, {self.first.id: self.first}), "")

    def test_vector_sum_labels_are_rendered_as_two_vectors(self) -> None:
        result = Linear2D(
            "sum",
            "vector",
            self.first.id,
            self.second.id,
            label="u+v",
        )

        self.assertEqual(
            geometry_latex(result, {self.first.id: self.first, self.second.id: self.second}),
            r"\vec{u}+\vec{v}=\overrightarrow{AB}",
        )

    def test_legacy_vector_sum_label_with_coordinates_is_normalized(self) -> None:
        result = Linear2D(
            "sum",
            "vector",
            self.first.id,
            self.second.id,
            label="a+b=(3,4)",
        )

        self.assertEqual(
            geometry_latex(result, {self.first.id: self.first, self.second.id: self.second}),
            r"\vec{a}+\vec{b}=\overrightarrow{AB}",
        )


if __name__ == "__main__":
    unittest.main()
