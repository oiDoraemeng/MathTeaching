"""Closed declarative mathematical specifications for chapter 4 visuals.

Artifacts, contracts, and the family compiler all consume these records.  No
topic meaning is inferred from display titles or from positional fallbacks.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

SemanticValue = int | float | tuple[object, ...]


@dataclass(frozen=True)
class EntityDescriptor:
    role: str
    kind: str
    dimension: int
    value: SemanticValue
    label: str


@dataclass(frozen=True)
class RelationDescriptor:
    name: str
    kind: str
    source_role: str
    target_role: str
    parameters: tuple[tuple[str, SemanticValue], ...] = ()

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.parameters)


@dataclass(frozen=True)
class StageDescriptor:
    name: str
    title: str
    layout: str
    input_roles: tuple[str, ...]
    output_roles: tuple[str, ...]
    relation_names: tuple[str, ...]
    invariants: tuple[str, ...]
    # 该步骤自己的公式标注。留空表示沿用主题级 formula——只有前后步骤说的不是同一个
    # 式子的主题才需要给出，例如 4.3 的两步分别是标准基读数与新基读数。
    caption: str = ""


@dataclass(frozen=True)
class Chapter4Semantic:
    scene_kind: str
    family: str
    capabilities: tuple[str, ...]
    entities: tuple[EntityDescriptor, ...]
    relations: tuple[RelationDescriptor, ...]
    stages: tuple[StageDescriptor, ...]
    invariants: tuple[str, ...]
    expected_operations: tuple[str, ...]
    formula: str
    example_kind: str
    example_given: SemanticValue
    example_result: SemanticValue
    mutation_role: str

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(entity.role for entity in self.entities)

    @property
    def relation(self) -> str:
        return self.relations[0].kind

    @property
    def primitive(self) -> str:
        return self.entities[0].kind

    @property
    def operation(self) -> str:
        return self.expected_operations[0]

    @property
    def required_kinds(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(entity.kind for entity in self.entities))


def V(*x: float) -> tuple[float, ...]: return tuple(float(v) for v in x)
def M(*rows: tuple[float, ...]) -> tuple[tuple[float, ...], ...]: return tuple(rows)
def E(role: str, kind: str, dim: int, value: SemanticValue, label: str = "") -> EntityDescriptor:
    return EntityDescriptor(role, kind, dim, value, label or role)
def R(name: str, kind: str, source: str, target: str, **params: SemanticValue) -> RelationDescriptor:
    return RelationDescriptor(name, kind, source, target, tuple(params.items()))
def S(name: str, title: str, inputs: tuple[str, ...], outputs: tuple[str, ...], relations: tuple[str, ...], invariants: tuple[str, ...], layout: str = "sequence", caption: str = "") -> StageDescriptor:
    return StageDescriptor(name, title, layout, inputs, outputs, relations, invariants, caption)

I2 = M(V(1, 0), V(0, 1))
I3 = M(V(1, 0, 0), V(0, 1, 0), V(0, 0, 1))
XY = M(V(1, 0, 0), V(0, 1, 0))
A10 = M(V(1, 0), V(0, 0))

_MAPPING: dict[str, Chapter4Semantic] = {
"ch04.space.closure": Chapter4Semantic(
 "2d", "subspace_region", ("vector_2d", "polygon_2d", "subspace_region"),
 (E("space","subspace",2,I2,"R²"), E("vector_a","vector",2,V(1,0),"u"), E("vector_b","vector",2,V(0,1),"v"), E("sum","vector",2,V(1,1),"u+v"), E("scaled","vector",2,V(2,0),"2u")),
 (R("addition","sum","vector_a","sum",other_vector=V(0,1),expected_result=V(1,1)), R("scaling","scalar_multiple","vector_a","scaled",scalar=2.0,expected_result=V(2,0)), R("sum_membership","contains","space","sum",expected_rank=2.0), R("scaled_membership","contains","space","scaled",expected_rank=2.0)),
 (S("addition","加法封闭",("space","vector_a","vector_b"),("sum",),("addition","sum_membership"),("additive_closure",)), S("scaling","数乘封闭",("space","vector_a"),("scaled",),("scaling","scaled_membership"),("scalar_closure",))),
 ("additive_closure","scalar_closure"), ("geometry.subspace_region","geometry.polygon","linear.upsert"), r"u+v=(1,1)\in R^2,\ 2u=(2,0)\in R^2", "vector_addition", (V(1,0),V(0,1)), V(1,1), "sum"),

"ch04.subspace.classification": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("origin","point",3,V(0,0,0),"{0}"), E("line","subspace",3,M(V(1,0,0)),"直线"), E("plane","subspace",3,XY,"平面"), E("whole_space","subspace",3,I3,"R³"), E("affine_counterexample","affine_set",3,M(V(1,0,0),V(0,1,0),V(0,0,1)),"z=1")),
 (R("zero_case","classification","origin","origin",expected_dimension=0.0,contains_origin=1.0), R("line_case","classification","origin","line",expected_dimension=1.0,contains_origin=1.0), R("plane_case","classification","origin","plane",expected_dimension=2.0,contains_origin=1.0), R("space_case","classification","origin","whole_space",expected_dimension=3.0,contains_origin=1.0), R("affine_failure","affine_translation","plane","affine_counterexample",offset=V(0,0,1),contains_origin=0.0)),
 (S("linear_cases","四类子空间",("origin",),("line","plane","whole_space"),("zero_case","line_case","plane_case","space_case"),("classification_dimensions","origin_contains"),"overlay"), S("affine_case","仿射反例",("plane",),("affine_counterexample",),("affine_failure",),("affine_not_subspace",),"side_by_side")),
 ("classification_dimensions","origin_contains","affine_not_subspace"), ("point3d.upsert","linear3d.upsert","plane3d.upsert"), r"\dim\{0\}=0,\dim L=1,\dim P=2,\dim R^3=3;\ (0,0,1)+P\not\ni0", "oriented_volume", (V(1,0,0),V(0,1,0),V(0,0,1)), 1.0, "affine_counterexample"),

"ch04.subspace.intersection": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("subspace_u","subspace",3,XY,"U=xy"), E("subspace_v","subspace",3,M(V(1,0,0),V(0,0,1)),"V=xz"), E("intersection","subspace",3,M(V(1,0,0)),"U∩V"), E("union_u","vector",3,V(0,1,0),"u"), E("union_v","vector",3,V(0,0,1),"v"), E("union_sum","vector",3,V(0,1,1),"u+v")),
 (R("intersection_result","intersects_in","subspace_u","subspace_v",expected_basis=M(V(1,0,0))), R("intersection_membership","contains","intersection","union_sum",expected_membership=0.0), R("union_addition","union_counterexample","union_u","union_sum",other_vector=V(0,0,1),in_union=0.0)),
 (S("intersection","交集",("subspace_u","subspace_v"),("intersection",),("intersection_result",),("intersection_closed",),"overlay"), S("union","并集反例",("union_u","union_v"),("union_sum",),("intersection_membership","union_addition"),("union_not_closed",))),
 ("intersection_closed","union_not_closed"), ("plane3d.upsert","geometry.intersection","geometry.parallelogram3d"), r"U\cap V=\operatorname{span}(e_1);\ e_2+e_3\notin U\cup V", "cross_product", (V(0,0,1),V(0,1,0)), V(-1,0,0), "union_sum"),

"ch04.subspace.col-null": Chapter4Semantic(
 # 4.1.3 的三维类比：A=diag(1,1,0) 把 R³ 沿竖直方向压到 xy 平面，正是讲义二维图
 # A=(1 0;0 0)（压到 x 轴）升一维的结果。矩阵只作为关系参数，不再单独画成一个与
 # 列空间重合的平面；两组案例都用多支采样向量把「子空间」本身铺出来：
 #   列空间：三支高度和水平方向都不同的输入，输出全部落在平面上、并把平面铺开三个方向；
 #   零空间：一支垂直于平面的代表输入被压到原点。
 #   零空间窗格只放这条主线：那张平面、一支竖直向量、原点，加上平面上下各一小段虚线；
 #   一支轴外向量都不放（轴外采样全部留在列空间窗格），否则「垂直于平面」会被读糊。
 "3d", "subspace_region", ("vector_3d","subspace_region","linear3d","plane3d"),
 (E("column_space","subspace",3,XY,"Col(A)"), E("null_space","subspace",3,M(V(0,0,1)),"Null(A)"),
  E("input_vector_a","vector",3,V(2,0,3),"x1"), E("output_vector_a","vector",3,V(2,0,0),"A x1"),
  E("input_vector_b","vector",3,V(-1,2,2),"x2"), E("output_vector_b","vector",3,V(-1,2,0),"A x2"),
  E("input_vector_c","vector",3,V(-1,-2,1),"x3"), E("output_vector_c","vector",3,V(-1,-2,0),"A x3"),
  E("kernel_vector","vector",3,V(0,0,3),"k"),
  E("zero","point",3,V(0,0,0),"0")),
 (R("projection_a","maps_to","input_vector_a","output_vector_a",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(2,0,3),expected_result=V(2,0,0)),
  R("projection_b","maps_to","input_vector_b","output_vector_b",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(-1,2,2),expected_result=V(-1,2,0)),
  R("projection_c","maps_to","input_vector_c","output_vector_c",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(-1,-2,1),expected_result=V(-1,-2,0)),
  R("collapse","maps_to","kernel_vector","zero",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(0,0,3),expected_result=V(0,0,0))),
 (S("column_space","列空间：所有可能的输出",("input_vector_a","input_vector_b","input_vector_c","column_space"),("output_vector_a","output_vector_b","output_vector_c"),("projection_a","projection_b","projection_c"),("diag_1_1_0","image_xy_plane"),"side_by_side"),
  S("null_space","零空间：与平面垂直的方向被压成一点",("column_space","null_space","kernel_vector"),("zero",),("collapse",),("kernel_to_zero",),"side_by_side")),
 ("diag_1_1_0","kernel_to_zero","image_xy_plane"), ("plane3d.upsert","linear3d.upsert","point3d.upsert"), r"\boldsymbol A=\operatorname{diag}(1,1,0),\ Null(\boldsymbol A)=\operatorname{span}(\boldsymbol e_3),\ Col(\boldsymbol A)=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)", "matrix_transform", (M(V(1,0,0),V(0,1,0),V(0,0,0)),V(2,0,3)), V(2,0,0), "kernel_vector"),
"ch04.span.dimension": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("span_1d","basis",3,M(V(1,0,0))), E("span_2d","basis",3,XY), E("span_3d","basis",3,I3)),
 (R("one_dimensional","dimension_of","span_1d","span_1d",expected_dimension=1.0), R("two_dimensional","dimension_of","span_2d","span_2d",expected_dimension=2.0), R("three_dimensional","dimension_of","span_3d","span_3d",expected_dimension=3.0)),
 (S("line","一向量张成直线",("span_1d",),("span_1d",),("one_dimensional",),("span_rank_1",)), S("plane","两向量张成平面",("span_2d",),("span_2d",),("two_dimensional",),("span_rank_2",)), S("space","三向量张成空间",("span_3d",),("span_3d",),("three_dimensional",),("span_rank_3","rank_equals_dimension"))),
 ("span_rank_1","span_rank_2","span_rank_3","rank_equals_dimension"), ("linear3d.upsert","plane3d.upsert"), r"\dim span(e_1)=1,\dim span(e_1,e_2)=2,\dim span(e_1,e_2,e_3)=3", "oriented_volume", (V(1,0,0),V(0,1,0),V(0,0,1)), 1.0, "span_3d"),

"ch04.dependence.redundancy": Chapter4Semantic(
 "3d", "basis_change", ("vector_3d","parallelepiped_3d"),
 (E("dependent_set","basis",3,M(V(1,0,0),V(0,1,0),V(1,1,0)),"相关组"), E("independent_set","basis",3,I3,"无关组"), E("coefficients","vector",3,V(1,1,-1),"(1,1,-1)"), E("zero_combination","point",3,V(0,0,0),"0"), E("redundant_vector","vector",3,V(1,1,0),"c₃")),
 (R("dependent_combination","linear_combination","dependent_set","zero_combination",coefficients=V(1,1,-1),expected_result=V(0,0,0)), R("independent_rank","dimension_of","independent_set","independent_set",expected_dimension=3.0), R("redundancy","sum","dependent_set","redundant_vector",coefficients=V(1,1,-1),expected_result=V(1,1,0))),
 (S("dependent","非零系数组合为零",("dependent_set","coefficients"),("zero_combination","redundant_vector"),("dependent_combination","redundancy"),("nonzero_coefficients_sum_zero",)), S("independent","满秩无关组",("independent_set",),("independent_set",),("independent_rank",),("independent_full_rank",))),
 ("nonzero_coefficients_sum_zero","independent_full_rank"), ("linear3d.upsert","geometry.parallelogram3d","geometry.parallelepiped"), r"c_1+c_2-c_3=0,\ rank[e_1\ e_2\ e_3]=3", "oriented_volume", (V(1,0,0),V(0,1,0),V(0,0,1)), 1.0, "coefficients"),

"ch04.nullspace.test": Chapter4Semantic(
 "3d", "basis_change", ("vector_3d","parallelepiped_3d"),
 (E("columns","matrix",3,M(V(1,0,1),V(0,1,1),V(0,0,0)),"A"), E("null_vector","vector",3,V(1,1,-1),"x≠0"), E("zero","point",3,V(0,0,0),"Ax=0"), E("independent_columns","matrix",3,I3,"I"), E("trivial_nullspace","point",3,V(0,0,0),"仅零解")),
 (R("nontrivial_solution","null_solution","columns","null_vector",matrix=M(V(1,0,1),V(0,1,1),V(0,0,0)),expected_result=V(0,0,0)), R("zero_result","maps_to","null_vector","zero",matrix=M(V(1,0,1),V(0,1,1),V(0,0,0)),expected_result=V(0,0,0)), R("trivial_solution","null_solution","independent_columns","trivial_nullspace",matrix=I3,expected_nullity=0.0)),
 (S("nontrivial","非零零空间解",("columns","null_vector"),("zero",),("nontrivial_solution","zero_result"),("Ax_zero","nonzero_null_solution")), S("trivial","无关列只有零解",("independent_columns",),("trivial_nullspace",),("trivial_solution",),("trivial_nullspace_only",))),
 ("Ax_zero","nonzero_null_solution","trivial_nullspace_only"), ("linear3d.upsert","geometry.parallelogram3d","point3d.upsert"), r"A(1,1,-1)^T=0,\ Ix=0\Rightarrow x=0", "matrix_transform", (M(V(1,0,1),V(0,1,1),V(0,0,0)),V(1,1,-1)), V(0,0,0), "null_vector"),

"ch04.rank.collapse": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","subspace_region"),
 (E("rank_two","matrix",2,I2), E("rank_one","matrix",2,A10), E("rank_zero","matrix",2,M(V(0,0),V(0,0))), E("plane_image","subspace",2,I2), E("line_image","subspace",2,M(V(1,0))), E("point_image","point",2,V(0,0),"O")),
 (R("rank_two_result","rank_of","rank_two","plane_image",expected_rank=2.0), R("rank_one_result","rank_of","rank_one","line_image",expected_rank=1.0), R("rank_zero_result","rank_of","rank_zero","point_image",expected_rank=0.0)),
 (S("rank_two","rank 2 平面",("rank_two",),("plane_image",),("rank_two_result",),("rank_two_plane",)), S("rank_one","rank 1 直线",("rank_one",),("line_image",),("rank_one_result",),("rank_one_line",)), S("rank_zero","rank 0 原点",("rank_zero",),("point_image",),("rank_zero_result",),("rank_zero_point","rank_collapse_sequence"))),
 ("rank_two_plane","rank_one_line","rank_zero_point","rank_collapse_sequence"), ("geometry.transformed_grid","geometry.subspace_region","point.upsert"), r"rank(I)=2,\ rank(diag(1,0))=1,\ rank(0)=0", "determinant", I2, 1.0, "rank_one"),
"ch04.basis.definition": Chapter4Semantic(
 # 4.3 合并后的唯一条目：定义（4.3.1 定义 4.10 与维数）、维数（4.3.2）、坐标（4.3.3）
 # 写在同一小节里。两个窗格画同一个向量终点：标准基一格、斜基一格。点完全不动，
 # 只把尺子换成 B={b1=(1,1),b2=(1,-1)}，读数就从 (5,3) 变成 (4,1)——坐标不是向量
 # 本身，是向量相对某一组基的读数。数字取讲义 4.3.3 例 4（B 的列就是那两根基向量）。
 # 坐标读数只作为关系的参数（coordinates）存在，不另立实体：否则窗格里会多出两支与
 # 主向量完全重合的箭头，反而把「同一个向量」读糊。
 "2d", "basis_change", ("transformed_grid","vector_2d"),
 (E("standard_basis","basis",2,I2,"e"), E("oblique_basis","basis",2,M(V(1,1),V(1,-1)),"B"), E("same_vector","vector",2,V(5,3),"x")),
 (R("standard_readout","coordinate_equivalence","standard_basis","same_vector",basis_matrix=I2,coordinates=V(5,3),expected_vector=V(5,3)), R("oblique_readout","coordinate_equivalence","oblique_basis","same_vector",basis_matrix=M(V(1,1),V(1,-1)),coordinates=V(4,1),expected_vector=V(5,3))),
 # 两格各有自己的标注：左边写标准基这把尺子怎么读出 (5,3)，右边写换尺子之后
 # 用矩阵形式解出的读数 (4,1)。矩阵一律写成 pmatrix，不再图省事挤成一行。
 (S("standard","标准基下的读数",("standard_basis","same_vector"),("same_vector",),("standard_readout",),("standard_reconstruction",),"side_by_side",r"\boldsymbol x=5\boldsymbol e_1+3\boldsymbol e_2=5\begin{pmatrix}1\\0\end{pmatrix}+3\begin{pmatrix}0\\1\end{pmatrix}=\begin{pmatrix}5\\3\end{pmatrix}"), S("oblique","新基下的读数",("oblique_basis","same_vector"),("same_vector",),("oblique_readout",),("basis_independent_and_spanning","coordinate_reconstruction"),"side_by_side",r"\boldsymbol x=4\boldsymbol b_1+1\boldsymbol b_2=\begin{pmatrix}1&1\\1&-1\end{pmatrix}\begin{pmatrix}4\\1\end{pmatrix}=\begin{pmatrix}5\\3\end{pmatrix}")),
 ("basis_independent_and_spanning","standard_reconstruction","coordinate_reconstruction"), ("geometry.coordinate_readout","geometry.subspace_region","linear.upsert"), r"\boldsymbol x=5\boldsymbol e_1+3\boldsymbol e_2=\begin{pmatrix}1&1\\1&-1\end{pmatrix}\begin{pmatrix}4\\1\end{pmatrix}=(5,3)", "matrix_transform", (M(V(1,1),V(1,-1)),V(4,1)), V(5,3), "oblique_basis"),

"ch04.linear-map.definition": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","staged_transform","vector_2d"),
 (E("map_T","matrix",2,M(V(2,1),V(0,1))), E("u","vector",2,V(1,2)), E("v","vector",2,V(-1,1)), E("sum_test","vector",2,V(0,3),"u+v"), E("T_u","vector",2,V(4,2),"T(u)"), E("T_v","vector",2,V(-1,1),"T(v)"), E("T_sum","vector",2,V(3,3),"T(u+v)"), E("homogeneity_test","vector",2,V(3,6),"3u"), E("T_scaled","vector",2,V(12,6),"3T(u)"), E("origin","point",2,V(0,0),"O")),
 (R("map_u","maps_to","u","T_u",matrix=M(V(2,1),V(0,1)),expected_result=V(4,2)), R("map_v","maps_to","v","T_v",matrix=M(V(2,1),V(0,1)),expected_result=V(-1,1)), R("input_sum","sum","u","sum_test",other_vector=V(-1,1),expected_result=V(0,3)), R("additivity_test","additivity","sum_test","T_sum",matrix=M(V(2,1),V(0,1)),expected_result=V(3,3)), R("input_scaling","scalar_multiple","u","homogeneity_test",scalar=3.0,expected_result=V(3,6)), R("homogeneity_test","homogeneity","homogeneity_test","T_scaled",matrix=M(V(2,1),V(0,1)),scalar=3.0,expected_result=V(12,6)), R("origin_test","maps_to","origin","origin",matrix=M(V(2,1),V(0,1)),expected_result=V(0,0))),
 (S("origin","原点固定",("map_T","origin"),("origin",),("origin_test",),("origin_fixed",)), S("additivity","可加性",("u","v","sum_test"),("T_u","T_v","T_sum"),("map_u","map_v","input_sum","additivity_test"),("additivity",),"overlay"), S("homogeneity","齐次性",("u","homogeneity_test"),("T_u","T_scaled"),("input_scaling","homogeneity_test"),("homogeneity",),"overlay")),
 ("origin_fixed","additivity","homogeneity"), ("geometry.transformed_grid","geometry.polygon","linear.upsert","point.upsert"), r"T(u+v)=T(u)+T(v),\ T(3u)=3T(u),\ T(0)=0", "matrix_transform", (M(V(2,1),V(0,1)),V(1,2)), V(4,2), "T_sum"),
"ch04.linear-map.compare": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","vector_2d"),
 (E("rotation","matrix",2,M(V(0,-1),V(1,0))), E("stretch","matrix",2,M(V(2,0),V(0,.5))), E("projection","matrix",2,A10), E("translation","affine_set",2,V(1,1)), E("square_map","constraint",2,M(V(-1,1),V(0,0),V(2,4))), E("constant_shift","affine_set",2,V(0,2)), E("origin","point",2,V(0,0),"O")),
 (R("rotation_linear","classification","rotation","origin",is_linear=1.0,origin_image=V(0,0),u=V(1,2),v=V(-1,1),scalar=3.0,image_u=V(-2,1),image_v=V(-1,-1),sum_image=V(-3,0),scaled_image=V(-6,3)), R("stretch_linear","classification","stretch","origin",is_linear=1.0,origin_image=V(0,0),u=V(1,2),v=V(-1,1),scalar=3.0,image_u=V(2,1),image_v=V(-2,.5),sum_image=V(0,1.5),scaled_image=V(6,3)), R("projection_linear","classification","projection","origin",is_linear=1.0,origin_image=V(0,0),u=V(1,2),v=V(-1,1),scalar=3.0,image_u=V(1,0),image_v=V(-1,0),sum_image=V(0,0),scaled_image=V(3,0)), R("translation_failure","not_linear","translation","origin",origin_image=V(1,1),expected_origin=V(0,0)), R("square_failure","not_linear","square_map","origin",inputs=V(1,2),separate_sum=5.0,sum_image=9.0), R("constant_failure","not_linear","constant_shift","origin",origin_image=V(0,2),expected_origin=V(0,0))),
 (S("linear","三个线性例",("origin",),("rotation","stretch","projection"),("rotation_linear","stretch_linear","projection_linear"),("linear_examples_pass_axioms",),"side_by_side"), S("nonlinear","三个失败诊断",("origin",),("translation","square_map","constant_shift"),("translation_failure","square_failure","constant_failure"),("nonlinear_diagnostics",),"side_by_side")),
 ("linear_examples_pass_axioms","nonlinear_diagnostics"), ("geometry.transformed_grid","curve.create","linear.upsert"), r"R,S,P\text{线性};\ \tau(0)\ne0,\ f(1+2)=9\ne5,\ (Ax+c)(0)\ne0", "matrix_transform", (M(V(0,-1),V(1,0)),V(1,0)), V(0,1), "square_map"),

"ch04.linear-map.matrix-columns": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","vector_2d","polygon_2d"),
 (E("map_T","matrix",2,M(V(2,-1),V(1,3))), E("standard_e1","vector",2,V(1,0),"e₁"), E("standard_e2","vector",2,V(0,1),"e₂"), E("column_1","vector",2,V(2,1),"a₁"), E("column_2","vector",2,V(-1,3),"a₂")),
 (R("first_column","column_image","standard_e1","column_1",matrix=M(V(2,-1),V(1,3)),column_index=1.0,expected_result=V(2,1)), R("second_column","column_image","standard_e2","column_2",matrix=M(V(2,-1),V(1,3)),column_index=2.0,expected_result=V(-1,3)), R("grid_binding","image_of","map_T","column_1",expected_basis=M(V(2,1),V(-1,3)))),
 (S("columns","基向量映到矩阵列",("map_T","standard_e1","standard_e2"),("column_1","column_2"),("first_column","second_column"),("Tej_equals_column_j",),"overlay"), S("grid","矩阵列决定网格",("column_1","column_2"),("map_T",),("grid_binding",),("columns_determine_grid",),"overlay")),
 ("Tej_equals_column_j","columns_determine_grid"), ("geometry.transformed_grid","linear.upsert","geometry.polygon"), r"T(e_1)=(2,1)=a_1,\ T(e_2)=(-1,3)=a_2", "matrix_transform", (M(V(2,-1),V(1,3)),V(0,1)), V(-1,3), "column_2"),

"ch04.kernel-image": Chapter4Semantic(
 "2d", "subspace_region", ("transformed_grid","subspace_region","staged_transform"),
 # 教科书记号贯穿两个窗格：定义域的两根尺子写 e₁、e₂（e₂ 就是核方向），
 # 样本输入写 x、像写 T(x)，被压到的原点写 O。
 (E("map_T","matrix",2,A10), E("domain","basis",2,I2,"e"), E("kernel_direction","vector",2,V(0,1),"e₂"), E("zero","point",2,V(0,0),"O"), E("image","subspace",2,M(V(1,0))), E("sample_input","vector",2,V(2,3),"x"), E("sample_output","vector",2,V(2,0),"T(x)")),
 (R("kernel_map","maps_to","kernel_direction","zero",matrix=A10,expected_result=V(0,0)), R("kernel_binding","kernel_of","kernel_direction","map_T",expected_nullity=1.0), R("sample_map","maps_to","sample_input","sample_output",matrix=A10,expected_result=V(2,0)), R("image_binding","image_of","map_T","image",expected_rank=1.0)),
 (S("kernel","核到零",("domain","kernel_direction","map_T"),("zero",),("kernel_map","kernel_binding"),("kernel_maps_zero",),"side_by_side"), S("image","像是可达子空间",("sample_input","map_T"),("sample_output","image"),("sample_map","image_binding"),("image_reachable",),"side_by_side")),
 ("kernel_maps_zero","image_reachable"), ("geometry.mapping_bundle","geometry.transformed_grid","geometry.subspace_region","linear.upsert"), r"ker(T)=span(e_2),\ T(e_2)=0;\ im(T)=span(e_1)", "matrix_transform", (A10,V(2,3)), V(2,0), "kernel_direction"),

"ch04.rank-nullity": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("map_T","matrix",3,M(V(1,0,0),V(0,1,0),V(0,0,0))), E("domain","basis",3,I3,"e"), E("rank","subspace",3,XY), E("nullity","subspace",3,M(V(0,0,1))), E("preserved","basis",3,XY), E("collapsed","vector",3,V(0,0,1),"e₃"), E("zero","point",3,V(0,0,0),"O")),
 (R("rank_evidence","rank_of","map_T","rank",expected_rank=2.0), R("nullity_evidence","nullity_of","map_T","nullity",expected_nullity=1.0), R("collapse","maps_to","collapsed","zero",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),expected_result=V(0,0,0)), R("conservation","rank_nullity","domain","map_T",domain_dimension=3.0,rank=2.0,nullity=1.0)),
 (S("split","保留与压扁",("domain","map_T"),("preserved","collapsed","zero"),("collapse",),("preserved_plus_collapsed",),"overlay"), S("conservation","秩零化度守恒",("rank","nullity"),("domain",),("rank_evidence","nullity_evidence","conservation"),("rank_plus_nullity_equals_domain",),"overlay")),
 ("preserved_plus_collapsed","rank_plus_nullity_equals_domain"), ("linear3d.upsert","plane3d.upsert","point3d.upsert"), r"rank(T)=2,\ nullity(T)=1,\ 2+1=dim(R^3)", "matrix_transform", (M(V(1,0,0),V(0,1,0),V(0,0,0)),V(1,2,3)), V(1,2,0), "collapsed"),
}

TOPIC_SEMANTICS: Mapping[str, Chapter4Semantic] = MappingProxyType(_MAPPING)

def semantic_for(topic_id: str) -> Chapter4Semantic:
    try:
        return TOPIC_SEMANTICS[topic_id]
    except KeyError as error:
        raise KeyError(f"unknown chapter 4 semantic mapping: {topic_id}") from error

__all__ = ["Chapter4Semantic","EntityDescriptor","RelationDescriptor","StageDescriptor","TOPIC_SEMANTICS","semantic_for"]
