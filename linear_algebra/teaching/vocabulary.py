"""Closed, non-executable vocabulary for visual teaching semantics."""

from __future__ import annotations

from dataclasses import dataclass
import math


ENTITY_KINDS = frozenset({"point", "vector", "basis", "matrix", "grid", "region", "area", "volume", "subspace", "affine_set", "constraint", "eigenspace", "principal_axis", "quadratic_level_set"})
RELATION_KINDS = frozenset(
    {
        "sum", "difference", "scalar_multiple", "maps_to", "spans", "span", "projects_to",
        "orthogonal_to", "collapses_to", "composition_order", "compare", "orientation",
        "decomposes_into", "has_foot", "has_residual", "batch_maps_to", "endpoint_diff",
        "same_measure", "invariant", "contains", "affine_translation", "constraint_state", "row_operation", "coordinate_equivalence", "eigen_binding", "principal_axis", "classification",
        # Chapter-4 mathematical bindings.  These names distinguish a true
        # intersection, kernel/image/rank fact, and linearity test from a
        # generic arrow or display annotation.
        "intersects_in", "union_counterexample", "kernel_of", "image_of",
        "dimension_of", "linear_combination", "null_solution", "rank_of",
        "nullity_of", "basis_of", "linear_dependence", "additivity",
        "homogeneity", "not_linear", "column_image", "rank_nullity",
    }
)
LAYOUTS = frozenset({"overlay", "side_by_side", "sequence"})

VECTOR_DIMENSIONS = frozenset({2, 3})
MAX_MATRIX_ROWS = 3
MAX_MATRIX_COLUMNS = 3


@dataclass(frozen=True)
class VisualVocabulary:
    """Versioned projection of the closed vocabulary passed to the agent.

    The model sees names only; this record intentionally contains no rendering
    operations, colors, camera values, or other executable scene data.
    """

    version: str
    entity_kinds: tuple[str, ...]
    relation_kinds: tuple[str, ...]
    layouts: tuple[str, ...]

    @classmethod
    def v1(cls) -> "VisualVocabulary":
        """Return the canonical, deterministically ordered vocabulary."""

        return cls(
            version="visual-vocabulary-v1",
            entity_kinds=tuple(sorted(ENTITY_KINDS)),
            relation_kinds=tuple(sorted(RELATION_KINDS)),
            layouts=tuple(sorted(LAYOUTS)),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe projection suitable for a model prompt."""

        return {
            "version": self.version,
            "entity_kinds": list(self.entity_kinds),
            "relation_kinds": list(self.relation_kinds),
            "layouts": list(self.layouts),
        }


@dataclass(frozen=True)
class SemanticIssue:
    """One bounded diagnostic produced while checking a semantic value."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def require_finite_number(value: object, path: str) -> float:
    """Return a finite numeric value, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: expected number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{path}: expected finite number") from error
    if not math.isfinite(number):
        raise ValueError(f"{path}: expected finite number")
    return number


def validate_semantic_value(value: object, path: str) -> tuple[SemanticIssue, ...]:
    """Validate a scalar, 2D/3D vector, or bounded rectangular matrix."""
    try:
        _validate_semantic_value(value, path)
    except ValueError as error:
        message = str(error)
        issue_path, separator, detail = message.partition(": ")
        if separator and issue_path.startswith(path):
            return (SemanticIssue(issue_path, detail),)
        return (SemanticIssue(path, message),)
    return ()


def _validate_semantic_value(value: object, path: str) -> None:
    # A staged composition carries a bounded sequence of matrices.  Keep this
    # exception explicit and path-scoped so arbitrary nested payloads remain
    # rejected by the normal semantic vocabulary.
    if path.endswith(".matrices"):
        _validate_matrix_sequence(value, path)
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        require_finite_number(value, path)
        return
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{path}: expected scalar, 2D/3D vector, or matrix")

    if all(_is_number(item) for item in value):
        if len(value) not in VECTOR_DIMENSIONS:
            raise ValueError(f"{path}: expected 2D or 3D vector")
        for index, item in enumerate(value):
            require_finite_number(item, f"{path}[{index}]")
        return

    if not value or not all(_is_sequence(row) for row in value):
        raise ValueError(f"{path}: expected scalar, 2D/3D vector, or matrix")
    if len(value) > MAX_MATRIX_ROWS:
        raise ValueError(f"{path}: matrix has more than {MAX_MATRIX_ROWS} rows")

    first_row = value[0]
    assert isinstance(first_row, (list, tuple))
    if not first_row:
        raise ValueError(f"{path}[0]: matrix row must not be empty")
    if len(first_row) > MAX_MATRIX_COLUMNS:
        raise ValueError(f"{path}[0]: matrix has more than {MAX_MATRIX_COLUMNS} columns")
    column_count = len(first_row)

    for row_index, row in enumerate(value):
        assert isinstance(row, (list, tuple))
        if len(row) != column_count:
            raise ValueError(f"{path}[{row_index}]: matrix rows must have equal length")
        for column_index, item in enumerate(row):
            require_finite_number(item, f"{path}[{row_index}][{column_index}]")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_sequence(value: object) -> bool:
    return not isinstance(value, (str, bytes)) and isinstance(value, (list, tuple))


def _validate_matrix_sequence(value: object, path: str) -> None:
    if not isinstance(value, (list, tuple)) or not value or len(value) > 3:
        raise ValueError(f"{path}: expected one to three matrices")
    for index, matrix in enumerate(value):
        _validate_semantic_matrix(matrix, f"{path}[{index}]")


def _validate_semantic_matrix(value: object, path: str) -> None:
    if not isinstance(value, (list, tuple)) or not value or len(value) > MAX_MATRIX_ROWS:
        raise ValueError(f"{path}: expected a bounded matrix")
    if not all(isinstance(row, (list, tuple)) for row in value):
        raise ValueError(f"{path}: expected a bounded matrix")
    first_row = value[0]
    if not first_row or len(first_row) > MAX_MATRIX_COLUMNS:
        raise ValueError(f"{path}: matrix has invalid column count")
    column_count = len(first_row)
    for row_index, row in enumerate(value):
        if len(row) != column_count:
            raise ValueError(f"{path}[{row_index}]: matrix rows must have equal length")
        for column_index, item in enumerate(row):
            require_finite_number(item, f"{path}[{row_index}][{column_index}]")


__all__ = [
    "ENTITY_KINDS", "LAYOUTS", "MAX_MATRIX_COLUMNS", "MAX_MATRIX_ROWS", "RELATION_KINDS",
    "SemanticIssue", "VECTOR_DIMENSIONS", "VisualVocabulary", "require_finite_number",
    "validate_semantic_value",
]
