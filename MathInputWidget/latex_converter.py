"""将 MathLive LaTeX 转换为安全、规范的 CAS 曲面表达式。"""

from __future__ import annotations

from dataclasses import dataclass
import re

import sympy as sp
from sympy.core.sympify import SympifyError
from sympy.parsing.latex import parse_latex


class LatexParseError(ValueError):
    """当 MathLive 公式无法表示可渲染曲面时抛出。"""


_COORDINATES = {"x", "y", "z"}
_UNSUPPORTED_COMMANDS = (r"\int", r"\sum", r"\prod", r"\infty", r"\lim", r"\begin")
_OPERATOR_FUNCTIONS = ("abs", "cos", "exp", "log", "sin", "sqrt", "tan")
@dataclass(frozen=True)
class ParsedFormula:
    """已规范化、可接入现有 CAS 渲染流程的 MathLive 公式。"""

    latex: str
    kind: str
    expression: sp.Expr
    canonical_source: str
    parameter_names: tuple[str, ...]
    dependent_axis: str | None = None


class LatexParser:
    """解析 MathLive 输出，不让调用方依赖浏览器控件。"""

    def parse_2d(self, latex: str, requested_kind: str = "implicit") -> ParsedFormula:
        """解析二维公式，包括紧凑的带 t 范围参数式。"""
        latex = latex.strip()
        if not latex:
            raise LatexParseError("璇疯緭鍏ユ暟瀛﹀叕寮忋€?")
        if requested_kind == "parametric" or self._looks_like_2d_parametric(latex):
            return self._parse_parametric_2d(latex)
        return self.parse(latex, requested_kind)

    def parse(self, latex: str, requested_kind: str = "implicit") -> ParsedFormula:
        latex = latex.strip()
        if not latex:
            raise LatexParseError("请输入数学公式。")
        if requested_kind == "parametric" or self._looks_like_parametric(latex):
            return self._parse_parametric(latex)
        if any(command in latex for command in _UNSUPPORTED_COMMANDS):
            raise LatexParseError("积分、求和、极限和无穷符号不能直接绘制为三维曲面。")
        latex = self._normalize_functions(latex)

        try:
            parsed = parse_latex(latex, backend="antlr")
        except (ImportError, SyntaxError, ValueError) as error:
            raise LatexParseError("无法解析该 LaTeX 公式。") from error
        except (SympifyError, TypeError, AttributeError) as error:
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
        """使用 SymPy 分别解析 MathLive 坐标片段与参数范围片段。"""
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

    def _parse_parametric_2d(self, latex: str) -> ParsedFormula:
        source = self._normalize_parametric_source(latex)
        if source.count(";") != 1:
            raise LatexParseError("浜岀淮鍙傛暟鏇茬嚎搴斾负 (x(t), y(t)); t=[a,b]")
        coordinate_source, range_source = (part.strip() for part in source.split(";", 1))
        if not (coordinate_source.startswith("(") and coordinate_source.endswith(")")):
            raise LatexParseError("浜岀淮鍙傛暟鏇茬嚎鐨勫潗鏍囧繀椤讳娇鐢ㄥ渾鎷彿")
        components_source = self._split_top_level(coordinate_source[1:-1])
        if len(components_source) != 2:
            raise LatexParseError("浜岀淮鍙傛暟鏇茬嚎蹇呴』鍖呭惈涓や釜鍧愭爣琛ㄨ揪寮忋€?")
        match = re.fullmatch(r"t\s*=\s*\[([^\]]+)\]", range_source)
        if match is None:
            raise LatexParseError("浜岀淮鍙傛暟鑼冨洿蹇呴』浣跨敤 t=[a,b]")
        bounds = self._split_top_level(match.group(1))
        if len(bounds) != 2:
            raise LatexParseError("鍙傛暟鑼冨洿闇€瑕佷笅闄愬拰涓婇檺")
        components = tuple(self._parse_fragment(component) for component in components_source)
        lower, upper = (self._parse_fragment(value) for value in bounds)
        if lower.free_symbols or upper.free_symbols or float(lower) >= float(upper):
            raise LatexParseError("t 鐨勮寖鍥撮渶瑕佹槸閫掑鐨勬暟鍊艰寖鍥?")
        parameter_names = tuple(
            sorted(
                {
                    str(symbol)
                    for expression in (*components, lower, upper)
                    for symbol in expression.free_symbols
                    if str(symbol) not in {"x", "y", "t"}
                }
            )
        )
        canonical_source = (
            f"({sp.sstr(components[0])}, {sp.sstr(components[1])}); "
            f"t=[{sp.sstr(lower)},{sp.sstr(upper)}]"
        )
        return ParsedFormula(
            latex=latex,
            kind="parametric",
            expression=sp.Tuple(*components),
            canonical_source=canonical_source,
            parameter_names=parameter_names,
        )

    @staticmethod
    def _normalize_parametric_source(latex: str) -> str:
        return (
            latex.replace(r"\left(", "(")
            .replace(r"\right)", ")")
            .replace(r"\left[", "[")
            .replace(r"\right]", "]")
            .replace(r"\,", "")
        )

    @staticmethod
    def _looks_like_parametric(latex: str) -> bool:
        """识别同时包含 u、v 范围的三元坐标参数式。"""
        return ";" in latex and bool(
            re.search(r"\bu\s*=\s*(?:\\left\s*)?\[", latex)
            and re.search(r"\bv\s*=\s*(?:\\left\s*)?\[", latex)
        )

    @staticmethod
    def _looks_like_2d_parametric(latex: str) -> bool:
        return ";" in latex and bool(re.search(r"t\s*=\s*(?:\\left\s*)?\[", latex))

    def _parse_fragment(self, source: str) -> sp.Expr:
        try:
            return self._real_symbols(sp.simplify(parse_latex(source.strip(), backend="antlr")))
        except (SyntaxError, ValueError, SympifyError, TypeError, AttributeError) as error:
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
