"""Chapter 3: Determinants - 15 topic builders."""

from __future__ import annotations

from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import CommandPlan

from .primitives import (
    make_label,
    make_polygon,
    make_vector_2d,
    make_view_fit,
)
from ..palette import role_color


def build_oriented_area(context: RenderContext) -> CommandPlan:
    """行列式的几何定义：两列张成的有向平行四边形"""
    a = [2.0, 1.0]
    b = [1.0, 3.0]

    ops = []
    ops.append(make_polygon([[0, 0], [1, 0], [1, 1], [0, 1]], opacity=0.12, outline=True, color=role_color("neutral"), alias="unit_square"))
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.24, outline=True, color=role_color("area"), alias="oriented_area"))
    ops.append(make_label("5", [1.0, 1.6], offset=[0, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="行列式等于两列张成的有向平行四边形面积")


def build_det_row_swap(context: RenderContext) -> CommandPlan:
    """交换两行翻转方向"""
    a = [2.0, 0.5]
    b = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2, color=role_color("area"), alias="original_area"))
    ops.extend(make_vector_2d([0, 0], b, "b_swap", role="auxiliary"))
    ops.extend(make_vector_2d([0, 0], a, "a_swap", role="result"))
    ops.append(make_polygon([[0, 0], b, [a[0] + b[0], a[1] + b[1]], a], opacity=0.15, color=role_color("transformed_b"), alias="swapped_area"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="行交换改变行列式符号")


def build_det_scaling(context: RenderContext) -> CommandPlan:
    """一行数乘改变面积比例"""
    a = [2.0, 0.5]
    b = [0.5, 1.5]
    scaled_a = [3 * a[0], 3 * a[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15, alias="original_area"))
    ops.extend(make_vector_2d([0, 0], scaled_a, "3a", role="result"))
    ops.append(make_polygon([[0, 0], scaled_a, [scaled_a[0] + b[0], scaled_a[1] + b[1]], b], opacity=0.2, alias="scaled_area"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="行数乘使行列式倍增")


def build_det_shear(context: RenderContext) -> CommandPlan:
    """切变保持面积不变"""
    a = [2.0, 0.5]
    b = [0.5, 1.5]
    sheared_a = [a[0] + 1.5 * b[0], a[1] + 1.5 * b[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15, alias="original_area"))
    ops.extend(make_vector_2d([0, 0], sheared_a, "a_sheared", role="result"))
    ops.append(make_polygon([[0, 0], sheared_a, [sheared_a[0] + b[0], sheared_a[1] + b[1]], b], opacity=0.2, alias="sheared_area"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="切变不改变行列式")


def build_det_multiplicativity(context: RenderContext) -> CommandPlan:
    """det(AB) 的两阶段面积缩放"""
    v = [1.0, 1.0]
    av = [2.0, 1.5]
    bav = [3.0, 2.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], av, "Av", role="secondary"))
    ops.extend(make_vector_2d([0, 0], bav, "BAv", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="det(AB) = det(A)det(B)")


def build_cramer_area_ratio(context: RenderContext) -> CommandPlan:
    """克拉默法则的面积比解方程组"""
    a = [2.0, 0.5]
    b = [0.5, 2.0]
    target = [2.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.extend(make_vector_2d([0, 0], target, "target", role="result"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15, alias="basis_area"))
    ops.append(make_polygon([[0, 0], target, b], opacity=0.2, color=role_color("projection"), alias="target_area"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="面积比求解线性方程组")


def build_inverse_undo(context: RenderContext) -> CommandPlan:
    """逆矩阵的几何撤销"""
    v = [1.0, 1.0]
    av = [2.5, 1.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], av, "Av", role="secondary"))
    ops.extend(make_vector_2d(av, [av[0] + 1.5, av[1] + 0.5], "undo_arrow", role="result", style="dashed"))
    ops.append(make_label("A", [(v[0] + av[0]) / 2, (v[1] + av[1]) / 2], offset=[0, 0.3]))
    ops.append(make_label("A⁻¹", [av[0] + 0.75, av[1] + 0.25], offset=[0, 0.3]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="逆矩阵撤销变换")


def build_inverse_formula(context: RenderContext) -> CommandPlan:
    """2×2 求逆公式的几何参数"""
    a = [2.0, 0.5]
    b = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "col1", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "col2", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2, alias="cramer_area"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="逆矩阵公式的几何含义")


def build_inverse_examples(context: RenderContext) -> CommandPlan:
    """可逆与退化变换的分层例题"""
    a1 = [2.0, 0.5]
    b1 = [0.5, 2.0]
    a2 = [2.0, 1.0]
    b2 = [1.0, 0.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], a1, "a1", role="primary"))
    ops.extend(make_vector_2d([0, 0], b1, "b1", role="secondary"))
    ops.append(make_polygon([[0, 0], a1, [a1[0] + b1[0], a1[1] + b1[1]], b1], opacity=0.2))
    ops.extend(make_vector_2d([0, 0], a2, "a2", role="result"))
    ops.extend(make_vector_2d([0, 0], b2, "b2", role="auxiliary"))
    ops.append(make_view_fit(padding=1.3))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="对比可逆和不可逆矩阵")


def build_det_zero_equivalence(context: RenderContext) -> CommandPlan:
    """det=0 的等价几何条件"""
    a = [2.0, 1.0]
    b = [1.0, 0.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_label("共线", [1.0, 0.6], offset=[0.3, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="det=0等价于列向量共线")


BUILDERS = {
    "draw.ch03.det.oriented-area": build_oriented_area,
    "draw.ch03.det.row-swap": build_det_row_swap,
    "draw.ch03.det.scaling": build_det_scaling,
    "draw.ch03.det.shear": build_det_shear,
    "draw.ch03.det.multiplicativity": build_det_multiplicativity,
    "draw.ch03.cramer.area-ratio": build_cramer_area_ratio,
    "draw.ch03.inverse.undo": build_inverse_undo,
    "draw.ch03.inverse.formula": build_inverse_formula,
    "draw.ch03.inverse.examples": build_inverse_examples,
    "draw.ch03.det.zero.equivalence": build_det_zero_equivalence,
}
