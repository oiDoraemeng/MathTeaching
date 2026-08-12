"""Convert MathLive LaTeX into safe, canonical CAS surface expressions."""

from __future__ import annotations

from dataclasses import dataclass
import re

import sympy as sp
from sympy.parsing.latex import parse_latex


class LatexParseError(ValueError):
    """Raised when a MathLive formula cannot describe a renderable surface."""


_COORDINATES = {"x", "y", "z"}
_UNSUPPORTED_COMMANDS = (r"\int", r"\sum", r"\prod", r"\infty", r"\lim", r"\begin")
_OPERATOR_FUNCTIONS = ("abs", "cos", "exp", "log", "sin", "sqrt", "tan")
@dataclass(frozen=True)
class ParsedFormula:
    """A MathLive formula normalized for the existing CAS rendering pipeline."""

    latex: str
    kind: str
    expression: sp.Expr
    canonical_source: str
    parameter_names: tuple[str, ...]
    dependent_axis: str | None = None


class LatexParser:
    """Parse MathLive output without coupling callers to a browser widget."""

    def parse(self, latex: str, requested_kind: str = "implicit") -> ParsedFormula:
        latex = latex.strip()
        if not latex:
            raise LatexParseError("请输入数学公式。")
        if requested_kind == "parametric":
            return self._parse_parametric(latex)
        if any(command in latex for command in _UNSUPPORTED_COMMANDS):
            raise LatexParseError("积分、求和、极限和无穷符号不能直接绘制为三维曲面。")
        latex = self._normalize_functions(latex)

        try:
            parsed = parse_latex(latex, backend="antlr")
        except (ImportError, SyntaxError, ValueError) as error:
            raise LatexParseError("无法解析该 LaTeX 公式。") from error
        except Exception as error:
            raise LatexParseError("LaTeX 公式格式不完整或包含不支持的符号。") from error

        if isinstance(parsed, sp.Equality):
            return self._from_equation(latex, parsed, requested_kind)
        expression = self._real_symbols(sp.simplify(parsed))
        return self._build_implicit(latex, expression)

    def _from_equation(self, latex: str, equation: sp.Equality, requested_kind: str) -> ParsedFormula:
        left = self._real_symbols(sp.simplify(equation.lhs))
        right = self._real_symbols(sp.simplify(equation.rhs))
        if isinstance(left, sp.Symbol) and left.name in _COORDINATES:
            return self._build_explicit(latex, left.name, right)
        if isinstance(right, sp.Symbol) and right.name in _COORDINATES:
            return self._build_explicit(latex, right.name, left)
        return self._build_implicit(latex, left - right)

    def _parse_parametric(self, latex: str) -> ParsedFormula:
        """Parse MathLive coordinate and range fragments independently with SymPy."""
        source = (
            latex.replace(r"\left(", "(")
            .replace(r"\right)", ")")
            .replace(r"\left[", "[")
            .replace(r"\right]", "]")
            .replace(r"\,", "")
        )
        if source.count(";") != 1:
            raise LatexParseError("参数曲面应为坐标三元组，并指定 u、v 的范围。")
        coordinate_source, ranges_source = (part.strip() for part in source.split(";", 1))
        if not (coordinate_source.startswith("(") and coordinate_source.endswith(")")):
            raise LatexParseError("参数曲面的坐标必须使用圆括号包裹。")
        components_source = self._split_top_level(coordinate_source[1:-1])
        if len(components_source) != 3:
            raise LatexParseError("参数曲面必须包含三个坐标表达式。")
        components = tuple(self._parse_fragment(component) for component in components_source)

        ranges: dict[str, tuple[sp.Expr, sp.Expr]] = {}
        for match in re.finditer(r"([uv])\s*=\s*\[([^\]]+)\]", ranges_source):
            bounds = self._split_top_level(match.group(2))
            if len(bounds) != 2:
                raise LatexParseError("参数范围必须包含下界和上界。")
            ranges[match.group(1)] = (self._parse_fragment(bounds[0]), self._parse_fragment(bounds[1]))
        if set(ranges) != {"u", "v"}:
            raise LatexParseError("参数曲面必须指定 u=[下界,上界] 和 v=[下界,上界]。")
        if any(bound.free_symbols for range_bounds in ranges.values() for bound in range_bounds):
            raise LatexParseError("参数曲面的 u、v 范围暂不支持符号参数，请使用具体数值。")

        parameter_names = tuple(
            sorted(
                {
                str(symbol)
                for expression in (*components, *ranges["u"], *ranges["v"])
                for symbol in expression.free_symbols
                if str(symbol) not in {"u", "v", "x", "y", "z"}
                }
            )
        )
        canonical_source = (
            f"({', '.join(sp.sstr(component) for component in components)}); "
            f"u=[{sp.sstr(ranges['u'][0])},{sp.sstr(ranges['u'][1])}], "
            f"v=[{sp.sstr(ranges['v'][0])},{sp.sstr(ranges['v'][1])}]"
        )
        return ParsedFormula(
            latex=latex,
            kind="parametric",
            expression=sp.Tuple(*components),
            canonical_source=canonical_source,
            parameter_names=parameter_names,
        )

    def _parse_fragment(self, source: str) -> sp.Expr:
        try:
            return self._real_symbols(sp.simplify(parse_latex(source.strip(), backend="antlr")))
        except Exception as error:
            raise LatexParseError("参数曲面的坐标或范围无法解析。") from error

    @staticmethod
    def _normalize_functions(latex: str) -> str:
        names = "|".join(_OPERATOR_FUNCTIONS)
        latex = re.sub(rf"\\(?:operatorname|mathrm)\s*\{{({names})\}}", r"\\\1", latex)
        if r"\operatorname" in latex or r"\mathrm" in latex:
            raise LatexParseError("仅支持 sin、cos、tan、log、sqrt、exp 和 abs 函数。")
        return latex

    @staticmethod
    def _split_top_level(source: str) -> list[str]:
        parts: list[str] = []
        start = 0
        depth = 0
        for index, character in enumerate(source):
            if character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character == "," and depth == 0:
                parts.append(source[start:index].strip())
                start = index + 1
        parts.append(source[start:].strip())
        return parts

    @staticmethod
    def _real_symbols(expression: sp.Expr) -> sp.Expr:
        replacements = {
            symbol: sp.pi if symbol.name == "pi" else sp.Symbol(symbol.name, real=True)
            for symbol in expression.free_symbols
        }
        return expression.xreplace(replacements)

    @staticmethod
    def _build_implicit(latex: str, expression: sp.Expr) -> ParsedFormula:
        parameters = tuple(sorted(str(symbol) for symbol in expression.free_symbols if str(symbol) not in _COORDINATES))
        return ParsedFormula(
            latex=latex,
            kind="implicit",
            expression=expression,
            canonical_source=sp.sstr(expression),
            parameter_names=parameters,
        )

    @staticmethod
    def _build_explicit(latex: str, dependent_axis: str, expression: sp.Expr) -> ParsedFormula:
        parameters = tuple(sorted(str(symbol) for symbol in expression.free_symbols if str(symbol) not in _COORDINATES))
        return ParsedFormula(
            latex=latex,
            kind="explicit",
            expression=expression,
            canonical_source=f"{dependent_axis} = {sp.sstr(expression)}",
            parameter_names=parameters,
            dependent_axis=dependent_axis,
        )
