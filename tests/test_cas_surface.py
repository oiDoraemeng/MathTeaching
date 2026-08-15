"""本地代数曲面解析与采样行为测试。"""

import unittest

from geometry.cas_surface import build_surface_mesh, parse_surface_expression
from models.surface_layer import PlotDomain


class CasExpressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.domain = PlotDomain(
            x_range=(-2.0, 2.0),
            y_range=(-2.0, 2.0),
            z_range=(-2.0, 2.0),
            explicit_resolution=20,
            implicit_resolution=20,
        )

    def test_explicit_equation_accepts_any_coordinate_as_the_dependent_axis(self) -> None:
        expression = parse_surface_expression("x = y^2 + z^2", "explicit")

        self.assertEqual(expression.kind, "explicit")
        self.assertEqual(expression.dependent_axis, "x")
        mesh = build_surface_mesh(expression, {}, self.domain)

        self.assertGreater(mesh.n_points, 0)
        self.assertAlmostEqual(float(mesh.points[0, 0]), float(mesh.points[0, 1] ** 2 + mesh.points[0, 2] ** 2), places=5)

    def test_parametric_surface_accepts_formula_and_parameter_ranges_in_one_line(self) -> None:
        expression = parse_surface_expression(
            "(u*cos(v), u*sin(v), v); u=[0, 1], v=[-1, 1]",
            "parametric",
        )

        self.assertEqual(expression.kind, "parametric")
        self.assertEqual(expression.parameter_variables, ("u", "v"))
        mesh = build_surface_mesh(expression, {}, self.domain)

        self.assertGreater(mesh.n_points, 0)
        self.assertGreater(mesh.n_cells, 0)
        self.assertLessEqual(float(mesh.points[:, 2].max()), 1.0)
        self.assertGreaterEqual(float(mesh.points[:, 2].min()), -1.0)

    def test_linear_implicit_equation_is_meshed_as_a_rectangular_plane(self) -> None:
        expression = parse_surface_expression("0 = x + y + z", "implicit")

        mesh = build_surface_mesh(expression, {}, self.domain)

        self.assertEqual(mesh.n_cells, (self.domain.explicit_resolution - 1) ** 2)
        self.assertTrue(((mesh.points[:, 0] + mesh.points[:, 1] + mesh.points[:, 2]) ** 2 < 1e-10).all())

    def test_linear_explicit_equation_is_meshed_as_a_rectangular_plane_without_clipped_edges(self) -> None:
        expression = parse_surface_expression("z = x + y", "explicit")

        mesh = build_surface_mesh(expression, {}, self.domain)

        self.assertEqual(mesh.n_points, self.domain.explicit_resolution**2)
        self.assertEqual(mesh.n_cells, (self.domain.explicit_resolution - 1) ** 2)
        self.assertTrue(((mesh.points[:, 2] - mesh.points[:, 0] - mesh.points[:, 1]) ** 2 < 1e-10).all())

    def test_oblique_plane_keeps_four_straight_parameter_boundaries(self) -> None:
        expression = parse_surface_expression("0 = x + y + z", "implicit")

        mesh = build_surface_mesh(expression, {}, self.domain)
        boundary = mesh.extract_feature_edges(
            boundary_edges=True,
            feature_edges=False,
            manifold_edges=False,
            non_manifold_edges=False,
        )

        # 采样得到的矩形平面片有四条边，每条边包含 resolution - 1 条线段。
        self.assertEqual(boundary.n_cells, 4 * (self.domain.explicit_resolution - 1))
        self.assertEqual(boundary.n_points, 4 * (self.domain.explicit_resolution - 1))


if __name__ == "__main__":
    unittest.main()
