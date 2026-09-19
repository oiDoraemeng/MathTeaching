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
# 讲义 1.3.1 的两种定义把公式直接写在定义块内，正文只有「定义」「内积的
# 基本性质」与一组数值案例：不要求独立的「公式」或「几何意义」小节。
_INNER_DEFINITIONS = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples", "invariants"),
)
# 讲义 1.4.1 的投影公式（定理 1.6）与「从 v 的终点向 u 所在直线作垂线，垂足
# 对应的向量」都写在定义 1.13 之内，正文只有「定义」「定理 1.6（投影公式）的
# 推导」与一组数值案例：同样不要求独立的「公式」或「几何意义」小节。
_PROJECTION_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
_CAUCHY_SCHWARZ = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
# 讲义 1.5.2 把中位线定理写成「命题 + 向量证明」两段：命题就是定义块，
# 证明自带全部公式；这一小节没有独立的「案例」或「几何意义（注意）」内容。
_PROOF_MIDLINE = TeachingProfile(
    TeachingLevel.READ,
    ("definition", "formula", "derivation"),
)
# 2.5 矩阵 × 向量（核心节）的三个小节把公式写在定义（2.5.1）、定理（2.5.2）或
# 例题（2.5.3）之内，正文只有「定义 / 定理 / 分层例题」与一组分步数学案例：
# 不要求独立的「公式」或「几何意义」小节。2.7 矩阵与基同样把「旋转 90° 的矩阵」
# 写在核心认知里，正文只有「定义 2.9（基）」与一组分步数学案例。
_MATRIX_VECTOR_SUBSECTION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 合并后的 4.1 将定义、性质、证明与例题忠实保留在一个「定义」块内；案例仅保留
# 列空间和零空间的两幅三维图，因此不再要求独立的「公式」或「几何意义」分节。
_LINEAR_SPACE_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 讲义 2.2 的批量内积把「定义 2.4」与一句话总结连写，公式就在定义块内，正文
# 只有「定义」与一组分层例题（例 1 单位阵）：同样不要求独立的「公式」或
# 「几何意义」小节。
_BATCH_INNER_PRODUCT = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
)
# 讲义 3.1 的几何定义把行列式公式（定理 3.1）写在定义块内，正文随后是
# 「几何意义速查」表与一组数值案例：不要求独立的「公式」或「推导」小节。
_DET_GEOMETRY = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "geometric_meaning", "worked_examples"),
)
# 讲义 4.3 的三小节合并成一个小节：定义 4.10 与定理 4.1 连写（公式就在定义块内），
# 4.3.2 只有一段「性质 4 的证明」进「推导」，读数案例由定义自定；不要求独立的
# 「公式」或「几何意义」小节。
_BASIS_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "derivation", "worked_examples"),
)
# 4.2.1–4.2.2 合并后，生成集、几何说明、相关/无关定义及其表格都位于同一「定义」
# 块；讲义没有推导，也不应凭空增加独立的公式或几何意义分节。
_DEPENDENCE_DEFINITION = TeachingProfile(
    TeachingLevel.CALCULATE,
    ("definition", "worked_examples"),
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


# This remains a literal topic-ID mapping so catalog title or source changes cannot
# silently change the minimum teaching depth.
_PROFILES: dict[str, TeachingProfile] = {
    "ch01.vector.magnitude": _VECTOR_FOUNDATION,
    # Chapters 1--2 are presented as concise lecture notes: definition and
    # formula, an actual derivation only where the lecture gives one, geometric
    # meaning, and checked cases.  Do not force generic "intuition", pitfalls,
    # or cross-topic transfer copy into every small subsection.
    "ch01.ops.addition": _VECTOR_ADDITION,
    "ch01.ops.subtraction": _VECTOR_FOUNDATION,
    "ch01.ops.scalar": _VECTOR_FOUNDATION,
    "ch01.ops.linear-combination": _VECTOR_FOUNDATION,
    "ch01.inner.definitions": _INNER_DEFINITIONS,
    "ch01.inner.cauchy-schwarz": _CAUCHY_SCHWARZ,
    "ch01.projection.definition": _PROJECTION_DEFINITION,
    "ch01.proof.midline": _PROOF_MIDLINE,
    # 1.5.2 的两道补充例题（重心定理、平行四边形对角线）与中位线定理同构：
    # 讲义只写「命题 + 向量证明」两段，没有独立的「案例」或「几何意义」内容。
    "ch01.proof.centroid": _PROOF_MIDLINE,
    "ch01.proof.parallelogram-diagonals": _PROOF_MIDLINE,
    "ch02.batch.inner-products": _BATCH_INNER_PRODUCT,
    "ch02.batch.projection": _VECTOR_FOUNDATION,
    "ch02.matrix.additive-distributivity": _VECTOR_FOUNDATION,
    "ch02.matrix.transformed-grid": _MATRIX_VECTOR_SUBSECTION,
    "ch02.matrix.composition": _VECTOR_FOUNDATION,
    "ch02.matrix.basis": _MATRIX_VECTOR_SUBSECTION,
    "ch02.matrix.powers": _VECTOR_FOUNDATION,
    # 2.9 只剩讲义 2.9.1「线性无关与线性相关」与 2.9.2「秩」两小节：定义与公式
    # 连写（公式就在定义块内），正文只有「定义」与一组分步数学案例，因此沿用
    # 2.5 小节的 profile，不要求独立的「公式」或「几何意义」小节。
    "ch02.subspace.independence": _MATRIX_VECTOR_SUBSECTION,
    "ch02.subspace.rank": _MATRIX_VECTOR_SUBSECTION,
    "ch03.det.oriented-area": _DET_GEOMETRY,
    "ch03.det.row-swap": _CORE,
    "ch03.det.scaling": _CORE,
    "ch03.det.shear": _CORE,
    "ch03.det.multiplicativity": _BRIDGE,
    "ch03.cramer.area-ratio": _BRIDGE,
    "ch03.inverse.undo": _BRIDGE,
    "ch03.inverse.formula": _CORE,
    "ch03.inverse.examples": _CORE,
    "ch03.det.zero.equivalence": _BRIDGE,
}
_PROFILES["ch02.matrix.composition"] = _BRIDGE

# Chapter 4–8 entries share the explicit core policy until chapter-specific
# editorial profiles are authored; the mapping is still materialized per stable
# topic ID so coverage cannot silently drift with the catalog.
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
