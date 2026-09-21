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
  E("input_vector_a","vector",3,V(2,1,3),"x1"), E("output_vector_a","vector",3,V(2,1,0),"Ax1"),
  E("input_vector_b","vector",3,V(-2,1,2),"x2"), E("output_vector_b","vector",3,V(-2,1,0),"Ax2"),
  E("input_vector_c","vector",3,V(-1,-2,-2),"x3"), E("output_vector_c","vector",3,V(-1,-2,0),"Ax3"),
  E("kernel_vector","vector",3,V(0,0,3),"k"),
  E("zero","point",3,V(0,0,0),"0")),
 (R("projection_a","maps_to","input_vector_a","output_vector_a",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(2,1,3),expected_result=V(2,1,0)),
  R("projection_b","maps_to","input_vector_b","output_vector_b",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(-2,1,2),expected_result=V(-2,1,0)),
  R("projection_c","maps_to","input_vector_c","output_vector_c",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(-1,-2,-2),expected_result=V(-1,-2,0)),
  R("collapse","maps_to","kernel_vector","zero",matrix=M(V(1,0,0),V(0,1,0),V(0,0,0)),input_vector=V(0,0,3),expected_result=V(0,0,0))),
 (S("column_space","列空间：所有可能的输出",("input_vector_a","input_vector_b","input_vector_c","column_space"),("output_vector_a","output_vector_b","output_vector_c"),("projection_a","projection_b","projection_c"),("diag_1_1_0","image_xy_plane"),"side_by_side"),
  S("null_space","零空间：与平面垂直的方向被压成一点",("column_space","null_space","kernel_vector"),("zero",),("collapse",),("kernel_to_zero",),"side_by_side")),
 ("diag_1_1_0","kernel_to_zero","image_xy_plane"), ("plane3d.upsert","linear3d.upsert","point3d.upsert"), r"\boldsymbol A=\begin{pmatrix}1&0&0\\0&1&0\\0&0&0\end{pmatrix},\quad \operatorname{Null}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_3),\quad \operatorname{Col}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)", "matrix_transform", (M(V(1,0,0),V(0,1,0),V(0,0,0)),V(2,1,3)), V(2,1,0), "kernel_vector"),
"ch04.dependence.redundancy": Chapter4Semantic(
 # 4.2.1 与 4.2.2 合并后的四幅 3D 图按维数递增：一根向量张成直线、两根
 # 不共线向量张成平面、加入平面外方向张成 R³，最后加入冗余向量作相关对照。
 # 全部关系只复算定义中的线性组合，不引入 4.2.3 的 Ax=0 判定法。
 "3d", "subspace_region", ("vector_3d","subspace_region","linear3d","plane3d"),
 (E("span_line","basis",3,M(V(1,0,0)),"Span(u)"), E("line_sample","point",3,V(2,0,0),"2u"),
   E("span_plane","basis",3,M(V(1,0,0),V(0,1,0)),"Span(u,v)"), E("plane_sample","point",3,V(2,-1,0),"x"),
   E("independent_set","basis",3,I3,"independent"), E("independent_sample","point",3,V(1,1,1),"x"),
   E("dependent_set","basis",3,M(V(1,0,0),V(0,1,0),V(1,1,0)),"dependent"), E("zero_combination","point",3,V(0,0,0),"0")),
 (R("line_combination","linear_combination","span_line","line_sample",coefficient=2.0,expected_result=V(2,0,0)),
   R("plane_combination","linear_combination","span_plane","plane_sample",coefficients=V(2,-1),expected_result=V(2,-1,0)),
   R("independent_combination","linear_combination","independent_set","independent_sample",coefficients=V(1,1,1),expected_result=V(1,1,1)),
   R("dependent_combination","linear_combination","dependent_set","zero_combination",coefficients=V(1,1,-1),expected_result=V(0,0,0))),
  (S("line","一根向量张成过原点的直线",("span_line",),(),("line_combination",),("line_span_1d",),"side_by_side",r"\operatorname{Span}\{\boldsymbol u\}=\{t\boldsymbol u\mid t\in R\}"),
   S("plane","两根不共线向量张成过原点的平面",("span_plane",),(),("plane_combination",),("plane_span_2d",),"side_by_side",r"a\boldsymbol u+b\boldsymbol v=\begin{pmatrix}a\\b\\0\end{pmatrix}"),
   S("space","加入平面外方向后张成整个三维空间",("independent_set",),(),("independent_combination",),("independent_only_zero_solution","independent_span_r3"),"side_by_side",r"\boldsymbol x=\begin{pmatrix}a\\b\\c\end{pmatrix}=a\boldsymbol u+b\boldsymbol v+c\boldsymbol w"),
   S("dependent","加入冗余方向后仍只张成原平面",("dependent_set",),(),("dependent_combination",),("dependent_nonzero_combination_zero","dependent_coplanar"),"side_by_side",r"\boldsymbol u+\boldsymbol v-\boldsymbol w=\begin{pmatrix}0\\0\\0\end{pmatrix}")),
 ("line_span_1d","plane_span_2d","independent_only_zero_solution","independent_span_r3","dependent_nonzero_combination_zero","dependent_coplanar"), ("plane3d.upsert","linear3d.upsert","point3d.upsert"), r"\operatorname{Span}\{\boldsymbol v_1,\ldots,\boldsymbol v_k\}=\{\text{这些向量的所有线性组合}\}", "linear_combination", (M(V(1,0,0),V(0,1,0),V(0,0,1)),V(1,1,1)), V(1,1,1), "independent_set"),

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
 # 4.4.1 与 4.4.2 合并后的两个并排案例。拉伸同时验证加性与齐性；平移用同一组
 # u、v 直接展示加性两边落在不同位置。两个窗格共用范围，图形数据与案例公式一致。
 "2d", "basis_change", ("transformed_grid","vector_2d","polygon_2d"),
 (E("stretch_map","matrix",2,M(V(2,0),V(0,1)),"T"),
  E("stretch_result","point",2,V(2,1),"T(u+v)"),
  E("translation_shift","affine_set",2,V(1,0),"T"),
  E("translation_result","point",2,V(2,1),"T(u+v)")),
 (R("stretch_case","classification","stretch_map","stretch_result",
    matrix=M(V(2,0),V(0,1)),u=V(1,0),v=V(0,1),scalar=2.0,
    image_u=V(2,0),image_v=V(0,1),sum_image=V(2,1),sum_of_images=V(2,1),
    scaled_image=V(4,0),scaled_output=V(4,0)),
  R("translation_case","not_linear","translation_shift","translation_result",
    shift=V(1,0),u=V(1,0),v=V(0,1),image_u=V(2,0),image_v=V(1,1),
    sum_image=V(2,1),sum_of_images=V(3,1))),
 (S("stretch","拉伸（是）",(),(),("stretch_case",),("stretch_additivity","stretch_homogeneity"),"side_by_side",
    r"T(\boldsymbol u+\boldsymbol v)=T(\boldsymbol u)+T(\boldsymbol v)=(2,1),\quad T(2\boldsymbol u)=2T(\boldsymbol u)=(4,0)"),
  S("translation","平移（不是）",(),(),("translation_case",),("translation_not_additive",),"side_by_side",
    r"T(\boldsymbol u+\boldsymbol v)=(2,1)\ne(3,1)=T(\boldsymbol u)+T(\boldsymbol v)")),
 ("stretch_additivity","stretch_homogeneity","translation_not_additive"),
 ("geometry.transformed_grid","geometry.polygon","linear.upsert","point.upsert"),
 r"T(\boldsymbol u+\boldsymbol v)=T(\boldsymbol u)+T(\boldsymbol v),\quad T(k\boldsymbol v)=kT(\boldsymbol v)",
 "matrix_transform", (M(V(2,0),V(0,1)),V(1,1)), V(2,1), "translation_result"),

}

TOPIC_SEMANTICS: Mapping[str, Chapter4Semantic] = MappingProxyType(_MAPPING)

def semantic_for(topic_id: str) -> Chapter4Semantic:
    try:
        return TOPIC_SEMANTICS[topic_id]
    except KeyError as error:
        raise KeyError(f"unknown chapter 4 semantic mapping: {topic_id}") from error

__all__ = ["Chapter4Semantic","EntityDescriptor","RelationDescriptor","StageDescriptor","TOPIC_SEMANTICS","semantic_for"]
