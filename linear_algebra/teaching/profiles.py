"""Explicit teaching-depth policies for linear algebra catalog topics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from linear_algebra.catalog.manifest import topic_entries

from .model import TeachingProfileRecord


class TeachingLevel(IntEnum):
    """Minimum evidence a student-facing teaching artifact must provide."""

    SEE = 0
    READ = 1
    CALCULATE = 2
    EXPLAIN = 3
    TRANSFER = 4


@dataclass(frozen=True)
class TeachingProfile:
    """Policy requirements for one catalog topic, independent of its artifact."""

    minimum_level: TeachingLevel
    required_sections: tuple[str, ...]
    requires_analogy_boundary: bool = False

    def to_record(self) -> TeachingProfileRecord:
        """Return the stable, JSON-safe profile representation stored in artifacts."""

        return TeachingProfileRecord(
            minimum_level=int(self.minimum_level),
            required_sections=self.required_sections,
            requires_analogy_boundary=self.requires_analogy_boundary,
        )

    def to_dict(self) -> dict[str, object]:
        """Return the stable profile projection supplied to explanation prompts."""

        return {
            "minimum_level": int(self.minimum_level),
            "required_sections": list(self.required_sections),
            "requires_analogy_boundary": self.requires_analogy_boundary,
        }


_CORE = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "formula", "derivation", "worked_examples", "geometric_meaning", "pitfalls"),
)
_VECTOR_ADDITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "formula", "worked_examples", "geometric_meaning"),
)
_VECTOR_FOUNDATION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "formula", "worked_examples", "geometric_meaning"),
)
# 1.1.1 没有“几何意义”小节，因此不强制该字段。
_VECTOR_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "formula", "worked_examples"),
)
# 1.3.1 的公式已写入定义块，不要求独立公式和几何意义。
_INNER_DEFINITIONS = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples", "invariants"),
)
# 1.4.1 的投影公式和几何说明已写入定义块。
_PROJECTION_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
_CAUCHY_SCHWARZ = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
# 1.5.2 仅要求命题和向量证明。
_PROOF_MIDLINE = TeachingProfile(
    TeachingLevel.READ,
    ("definition", "formula", "derivation"),
)
# 2.5 和 2.7 的公式随定义、定理或例题展示，不另设公式分节。
_MATRIX_VECTOR_SUBSECTION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 4.1 的文字合并到定义块，案例只保留列空间和零空间图。
_LINEAR_SPACE_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 2.2 的公式位于定义块，不要求独立公式和几何意义。
_BATCH_INNER_PRODUCT = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 2.3 的公式和讲义给出的 x 轴说明都位于定义块；不另造公式、推导或几何意义分节。
_PROJECTION_MATRIX = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_MATRIX_COMPOSITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_MATRIX_POWERS = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 3.1 的行列式公式位于定义块，不要求独立公式和推导。
_DET_GEOMETRY = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "geometric_meaning", "worked_examples"),
)
# 3.2 的三个定理与行列式几何说明写在定义块；没有独立证明，案例负责数值复算。
_DET_CORE_PROPERTIES = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 3.3、3.4 的公式写入定义块；3.5、3.6 另保留讲义中的完整推导。
_CHAPTER_3_DEFINITION_CASE = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_ADJUGATE_MATRIX = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
# 4.3 合并后只要求定义、性质证明和读数案例。
_BASIS_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
# 4.2 的内容合并到定义块，不补讲义中没有的分节。
_DEPENDENCE_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_5_WITH_PROOF = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
_CHAPTER_5_DEFINITION_CASE = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_6_BASIS_CHANGE = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_6_SIMILARITY = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
_CHAPTER_7_DIRECTION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_7_POLYNOMIAL = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
_CHAPTER_7_EIGENSPACE = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "derivation", "worked_examples"),
)
_CHAPTER_7_DIAGONALIZATION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_8_DEFINITION_CASE = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
_CHAPTER_8_WITH_DERIVATION = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "derivation", "worked_examples"),
)
_BRIDGE = TeachingProfile(
    TeachingLevel.TRANSFER,
    (*_CORE.required_sections, "connections"),
)
_ANALOGY = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "intuition", "geometric_meaning", "connections"),
    requires_analogy_boundary=True,
)


# 以固定主题标识映射，避免标题或来源变化影响最低教学深度。
_PROFILES: dict[str, TeachingProfile] = {
    "ch01.vector.magnitude": _VECTOR_DEFINITION,
    # 第 1、2 章按讲义实际内容要求分节，不强加通用模板文案。
    "ch01.ops.addition": _VECTOR_ADDITION,
    "ch01.ops.subtraction": _VECTOR_FOUNDATION,
    "ch01.ops.scalar": _VECTOR_FOUNDATION,
    "ch01.ops.linear-combination": _VECTOR_FOUNDATION,
    "ch01.inner.definitions": _INNER_DEFINITIONS,
    "ch01.inner.cauchy-schwarz": _CAUCHY_SCHWARZ,
    "ch01.projection.definition": _PROJECTION_DEFINITION,
    "ch01.proof.midline": _PROOF_MIDLINE,
    # 1.5.2 的补充例题同样只要求命题和向量证明。
    "ch01.proof.centroid": _PROOF_MIDLINE,
    "ch01.proof.parallelogram-diagonals": _PROOF_MIDLINE,
    "ch02.batch.inner-products": _BATCH_INNER_PRODUCT,
    "ch02.batch.projection": _PROJECTION_MATRIX,
    "ch02.matrix.additive-distributivity": _MATRIX_VECTOR_SUBSECTION,
    "ch02.matrix.transformed-grid": _MATRIX_VECTOR_SUBSECTION,
    "ch02.matrix.composition": _MATRIX_COMPOSITION,
    "ch02.matrix.basis": _MATRIX_VECTOR_SUBSECTION,
    "ch02.matrix.powers": _MATRIX_POWERS,
    # 2.9 沿用 2.5 配置，仅要求定义和分步案例。
    "ch02.subspace.independence": _MATRIX_VECTOR_SUBSECTION,
    "ch02.subspace.rank": _MATRIX_VECTOR_SUBSECTION,
    "ch03.det.oriented-area": _DET_GEOMETRY,
    "ch03.det.basic-properties": _DET_CORE_PROPERTIES,
    "ch03.det.multiplicativity": _DET_CORE_PROPERTIES,
    "ch03.det.transpose": _DET_CORE_PROPERTIES,
    "ch03.cramer.area-ratio": _CHAPTER_3_DEFINITION_CASE,
    "ch03.inverse.undo": _CHAPTER_3_DEFINITION_CASE,
    "ch03.adjugate.matrix": _ADJUGATE_MATRIX,
    "ch03.det.zero.equivalence": _ADJUGATE_MATRIX,
}

# 第 4 至 8 章暂用统一策略，并按稳定主题标识显式登记。
_CHAPTER_4_8_PROFILE = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "formula", "derivation", "worked_examples", "geometric_meaning", "pitfalls", "connections"),
)
_PROFILES.update({
    topic.id: _CHAPTER_4_8_PROFILE
    for topic in topic_entries()
    if topic.chapter_number in {4, 5, 6, 7, 8}
})
# 4.1.1–4.1.3 已合并成「线性空间」。
_PROFILES["ch04.subspace.col-null"] = _LINEAR_SPACE_DEFINITION
_PROFILES["ch04.dependence.redundancy"] = _DEPENDENCE_DEFINITION
# 4.3 合并后的「基的定义」：定义、维数与坐标写在同一小节，公式在定义块内，
# 讲义唯一的证明进「推导」，读数案例由定义自定。
_PROFILES["ch04.basis.definition"] = _BASIS_DEFINITION
_PROFILES.update({
    "ch05.homogeneous.solution-space": _CHAPTER_5_WITH_PROOF,
    "ch05.affine.solution-set": _CHAPTER_5_WITH_PROOF,
    "ch05.consistency.geometry": _CHAPTER_5_DEFINITION_CASE,
    "ch05.gaussian-elimination": _CHAPTER_5_WITH_PROOF,
    "ch05.least-squares.projection": _CHAPTER_5_DEFINITION_CASE,
})
_PROFILES.update({
    "ch07.eigen.direction": _CHAPTER_7_DIRECTION,
    "ch07.characteristic-polynomial": _CHAPTER_7_POLYNOMIAL,
    "ch07.eigenspace": _CHAPTER_7_EIGENSPACE,
    "ch07.diagonalization": _CHAPTER_7_DIAGONALIZATION,
})
_PROFILES.update({
    "ch06.basis-change.coordinates": _CHAPTER_6_BASIS_CHANGE,
    "ch06.similarity-transform": _CHAPTER_6_SIMILARITY,
})
_PROFILES.update({
    "ch08.quadratic.matrix-form": _CHAPTER_8_DEFINITION_CASE,
    "ch08.quadratic.level-sets": _CHAPTER_8_DEFINITION_CASE,
    "ch08.principal-axis": _CHAPTER_8_WITH_DERIVATION,
    "ch08.definiteness": _CHAPTER_8_WITH_DERIVATION,
})


def profile_for(topic_id: str) -> TeachingProfile:
    """Return the explicitly assigned profile for ``topic_id``."""

    return _PROFILES[topic_id]


def validate_profile_coverage() -> tuple[str, ...]:
    """Return catalog/profile ID differences in deterministic order."""

    catalog_ids = {topic.id for topic in topic_entries()}
    return tuple(sorted(catalog_ids.symmetric_difference(_PROFILES)))


__all__ = [
    "TeachingLevel",
    "TeachingProfile",
    "profile_for",
    "validate_profile_coverage",
]
