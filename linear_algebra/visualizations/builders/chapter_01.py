"""Chapter 1: Vectors and Geometric Measurement - 12 topic builders."""

from __future__ import annotations

from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import CommandPlan

from .primitives import (
    make_angle_arc,
    make_label,
    make_polygon,
    make_projection,
    make_vector_2d,
    make_view_fit,
)
from ..palette import role_color


def build_vector_magnitude(context: RenderContext) -> CommandPlan:
    """向量的几何量：方向、长度与零向量"""
    v = [2.5, 1.8]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.append(make_label("v", [v[0] / 2, v[1] / 2], offset=[0.2, 0.2]))
    ops.append(make_label("O", [0, 0], offset=[-0.3, -0.3]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(
        scene="2d", operations=tuple(ops), summary="向量的方向、长度与零向量"
    )


def build_vector_addition(context: RenderContext) -> CommandPlan:
    """向量加法：显示 a + b = c 的平行四边形法则"""
    a = [2.0, 1.0]
    b = [1.0, 2.0]
    c = [a[0] + b[0], a[1] + b[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.extend(make_vector_2d(a, c, "b_translated", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], c, "result", role="result"))
    ops.append(make_polygon([[0, 0], a, c, b], opacity=0.15))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[-0.2, -0.2]))
    ops.append(make_label("b", [b[0] / 2, b[1] / 2], offset=[0.2, 0.2]))
    ops.append(make_label("a+b", [c[0] / 2, c[1] / 2], offset=[0.2, 0]))
    ops.append(make_view_fit(padding=1.15))

    return CommandPlan(
        scene="2d", operations=tuple(ops), summary="向量加法的平行四边形法则"
    )


def build_vector_subtraction(context: RenderContext) -> CommandPlan:
    """向量减法：显示 a - b = a + (-b)"""
    a = [3.0, 2.0]
    b = [1.0, 2.0]
    neg_b = [-b[0], -b[1]]
    result = [a[0] - b[0], a[1] - b[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], neg_b, "neg_b", role="secondary"))
    ops.extend(
        make_vector_2d(a, result, "neg_b_translated", role="auxiliary", style="dashed")
    )
    ops.extend(make_vector_2d([0, 0], result, "result", role="result"))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[0.2, 0]))
    ops.append(make_label("b", [b[0] / 2, b[1] / 2], offset=[0.2, 0.2]))
    ops.append(make_label("-b", [neg_b[0] / 2, neg_b[1] / 2], offset=[-0.3, 0]))
    ops.append(make_label("a-b", [result[0] / 2, result[1] / 2], offset=[0, -0.3]))
    ops.append(make_view_fit(padding=1.15))

    return CommandPlan(
        scene="2d", operations=tuple(ops), summary="向量减法：a - b = a + (-b)"
    )


def build_vector_scalar(context: RenderContext) -> CommandPlan:
    """向量数乘与共线"""
    a = [1.5, 1.0]
    two_a = [2 * a[0], 2 * a[1]]
    neg_a = [-a[0], -a[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], two_a, "two_a", role="secondary"))
    ops.extend(make_vector_2d([0, 0], neg_a, "neg_a", role="auxiliary"))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[0.2, 0.2]))
    ops.append(make_label("2a", [two_a[0] / 2, two_a[1] / 2], offset=[0.2, 0]))
    ops.append(make_label("-a", [neg_a[0] / 2, neg_a[1] / 2], offset=[-0.3, -0.3]))
    ops.append(make_view_fit(padding=1.15))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="数乘改变长度和方向")


def build_linear_combination(context: RenderContext) -> CommandPlan:
    """线性组合：αa + βb"""
    a = [2.0, 0.5]
    b = [0.5, 1.5]
    alpha = 1.5
    beta = 0.8
    alpha_a = [alpha * a[0], alpha * a[1]]
    beta_b = [beta * b[0], beta * b[1]]
    result = [alpha_a[0] + beta_b[0], alpha_a[1] + beta_b[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.extend(
        make_vector_2d([0, 0], alpha_a, "alpha_a", role="auxiliary", style="dashed")
    )
    ops.extend(
        make_vector_2d(
            alpha_a, result, "beta_b_translated", role="auxiliary", style="dashed"
        )
    )
    ops.extend(make_vector_2d([0, 0], result, "result", role="result"))
    ops.append(make_polygon([[0, 0], alpha_a, result, beta_b], opacity=0.12))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[0, -0.3]))
    ops.append(make_label("b", [b[0] / 2, b[1] / 2], offset=[-0.3, 0]))
    ops.append(make_label("αa+βb", [result[0] / 2, result[1] / 2], offset=[0.2, 0]))
    ops.append(make_view_fit(padding=1.15))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="线性组合生成新向量")


def build_inner_product_definitions(context: RenderContext) -> CommandPlan:
    """内积、夹角与投影"""
    a = [3.0, 1.0]
    b = [1.5, 2.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_angle_arc([0, 0], a, b, radius=0.5))
    ops.append(make_projection(a, b))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[0.2, 0]))
    ops.append(make_label("b", [b[0] / 2, b[1] / 2], offset=[-0.2, 0.2]))
    ops.append(make_label("θ", [0.3, 0.3], offset=[0, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="内积、夹角与投影的关系")


def build_cauchy_schwarz(context: RenderContext) -> CommandPlan:
    """柯西—施瓦茨不等式：投影长度不超过原向量长度。"""
    a = [3.0, 0.0]
    b = [2.0, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_projection(b, a))
    ops.append(make_label("a", [a[0] / 2, a[1] / 2], offset=[0.2, 0]))
    ops.append(make_label("b", [b[0] / 2, b[1] / 2], offset=[-0.2, 0.2]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="投影长度不超过原向量")


def build_projection_definition(context: RenderContext) -> CommandPlan:
    """投影、垂足与残差"""
    v = [2.5, 2.0]
    u = [2.5, 0.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], u, "u", role="secondary"))
    ops.append(make_projection(v, u))
    ops.append(make_label("v", [v[0] / 2, v[1] / 2], offset=[0.2, 0.2]))
    ops.append(make_label("u", [u[0] / 2, u[1] / 2], offset=[0.2, -0.2]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="投影分解为平行和正交分量")


def build_midline_theorem(context: RenderContext) -> CommandPlan:
    """三角形中位线定理"""
    a = [0, 0]
    b = [4, 0]
    c = [2, 3]
    m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
    n = [(b[0] + c[0]) / 2, (b[1] + c[1]) / 2]

    ops = []
    ops.append(make_polygon([a, b, c], opacity=0.1))
    ops.extend(make_vector_2d(m, n, "midline", role="result"))
    ops.append({"op": "point.upsert", "alias": "M", "coordinates": m, "name": "M"})
    ops.append({"op": "point.upsert", "alias": "N", "coordinates": n, "name": "N"})
    ops.append({"op": "point.upsert", "alias": "A", "coordinates": a, "name": "A"})
    ops.append({"op": "point.upsert", "alias": "B", "coordinates": b, "name": "B"})
    ops.append({"op": "point.upsert", "alias": "C", "coordinates": c, "name": "C"})
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="中位线平行且长度减半")


def build_centroid_theorem(context: RenderContext) -> CommandPlan:
    """三角形重心定理"""
    a = [0, 0]
    b = [4, 0]
    c = [2, 3.5]
    g = [(a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3]

    ops = []
    ops.append(make_polygon([a, b, c], opacity=0.1))
    ops.extend(make_vector_2d(a, g, "ag", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d(b, g, "bg", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d(c, g, "cg", role="auxiliary", style="dashed"))
    ops.append({"op": "point.upsert", "alias": "G", "coordinates": g, "name": "G"})
    ops.append({"op": "point.upsert", "alias": "A", "coordinates": a, "name": "A"})
    ops.append({"op": "point.upsert", "alias": "B", "coordinates": b, "name": "B"})
    ops.append({"op": "point.upsert", "alias": "C", "coordinates": c, "name": "C"})
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="三条中线交于重心")


def build_parallelogram_diagonals(context: RenderContext) -> CommandPlan:
    """平行四边形对角线互相平分"""
    a = [0, 0]
    b = [3, 0.5]
    c = [4, 2.5]
    d = [1, 2]
    mid = [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2]

    ops = []
    ops.append(make_polygon([a, b, c, d], opacity=0.1))
    ops.extend(make_vector_2d(a, c, "ac", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d(b, d, "bd", role="auxiliary", style="dashed"))
    ops.append({"op": "point.upsert", "alias": "M", "coordinates": mid, "name": "M"})
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="对角线共同中点")


# Builder registry for Chapter 1
BUILDERS = {
    "draw.ch01.vector.magnitude": build_vector_magnitude,
    "draw.ch01.ops.addition": build_vector_addition,
    "draw.ch01.ops.subtraction": build_vector_subtraction,
    "draw.ch01.ops.scalar": build_vector_scalar,
    "draw.ch01.ops.linear-combination": build_linear_combination,
    "draw.ch01.inner.definitions": build_inner_product_definitions,
    "draw.ch01.inner.cauchy-schwarz": build_cauchy_schwarz,
    "draw.ch01.projection.definition": build_projection_definition,
    "draw.ch01.proof.midline": build_midline_theorem,
    "draw.ch01.proof.centroid": build_centroid_theorem,
    "draw.ch01.proof.parallelogram-diagonals": build_parallelogram_diagonals,
}
