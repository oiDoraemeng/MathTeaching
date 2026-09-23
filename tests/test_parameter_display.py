"""Parameterized formulas shown in the algebra panel use current numeric values."""

import unittest

from geometry.cas_curve import parse_curve_expression
from geometry.parameter_display import format_parameterized_latex


class ParameterDisplayTests(unittest.TestCase):
    def test_explicit_line_substitutes_every_adjustable_parameter(self) -> None:
        parsed = parse_curve_expression("y = a*x + b", "explicit")

        latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters={"a": 1.0, "b": 1.0},
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
        )

        self.assertEqual(latex, "y=x + 1")
        self.assertFalse({"a", "b"}.intersection(latex))

    def test_arbitrary_parameter_names_are_substituted(self) -> None:
        parsed = parse_curve_expression("y = p*x^2 + q", "explicit")

        latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters={"p": 2.5, "q": -3.0},
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
        )

        self.assertIn("2.5", latex)
        self.assertIn("- 3", latex)
        self.assertFalse({"p", "q"}.intersection(latex))

    def test_implicit_formula_keeps_the_original_standard_equation_layout(self) -> None:
        parsed = parse_curve_expression("x^2/a^2 + y^2/b^2 = 1", "implicit")

        latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters={"a": 5.0, "b": 3.0},
            source=parsed.source,
        )

        self.assertEqual(latex, r"\frac{x^{2}}{25} + \frac{y^{2}}{9}=1")

    def test_implicit_parabola_is_not_rearranged_to_equal_zero(self) -> None:
        parsed = parse_curve_expression("y^2 = 4*a*x", "implicit")

        latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters={"a": 1.0},
            source=parsed.source,
        )

        self.assertEqual(latex, r"y^{2}=4 x")


if __name__ == "__main__":
    unittest.main()
