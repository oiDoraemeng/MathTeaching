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
    # This introductory distinction is deliberately constrained to the
    # lecture's definitions, standard-basis formula, and two geometric cases.
    # It does not call for a synthetic derivation or a generic pitfalls block.
    "ch01.vector.point-distinction": _VECTOR_FOUNDATION,
    # Chapters 1--2 are presented as concise lecture notes: definition and
    # formula, an actual derivation only where the lecture gives one, geometric
    # meaning, and checked cases.  Do not force generic "intuition", pitfalls,
    # or cross-topic transfer copy into every small subsection.
    "ch01.vector.coordinate-system": _VECTOR_FOUNDATION,
    "ch01.vector.direction-examples": _VECTOR_FOUNDATION,
    "ch01.ops.addition": _VECTOR_ADDITION,
    "ch01.ops.subtraction": _VECTOR_FOUNDATION,
    "ch01.ops.scalar": _VECTOR_FOUNDATION,
    "ch01.ops.linear-combination": _VECTOR_FOUNDATION,
    "ch01.inner.equivalence": _VECTOR_FOUNDATION,
    "ch01.inner.definitions": _INNER_DEFINITIONS,
    "ch01.inner.applications": _VECTOR_FOUNDATION,
    "ch01.inner.cauchy-schwarz": _VECTOR_FOUNDATION,
    "ch01.inner.examples": _VECTOR_FOUNDATION,
    "ch01.projection.definition": _PROJECTION_DEFINITION,
    "ch01.projection.properties": _VECTOR_FOUNDATION,
    "ch01.projection.force": _VECTOR_FOUNDATION,
    "ch01.proof.method": _VECTOR_FOUNDATION,
    "ch01.proof.midline": _VECTOR_FOUNDATION,
    "ch01.proof.centroid": _VECTOR_FOUNDATION,
    "ch01.proof.parallelogram-diagonals": _VECTOR_FOUNDATION,
    "ch01.high-dimensional.analogy": _VECTOR_FOUNDATION,
    "ch02.batch.inner-products": _VECTOR_FOUNDATION,
    "ch02.batch.projection": _VECTOR_FOUNDATION,
    "ch02.matrix.additive-distributivity": _VECTOR_FOUNDATION,
    "ch02.matrix.row-column": _VECTOR_FOUNDATION,
    "ch02.matrix.transformed-grid": _VECTOR_FOUNDATION,
    "ch02.matrix.stretch-rotate-scale": _VECTOR_FOUNDATION,
    "ch02.matrix.composition": _VECTOR_FOUNDATION,
    "ch02.matrix.basis": _VECTOR_FOUNDATION,
    "ch02.matrix.powers": _VECTOR_FOUNDATION,
    "ch02.subspace.independence": _VECTOR_FOUNDATION,
    "ch02.subspace.rank": _VECTOR_FOUNDATION,
    "ch02.subspace.null": _VECTOR_FOUNDATION,
    "ch02.subspace.column": _VECTOR_FOUNDATION,
    "ch02.subspace.rank-nullity": _VECTOR_FOUNDATION,
    "ch02.high-dimensional.analogy": _VECTOR_FOUNDATION,
    "ch03.det.oriented-area": _CORE,
    "ch03.det.ad-bc": _CORE,
    "ch03.det.sign-zero-one": _CORE,
    "ch03.det.examples": _CORE,
    "ch03.det.row-swap": _CORE,
    "ch03.det.scaling": _CORE,
    "ch03.det.shear": _CORE,
    "ch03.det.multiplicativity": _BRIDGE,
    "ch03.cramer.area-ratio": _BRIDGE,
    "ch03.inverse.undo": _BRIDGE,
    "ch03.inverse.formula": _CORE,
    "ch03.inverse.examples": _CORE,
    "ch03.det.zero.equivalence": _BRIDGE,
    "ch03.det.high-dimensional-volume": _ANALOGY,
    "ch03.inverse.reverse-order": _BRIDGE,
}
_PROFILES["ch02.matrix.composition"] = _BRIDGE
_PROFILES["ch02.high-dimensional.analogy"] = _ANALOGY

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
