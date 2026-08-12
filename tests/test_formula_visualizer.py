"""Tests for the independent SymPy-to-PyVista FormulaVisualizer bridge."""

import unittest

import sympy as sp

from MathInputWidget.api import FormulaVisualizer
from models.surface_layer import PlotDomain


class FormulaVisualizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.domain = PlotDomain(
            x_range=(-2.0, 2.0),
            y_range=(-2.0, 2.0),
            z_range=(-2.0, 2.0),
            explicit_resolution=12,
            implicit_resolution=12,
        )

    def test_coordinate_equality_builds_the_existing_rectangular_plane_mesh(self) -> None:
        x, y, z = sp.symbols("x y z", real=True)

        mesh = FormulaVisualizer().build_mesh(sp.Eq(z, x + y), self.domain)

        self.assertEqual(mesh.n_cells, (self.domain.explicit_resolution - 1) ** 2)
        self.assertTrue(((mesh.points[:, 2] - mesh.points[:, 0] - mesh.points[:, 1]) ** 2 < 1e-10).all())

    def test_implicit_expression_builds_a_surface_mesh(self) -> None:
        x, y, z = sp.symbols("x y z", real=True)

        mesh = FormulaVisualizer().build_mesh(x**2 + y**2 + z**2 - 1, self.domain)

        self.assertGreater(mesh.n_points, 0)

    def test_plain_sympy_symbols_are_compatible_with_the_cas_sampler(self) -> None:
        x, y, z = sp.symbols("x y z")

        mesh = FormulaVisualizer().build_mesh(x**2 + y**2 + z**2 - 1, self.domain)

        self.assertGreater(mesh.n_points, 0)

    def test_plain_sympy_coordinate_equality_keeps_its_plane_equation(self) -> None:
        x, y, z = sp.symbols("x y z")

        mesh = FormulaVisualizer().build_mesh(sp.Eq(z, x + y), self.domain)

        self.assertLess(float(abs(mesh.points[:, 2] - mesh.points[:, 0] - mesh.points[:, 1]).max()), 1e-10)


if __name__ == "__main__":
    unittest.main()
