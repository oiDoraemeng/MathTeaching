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


def build_oriented_area(context: RenderContext) -> CommandPlan:
    """行列式的有向面积定义"""
    a = [2.5, 0.5]
    b = [0.8, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2))
    ops.append(make_label("det>0", [1.0, 1.0], offset=[0, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="行列式是有向面积")


def build_ad_bc_decomposition(context: RenderContext) -> CommandPlan:
    """ad-bc 公式的面积分解"""
    a = [2.0, 0.5]
    b = [0.5, 1.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="ad-bc的几何推导")


def build_det_sign_zero_one(context: RenderContext) -> CommandPlan:
    """行列式符号、零和一的几何意义"""
    a1 = [1.5, 0.5]
    b1 = [0.5, 1.5]
    a2 = [1.0, 0.0]
    b2 = [0.0, 1.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a1, "a1", role="primary"))
    ops.extend(make_vector_2d([0, 0], b1, "b1", role="secondary"))
    ops.append(make_polygon([[0, 0], a1, [a1[0] + b1[0], a1[1] + b1[1]], b1], opacity=0.15))
    ops.extend(make_vector_2d([0, 0], a2, "a2", role="result"))
    ops.extend(make_vector_2d([0, 0], b2, "b2", role="auxiliary"))
    ops.append(make_polygon([[0, 0], a2, [a2[0] + b2[0], a2[1] + b2[1]], b2], opacity=0.1, outline=True, color="#888888"))
    ops.append(make_view_fit(padding=1.3))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="det的符号、零、一")


def build_det_examples(context: RenderContext) -> CommandPlan:
    """行列式面积缩放分层例题"""
    a = [2.0, 0.5]
    b = [0.8, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="计算和比较不同矩阵的行列式")


def build_det_row_swap(context: RenderContext) -> CommandPlan:
    """交换两行翻转方向"""
    a = [2.0, 0.5]
    b = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2, color="#5b8def"))
    ops.extend(make_vector_2d([0, 0], b, "b_swap", role="auxiliary"))
    ops.extend(make_vector_2d([0, 0], a, "a_swap", role="result"))
    ops.append(make_polygon([[0, 0], b, [a[0] + b[0], a[1] + b[1]], a], opacity=0.15, color="#ef5b5b"))
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
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15))
    ops.extend(make_vector_2d([0, 0], scaled_a, "3a", role="result"))
    ops.append(make_polygon([[0, 0], scaled_a, [scaled_a[0] + b[0], scaled_a[1] + b[1]], b], opacity=0.2))
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
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15))
    ops.extend(make_vector_2d([0, 0], sheared_a, "a_sheared", role="result"))
    ops.append(make_polygon([[0, 0], sheared_a, [sheared_a[0] + b[0], sheared_a[1] + b[1]], b], opacity=0.2))
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
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.15))
    ops.append(make_polygon([[0, 0], target, b], opacity=0.2, color="#9f70c0"))
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
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2))
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


def build_det_high_dimensional_volume(context: RenderContext) -> CommandPlan:
    """n 阶行列式与面积、体积类比"""
    a = [2.0, 0.5]
    b = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="secondary"))
    ops.append(make_polygon([[0, 0], a, [a[0] + b[0], a[1] + b[1]], b], opacity=0.2))
    ops.append(make_label("2D → area", [1.5, 1.5], offset=[0, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="从2D面积类比到高维体积")


def build_inverse_reverse_order(context: RenderContext) -> CommandPlan:
    """逆矩阵乘积的逆序撤销"""
    v = [1.0, 1.0]
    av = [2.0, 1.5]
    bav = [3.0, 2.8]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], av, "Av", role="secondary"))
    ops.extend(make_vector_2d([0, 0], bav, "BAv", role="result"))
    ops.append(make_label("B⁻¹A⁻¹", [2.0, 2.0], offset=[0.3, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="(AB)⁻¹ = B⁻¹A⁻¹")


BUILDERS = {
    "draw.ch03.det.oriented-area": build_oriented_area,
    "draw.ch03.det.ad-bc": build_ad_bc_decomposition,
    "draw.ch03.det.sign-zero-one": build_det_sign_zero_one,
    "draw.ch03.det.examples": build_det_examples,
    "draw.ch03.det.row-swap": build_det_row_swap,
    "draw.ch03.det.scaling": build_det_scaling,
    "draw.ch03.det.shear": build_det_shear,
    "draw.ch03.det.multiplicativity": build_det_multiplicativity,
    "draw.ch03.cramer.area-ratio": build_cramer_area_ratio,
    "draw.ch03.inverse.undo": build_inverse_undo,
    "draw.ch03.inverse.formula": build_inverse_formula,
    "draw.ch03.inverse.examples": build_inverse_examples,
    "draw.ch03.det.zero.equivalence": build_det_zero_equivalence,
    "draw.ch03.det.high-dimensional-volume": build_det_high_dimensional_volume,
    "draw.ch03.inverse.reverse-order": build_inverse_reverse_order,
}
