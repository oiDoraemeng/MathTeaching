"""二维笛卡尔曲线的安全代数解析与数值采样。"""

from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np
import pyvista as pv
import sympy as sp
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from models.curve_layer import CurveLayer, Plot2DDomain


class CurveExpressionError(ValueError):
    """当公式无法安全地表示二维曲线时抛出。"""


_COORDINATES = ("x", "y")
_PARAMETER = "t"
_ALLOWED_FUNCTIONS = {
    "abs": sp.Abs,
    "cos": sp.cos,
    "exp": sp.exp,
    "log": sp.log,
    "sin": sp.sin,
    "sqrt": sp.sqrt,
    "tan": sp.tan,
}
_ALLOWED_CONSTANTS = {"E": sp.E, "pi": sp.pi}
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_FUNCTION_CALL = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*\(")
_ALGEBRA_CHARACTERS = re.compile(r"[A-Za-z0-9_+\-*/^().=,;\[\] \t]+\Z")
_TRANSFORMATIONS = standard_transformations + (convert_xor,)


@dataclass(frozen=True)
class CurveExpression:
    """已解析完成、可进行向量化计算的二维曲线。"""

    kind: str
    source: str
    simplified: sp.Expr | tuple[sp.Expr, sp.Expr]
    parameter_names: tuple[str, ...]
    dependent_axis: str | None = None
    parameter_range: tuple[sp.Expr, sp.Expr] | None = None


def parse_curve_expression(source: str, kind: str) -> CurveExpression:
    """解析显式、隐式和参数曲线，不执行用户输入的代码。"""
    source = _normalize_source(source.strip())
    if not source:
        raise CurveExpressionError("请输入二维函数表达式。")
    if kind == "explicit":
        dependent_axis, expression = _parse_explicit(source)
        return CurveExpression(
            kind="explicit",
            source=source,
            simplified=sp.simplify(expression),
            parameter_names=_parameter_names((expression,), excluded=_COORDINATES),
            dependent_axis=dependent_axis,
        )
    if kind == "implicit":
        expression = _parse_implicit(source)
        return CurveExpression(
            kind="implicit",
            source=source,
            simplified=sp.simplify(expression),
            parameter_names=_parameter_names((expression,), excluded=_COORDINATES),
        )
    if kind == "parametric":
        components, parameter_range = _parse_parametric(source)
        return CurveExpression(
            kind="parametric",
            source=source,
            simplified=tuple(sp.simplify(component) for component in components),
            parameter_names=_parameter_names(components, excluded=(*_COORDINATES, _PARAMETER)),
            parameter_range=parameter_range,
        )
    raise CurveExpressionError("二维函数类型必须是显式、隐式或参数形式。")


def build_curve_mesh(
    expression: CurveExpression,
    parameters: dict[str, float],
    domain: Plot2DDomain,
) -> pv.PolyData:
    """在 XY 平面为一条已采样曲线生成折线网格。"""
    if expression.kind == "explicit":
        return _build_explicit_curve(expression, parameters, domain)
    if expression.kind == "implicit":
        return _build_implicit_curve(expression, parameters, domain)
    return _build_parametric_curve(expression, parameters, domain)


def create_curve_layer(name: str, kind: str, source: str, *, latex: str | None = None) -> CurveLayer:
    """创建曲线图层，并将表达式中的符号常量暴露为可编辑参数。"""
    expression = parse_curve_expression(source, kind)
    return CurveLayer(
        name=name.strip() or "函数",
        kind=expression.kind,
        expression=expression.source,
        latex=latex,
        parameters={parameter: 1.0 for parameter in expression.parameter_names},
    )


def _parse_explicit(source: str) -> tuple[str, sp.Expr]:
    if source.count("=") != 1:
        raise CurveExpressionError("显式二维函数应写作 y = f(x) 或 x = f(y)。")
    left, right = (part.strip() for part in source.split("=", 1))
    left_expression = _parse_algebra(left)
    if not isinstance(left_expression, sp.Symbol) or left_expression.name not in _COORDINATES:
        raise CurveExpressionError("显式二维函数左侧必须是 x 或 y。")
    return left_expression.name, _parse_algebra(right)


def _parse_implicit(source: str) -> sp.Expr:
    if source.count("=") > 1:
        raise CurveExpressionError("隐式二维方程只能包含一个等号。")
    if "=" not in source:
        return _parse_algebra(source)
    left, right = (part.strip() for part in source.split("=", 1))
    return _parse_algebra(left) - _parse_algebra(right)


def _parse_parametric(source: str) -> tuple[tuple[sp.Expr, sp.Expr], tuple[sp.Expr, sp.Expr]]:
    if source.count(";") != 1:
        raise CurveExpressionError("参数曲线格式为 '(x(t), y(t)); t=[a,b]'。")
    coordinate_part, range_part = (part.strip() for part in source.split(";", 1))
    if not (coordinate_part.startswith("(") and coordinate_part.endswith(")")):
        raise CurveExpressionError("参数曲线坐标必须使用圆括号。")
    coordinates = _split_top_level(coordinate_part[1:-1])
    if len(coordinates) != 2:
        raise CurveExpressionError("参数曲线必须包含两个坐标表达式。")
    if "=" not in range_part:
        raise CurveExpressionError("参数范围必须使用 t=[最小值,最大值]。")
    parameter, values = (part.strip() for part in range_part.split("=", 1))
    if parameter != _PARAMETER or not (values.startswith("[") and values.endswith("]")):
        raise CurveExpressionError("参数范围必须使用 t=[最小值,最大值]。")
    bounds = _split_top_level(values[1:-1])
    if len(bounds) != 2:
        raise CurveExpressionError("参数范围需要下限和上限。")
    lower, upper = (_parse_algebra(value) for value in bounds)
    if lower.free_symbols or upper.free_symbols:
        raise CurveExpressionError("参数范围必须是数值常量。")
    if float(lower) >= float(upper):
        raise CurveExpressionError("参数范围必须从较小值递增到较大值。")
    return tuple(_parse_algebra(value) for value in coordinates), (lower, upper)


def _parse_algebra(text: str) -> sp.Expr:
    if not text or "__" in text or not _ALGEBRA_CHARACTERS.fullmatch(text):
        raise CurveExpressionError("表达式包含不支持的字符。")
    # 在调用 sympify 前限制字符集和函数白名单，避免把用户输入当作任意 Python 表达式。
    for function_name in _FUNCTION_CALL.findall(text):
        if function_name not in _ALLOWED_FUNCTIONS:
            raise CurveExpressionError(f"不支持的函数: {function_name}")
    identifiers = set(_IDENTIFIER.findall(text))
    parameters = identifiers - set(_COORDINATES) - {_PARAMETER} - set(_ALLOWED_FUNCTIONS) - set(_ALLOWED_CONSTANTS)
    local_dict = {
        **{name: sp.Symbol(name, real=True) for name in (*_COORDINATES, _PARAMETER)},
        **{name: sp.Symbol(name, real=True) for name in parameters},
        **_ALLOWED_FUNCTIONS,
        **_ALLOWED_CONSTANTS,
    }
    try:
        return sp.sympify(text.replace("^", "**"), locals=local_dict, evaluate=True)
    except (SyntaxError, TypeError, ValueError, SympifyError) as error:
        raise CurveExpressionError("无法解析该二维表达式。") from error


def _normalize_source(source: str) -> str:
    """规整参数式中 MathLive 可能保留的分隔符。"""
    return (
        source.replace(r"\left(", "(")
        .replace(r"\right)", ")")
        .replace(r"\left[", "[")
        .replace(r"\right]", "]")
        .replace(r"\,", "")
    )


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise CurveExpressionError("表达式中的括号不匹配。")
    parts.append(text[start:].strip())
    return parts


def _parameter_names(expressions: tuple[sp.Expr, ...], excluded: tuple[str, ...]) -> tuple[str, ...]:
    symbols = {str(symbol) for expression in expressions for symbol in expression.free_symbols}
    return tuple(sorted(symbols - set(excluded)))


def _evaluate(
    expressions: tuple[sp.Expr, ...],
    variables: tuple[str, ...],
    values: tuple[np.ndarray, ...],
    parameter_names: tuple[str, ...],
    parameters: dict[str, float],
) -> tuple[np.ndarray, ...]:
    missing = [name for name in parameter_names if name not in parameters]
    if missing:
        raise CurveExpressionError(f"缺少参数值: {', '.join(missing)}")
    symbols = [sp.Symbol(name, real=True) for name in (*variables, *parameter_names)]
    function = sp.lambdify(symbols, expressions, modules="numpy")
    try:
        raw_values = function(*values, *(parameters[name] for name in parameter_names))
    except (ArithmeticError, TypeError, ValueError) as error:
        raise CurveExpressionError("无法在当前范围内计算二维函数。") from error
    if not isinstance(raw_values, tuple):
        raw_values = (raw_values,)
    result: list[np.ndarray] = []
    shape = values[0].shape
    for raw_value in raw_values:
        value = np.asarray(raw_value, dtype=float)
        if value.ndim == 0:
            value = np.full(shape, float(value))
        result.append(np.broadcast_to(value, shape).copy())
    return tuple(result)


def _build_explicit_curve(expression: CurveExpression, parameters: dict[str, float], domain: Plot2DDomain) -> pv.PolyData:
    dependent_axis = expression.dependent_axis
    if dependent_axis is None:
        raise CurveExpressionError("显式二维函数缺少因变量坐标。")
    independent_axis = "x" if dependent_axis == "y" else "y"
    independent_range = domain.x_range if independent_axis == "x" else domain.y_range
    dependent_range = domain.y_range if dependent_axis == "y" else domain.x_range
    independent_values = np.linspace(*independent_range, domain.curve_resolution)
    x_values, y_values = (
        (independent_values, np.zeros_like(independent_values))
        if independent_axis == "x"
        else (np.zeros_like(independent_values), independent_values)
    )
    dependent_values = _evaluate(
        (expression.simplified,),
        _COORDINATES,
        (x_values, y_values),
        expression.parameter_names,
        parameters,
    )[0]
    if dependent_axis == "y":
        x_values, y_values = independent_values, dependent_values
    else:
        x_values, y_values = dependent_values, independent_values
    valid = np.isfinite(x_values) & np.isfinite(y_values)
    valid &= (x_values >= domain.x_range[0]) & (x_values <= domain.x_range[1])
    valid &= (y_values >= domain.y_range[0]) & (y_values <= domain.y_range[1])
    return _segments_to_mesh(_split_valid_segments(x_values, y_values, valid))


def _build_implicit_curve(expression: CurveExpression, parameters: dict[str, float], domain: Plot2DDomain) -> pv.PolyData:
    x_values = np.linspace(*domain.x_range, domain.implicit_resolution)
    y_values = np.linspace(*domain.y_range, domain.implicit_resolution)
    x_grid, y_grid = np.meshgrid(x_values, y_values, indexing="ij")
    field = _evaluate(
        (expression.simplified,),
        _COORDINATES,
        (x_grid, y_grid),
        expression.parameter_names,
        parameters,
    )[0]
    field[~np.isfinite(field)] = np.nan
    # 将标量场写入规则网格后提取零等值线，可统一处理圆锥曲线等隐式方程。
    grid = pv.ImageData(
        dimensions=(domain.implicit_resolution, domain.implicit_resolution, 1),
        spacing=(
            (domain.x_range[1] - domain.x_range[0]) / (domain.implicit_resolution - 1),
            (domain.y_range[1] - domain.y_range[0]) / (domain.implicit_resolution - 1),
            1.0,
        ),
        origin=(domain.x_range[0], domain.y_range[0], 0.0),
    )
    grid.point_data["curve_field"] = field.ravel(order="F")
    return grid.contour([0.0], scalars="curve_field").clean()


def _build_parametric_curve(expression: CurveExpression, parameters: dict[str, float], domain: Plot2DDomain) -> pv.PolyData:
    if expression.parameter_range is None:
        raise CurveExpressionError("参数曲线缺少参数范围。")
    lower, upper = (float(value) for value in expression.parameter_range)
    t_values = np.linspace(lower, upper, domain.curve_resolution)
    x_values, y_values = _evaluate(
        expression.simplified,
        (_PARAMETER,),
        (t_values,),
        expression.parameter_names,
        parameters,
    )
    valid = np.isfinite(x_values) & np.isfinite(y_values)
    valid &= (x_values >= domain.x_range[0]) & (x_values <= domain.x_range[1])
    valid &= (y_values >= domain.y_range[0]) & (y_values <= domain.y_range[1])
    return _segments_to_mesh(_split_valid_segments(x_values, y_values, valid))


def _split_valid_segments(x_values: np.ndarray, y_values: np.ndarray, valid: np.ndarray) -> list[np.ndarray]:
    segments: list[np.ndarray] = []
    start: int | None = None
    for index, is_valid in enumerate(valid):
        if is_valid and start is None:
            start = index
        elif not is_valid and start is not None:
            if index - start > 1:
                segments.append(np.column_stack((x_values[start:index], y_values[start:index], np.zeros(index - start))))
            # 在无定义点处分段，避免把渐近线两侧错误地连接起来。
            start = None
    if start is not None and len(valid) - start > 1:
        segments.append(np.column_stack((x_values[start:], y_values[start:], np.zeros(len(valid) - start))))
    return segments


def _segments_to_mesh(segments: list[np.ndarray]) -> pv.PolyData:
    if not segments:
        return pv.PolyData()
    points = np.concatenate(segments)
    cells: list[int] = []
    offset = 0
    for segment in segments:
        cells.extend((len(segment), *range(offset, offset + len(segment))))
        offset += len(segment)
    # 直接用 points 初始化会自动创建 vertex cell，导致采样点以圆点形式显示；
    # 先创建空网格，再只写入 lines，保留采样数据但不生成独立顶点单元。
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = np.asarray(cells, dtype=np.int64)
    return mesh
