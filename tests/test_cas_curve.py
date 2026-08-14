"""Regression tests for 2D MathLive parsing and numerical curve sampling."""

import unittest

from MathInputWidget import LatexParser
from geometry.cas_curve import build_curve_mesh, parse_curve_expression
from models.curve_layer import Plot2DDomain


class CasCurveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LatexParser()
        self.domain = Plot2DDomain(curve_resolution=160, implicit_resolution=96)

    def test_explicit_mathlive_formula_samples_a_polyline(self) -> None:
        formula = self.parser.parse_2d(r"y=\frac{x^2}{2}", "explicit")
        expression = parse_curve_expression(formula.canonical_source, formula.kind)
        mesh = build_curve_mesh(expression, {}, self.domain)

        self.assertEqual(expression.dependent_axis, "y")
        self.assertGreater(mesh.n_points, 40)
        self.assertGreater(mesh.n_cells, 0)

    def test_implicit_mathlive_formula_extracts_a_zero_contour(self) -> None:
        formula = self.parser.parse_2d(r"x^2+y^2=1", "explicit")
        expression = parse_curve_expression(formula.canonical_source, formula.kind)
        mesh = build_curve_mesh(expression, {}, self.domain)

        self.assertEqual(expression.kind, "implicit")
        self.assertGreater(mesh.n_points, 20)
        self.assertLess(abs(mesh.points[:, 2]).max(), 1e-9)

    def test_parametric_mathlive_formula_normalizes_t_range_and_samples(self) -> None:
        formula = self.parser.parse_2d(
            r"\left(\cos(t),\sin(t)\right);t=\left[0,2\pi\right]",
            "explicit",
        )
        expression = parse_curve_expression(formula.canonical_source, formula.kind)
        mesh = build_curve_mesh(expression, {}, self.domain)

        self.assertEqual(formula.canonical_source, "(cos(t), sin(t)); t=[0,2*pi]")
        self.assertEqual(expression.kind, "parametric")
        self.assertGreater(mesh.n_points, 100)

    def test_out_of_range_asymptote_is_split_into_multiple_segments(self) -> None:
        expression = parse_curve_expression("y = 1/x", "explicit")
        mesh = build_curve_mesh(expression, {}, self.domain)

        self.assertGreater(mesh.n_cells, 1)


if __name__ == "__main__":
    unittest.main()
