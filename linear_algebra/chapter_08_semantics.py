"""Lecture-grounded semantic witnesses for the retained Chapter 8 topics."""

from dataclasses import dataclass
from math import sqrt
from types import MappingProxyType

from linear_algebra.chapter_04_semantics import EntityDescriptor, RelationDescriptor, StageDescriptor


@dataclass(frozen=True)
class Ch8Spec:
    topic: str
    entities: tuple[EntityDescriptor, ...]
    relations: tuple[RelationDescriptor, ...]
    stages: tuple[StageDescriptor, ...]
    invariants: tuple[str, ...]
    formula: str
    operations: tuple[str, ...] = ("geometry.quadratic_level_set",)

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(entity.role for entity in self.entities)


def _entity(role: str, kind: str, value: object, label: str | None = None) -> EntityDescriptor:
    return EntityDescriptor(role, kind, 2, value, label or role)


def _relation(name: str, source: str, target: str, **parameters: object) -> RelationDescriptor:
    return RelationDescriptor(name, "maps_to", source, target, tuple(parameters.items()))


def _stage(
    name: str,
    title: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    relations: tuple[str, ...],
    *invariants: str,
) -> StageDescriptor:
    return StageDescriptor(name, title, "sequence", inputs, outputs, relations, invariants)


H = 1.0 / sqrt(2.0)
PRINCIPAL_MATRIX = ((5.0, -3.0), (-3.0, 5.0))
PRINCIPAL_AXES = ((H, H), (-H, H))
PRINCIPAL_STANDARD = ((8.0, 0.0), (0.0, 2.0))


SPECS = MappingProxyType({
    "ch08.quadratic.matrix-form": Ch8Spec(
        "ch08.quadratic.matrix-form",
        (
            _entity("circle", "matrix", ((1.0, 0.0), (0.0, 1.0)), "x^2+y^2"),
            _entity("aligned_ellipse", "matrix", ((2.0, 0.0), (0.0, 3.0)), "2x^2+3y^2"),
            _entity("positive_unit", "matrix", ((1.0, 1.0), (1.0, 1.0)), "x^2+2xy+y^2"),
            _entity("positive_scaled", "matrix", ((1.0, 3.0), (3.0, 9.0)), "x^2+6xy+9y^2"),
            _entity("negative_cross", "matrix", ((3.0, -1.0), (-1.0, 1.0)), "3x^2-2xy+y^2"),
        ),
        (
            _relation(
                "diagonal_examples", "circle", "aligned_ellipse",
                circle_matrix=((1.0, 0.0), (0.0, 1.0)),
                ellipse_matrix=((2.0, 0.0), (0.0, 3.0)),
                circle_coefficients=(1.0, 0.0, 1.0),
                ellipse_coefficients=(2.0, 0.0, 3.0),
            ),
            _relation(
                "positive_cross_examples", "positive_unit", "positive_scaled",
                unit_matrix=((1.0, 1.0), (1.0, 1.0)),
                scaled_matrix=((1.0, 3.0), (3.0, 9.0)),
                unit_coefficients=(1.0, 2.0, 1.0),
                scaled_coefficients=(1.0, 6.0, 9.0),
            ),
            _relation(
                "negative_cross_example", "negative_cross", "negative_cross",
                matrix=((3.0, -1.0), (-1.0, 1.0)),
                coefficients=(3.0, -2.0, 1.0),
            ),
        ),
        (
            _stage("diagonal", "无交叉项：两个对角矩阵", ("circle", "aligned_ellipse"), ("circle", "aligned_ellipse"), ("diagonal_examples",), "diagonal_coefficients"),
            _stage("positive_cross", "正交叉项：系数拆到两个非对角元", ("positive_unit", "positive_scaled"), ("positive_unit", "positive_scaled"), ("positive_cross_examples",), "positive_cross_split"),
            _stage("negative_cross", "负交叉项：负号随非对角元", ("negative_cross",), ("negative_cross",), ("negative_cross_example",), "negative_cross_split"),
        ),
        ("diagonal_coefficients", "positive_cross_split", "negative_cross_split"),
        r"Q(\boldsymbol x)=\boldsymbol x^{T}\boldsymbol A\boldsymbol x",
        ("linear.upsert", "point.upsert"),
    ),
    "ch08.quadratic.level-sets": Ch8Spec(
        "ch08.quadratic.level-sets",
        (
            _entity("aligned", "matrix", ((3.0, 0.0), (0.0, 1.0)), "3x^2+y^2"),
            _entity("tilted", "matrix", ((2.0, 1.0), (1.0, 2.0)), "2x^2+2xy+2y^2"),
            _entity("rotation", "matrix", ((H, -H), (H, H)), "R"),
        ),
        (
            _relation(
                "level_comparison", "aligned", "tilted",
                aligned=((3.0, 0.0), (0.0, 1.0)),
                tilted=((2.0, 1.0), (1.0, 2.0)),
                rotation=((H, -H), (H, H)),
                eigenvalues=(1.0, 3.0),
                signature=(2, 0, 0),
                level=1.0,
            ),
        ),
        (
            _stage("aligned", "无交叉项：椭圆与坐标轴对齐", ("aligned",), ("aligned",), ("level_comparison",), "same_eigenvalues", "aligned_axes"),
            _stage("tilted", "有交叉项：椭圆主轴倾斜", ("tilted", "rotation"), ("tilted",), ("level_comparison",), "same_eigenvalues", "tilted_axes"),
        ),
        ("same_eigenvalues", "aligned_axes", "tilted_axes"),
        r"Q(x,y)=1",
    ),
    "ch08.principal-axis": Ch8Spec(
        "ch08.principal-axis",
        (
            _entity("matrix", "matrix", PRINCIPAL_MATRIX, "A"),
            _entity("axes", "matrix", PRINCIPAL_AXES, "Q"),
            _entity("standard", "matrix", PRINCIPAL_STANDARD, "D"),
            _entity("point", "vector", (2.0, 1.0), "x"),
            _entity("coordinates", "vector", (H, 3.0 * H), "y"),
        ),
        (
            _relation("orthogonal_axes", "matrix", "axes", matrix=PRINCIPAL_MATRIX, axes=PRINCIPAL_AXES, eigenvalues=(8.0, 2.0)),
            _relation("rotation", "point", "coordinates", axes=PRINCIPAL_AXES, point=(2.0, 1.0), coordinates=(H, 3.0 * H)),
            _relation("standard_form", "matrix", "standard", matrix=PRINCIPAL_MATRIX, axes=PRINCIPAL_AXES, standard=PRINCIPAL_STANDARD, signature=(2, 0, 0)),
        ),
        (
            _stage("original", "原始倾斜椭圆", ("matrix", "point"), ("matrix",), ("orthogonal_axes",), "axes_are_eigenvectors"),
            _stage("axes", "显示两条特征方向", ("matrix", "axes", "point"), ("axes", "coordinates"), ("orthogonal_axes", "rotation"), "axes_are_eigenvectors", "same_quadratic_value"),
            _stage("standard", "旋转后得到标准形", ("matrix", "axes", "coordinates"), ("standard",), ("standard_form",), "cross_term_zero", "same_quadratic_value"),
        ),
        ("axes_are_eigenvectors", "same_quadratic_value", "cross_term_zero"),
        r"\boldsymbol Q^{T}\boldsymbol A\boldsymbol Q=\operatorname{diag}(8,2)",
        ("geometry.quadratic_level_set", "geometry.staged_transform", "linear.upsert"),
    ),
    "ch08.definiteness": Ch8Spec(
        "ch08.definiteness",
        (
            _entity("positive", "matrix", ((1.0, 0.0), (0.0, 2.0)), "Q_1"),
            _entity("negative", "matrix", ((-1.0, 0.0), (0.0, -2.0)), "-Q_1"),
            _entity("indefinite", "matrix", ((1.0, 0.0), (0.0, -1.0)), "Q_2"),
            _entity("semidefinite", "matrix", ((1.0, 1.0), (1.0, 1.0)), "Q_3"),
        ),
        (
            _relation("positive", "positive", "positive", matrix=((1.0, 0.0), (0.0, 2.0)), eigenvalues=(1.0, 2.0), signature=(2, 0, 0), level=1.0),
            _relation("negative", "negative", "negative", matrix=((-1.0, 0.0), (0.0, -2.0)), eigenvalues=(-2.0, -1.0), signature=(0, 2, 0), level=1.0),
            _relation("indefinite", "indefinite", "indefinite", matrix=((1.0, 0.0), (0.0, -1.0)), eigenvalues=(-1.0, 1.0), signature=(1, 1, 0), level=1.0),
            _relation("semidefinite", "semidefinite", "semidefinite", matrix=((1.0, 1.0), (1.0, 1.0)), eigenvalues=(0.0, 2.0), signature=(1, 0, 1), level=0.0),
        ),
        (
            _stage("positive", "正定：椭圆", ("positive",), ("positive",), ("positive",), "positive_classification"),
            _stage("negative", "负定：单位正等值集为空", ("negative",), ("negative",), ("negative",), "negative_classification"),
            _stage("indefinite", "不定：双曲线", ("indefinite",), ("indefinite",), ("indefinite",), "indefinite_classification"),
            _stage("semidefinite", "半正定：零等值集退化为直线", ("semidefinite",), ("semidefinite",), ("semidefinite",), "semidefinite_classification"),
        ),
        ("positive_classification", "negative_classification", "indefinite_classification", "semidefinite_classification"),
        r"\operatorname{signature}(\boldsymbol A)=(n_{+},n_{-},n_{0})",
        ("geometry.quadratic_level_set", "linear.upsert"),
    ),
})


def spec_for(topic: str) -> Ch8Spec:
    return SPECS[topic if topic.startswith("ch08.") else f"ch08.{topic}"]


def specs() -> tuple[Ch8Spec, ...]:
    return tuple(SPECS.values())
