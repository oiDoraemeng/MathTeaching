"""Closed mathematical witnesses and stage contracts for Chapter 7."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from linear_algebra.chapter_04_semantics import EntityDescriptor, RelationDescriptor, StageDescriptor


@dataclass(frozen=True)
class Ch7Spec:
    topic: str
    entities: tuple[EntityDescriptor, ...]
    relations: tuple[RelationDescriptor, ...]
    stages: tuple[StageDescriptor, ...]
    invariants: tuple[str, ...]
    formula: str
    operations: tuple[str, ...]

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(entity.role for entity in self.entities)


def _entity(role: str, value: object, kind: str = "vector") -> EntityDescriptor:
    return EntityDescriptor(role, kind, 2, value, role)


def _relation(name: str, kind: str, source: str, target: str, **parameters: object) -> RelationDescriptor:
    return RelationDescriptor(name, kind, source, target, tuple(parameters.items()))


def _stage(name: str, title: str, inputs: tuple[str, ...], outputs: tuple[str, ...], relations: tuple[str, ...], invariants: tuple[str, ...]) -> StageDescriptor:
    return StageDescriptor(name, title, "overlay", inputs, outputs, relations, invariants)


def _eigen_directions() -> Ch7Spec:
    stretch = ((2.0, 0.0), (0.0, 1.0))
    projection = ((1.0, 0.0), (0.0, 0.0))
    rotation = ((0.0, -1.0), (1.0, 0.0))
    reflection = ((0.0, 1.0), (1.0, 0.0))
    invariants = (
        r"$\boldsymbol A\boldsymbol v=\lambda\boldsymbol v$ 对每个展示的特征向量成立。",
        r"当 $\lambda=0$ 时，$E_{0}=\operatorname{Null}(\boldsymbol A)$。",
        r"$90^\circ$ 旋转在实数范围内没有非零特征向量。",
    )
    entities = (
        _entity("stretch_operator", stretch, "matrix"),
        _entity("stretch_x", (1.0, 0.0)), _entity("stretch_x_image", (2.0, 0.0)),
        _entity("stretch_y", (0.0, 1.0)), _entity("stretch_y_image", (0.0, 1.0)),
        _entity("stretch_diagonal", (1.0, 1.0)), _entity("stretch_diagonal_image", (2.0, 1.0)),
        _entity("projection_operator", projection, "matrix"),
        _entity("projection_x", (1.0, 0.0)), _entity("projection_x_image", (1.0, 0.0)),
        _entity("projection_y", (0.0, 1.0)), _entity("projection_y_image", (0.0, 0.0)),
        _entity("rotation_operator", rotation, "matrix"),
        _entity("rotation_vector", (1.0, 0.0)), _entity("rotation_image", (0.0, 1.0)),
        _entity("reflection_operator", reflection, "matrix"),
        _entity("reflection_plus", (1.0, 1.0)), _entity("reflection_plus_image", (1.0, 1.0)),
        _entity("reflection_minus", (1.0, -1.0)), _entity("reflection_minus_image", (-1.0, 1.0)),
    )
    relations = (
        _relation("stretch_x", "maps_to", "stretch_x", "stretch_x_image", matrix=stretch, vector=(1.0, 0.0), output=(2.0, 0.0), eigenvalue=2.0),
        _relation("stretch_y", "maps_to", "stretch_y", "stretch_y_image", matrix=stretch, vector=(0.0, 1.0), output=(0.0, 1.0), eigenvalue=1.0),
        _relation("stretch_diagonal", "maps_to", "stretch_diagonal", "stretch_diagonal_image", matrix=stretch, vector=(1.0, 1.0), output=(2.0, 1.0)),
        _relation("projection_x", "maps_to", "projection_x", "projection_x_image", matrix=projection, vector=(1.0, 0.0), output=(1.0, 0.0), eigenvalue=1.0),
        _relation("projection_y", "collapses_to", "projection_y", "projection_y_image", matrix=projection, vector=(0.0, 1.0), output=(0.0, 0.0), eigenvalue=0.0),
        _relation("rotation", "maps_to", "rotation_vector", "rotation_image", matrix=rotation, vector=(1.0, 0.0), output=(0.0, 1.0), characteristic=(1.0, 0.0, 1.0), discriminant=-4.0),
        _relation("reflection_plus", "maps_to", "reflection_plus", "reflection_plus_image", matrix=reflection, vector=(1.0, 1.0), output=(1.0, 1.0), eigenvalue=1.0),
        _relation("reflection_minus", "maps_to", "reflection_minus", "reflection_minus_image", matrix=reflection, vector=(1.0, -1.0), output=(-1.0, 1.0), eigenvalue=-1.0),
    )
    stages = (
        _stage("stretch", "拉伸：方向保持与方向改变", ("stretch_operator", "stretch_x", "stretch_diagonal"), ("stretch_x_image", "stretch_diagonal_image"), ("stretch_x", "stretch_diagonal"), invariants),
        _stage("projection", "投影：一个方向不变，一个方向消失", ("projection_operator", "projection_x", "projection_y"), ("projection_x_image", "projection_y_image"), ("projection_x", "projection_y"), invariants),
        _stage("rotation", "旋转 90 度：没有实特征方向", ("rotation_operator", "rotation_vector"), ("rotation_image",), ("rotation",), invariants),
        _stage("reflection", "关于 y=x 反射：一个方向不变，一个方向反向", ("reflection_operator", "reflection_plus", "reflection_minus"), ("reflection_plus_image", "reflection_minus_image"), ("reflection_plus", "reflection_minus"), invariants),
    )
    return Ch7Spec("ch07.eigen.direction", entities, relations, stages, invariants, r"\boldsymbol A\boldsymbol v=\lambda\boldsymbol v", ("geometry.transformed_grid", "linear.upsert"))


def _characteristic_polynomial() -> Ch7Spec:
    real_matrix = ((2.0, 1.0), (1.0, 2.0))
    complex_matrix = ((1.0, -1.0), (1.0, 1.0))
    invariants = (
        r"$p(\lambda)=\det(\boldsymbol A-\lambda\boldsymbol I)$ 的根就是特征值。",
        r"每个实根 $\lambda$ 对应 $\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I)$。",
        r"判别式小于零时没有实特征值。",
    )
    entities = (
        _entity("real_operator", real_matrix, "matrix"),
        _entity("real_polynomial", (1.0, -4.0, 3.0), "region"),
        _entity("real_roots", ((1.0, 0.0), (3.0, 0.0)), "region"),
        _entity("space_3", ((1.0, 1.0),), "eigenspace"),
        _entity("space_1", ((1.0, -1.0),), "eigenspace"),
        _entity("complex_operator", complex_matrix, "matrix"),
        _entity("complex_polynomial", (1.0, -2.0, 2.0), "region"),
        _entity("complex_roots", ((1.0, -1.0), (1.0, 1.0)), "region"),
    )
    relations = (
        _relation("real_spectrum", "eigen_binding", "real_operator", "real_polynomial", matrix=real_matrix, coefficients=(1.0, -4.0, 3.0), roots=((1.0, 0.0), (3.0, 0.0)), basis_3=((1.0, 1.0),), basis_1=((1.0, -1.0),)),
        _relation("complex_spectrum", "eigen_binding", "complex_operator", "complex_polynomial", matrix=complex_matrix, coefficients=(1.0, -2.0, 2.0), roots=((1.0, -1.0), (1.0, 1.0)), discriminant=-4.0),
    )
    stages = (
        _stage("real", "例 1：两个实特征值", ("real_operator", "real_polynomial"), ("real_roots", "space_3", "space_1"), ("real_spectrum",), invariants),
        _stage("complex", "例 2：没有实特征值", ("complex_operator", "complex_polynomial"), ("complex_roots",), ("complex_spectrum",), invariants),
    )
    return Ch7Spec("ch07.characteristic-polynomial", entities, relations, stages, invariants, r"p(\lambda)=\det(\boldsymbol A-\lambda\boldsymbol I)=0", ("curve.create", "point.upsert", "geometry.subspace_region"))


def _eigenspaces() -> Ch7Spec:
    operator = ((2.0, 1.0), (1.0, 2.0))
    shear = ((1.0, 1.0), (0.0, 1.0))
    invariants = (
        r"$E_{\lambda}=\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I)$。",
        "不同特征值对应的特征向量线性无关。",
        r"$\det(\boldsymbol A)=\lambda_{1}\lambda_{2}\cdots\lambda_{n}$。",
        r"$\operatorname{tr}(\boldsymbol A)=\lambda_{1}+\lambda_{2}+\cdots+\lambda_{n}$。",
        r"$1\leq m_g(\lambda_0)\leq m_a(\lambda_0)$。",
    )
    entities = (
        _entity("operator", operator, "matrix"),
        _entity("space_3", ((1.0, 1.0),), "eigenspace"),
        _entity("space_1", ((1.0, -1.0),), "eigenspace"),
        _entity("shear_operator", shear, "matrix"),
        _entity("shear_space", ((1.0, 0.0),), "eigenspace"),
        _entity("invariant_values", ((3.0, 1.0), (3.0, 4.0)), "region"),
    )
    relations = (
        _relation("space_3", "eigen_binding", "operator", "space_3", matrix=operator, eigenvalue=3.0, shifted=((-1.0, 1.0), (1.0, -1.0)), basis=((1.0, 1.0),)),
        _relation("space_1", "eigen_binding", "operator", "space_1", matrix=operator, eigenvalue=1.0, shifted=((1.0, 1.0), (1.0, 1.0)), basis=((1.0, -1.0),)),
        _relation("shear_space", "eigen_binding", "shear_operator", "shear_space", matrix=shear, eigenvalue=1.0, shifted=((0.0, 1.0), (0.0, 0.0)), basis=((1.0, 0.0),), algebraic_multiplicity=2.0, geometric_multiplicity=1.0),
        _relation("invariants", "invariant", "operator", "invariant_values", determinant=3.0, trace=4.0, eigenvalues=(3.0, 1.0)),
    )
    stages = (
        _stage("eigenspaces", "两个特征值对应两个特征空间", ("operator",), ("space_3", "space_1"), ("space_3", "space_1"), invariants),
        _stage("defective", "例 7：切变矩阵不能对角化", ("shear_operator",), ("shear_space",), ("shear_space",), invariants),
        _stage("invariants", "例 8：用特征值验证行列式与迹", ("operator",), ("invariant_values",), ("invariants",), invariants),
    )
    return Ch7Spec("ch07.eigenspace", entities, relations, stages, invariants, r"E_\lambda=\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I)", ("geometry.transformed_grid", "geometry.subspace_region", "linear.upsert"))


def _diagonalization() -> Ch7Spec:
    operator = ((2.0, 1.0), (1.0, 2.0))
    basis = ((1.0, 1.0), (1.0, -1.0))
    inverse = ((0.5, 0.5), (0.5, -0.5))
    diagonal = ((3.0, 0.0), (0.0, 1.0))
    invariants = (
        r"$\boldsymbol P^{-1}\boldsymbol A\boldsymbol P=\boldsymbol D$。",
        r"$\boldsymbol P$ 的列是线性无关的特征向量。",
        r"$\boldsymbol D$ 在特征坐标中沿各坐标方向独立缩放。",
        r"$\boldsymbol P\boldsymbol D\boldsymbol P^{-1}=\boldsymbol A$。",
    )
    entities = (
        _entity("operator", operator, "matrix"), _entity("basis", basis, "matrix"),
        _entity("inverse_basis", inverse, "matrix"), _entity("diagonal", diagonal, "matrix"),
        _entity("coordinate_e1", (1.0, 0.0)), _entity("coordinate_e2", (0.0, 1.0)),
        _entity("scaled_e1", (3.0, 0.0)), _entity("scaled_e2", (0.0, 1.0)),
        _entity("basis_v1", (1.0, 1.0)), _entity("basis_v2", (1.0, -1.0)),
        _entity("image_v1", (3.0, 3.0)), _entity("image_v2", (1.0, -1.0)),
    )
    relations = (
        _relation("similarity", "coordinate_equivalence", "operator", "diagonal", operator=operator, basis=basis, inverse_basis=inverse, diagonal=diagonal),
        _relation("diagonal_v1", "maps_to", "coordinate_e1", "scaled_e1", matrix=diagonal, vector=(1.0, 0.0), output=(3.0, 0.0), eigenvalue=3.0),
        _relation("diagonal_v2", "maps_to", "coordinate_e2", "scaled_e2", matrix=diagonal, vector=(0.0, 1.0), output=(0.0, 1.0), eigenvalue=1.0),
        _relation("eigen_v1", "maps_to", "basis_v1", "image_v1", matrix=operator, vector=(1.0, 1.0), output=(3.0, 3.0), eigenvalue=3.0),
        _relation("eigen_v2", "maps_to", "basis_v2", "image_v2", matrix=operator, vector=(1.0, -1.0), output=(1.0, -1.0), eigenvalue=1.0),
    )
    stages = (
        _stage("change_basis", "第一步：换到特征基", ("basis", "inverse_basis"), ("basis_v1", "basis_v2"), ("similarity",), invariants),
        _stage("diagonal_scale", "第二步：沿特征方向独立缩放", ("diagonal", "coordinate_e1", "coordinate_e2"), ("scaled_e1", "scaled_e2"), ("diagonal_v1", "diagonal_v2"), invariants),
        _stage("change_basis_back", "第三步：换回标准基", ("operator", "basis_v1", "basis_v2"), ("image_v1", "image_v2"), ("similarity", "eigen_v1", "eigen_v2"), invariants),
    )
    return Ch7Spec("ch07.diagonalization", entities, relations, stages, invariants, r"\boldsymbol A=\boldsymbol P\boldsymbol D\boldsymbol P^{-1}", ("geometry.transformed_grid", "linear.upsert"))


_SPECS = MappingProxyType({
    "ch07.eigen.direction": _eigen_directions(),
    "ch07.characteristic-polynomial": _characteristic_polynomial(),
    "ch07.eigenspace": _eigenspaces(),
    "ch07.diagonalization": _diagonalization(),
})


def spec_for(topic: str) -> Ch7Spec:
    return _SPECS[topic if topic.startswith("ch07.") else f"ch07.{topic}"]


def specs() -> tuple[Ch7Spec, ...]:
    return tuple(_SPECS.values())


__all__ = ["Ch7Spec", "spec_for", "specs"]
