"""二维点线几何模型与渲染器测试。"""

import unittest

from models.geometry_2d import Linear2D, Point2D, geometry_latex
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


if __name__ == "__main__":
    unittest.main()
