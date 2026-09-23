"""二维交互几何对象及其代数显示文本。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Mapping, TypeAlias
from uuid import uuid4


LinearKind: TypeAlias = Literal["line", "segment", "ray", "vector"]
GeometryKind: TypeAlias = Literal["point", "line", "segment", "ray", "vector"]
LinearStyle: TypeAlias = Literal["solid", "dashed"]
LinearRole: TypeAlias = Literal["primary", "construction", "result"]
LinearLabelSide: TypeAlias = Literal["above", "below"]
PointConstraintKind: TypeAlias = Literal["midpoint", "intersection"]
LINEAR_KINDS = frozenset(("line", "segment", "ray", "vector"))
_VECTOR_EXPRESSION_PATTERN = re.compile(
    r"^\s*(?P<first>[+-]?[A-Za-z0-9_]+)"
    r"(?P<rest>(?:\s*[+-]\s*[A-Za-z0-9_]+)*)"
    r"\s*(?:=.*)?$"
)


@dataclass
class Point2D:
    """二维笛卡尔坐标平面中的一个命名点。"""

    name: str
    x: float
    y: float
    visible: bool = True
    color: str = "#d64545"
    id: str = field(default_factory=lambda: uuid4().hex)
    agent_alias: str | None = None
    constraint_kind: PointConstraintKind | None = None
    constraint_refs: tuple[str, ...] = ()
    constraint_owned: bool = False
    kind: Literal["point"] = field(default="point", init=False)

    def __post_init__(self) -> None:
        if self.constraint_kind not in {None, "midpoint", "intersection"}:
            raise ValueError(f"Unsupported point constraint: {self.constraint_kind}")
        self.constraint_refs = tuple(str(reference) for reference in self.constraint_refs)


@dataclass
class Linear2D:
    """由两个端点定义的二维直线类几何对象。"""

    name: str
    kind: LinearKind
    start_point_id: str
    end_point_id: str
    visible: bool = True
    color: str = "#2777b6"
    line_width: float = 3.2
    id: str = field(default_factory=lambda: uuid4().hex)
    style: LinearStyle = "solid"
    role: LinearRole = "primary"
    label: str | None = None
    # 标签方位需随几何对象持久化。
    label_side: LinearLabelSide = "below"
    # 标签偏移独立于线段端点。
    label_offset_x: float = 0.0
    label_offset_y: float = 0.0
    agent_alias: str | None = None
    # 关系生成的结果向量可能使用独立的无名端点。代数区仍需显示图中
    # 对应的可见端点名，因此把显示名与可拖动的内部点 ID 分开持久化。
    display_start_name: str = ""
    display_end_name: str = ""

    def __post_init__(self) -> None:
        if self.kind not in LINEAR_KINDS:
            raise ValueError(f"Unsupported linear geometry kind: {self.kind}")
        self.line_width = max(1.0, min(8.0, float(self.line_width)))
        if self.style not in {"solid", "dashed"}:
            raise ValueError(f"Unsupported linear style: {self.style}")
        if self.role not in {"primary", "construction", "result"}:
            raise ValueError(f"Unsupported linear role: {self.role}")
        if self.label_side not in {"above", "below"}:
            raise ValueError(f"Unsupported linear label side: {self.label_side}")
        self.label_offset_x = float(self.label_offset_x)
        self.label_offset_y = float(self.label_offset_y)


@dataclass
class Annotation2D:
    """二维教学标注，位置使用世界坐标。"""

    name: str
    text: str
    x: float
    y: float
    latex: str | None = None
    visible: bool = True
    color: str = "#263241"
    offset_x: float = 0.0
    offset_y: float = 0.0
    id: str = field(default_factory=lambda: uuid4().hex)
    agent_alias: str | None = None
    # 教学标注只读，用户在视口中创建的标记可编辑。
    editable: bool = False


GeometryObject: TypeAlias = Point2D | Linear2D


def _endpoint_display_name(
    preferred: str,
    point: Point2D | None,
    points: dict[str, Point2D],
) -> str:
    """Return a student-facing endpoint name without exposing an object ID."""
    name = preferred.strip()
    if name:
        return name
    if point is not None and point.name.strip():
        return point.name.strip()
    if point is not None:
        for candidate in points.values():
            if (
                candidate.id != point.id
                and candidate.name.strip()
                and abs(candidate.x - point.x) <= 1e-10
                and abs(candidate.y - point.y) <= 1e-10
            ):
                return candidate.name.strip()
    return ""


def _vector_expression_terms(label: str | None) -> tuple[tuple[str, str], ...] | None:
    """Split a short vector expression into terms for separate vector glyphs.

    A relation label is data, not LaTeX.  Treating ``2a-b`` as one symbol and
    interpolating it into ``\\vec{...}`` makes the rendered expression look like
    one vector named ``2a-b``.  A legacy label may also contain a trailing
    coordinate equation (``a+b=(x,y)``); that suffix is discarded.  Keep the
    coefficient beside the corresponding vector glyph, so ``2a-b`` becomes
    ``2\\vec{a}-\\vec{b}``.
    """
    if not isinstance(label, str):
        return None
    match = _VECTOR_EXPRESSION_PATTERN.fullmatch(label)
    if match is None:
        return None
    first = match.group("first")
    rest = match.group("rest")
    terms: list[tuple[str, str]] = []
    first_sign = "-" if first.startswith("-") else "+"
    first_term = first[1:] if first[:1] in "+-" else first
    if not first_term:
        return None
    terms.append((first_sign, first_term))
    for operator, term in re.findall(r"([+-])\s*([A-Za-z0-9_]+)", rest):
        terms.append((operator, term))
    return tuple(terms)


def _vector_symbol_latex(symbol: str, subscript: str = "") -> str:
    suffix = rf"_{{{subscript}}}" if subscript else ""
    return rf"\vec{{{symbol}}}{suffix}"


def _vector_term_latex(term: str) -> str:
    """Format one semantic vector term without absorbing scalars or matrices."""

    matrix_product = re.fullmatch(
        r"(?P<matrix>[A-Z]+|\([A-Z](?:[+-][A-Z])+\))"
        r"(?P<vector>[a-z])(?P<subscript>[0-9]*)",
        term,
    )
    if matrix_product is not None:
        return (
            matrix_product.group("matrix")
            + _vector_symbol_latex(
                matrix_product.group("vector"),
                matrix_product.group("subscript"),
            )
        )

    scalar_vector = re.fullmatch(
        r"(?P<coefficient>[0-9]+(?:\.[0-9]+)?)?"
        r"(?P<vector>[A-Za-z])(?P<subscript>[0-9]*)",
        term,
    )
    if scalar_vector is not None:
        return (
            (scalar_vector.group("coefficient") or "")
            + _vector_symbol_latex(
                scalar_vector.group("vector"),
                scalar_vector.group("subscript"),
            )
        )
    return rf"\vec{{{term}}}"


def _vector_expression_latex(label: str | None) -> str | None:
    if isinstance(label, str):
        compact = label.split("=", 1)[0].strip().replace(" ", "")
        if re.fullmatch(r"\([A-Z](?:[+-][A-Z])+\)[a-z][0-9]*", compact):
            return _vector_term_latex(compact)
    terms = _vector_expression_terms(label)
    if terms is None:
        return None
    parts: list[str] = []
    for index, (operator, term) in enumerate(terms):
        glyph = _vector_term_latex(term)
        if index == 0:
            parts.append(f"-{glyph}" if operator == "-" else glyph)
        else:
            parts.append(f"{operator}{glyph}")
    return "".join(parts)


def geometry_latex(
    geometry: GeometryObject,
    points: dict[str, Point2D],
) -> str:
    """返回适合 MathLive 只读预览的对象表达式。"""
    if isinstance(geometry, Point2D):
        return f"{geometry.name}=({format_number(geometry.x)}, {format_number(geometry.y)})"

    start = points.get(geometry.start_point_id)
    end = points.get(geometry.end_point_id)
    start_name = _endpoint_display_name(geometry.display_start_name, start, points)
    end_name = _endpoint_display_name(geometry.display_end_name, end, points)
    if geometry.kind == "line":
        if start is not None and end is not None:
            return _line_equation_latex(geometry.name, start, end)
        return geometry.name.strip()
    if geometry.kind == "segment":
        if not start_name or not end_name:
            return geometry.name.strip()
        prefix = f"{geometry.name}=" if geometry.name.strip() else ""
        return rf"{prefix}\overline{{{start_name}{end_name}}}"
    if geometry.kind == "ray":
        if not start_name or not end_name:
            return geometry.name.strip()
        prefix = f"{geometry.name}=" if geometry.name.strip() else ""
        return rf"{prefix}\overrightarrow{{{start_name}{end_name}}}"
    # 向量加法的和向量在代数区直接写成两个独立的向量，例如
    # ``\vec{a}+\vec{b}=\overrightarrow{AD}``。不能把 ``a+b`` 整体放进
    # 一个 ``\vec{...}``；结果向量的起点是关系专用的无名副本，端点名
    # 仍从可见点借用，绝不把内部 UUID 泄漏出去。
    expression = _vector_expression_latex(geometry.label)
    if expression is not None:
        if start_name and end_name:
            return rf"{expression}=\overrightarrow{{{start_name}{end_name}}}"
        # 数据缺少可见端点名时仍保持可读，不回退到内部点 ID。
        return expression
    symbol = (geometry.label or "").strip()
    if start_name and end_name:
        endpoint = rf"\overrightarrow{{{start_name}{end_name}}}"
        return rf"\vec{{{symbol}}}={endpoint}" if symbol else endpoint
    if symbol:
        # 1.1 的终点没有教学标签时，代数区仍应给出向量的坐标形式；
        # 这比只显示 ``\vec{{v}}`` 更完整，也不会把内部 ID 泄漏给学生。
        if start is not None and end is not None:
            dx = format_number(end.x - start.x)
            dy = format_number(end.y - start.y)
            return rf"\vec{{{symbol}}}=({dx}, {dy})"
        return rf"\vec{{{symbol}}}"
    # 没有向量符号时仅保留端点形式；没有可见端点则不生成占位公式。
    if start_name and end_name:
        return rf"\overrightarrow{{{start_name}{end_name}}}"
    return geometry.name.strip()


def _line_equation_latex(name: str, start: Point2D, end: Point2D) -> str:
    """根据两点生成一般式 ax + by + c = 0。"""
    a = start.y - end.y
    b = end.x - start.x
    c = start.x * end.y - end.x * start.y
    terms: list[str] = []
    for coefficient, symbol in ((a, "x"), (b, "y"), (c, "")):
        if abs(coefficient) <= 1e-10:
            continue
        magnitude = format_number(abs(coefficient))
        value = symbol if magnitude == "1" and symbol else f"{magnitude}{symbol}"
        if not terms:
            terms.append(f"-{value}" if coefficient < 0 else value)
        else:
            terms.append(f" {'-' if coefficient < 0 else '+'} {value}")
    expression = "".join(terms) or "0"
    prefix = f"{name}: " if name.strip() else ""
    return f"{prefix}{expression}=0"


def format_number(value: float) -> str:
    """将坐标和系数规整为易读的有限小数。"""
    if abs(value) <= 1e-10:
        return "0"
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def operation_label(operation: Mapping[str, object]) -> str:
    """返回计划声明的显示名；计划没声明就返回空串。

    别名（``ch04__relation__standard_readout__component_1__start``）是对象的身份，
    不是给人看的文字。一旦拿它兜底，窗格里就会出现一串内部编号当标记；没声明
    名字的辅助点（读数拐点、分量端点）本来也不需要标记，所以这里返回空串，
    由渲染层跳过。
    """
    name = operation.get("name")
    return name.strip() if isinstance(name, str) else ""


_COORDINATE_PATTERN = re.compile(
    r"""
    ^\s*
    (?:[A-Za-z][A-Za-z0-9_]*\s*=\s*)?          # 可选的 "A=" 前缀
    \\?[(\[]?\s*                                # 可选左括号（含 LaTeX 转义）
    (?P<x>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)      # x 分量
    \s*,\s*
    (?P<y>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)      # y 分量
    \s*\\?[)\]]?\s*$                            # 可选右括号
    """,
    re.VERBOSE,
)


def parse_point_coordinates(text: str) -> tuple[float, float] | None:
    """从形如 ``A=(1, 2)``、``(1,2)`` 或 ``1, 2`` 的文本解析坐标。

    解析失败时返回 ``None``，交由调用方给出错误提示。
    """
    cleaned = text.replace("\\left", "").replace("\\right", "").replace("{", "").replace("}", "")
    match = _COORDINATE_PATTERN.match(cleaned)
    if match is None:
        return None
    try:
        return float(match.group("x")), float(match.group("y"))
    except ValueError:
        return None
