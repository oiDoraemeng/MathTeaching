"""Built-in linear algebra teaching cases for the 2D workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from services.scene_commands import CommandPlan


@dataclass(frozen=True)
class LinearAlgebraCase:
    id: str
    category: str
    name: str
    formula: str
    steps: tuple[str, ...]
    conclusion: str
    summary: str
    plan: CommandPlan


def _point(alias: str, coordinates: tuple[float, float]) -> dict[str, object]:
    return {"op": "point.upsert", "alias": alias, "coordinates": list(coordinates), "name": alias}


def _vector(alias: str, start: str, end: str, *, color: str, role: str = "primary", label: str = "") -> dict[str, object]:
    operation: dict[str, object] = {
        "op": "linear.upsert",
        "alias": alias,
        "kind": "vector",
        "start": start,
        "end": end,
        "color": color,
        "role": role,
    }
    if label:
        operation["label"] = label
    return operation


def _annotation(alias: str, text: str, position: tuple[float, float], *, color: str = "#d64545") -> dict[str, object]:
    return {"op": "annotation.upsert", "alias": alias, "text": text, "position": list(position), "color": color}


def _plan(*operations: dict[str, object]) -> CommandPlan:
    return CommandPlan(scene="2d", operations=tuple((*operations, {"op": "view.fit", "padding": 1.2})))


VECTOR_ADDITION: Final = LinearAlgebraCase(
    id="vector-addition",
    category="向量",
    name="向量加法",
    formula="a + b = (3, 3)",
    steps=("从原点 O 画出向量 a=(2,1) 和 b=(1,2)。", "将 b 平移到 a 的终点，形成平行四边形。", "从 O 指向对角点 C，得到和向量。"),
    conclusion="向量加法可用平行四边形法则表示，结果为 a+b=(3,3)。",
    summary="用平行四边形法则演示向量加法",
    plan=CommandPlan(
        scene="2d",
        summary="演示向量加法和平行四边形法",
        operations=(
            {"op": "teach.vector_addition", "a": [2, 1], "b": [1, 2], "show_parallelogram": True, "show_triangle_rule": True},
        ),
    ),
)


VECTOR_SUBTRACTION: Final = LinearAlgebraCase(
    id="vector-subtraction",
    category="向量",
    name="向量减法",
    formula="a - b = (1, -1)",
    steps=("取 a=(2,1) 和 b=(1,2)。", "减去 b 等价于加上 -b=(-1,-2)。", "从 O 指向结果点 C，得到 a-b=(1,-1)。"),
    conclusion="向量减法可以转化为加上相反向量。",
    summary="用相反向量演示向量减法",
    plan=_plan(
        _point("O", (0, 0)),
        _point("A", (2, 1)),
        _point("B", (-1, -2)),
        _point("C", (1, -1)),
        _vector("a", "O", "A", color="#2777b6", label="a=(2,1)"),
        _vector("minus_b", "O", "B", color="#2f9e5b", label="-b=(-1,-2)"),
        _vector("a_minus_b", "O", "C", color="#d64545", role="result", label="a-b=(1,-1)"),
        {"op": "linear.upsert", "alias": "subtraction_translate", "kind": "segment", "start": "A", "end": "C", "style": "dashed", "role": "construction", "color": "#6c7b8d"},
        _annotation("vector_subtraction_result", "a-b=(1, -1)", (0.75, -0.85)),
    ),
)


VECTOR_SCALAR_MULTIPLICATION: Final = LinearAlgebraCase(
    id="vector-scalar-multiplication",
    category="向量",
    name="向量数乘",
    formula="2a = 2(2,1) = (4,2)",
    steps=("取向量 a=(2,1)。", "数乘 2 保持方向不变，将长度扩大为原来的 2 倍。", "终点移动到 C=(4,2)。"),
    conclusion="向量数乘会按标量改变长度；正数不改变方向。",
    summary="演示标量如何改变向量长度",
    plan=_plan(
        _point("O", (0, 0)),
        _point("A", (2, 1)),
        _point("C", (4, 2)),
        _vector("a", "O", "A", color="#2777b6", label="a=(2,1)"),
        _vector("two_a", "O", "C", color="#d64545", role="result", label="2a=(4,2)"),
        {"op": "linear.upsert", "alias": "scalar_marker", "kind": "segment", "start": "A", "end": "C", "style": "dashed", "role": "construction", "color": "#6c7b8d"},
        _annotation("scalar_result", "2a=(4, 2)", (2.25, 1.55)),
    ),
)


VECTOR_DOT_PRODUCT: Final = LinearAlgebraCase(
    id="vector-dot-product",
    category="向量",
    name="向量内积",
    formula="a·b = 3×1 + 1×2 = 5",
    steps=("取 a=(3,1) 和 b=(1,2)。", "对应分量相乘后相加：3×1+1×2。", "结果是一个标量 5，可用于判断夹角关系。"),
    conclusion="内积把两个向量映射为标量；本例 a·b=5。",
    summary="演示分量乘积之和得到向量内积",
    plan=_plan(
        _point("O", (0, 0)),
        _point("A", (3, 1)),
        _point("B", (1, 2)),
        _vector("dot_a", "O", "A", color="#2777b6", label="a=(3,1)"),
        _vector("dot_b", "O", "B", color="#2f9e5b", label="b=(1,2)"),
        _annotation("dot_product_result", "a·b=5", (1.35, 1.55)),
    ),
)


VECTOR_CROSS_PRODUCT: Final = LinearAlgebraCase(
    id="vector-cross-product",
    category="向量",
    name="向量外积",
    formula="a×b = 3×2 - 1×1 = 5",
    steps=("取 a=(3,1) 和 b=(1,2)。", "两向量张成一个平行四边形。", "有向面积等于行列式 3×2-1×1=5。"),
    conclusion="二维向量外积用标量表示有向面积，本例结果为 5。",
    summary="用平行四边形面积演示二维向量外积",
    plan=CommandPlan(
        scene="2d",
        summary="演示向量外积对应的有向面积",
        operations=({"op": "linear_algebra.determinant_area", "a": [3, 1], "b": [1, 2], "show_basis": True},),
    ),
)


_CASES: Final[tuple[LinearAlgebraCase, ...]] = (
    VECTOR_ADDITION,
    VECTOR_SUBTRACTION,
    VECTOR_SCALAR_MULTIPLICATION,
    VECTOR_DOT_PRODUCT,
    VECTOR_CROSS_PRODUCT,
)


def linear_algebra_cases() -> tuple[LinearAlgebraCase, ...]:
    return _CASES


def linear_algebra_case(case_id: str) -> LinearAlgebraCase | None:
    return next((item for item in _CASES if item.id == case_id), None)
