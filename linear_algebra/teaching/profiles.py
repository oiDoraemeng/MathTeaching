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
    "ch01.vector.magnitude": _CORE,
    "ch01.vector.point-distinction": _CORE,
    "ch01.vector.coordinate-system": _CORE,
    "ch01.vector.direction-examples": _CORE,
    "ch01.ops.addition": _VECTOR_ADDITION,
    "ch01.ops.subtraction": _CORE,
    "ch01.ops.scalar": _CORE,
    "ch01.ops.linear-combination": _BRIDGE,
    "ch01.ops.velocity": _BRIDGE,
    "ch01.ops.cross-product": _CORE,
    "ch01.ops.scalar-triple": _BRIDGE,
    "ch01.inner.equivalence": _CORE,
    "ch01.inner.definitions": _CORE,
    "ch01.inner.applications": _BRIDGE,
    "ch01.inner.cauchy-schwarz": _CORE,
    "ch01.inner.examples": _CORE,
    "ch01.projection.definition": _CORE,
    "ch01.projection.properties": _CORE,
    "ch01.projection.force": _BRIDGE,
    "ch01.proof.method": _BRIDGE,
    "ch01.proof.midline": _CORE,
    "ch01.proof.centroid": _CORE,
    "ch01.proof.parallelogram-diagonals": _CORE,
    "ch01.high-dimensional.analogy": _ANALOGY,
    "ch02.batch.inner-products": _BRIDGE,
    "ch02.batch.projection": _BRIDGE,
    "ch02.matrix.additive-distributivity": _CORE,
    "ch02.matrix.row-column": _CORE,
    "ch02.matrix.transformed-grid": _CORE,
    "ch02.matrix.stretch-rotate-scale": _CORE,
    "ch02.matrix.composition": _BRIDGE,
    "ch02.matrix.basis": _BRIDGE,
    "ch02.matrix.powers": _CORE,
    "ch02.subspace.independence": _CORE,
    "ch02.subspace.rank": _BRIDGE,
    "ch02.subspace.null": _BRIDGE,
    "ch02.subspace.column": _BRIDGE,
    "ch02.subspace.rank-nullity": _BRIDGE,
    "ch02.high-dimensional.analogy": _ANALOGY,
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
