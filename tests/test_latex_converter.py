"""MathLive LaTeX 转换为现有 CAS 曲面公式的测试。"""

import unittest

import sympy as sp

from MathInputWidget.latex_converter import LatexParseError, LatexParser


class LatexParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LatexParser()

    def test_equation_becomes_an_implicit_residual_and_canonical_cas_source(self) -> None:
        parsed = self.parser.parse(r"\frac{x^2}{a^2}+y^2=1", "implicit")

        x, y, a = sp.symbols("x y a", real=True)
        self.assertEqual(parsed.kind, "implicit")
        self.assertEqual(parsed.canonical_source, "y**2 - 1 + x**2/a**2")
        self.assertEqual(sp.simplify(parsed.expression - (x**2 / a**2 + y**2 - 1)), 0)
        self.assertEqual(parsed.parameter_names, ("a",))

    def test_coordinate_equality_becomes_an_explicit_surface(self) -> None:
        parsed = self.parser.parse("z=x+y", "implicit")

        x, y = sp.symbols("x y", real=True)
        self.assertEqual(parsed.kind, "explicit")
        self.assertEqual(parsed.dependent_axis, "z")
        self.assertEqual(parsed.canonical_source, "z = x + y")
        self.assertEqual(sp.simplify(parsed.expression - (x + y)), 0)

    def test_non_coordinate_equality_is_inferred_as_implicit_even_when_explicit_is_selected(self) -> None:
        parsed = self.parser.parse(r"x^2+y^2+z^2=1", "explicit")

        self.assertEqual(parsed.kind, "implicit")

    def test_invalid_latex_raises_a_domain_specific_error(self) -> None:
        with self.assertRaises(LatexParseError):
            self.parser.parse(r"\int_0^1 x\,dx", "implicit")

    def test_common_mathlive_functions_and_greek_parameters_remain_single_symbols(self) -> None:
        parsed = self.parser.parse(r"\alpha\sin(x)+\sqrt{y^2}=1", "implicit")

        x, y, alpha = sp.symbols("x y alpha", real=True)
        self.assertEqual(parsed.parameter_names, ("alpha",))
        self.assertEqual(sp.simplify(parsed.expression - (alpha * sp.sin(x) + sp.sqrt(y**2) - 1)), 0)

    def test_mathlive_operatorname_function_is_not_split_into_individual_symbols(self) -> None:
        parsed = self.parser.parse(r"\operatorname{sin}(x)=z", "implicit")

        x = sp.symbols("x", real=True)
        self.assertEqual(parsed.kind, "explicit")
        self.assertEqual(parsed.dependent_axis, "z")
        self.assertEqual(sp.simplify(parsed.expression - sp.sin(x)), 0)
        self.assertEqual(parsed.parameter_names, ())

    def test_mathlive_pi_is_the_sympy_constant_not_a_surface_parameter(self) -> None:
        parsed = self.parser.parse(r"z=\pi", "explicit")

        self.assertEqual(parsed.parameter_names, ())
        self.assertEqual(parsed.expression, sp.pi)

    def test_parametric_mathlive_coordinates_keep_the_existing_range_syntax(self) -> None:
        parsed = self.parser.parse(
            r"\left(u\cos\left(v\right),u\sin\left(v\right),v\right);u=\left[0,1\right],v=\left[-1,1\right]",
            "parametric",
        )

        self.assertEqual(parsed.kind, "parametric")
        self.assertEqual(parsed.canonical_source, "(u*cos(v), u*sin(v), v); u=[0,1], v=[-1,1]")

    def test_parametric_syntax_is_detected_without_a_surface_type_selector(self) -> None:
        parsed = self.parser.parse(
            r"\left(u\cos\left(v\right),u\sin\left(v\right),v\right);u=\left[0,1\right],v=\left[-1,1\right]",
            "explicit",
        )

        self.assertEqual(parsed.kind, "parametric")

    def test_parametric_mathlive_formula_converts_fractional_components(self) -> None:
        parsed = self.parser.parse(
            r"\left(\frac{u}{2}\cos\left(v\right),\frac{u}{2}\sin\left(v\right),v\right);u=\left[0,2\right],v=\left[-1,1\right]",
            "parametric",
        )

        self.assertEqual(parsed.canonical_source, "(u*cos(v)/2, u*sin(v)/2, v); u=[0,2], v=[-1,1]")

    def test_2d_parametric_syntax_is_detected_without_a_type_selector(self) -> None:
        parsed = self.parser.parse_2d(
            r"\left(\cos(t),\sin(t)\right);t=\left[0,2\pi\right]",
            "explicit",
        )

        self.assertEqual(parsed.kind, "parametric")
        self.assertEqual(parsed.canonical_source, "(cos(t), sin(t)); t=[0,2*pi]")

    def test_empty_input_raises_a_domain_specific_error(self) -> None:
        with self.assertRaises(LatexParseError):
            self.parser.parse("", "implicit")
        with self.assertRaises(LatexParseError):
            self.parser.parse("   ", "implicit")

    def test_unsupported_function_raises_a_domain_specific_error(self) -> None:
        with self.assertRaises(LatexParseError):
            self.parser.parse(r"\operatorname{arctan}(x)=z", "implicit")

    def test_parametric_missing_ranges_raises_a_domain_specific_error(self) -> None:
        with self.assertRaises(LatexParseError):
            self.parser.parse(r"\left(u,v,0\right);u=\left[0,1\right]", "parametric")

    def test_parametric_wrong_component_count_raises_a_domain_specific_error(self) -> None:
        with self.assertRaises(LatexParseError):
            self.parser.parse(
                r"\left(u,v\right);u=\left[0,1\right],v=\left[0,1\right]",
                "parametric",
            )


if __name__ == "__main__":
    unittest.main()
