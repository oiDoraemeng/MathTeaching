"""Chapter 3 determinant visualization recipes."""

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


def build_det_basic_properties(context: RenderContext) -> CommandPlan:
    """行列式的基本性质：目录配方保留有向面积图。"""
    return build_det_row_swap(context)


def build_det_transpose(context: RenderContext) -> CommandPlan:
    """转置不变性：目录配方保留两条邻边与有向面积图。"""
    return build_oriented_area(context)


def build_cramer_area_ratio(context: RenderContext) -> CommandPlan:
    """纯讲义主题只保留一个合法的无图场景计划。"""
    return build_text_only(context)


def build_inverse_undo(context: RenderContext) -> CommandPlan:
    """纯讲义主题只保留一个合法的无图场景计划。"""
    return build_text_only(context)


def build_text_only(context: RenderContext) -> CommandPlan:
    """Return a valid plan without teaching geometry or annotations."""
    return CommandPlan(
        scene="2d",
        operations=(make_view_fit(padding=1.15),),
        summary="仅显示讲义与数学案例",
    )


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
    "draw.ch03.det.basic-properties": build_det_basic_properties,
    "draw.ch03.det.row-swap": build_det_row_swap,
    "draw.ch03.det.scaling": build_det_scaling,
    "draw.ch03.det.shear": build_det_shear,
    "draw.ch03.det.multiplicativity": build_det_multiplicativity,
    "draw.ch03.det.transpose": build_det_transpose,
    "draw.ch03.cramer.area-ratio": build_cramer_area_ratio,
    "draw.ch03.inverse.undo": build_inverse_undo,
    "draw.ch03.adjugate.matrix": build_text_only,
    "draw.ch03.det.zero.equivalence": build_text_only,
}
