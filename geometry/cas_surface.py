"""曲面的安全本地代数解析与数值网格生成。"""

from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np
import pyvista as pv
import sympy as sp
from sympy.parsing.sympy_parser import convert_xor, standard_transformations

from models.surface_layer import PlotDomain, SurfaceLayer


class ExpressionError(ValueError):
    """当用户代数式无法安全解析或采样时抛出。"""


_COORDINATES = ("x", "y", "z")
_PARAMETERS = ("u", "v")
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
_ALGEBRA_CHARACTERS = re.compile(r"[A-Za-z0-9_+\-*/^().= \t]+\Z")
_TRANSFORMATIONS = standard_transformations + (convert_xor,)


@dataclass(frozen=True)
class SurfaceExpression:
    """已解析完成、可进行向量化数值计算的曲面公式。"""

    kind: str
    source: str
    simplified: sp.Expr | tuple[sp.Expr, sp.Expr, sp.Expr]
    parameter_names: tuple[str, ...]
    dependent_axis: str | None = None
    parameter_variables: tuple[str, str] | tuple[()] = ()
    parameter_ranges: tuple[tuple[sp.Expr, sp.Expr], tuple[sp.Expr, sp.Expr]] | tuple[()] = ()


def parse_surface_expression(source: str, kind: str) -> SurfaceExpression:
    """解析显式、隐式或参数曲面，不执行用户输入的代码。"""
    source = source.strip()
    if not source:
        raise ExpressionError("请输入曲面表达式。")
    if kind == "explicit":
        dependent_axis, expression = _parse_explicit(source)
        parameter_names = _parameter_names((expression,), excluded=_COORDINATES)
        return SurfaceExpression("explicit", source, sp.simplify(expression), parameter_names, dependent_axis)
    if kind == "implicit":
        expression = _parse_implicit(source)
        parameter_names = _parameter_names((expression,), excluded=_COORDINATES)
        return SurfaceExpression("implicit", source, sp.simplify(expression), parameter_names)
    if kind == "parametric":
        components, ranges = _parse_parametric(source)
        parameter_names = _parameter_names(components, excluded=(*_COORDINATES, *_PARAMETERS))
        return SurfaceExpression(
            "parametric",
            source,
            tuple(sp.simplify(component) for component in components),
            parameter_names,
            parameter_variables=("u", "v"),
            parameter_ranges=ranges,
        )
    raise ExpressionError("曲面类型必须为显式、隐式或参数形式。")


def build_surface_mesh(expression: SurfaceExpression, parameters: dict[str, float], domain: PlotDomain) -> pv.PolyData:
    """在指定定义域内为已解析曲面生成 PyVista 网格。"""
    if expression.kind == "implicit":
        return _build_implicit_mesh(expression, parameters, domain)
    if expression.kind == "explicit":
        return _build_explicit_mesh(expression, parameters, domain)
    return _build_parametric_mesh(expression, parameters, domain)


def create_cas_layer(name: str, kind: str, source: str) -> SurfaceLayer:
    """创建曲面图层，并将检测到的符号常量暴露为控制参数。"""
    expression = parse_surface_expression(source, kind)
    return SurfaceLayer(
        name=name.strip() or "CAS surface",
        kind=expression.kind,
        expression=expression.source,
        parameters={parameter: 1.0 for parameter in expression.parameter_names},
    )


def _parse_explicit(source: str) -> tuple[str, sp.Expr]:
    if source.count("=") != 1:
        raise ExpressionError("显式曲面必须使用一个方程，例如 z = f(x, y)。")
    left, right = (part.strip() for part in source.split("=", 1))
    left_expression = _parse_algebra(left)
    if not isinstance(left_expression, sp.Symbol) or left_expression.name not in _COORDINATES:
        raise ExpressionError("显式曲面的左侧必须是 x、y 或 z。")
    return left_expression.name, _parse_algebra(right)


def _parse_implicit(source: str) -> sp.Expr:
    if source.count("=") > 1:
        raise ExpressionError("隐式方程只能包含一个等号。")
    if "=" not in source:
        return _parse_algebra(source)
    left, right = (part.strip() for part in source.split("=", 1))
    return _parse_algebra(left) - _parse_algebra(right)


def _parse_parametric(source: str) -> tuple[tuple[sp.Expr, sp.Expr, sp.Expr], tuple[tuple[sp.Expr, sp.Expr], tuple[sp.Expr, sp.Expr]]]:
    if source.count(";") != 1:
        raise ExpressionError("参数曲面格式为 '(x(u,v), y(u,v), z(u,v)); u=[a,b], v=[c,d]'。")
    coordinate_part, range_part = (part.strip() for part in source.split(";", 1))
    if not (coordinate_part.startswith("(") and coordinate_part.endswith(")")):
        raise ExpressionError("参数坐标必须使用圆括号包裹。")
    coordinate_parts = _split_top_level(coordinate_part[1:-1])
    if len(coordinate_parts) != 3:
        raise ExpressionError("参数曲面必须恰好包含三个坐标表达式。")
    components = tuple(_parse_algebra(part) for part in coordinate_parts)
    definitions = _split_top_level(range_part)
    if len(definitions) != 2:
        raise ExpressionError("请同时定义 u 和 v 的取值范围。")
    ranges: dict[str, tuple[sp.Expr, sp.Expr]] = {}
    for definition in definitions:
        if "=" not in definition:
            raise ExpressionError("参数范围必须使用 u=[最小值,最大值] 或 v=[最小值,最大值]。")
        parameter, values = (part.strip() for part in definition.split("=", 1))
        if parameter not in _PARAMETERS or not (values.startswith("[") and values.endswith("]")):
            raise ExpressionError("参数范围必须使用 u=[最小值,最大值] 或 v=[最小值,最大值]。")
        bounds = _split_top_level(values[1:-1])
        if len(bounds) != 2:
            raise ExpressionError("每个参数范围都需要下限和上限。")
        lower, upper = (_parse_algebra(value) for value in bounds)
        if lower.free_symbols or upper.free_symbols:
            raise ExpressionError("参数范围边界必须为数值常量。")
        ranges[parameter] = (lower, upper)
    if set(ranges) != set(_PARAMETERS):
        raise ExpressionError("请分别为 u 和 v 定义一个范围。")
    return components, (ranges["u"], ranges["v"])


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
        raise ExpressionError("表达式中的括号不匹配。")
    parts.append(text[start:].strip())
    return parts


def _parse_algebra(text: str) -> sp.Expr:
    if not text or "__" in text or not _ALGEBRA_CHARACTERS.fullmatch(text):
        raise ExpressionError("表达式包含不支持的字符。")
    # 先校验字符与函数白名单，再交给 SymPy 解析，防止用户输入越过可用语法范围。
    for function_name in _FUNCTION_CALL.findall(text):
        if function_name not in _ALLOWED_FUNCTIONS:
            raise ExpressionError(f"不支持的函数: {function_name}")
    identifiers = set(_IDENTIFIER.findall(text))
    parameters = identifiers - set(_COORDINATES) - set(_PARAMETERS) - set(_ALLOWED_FUNCTIONS) - set(_ALLOWED_CONSTANTS)
    local_dict = {
        **{name: sp.Symbol(name, real=True) for name in (*_COORDINATES, *_PARAMETERS)},
        **{name: sp.Symbol(name, real=True) for name in parameters},
        **_ALLOWED_FUNCTIONS,
        **_ALLOWED_CONSTANTS,
    }
    try:
        return sp.sympify(text.replace("^", "**"), locals=local_dict, evaluate=True)
    except (SyntaxError, TypeError, ValueError) as error:
        raise ExpressionError("无法解析该表达式。") from error


def _parameter_names(expressions: tuple[sp.Expr, ...], excluded: tuple[str, ...]) -> tuple[str, ...]:
    symbols = {str(symbol) for expression in expressions for symbol in expression.free_symbols}
    return tuple(sorted(symbols - set(excluded)))


def _numeric_values(
    expressions: tuple[sp.Expr, ...],
    variables: tuple[str, ...],
    coordinates: tuple[np.ndarray, ...],
    parameter_names: tuple[str, ...],
    parameters: dict[str, float],
) -> tuple[np.ndarray, ...]:
    missing = [name for name in parameter_names if name not in parameters]
    if missing:
        raise ExpressionError(f"缺少参数值: {', '.join(missing)}")
    symbols = [sp.Symbol(name, real=True) for name in (*variables, *parameter_names)]
    function = sp.lambdify(symbols, expressions, modules="numpy")
    try:
        raw_values = function(*coordinates, *(parameters[name] for name in parameter_names))
    except (ArithmeticError, TypeError, ValueError) as error:
        raise ExpressionError("无法在当前范围内计算该表达式。") from error
    if not isinstance(raw_values, tuple):
        raw_values = (raw_values,)
    shape = coordinates[0].shape
    values: list[np.ndarray] = []
    for raw_value in raw_values:
        value = np.asarray(raw_value, dtype=float)
        if value.ndim == 0:
            value = np.full(shape, float(value))
        try:
            values.append(np.broadcast_to(value, shape).copy())
        except ValueError as error:
            raise ExpressionError("表达式返回的坐标维度不匹配。") from error
    return tuple(values)


def _build_explicit_mesh(expression: SurfaceExpression, parameters: dict[str, float], domain: PlotDomain) -> pv.PolyData:
    axis_ranges = {"x": domain.x_range, "y": domain.y_range, "z": domain.z_range}
    dependent_axis = expression.dependent_axis
    if dependent_axis is None:
        raise ExpressionError("显式曲面缺少因变量坐标。")
    plane = _build_linear_plane_mesh(
        expression,
        parameters,
        domain,
        sp.Symbol(dependent_axis, real=True) - expression.simplified,
    )
    if plane is not None:
        return plane
    independent_axes = tuple(axis for axis in _COORDINATES if axis != dependent_axis)
    first_values = np.linspace(*axis_ranges[independent_axes[0]], domain.explicit_resolution)
    second_values = np.linspace(*axis_ranges[independent_axes[1]], domain.explicit_resolution)
    first_grid, second_grid = np.meshgrid(first_values, second_values, indexing="ij")
    dependent_values = _numeric_values(
        (expression.simplified,),
        _COORDINATES,
        tuple(
            {independent_axes[0]: first_grid, independent_axes[1]: second_grid}.get(axis, np.zeros_like(first_grid))
            for axis in _COORDINATES
        ),
        expression.parameter_names,
        parameters,
    )[0]
    valid = np.isfinite(dependent_values) & (dependent_values >= axis_ranges[dependent_axis][0]) & (dependent_values <= axis_ranges[dependent_axis][1])
    if not np.any(valid):
        return pv.PolyData()
    coordinate_grids: dict[str, np.ndarray] = {
        independent_axes[0]: first_grid,
        independent_axes[1]: second_grid,
        dependent_axis: np.where(valid, dependent_values, np.nan),
    }
    mesh = pv.StructuredGrid(coordinate_grids["x"], coordinate_grids["y"], coordinate_grids["z"]).extract_surface(
        algorithm="dataset_surface"
    )
    return _remove_invalid_points(mesh)


def _build_implicit_mesh(expression: SurfaceExpression, parameters: dict[str, float], domain: PlotDomain) -> pv.PolyData:
    plane = _build_linear_plane_mesh(expression, parameters, domain, expression.simplified)
    if plane is not None:
        return plane

    x_values = np.linspace(*domain.x_range, domain.implicit_resolution)
    y_values = np.linspace(*domain.y_range, domain.implicit_resolution)
    z_values = np.linspace(*domain.z_range, domain.implicit_resolution)
    x_grid, y_grid, z_grid = np.meshgrid(x_values, y_values, z_values, indexing="ij")
    field = _numeric_values(
        (expression.simplified,),
        _COORDINATES,
        (x_grid, y_grid, z_grid),
        expression.parameter_names,
        parameters,
    )[0]
    field[~np.isfinite(field)] = np.nan
    # 隐式曲面通过三维标量场的零等值面提取，网格间距须与采样点数量严格对应。
    grid = pv.ImageData(
        dimensions=(domain.implicit_resolution,) * 3,
        spacing=(
            (domain.x_range[1] - domain.x_range[0]) / (domain.implicit_resolution - 1),
            (domain.y_range[1] - domain.y_range[0]) / (domain.implicit_resolution - 1),
            (domain.z_range[1] - domain.z_range[0]) / (domain.implicit_resolution - 1),
        ),
        origin=(domain.x_range[0], domain.y_range[0], domain.z_range[0]),
    )
    grid.point_data["surface_field"] = field.ravel(order="F")
    return grid.contour([0.0], scalars="surface_field").clean()


def _build_linear_plane_mesh(
    expression: SurfaceExpression,
    parameters: dict[str, float],
    domain: PlotDomain,
    equation: sp.Expr,
) -> pv.PolyData | None:
    """当方程关于 x、y、z 均为线性时生成固定的矩形平面片。"""
    coordinates = tuple(sp.Symbol(axis, real=True) for axis in _COORDINATES)
    try:
        polynomial = sp.Poly(equation, *coordinates)
    except sp.PolynomialError:
        return None
    if polynomial.total_degree() > 1:
        return None

    coefficient_expressions = tuple(polynomial.coeff_monomial(axis) for axis in coordinates)
    constant_expression = polynomial.coeff_monomial(1)
    samples = np.zeros(1)
    values = _numeric_values(
        (*coefficient_expressions, constant_expression),
        _COORDINATES,
        (samples, samples, samples),
        expression.parameter_names,
        parameters,
    )
    normal = np.array([float(value[0]) for value in values[:3]])
    constant = float(values[3][0])
    normal_length = np.linalg.norm(normal)
    if normal_length <= np.finfo(float).eps:
        return None

    domain_center = np.array(
        [
            (domain.x_range[0] + domain.x_range[1]) / 2,
            (domain.y_range[0] + domain.y_range[1]) / 2,
            (domain.z_range[0] + domain.z_range[1]) / 2,
        ]
    )
    center = domain_center - (np.dot(normal, domain_center) + constant) / (normal_length**2) * normal
    half_diagonal = np.linalg.norm(
        [
            (domain.x_range[1] - domain.x_range[0]) / 2,
            (domain.y_range[1] - domain.y_range[0]) / 2,
            (domain.z_range[1] - domain.z_range[0]) / 2,
        ]
    )
    if np.linalg.norm(center - domain_center) > half_diagonal:
        return pv.PolyData()

    normal_unit = normal / normal_length
    reference = np.array((0.0, 0.0, 1.0))
    if abs(np.dot(normal_unit, reference)) > 0.9:
        reference = np.array((0.0, 1.0, 0.0))
    first_axis = np.cross(normal_unit, reference)
    first_axis /= np.linalg.norm(first_axis)
    second_axis = np.cross(normal_unit, first_axis)

    # 这里有意使用矩形参数片。若用体等值面采样平面，会被定义域立方体裁剪成
    # 六边形并产生阶梯边缘，不适合展示 z = x + y 这类教学平面。
    half_size = max(
        np.ptp(domain.x_range),
        np.ptp(domain.y_range),
        np.ptp(domain.z_range),
    ) / 2
    first_values = np.linspace(-half_size, half_size, domain.explicit_resolution)
    second_values = np.linspace(-half_size, half_size, domain.explicit_resolution)
    first_grid, second_grid = np.meshgrid(first_values, second_values, indexing="ij")
    points = center + first_grid[..., np.newaxis] * first_axis + second_grid[..., np.newaxis] * second_axis
    return pv.StructuredGrid(points[..., 0], points[..., 1], points[..., 2]).extract_surface(
        algorithm="dataset_surface"
    )


def _build_parametric_mesh(expression: SurfaceExpression, parameters: dict[str, float], domain: PlotDomain) -> pv.PolyData:
    if not expression.parameter_ranges:
        raise ExpressionError("参数曲面缺少参数范围。")
    try:
        u_range = tuple(float(bound) for bound in expression.parameter_ranges[0])
        v_range = tuple(float(bound) for bound in expression.parameter_ranges[1])
    except (TypeError, ValueError) as error:
        raise ExpressionError("参数范围必须能计算为实数。") from error
    if u_range[0] >= u_range[1] or v_range[0] >= v_range[1]:
        raise ExpressionError("参数范围必须从较小值递增到较大值。")
    u_values = np.linspace(*u_range, domain.explicit_resolution)
    v_values = np.linspace(*v_range, domain.explicit_resolution)
    u_grid, v_grid = np.meshgrid(u_values, v_values, indexing="ij")
    components = _numeric_values(
        expression.simplified,
        ("u", "v"),
        (u_grid, v_grid),
        expression.parameter_names,
        parameters,
    )
    valid = np.logical_and.reduce([np.isfinite(component) for component in components])
    valid &= (components[0] >= domain.x_range[0]) & (components[0] <= domain.x_range[1])
    valid &= (components[1] >= domain.y_range[0]) & (components[1] <= domain.y_range[1])
    valid &= (components[2] >= domain.z_range[0]) & (components[2] <= domain.z_range[1])
    if not np.any(valid):
        return pv.PolyData()
    coordinates = tuple(np.where(valid, component, np.nan) for component in components)
    mesh = pv.StructuredGrid(*coordinates).extract_surface(algorithm="dataset_surface")
    return _remove_invalid_points(mesh)


def _remove_invalid_points(mesh: pv.PolyData) -> pv.PolyData:
    """移除接触到绘图范围外采样点的单元。"""
    valid_points = np.isfinite(mesh.points).all(axis=1)
    if not np.all(valid_points):
        mesh = mesh.extract_points(valid_points, adjacent_cells=False).extract_surface(algorithm="dataset_surface")
    return mesh.clean()
