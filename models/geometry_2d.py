"""二维交互几何对象及其代数显示文本。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, TypeAlias
from uuid import uuid4


LinearKind: TypeAlias = Literal["line", "segment", "ray", "vector"]
GeometryKind: TypeAlias = Literal["point", "line", "segment", "ray", "vector"]
LinearStyle: TypeAlias = Literal["solid", "dashed"]
LinearRole: TypeAlias = Literal["primary", "construction", "result"]
LINEAR_KINDS = frozenset(("line", "segment", "ray", "vector"))


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
    kind: Literal["point"] = field(default="point", init=False)


@dataclass
class Linear2D:
    """由两个端点定义的二维直线类几何对象。"""

    name: str
    kind: LinearKind
    start_point_id: str
    end_point_id: str
    visible: bool = True
    color: str = "#2777b6"
    line_width: float = 2.5
    id: str = field(default_factory=lambda: uuid4().hex)
    style: LinearStyle = "solid"
    role: LinearRole = "primary"
    label: str | None = None
    agent_alias: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in LINEAR_KINDS:
            raise ValueError(f"Unsupported linear geometry kind: {self.kind}")
        self.line_width = max(1.0, min(8.0, float(self.line_width)))
        if self.style not in {"solid", "dashed"}:
            raise ValueError(f"Unsupported linear style: {self.style}")
        if self.role not in {"primary", "construction", "result"}:
            raise ValueError(f"Unsupported linear role: {self.role}")


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


GeometryObject: TypeAlias = Point2D | Linear2D


def geometry_latex(
    geometry: GeometryObject,
    points: dict[str, Point2D],
) -> str:
    """返回适合 MathLive 只读预览的对象表达式。"""
    if isinstance(geometry, Point2D):
        return f"{geometry.name}=({format_number(geometry.x)}, {format_number(geometry.y)})"

    start = points.get(geometry.start_point_id)
    end = points.get(geometry.end_point_id)
    start_name = start.name if start is not None else geometry.start_point_id
    end_name = end.name if end is not None else geometry.end_point_id
    if geometry.kind == "line":
        if start is not None and end is not None:
            return _line_equation_latex(geometry.name, start, end)
        return f"{geometry.name}: {start_name}, {end_name}"
    if geometry.kind == "segment":
        return rf"{geometry.name}=\overline{{{start_name}{end_name}}}"
    if geometry.kind == "ray":
        return rf"{geometry.name}=\overrightarrow{{{start_name}{end_name}}}"
    return rf"\vec{{{geometry.name}}}=\overrightarrow{{{start_name}{end_name}}}"


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
    return f"{name}: {expression}=0"


def format_number(value: float) -> str:
    """将坐标和系数规整为易读的有限小数。"""
    if abs(value) <= 1e-10:
        return "0"
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


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
