"""Chapter 2: Matrices and Transformations - 16 topic builders."""

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


def build_batch_inner_products(context: RenderContext) -> CommandPlan:
    """批量内积：矩阵向量乘法的几何理解"""
    v = [2.0, 1.5]
    a1 = [1.0, 0.5]
    a2 = [0.3, 1.2]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], a1, "a1", role="secondary"))
    ops.extend(make_vector_2d([0, 0], a2, "a2", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="矩阵与向量的内积序列")


def build_batch_projection(context: RenderContext) -> CommandPlan:
    """批量投影：投影矩阵"""
    v = [2.5, 2.0]
    u1 = [2.0, 0.5]
    u2 = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], u1, "u1", role="secondary"))
    ops.extend(make_vector_2d([0, 0], u2, "u2", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="向量在多个方向上的投影")


def build_matrix_additive_distributivity(context: RenderContext) -> CommandPlan:
    """矩阵乘法的加法分配律"""
    v = [2.0, 1.0]
    w = [1.0, 1.5]
    result = [v[0] + w[0], v[1] + w[1]]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], w, "w", role="secondary"))
    ops.extend(make_vector_2d([0, 0], result, "v_plus_w", role="result"))
    ops.append(make_polygon([[0, 0], v, result, w], opacity=0.12))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="矩阵对加法的线性性")


def build_matrix_row_column(context: RenderContext) -> CommandPlan:
    """行列视角的矩阵乘法"""
    v = [2.0, 1.5]
    row1 = [1.0, 0.5]
    row2 = [0.3, 1.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], row1, "row1", role="secondary"))
    ops.extend(make_vector_2d([0, 0], row2, "row2", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="行视角和列视角")


def build_transformed_grid(context: RenderContext) -> CommandPlan:
    """基向量的变换决定整个网格变换"""
    e1_orig = [1.0, 0.0]
    e2_orig = [0.0, 1.0]
    e1_new = [2.0, 0.5]
    e2_new = [0.5, 1.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], e1_orig, "e1_orig", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], e2_orig, "e2_orig", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], e1_new, "e1_new", role="primary"))
    ops.extend(make_vector_2d([0, 0], e2_new, "e2_new", role="secondary"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="基变换决定所有点的变换")


def build_stretch_rotate_scale(context: RenderContext) -> CommandPlan:
    """拉伸、旋转、缩放的几何含义"""
    v = [1.5, 1.0]
    stretched = [3.0, 1.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], stretched, "stretched", role="secondary"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="几何变换的直观")


def build_matrix_composition(context: RenderContext) -> CommandPlan:
    """矩阵复合：连续变换"""
    v = [1.0, 1.0]
    transformed1 = [2.0, 1.5]
    transformed2 = [3.5, 2.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], transformed1, "t1", role="secondary"))
    ops.extend(make_vector_2d([0, 0], transformed2, "t2", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="先后变换的复合")


def build_matrix_basis(context: RenderContext) -> CommandPlan:
    """矩阵列是基向量的像"""
    e1 = [1.0, 0.0]
    e2 = [0.0, 1.0]
    ae1 = [2.0, 0.5]
    ae2 = [0.5, 1.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], e1, "e1", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], e2, "e2", role="auxiliary", style="dashed"))
    ops.extend(make_vector_2d([0, 0], ae1, "Ae1", role="primary"))
    ops.extend(make_vector_2d([0, 0], ae2, "Ae2", role="secondary"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="矩阵列是标准基的像")


def build_matrix_powers(context: RenderContext) -> CommandPlan:
    """矩阵幂的几何含义"""
    v = [1.0, 0.8]
    av = [1.5, 1.0]
    aav = [2.0, 1.2]

    ops = []
    ops.extend(make_vector_2d([0, 0], v, "v", role="primary"))
    ops.extend(make_vector_2d([0, 0], av, "Av", role="secondary"))
    ops.extend(make_vector_2d([0, 0], aav, "A²v", role="result"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="重复应用变换")


def build_subspace_independence(context: RenderContext) -> CommandPlan:
    """线性无关与张成空间"""
    v1 = [2.0, 0.5]
    v2 = [0.5, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v1, "v1", role="primary"))
    ops.extend(make_vector_2d([0, 0], v2, "v2", role="secondary"))
    ops.append(make_polygon([[-3, -3], [3, -3], [3, 3], [-3, 3]], color=role_color("neutral"), opacity=0.05))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="两个无关向量张成平面")


def build_subspace_rank(context: RenderContext) -> CommandPlan:
    """秩：输出空间的维数"""
    v1 = [2.0, 1.0]
    v2 = [1.0, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v1, "v1", role="primary"))
    ops.extend(make_vector_2d([0, 0], v2, "v2", role="secondary"))
    ops.append(make_polygon([[-3, -3], [3, -3], [3, 3], [-3, 3]], color=role_color("vector_a"), opacity=0.08))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="输出空间的维数")


def build_subspace_null(context: RenderContext) -> CommandPlan:
    """零空间：被压缩到零的方向"""
    v_in_null = [1.0, -0.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v_in_null, "v", role="primary"))
    ops.append(make_label("→ 0", [0.5, -0.25], offset=[0.3, 0]))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="映射到零的向量集合")


def build_subspace_column(context: RenderContext) -> CommandPlan:
    """列空间：所有可能的输出"""
    v1 = [2.0, 0.8]
    v2 = [0.8, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v1, "col1", role="primary"))
    ops.extend(make_vector_2d([0, 0], v2, "col2", role="secondary"))
    ops.append(make_polygon([[-3, -3], [3, -3], [3, 3], [-3, 3]], color=role_color("vector_a"), opacity=0.08))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="列向量张成的输出空间")


def build_subspace_rank_nullity(context: RenderContext) -> CommandPlan:
    """秩-零化度定理"""
    v_in = [2.0, 1.0]
    v_null = [1.0, -0.5]
    v_out = [1.5, 1.5]

    ops = []
    ops.extend(make_vector_2d([0, 0], v_in, "input", role="primary"))
    ops.extend(make_vector_2d([0, 0], v_null, "null", role="auxiliary"))
    ops.extend(make_vector_2d([0, 0], v_out, "output", role="secondary"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="输入维数 = 秩 + 零化度")


def build_high_dimensional_matrix_analogy(context: RenderContext) -> CommandPlan:
    """高维矩阵的类比理解"""
    v1 = [2.0, 1.0]
    v2 = [1.0, 2.0]

    ops = []
    ops.extend(make_vector_2d([0, 0], v1, "v1", role="primary"))
    ops.extend(make_vector_2d([0, 0], v2, "v2", role="secondary"))
    ops.append(make_view_fit(padding=1.2))

    return CommandPlan(scene="2d", operations=tuple(ops), summary="从2D类比到高维")


BUILDERS = {
    "draw.ch02.batch.inner-products": build_batch_inner_products,
    "draw.ch02.batch.projection": build_batch_projection,
    "draw.ch02.matrix.additive-distributivity": build_matrix_additive_distributivity,
    "draw.ch02.matrix.row-column": build_matrix_row_column,
    "draw.ch02.matrix.transformed-grid": build_transformed_grid,
    "draw.ch02.matrix.stretch-rotate-scale": build_stretch_rotate_scale,
    "draw.ch02.matrix.composition": build_matrix_composition,
    "draw.ch02.matrix.basis": build_matrix_basis,
    "draw.ch02.matrix.powers": build_matrix_powers,
    "draw.ch02.subspace.independence": build_subspace_independence,
    "draw.ch02.subspace.rank": build_subspace_rank,
    "draw.ch02.subspace.null": build_subspace_null,
    "draw.ch02.subspace.column": build_subspace_column,
    "draw.ch02.subspace.rank-nullity": build_subspace_rank_nullity,
    "draw.ch02.high-dimensional.analogy": build_high_dimensional_matrix_analogy,
}
