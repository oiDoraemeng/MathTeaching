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
def S(name: str, title: str, inputs: tuple[str, ...], outputs: tuple[str, ...], relations: tuple[str, ...], invariants: tuple[str, ...], layout: str = "sequence") -> StageDescriptor:
    return StageDescriptor(name, title, layout, inputs, outputs, relations, invariants)

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
 "2d", "subspace_region", ("transformed_grid","subspace_region","vector_2d"),
 (E("map_A","matrix",2,A10,"A"), E("domain","basis",2,I2,"R² domain"), E("codomain","basis",2,I2,"R² codomain"), E("kernel","subspace",2,M(V(0,1)),"Null(A)"), E("column_space","subspace",2,M(V(1,0)),"Col(A)"), E("kernel_vector","vector",2,V(0,1),"k"), E("zero","point",2,V(0,0),"0"), E("image_vector","vector",2,V(2,0),"A(2,3)")),
 (R("kernel_map","maps_to","kernel_vector","zero",matrix=A10,expected_result=V(0,0)), R("kernel_binding","kernel_of","kernel","map_A",expected_nullity=1.0), R("column_binding","image_of","map_A","column_space",expected_rank=1.0), R("domain_image","maps_to","domain","column_space",matrix=A10,input_vector=V(2,3),expected_result=V(2,0))),
 (S("domain","核方向",("domain","kernel","kernel_vector"),("zero",),("kernel_map","kernel_binding"),("kernel_to_zero",),"side_by_side"), S("codomain","列空间",("map_A","codomain"),("column_space","image_vector"),("column_binding","domain_image"),("image_x_axis","diag_1_0"),"side_by_side")),
 ("diag_1_0","kernel_to_zero","image_x_axis"), ("geometry.transformed_grid","geometry.subspace_region","linear.upsert"), r"A=\operatorname{diag}(1,0),\ Null(A)=\operatorname{span}(e_2),\ Col(A)=\operatorname{span}(e_1)", "matrix_transform", (A10,V(2,3)), V(2,0), "kernel_vector"),
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
 (E("rank_two","matrix",2,I2), E("rank_one","matrix",2,A10), E("rank_zero","matrix",2,M(V(0,0),V(0,0))), E("plane_image","subspace",2,I2), E("line_image","subspace",2,M(V(1,0))), E("point_image","point",2,V(0,0))),
 (R("rank_two_result","rank_of","rank_two","plane_image",expected_rank=2.0), R("rank_one_result","rank_of","rank_one","line_image",expected_rank=1.0), R("rank_zero_result","rank_of","rank_zero","point_image",expected_rank=0.0)),
 (S("rank_two","rank 2 平面",("rank_two",),("plane_image",),("rank_two_result",),("rank_two_plane",)), S("rank_one","rank 1 直线",("rank_one",),("line_image",),("rank_one_result",),("rank_one_line",)), S("rank_zero","rank 0 原点",("rank_zero",),("point_image",),("rank_zero_result",),("rank_zero_point","rank_collapse_sequence"))),
 ("rank_two_plane","rank_one_line","rank_zero_point","rank_collapse_sequence"), ("geometry.transformed_grid","geometry.subspace_region","point.upsert"), r"rank(I)=2,\ rank(diag(1,0))=1,\ rank(0)=0", "determinant", I2, 1.0, "rank_one"),
"ch04.basis.span": Chapter4Semantic(
 "2d", "subspace_region", ("vector_2d","subspace_region"),
 (E("independent_basis","basis",2,I2), E("spanning_set","subspace",2,I2,"R²"), E("too_few","basis",2,M(V(1,0))), E("too_many","basis",2,M(V(1,0),V(0,1),V(1,1)))),
 (R("basis_binding","basis_of","independent_basis","spanning_set",expected_rank=2.0,vector_count=2.0), R("too_few_span","dimension_of","too_few","spanning_set",expected_dimension=1.0), R("too_many_dependence","linear_dependence","too_many","spanning_set",expected_rank=2.0,vector_count=3.0)),
 (S("complete","独立且生成",("independent_basis",),("spanning_set",),("basis_binding",),("independent_and_spanning",)), S("comparisons","过少与冗余",("too_few","too_many"),("spanning_set",),("too_few_span","too_many_dependence"),("too_few_not_spanning","too_many_redundant"),"side_by_side")),
 ("independent_and_spanning","too_few_not_spanning","too_many_redundant"), ("geometry.subspace_region",), r"rank(e_1,e_2)=2;\ rank(e_1)=1;\ rank(e_1,e_2,e_1+e_2)=2<3", "determinant", I2, 1.0, "too_many"),

"ch04.dimension.ladder": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("point","point",3,V(0,0,0)), E("line","subspace",3,M(V(1,0,0))), E("plane","subspace",3,XY), E("volume","subspace",3,I3)),
 (R("point_in_line","contains","line","point",container_dimension=1.0,member_dimension=0.0), R("line_in_plane","contains","plane","line",container_dimension=2.0,member_dimension=1.0), R("plane_in_volume","contains","volume","plane",container_dimension=3.0,member_dimension=2.0)),
 (S("ladder_low","点线面",("point","line"),("plane",),("point_in_line","line_in_plane"),("nested_0_1_2",),"overlay"), S("ladder_full","面与体",("plane",),("volume",),("plane_in_volume",),("nested_dimensions",),"overlay")),
 ("nested_0_1_2","nested_dimensions"), ("point3d.upsert","linear3d.upsert","plane3d.upsert"), r"\{0\}\subset span(e_1)\subset span(e_1,e_2)\subset R^3", "oriented_volume", (V(1,0,0),V(0,1,0),V(0,0,1)), 1.0, "volume"),

"ch04.coordinates.readout": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","vector_2d"),
 (E("standard_basis","basis",2,I2), E("oblique_basis","basis",2,M(V(1,1),V(0,1))), E("same_vector","vector",2,V(2,1),"v"), E("standard_coordinates","vector",2,V(2,1),"[v]E"), E("oblique_coordinates","vector",2,V(1,1),"[v]B")),
 (R("standard_readout","coordinate_equivalence","standard_basis","same_vector",basis_matrix=I2,coordinates=V(2,1),expected_vector=V(2,1)), R("oblique_readout","coordinate_equivalence","oblique_basis","same_vector",basis_matrix=M(V(1,1),V(0,1)),coordinates=V(1,1),expected_vector=V(2,1)), R("same_geometric_vector","same_measure","standard_coordinates","oblique_coordinates",expected_vector=V(2,1))),
 (S("standard","标准基读数",("standard_basis","same_vector"),("standard_coordinates",),("standard_readout",),("standard_reconstruction",),"side_by_side"), S("oblique","斜基读数",("oblique_basis","same_vector"),("oblique_coordinates",),("oblique_readout","same_geometric_vector"),("coordinate_reconstruction",),"side_by_side")),
 ("standard_reconstruction","coordinate_reconstruction"), ("geometry.coordinate_readout","geometry.subspace_region","linear.upsert"), r"v=2e_1+e_2=b_1+b_2=(2,1)", "matrix_transform", (M(V(1,1),V(0,1)),V(1,1)), V(2,1), "oblique_coordinates"),

"ch04.linear-map.definition": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","staged_transform","vector_2d"),
 (E("map_T","matrix",2,M(V(2,1),V(0,1))), E("u","vector",2,V(1,2)), E("v","vector",2,V(-1,1)), E("sum_test","vector",2,V(0,3),"u+v"), E("T_u","vector",2,V(4,2)), E("T_v","vector",2,V(-1,1)), E("T_sum","vector",2,V(3,3)), E("homogeneity_test","vector",2,V(3,6),"3u"), E("T_scaled","vector",2,V(12,6)), E("origin","point",2,V(0,0))),
 (R("map_u","maps_to","u","T_u",matrix=M(V(2,1),V(0,1)),expected_result=V(4,2)), R("map_v","maps_to","v","T_v",matrix=M(V(2,1),V(0,1)),expected_result=V(-1,1)), R("input_sum","sum","u","sum_test",other_vector=V(-1,1),expected_result=V(0,3)), R("additivity_test","additivity","sum_test","T_sum",matrix=M(V(2,1),V(0,1)),expected_result=V(3,3)), R("input_scaling","scalar_multiple","u","homogeneity_test",scalar=3.0,expected_result=V(3,6)), R("homogeneity_test","homogeneity","homogeneity_test","T_scaled",matrix=M(V(2,1),V(0,1)),scalar=3.0,expected_result=V(12,6)), R("origin_test","maps_to","origin","origin",matrix=M(V(2,1),V(0,1)),expected_result=V(0,0))),
 (S("origin","原点固定",("map_T","origin"),("origin",),("origin_test",),("origin_fixed",)), S("additivity","可加性",("u","v","sum_test"),("T_u","T_v","T_sum"),("map_u","map_v","input_sum","additivity_test"),("additivity",),"overlay"), S("homogeneity","齐次性",("u","homogeneity_test"),("T_u","T_scaled"),("input_scaling","homogeneity_test"),("homogeneity",),"overlay")),
 ("origin_fixed","additivity","homogeneity"), ("geometry.transformed_grid","geometry.polygon","linear.upsert","point.upsert"), r"T(u+v)=T(u)+T(v),\ T(3u)=3T(u),\ T(0)=0", "matrix_transform", (M(V(2,1),V(0,1)),V(1,2)), V(4,2), "T_sum"),
"ch04.linear-map.compare": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","vector_2d"),
 (E("rotation","matrix",2,M(V(0,-1),V(1,0))), E("stretch","matrix",2,M(V(2,0),V(0,.5))), E("projection","matrix",2,A10), E("translation","affine_set",2,V(1,1)), E("square_map","constraint",2,M(V(-1,1),V(0,0),V(2,4))), E("constant_shift","affine_set",2,V(0,2)), E("origin","point",2,V(0,0))),
 (R("rotation_linear","classification","rotation","origin",is_linear=1.0,origin_image=V(0,0)), R("stretch_linear","classification","stretch","origin",is_linear=1.0,origin_image=V(0,0)), R("projection_linear","classification","projection","origin",is_linear=1.0,origin_image=V(0,0)), R("translation_failure","not_linear","translation","origin",origin_image=V(1,1),expected_origin=V(0,0)), R("square_failure","not_linear","square_map","origin",inputs=V(1,2),separate_sum=5.0,sum_image=9.0), R("constant_failure","not_linear","constant_shift","origin",origin_image=V(0,2),expected_origin=V(0,0))),
 (S("linear","三个线性例",("origin",),("rotation","stretch","projection"),("rotation_linear","stretch_linear","projection_linear"),("linear_examples_pass_axioms",),"side_by_side"), S("nonlinear","三个失败诊断",("origin",),("translation","square_map","constant_shift"),("translation_failure","square_failure","constant_failure"),("nonlinear_diagnostics",),"side_by_side")),
 ("linear_examples_pass_axioms","nonlinear_diagnostics"), ("geometry.transformed_grid","curve.create","linear.upsert"), r"R,S,P\text{线性};\ \tau(0)\ne0,\ f(1+2)=9\ne5,\ (Ax+c)(0)\ne0", "matrix_transform", (M(V(0,-1),V(1,0)),V(1,0)), V(0,1), "square_map"),

"ch04.linear-map.matrix-columns": Chapter4Semantic(
 "2d", "basis_change", ("transformed_grid","vector_2d","polygon_2d"),
 (E("map_T","matrix",2,M(V(2,-1),V(1,3))), E("standard_e1","vector",2,V(1,0)), E("standard_e2","vector",2,V(0,1)), E("column_1","vector",2,V(2,1)), E("column_2","vector",2,V(-1,3))),
 (R("first_column","column_image","standard_e1","column_1",matrix=M(V(2,-1),V(1,3)),column_index=1.0,expected_result=V(2,1)), R("second_column","column_image","standard_e2","column_2",matrix=M(V(2,-1),V(1,3)),column_index=2.0,expected_result=V(-1,3)), R("grid_binding","image_of","map_T","column_1",expected_basis=M(V(2,1),V(-1,3)))),
 (S("columns","基向量映到矩阵列",("map_T","standard_e1","standard_e2"),("column_1","column_2"),("first_column","second_column"),("Tej_equals_column_j",),"overlay"), S("grid","矩阵列决定网格",("column_1","column_2"),("map_T",),("grid_binding",),("columns_determine_grid",),"overlay")),
 ("Tej_equals_column_j","columns_determine_grid"), ("geometry.transformed_grid","linear.upsert","geometry.polygon"), r"T(e_1)=(2,1)=a_1,\ T(e_2)=(-1,3)=a_2", "matrix_transform", (M(V(2,-1),V(1,3)),V(0,1)), V(-1,3), "column_2"),

"ch04.kernel-image": Chapter4Semantic(
 "2d", "subspace_region", ("transformed_grid","subspace_region","staged_transform"),
 (E("map_T","matrix",2,A10), E("domain","basis",2,I2), E("kernel_direction","vector",2,V(0,1)), E("zero","point",2,V(0,0)), E("image","subspace",2,M(V(1,0))), E("sample_input","vector",2,V(2,3)), E("sample_output","vector",2,V(2,0))),
 (R("kernel_map","maps_to","kernel_direction","zero",matrix=A10,expected_result=V(0,0)), R("kernel_binding","kernel_of","kernel_direction","map_T",expected_nullity=1.0), R("sample_map","maps_to","sample_input","sample_output",matrix=A10,expected_result=V(2,0)), R("image_binding","image_of","map_T","image",expected_rank=1.0)),
 (S("kernel","核到零",("domain","kernel_direction","map_T"),("zero",),("kernel_map","kernel_binding"),("kernel_maps_zero",),"side_by_side"), S("image","像是可达子空间",("sample_input","map_T"),("sample_output","image"),("sample_map","image_binding"),("image_reachable",),"side_by_side")),
 ("kernel_maps_zero","image_reachable"), ("geometry.mapping_bundle","geometry.transformed_grid","geometry.subspace_region","linear.upsert"), r"ker(T)=span(e_2),\ T(e_2)=0;\ im(T)=span(e_1)", "matrix_transform", (A10,V(2,3)), V(2,0), "kernel_direction"),

"ch04.rank-nullity": Chapter4Semantic(
 "3d", "subspace_region", ("vector_3d","subspace_region"),
 (E("map_T","matrix",3,M(V(1,0,0),V(0,1,0),V(0,0,0))), E("domain","basis",3,I3), E("rank","subspace",3,XY), E("nullity","subspace",3,M(V(0,0,1))), E("preserved","basis",3,XY), E("collapsed","vector",3,V(0,0,1)), E("zero","point",3,V(0,0,0))),
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
