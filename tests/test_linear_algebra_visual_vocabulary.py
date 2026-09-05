"""Contracts for the non-executable visual-semantics vocabulary."""

from __future__ import annotations

import math

import pytest

from linear_algebra.teaching.model import VisualSemantics
from linear_algebra.teaching.vocabulary import (
    ENTITY_KINDS,
    LAYOUTS,
    RELATION_KINDS,
    validate_semantic_value,
)
from tests.teaching_fixtures import composition_artifact_payload


@pytest.mark.parametrize("value", [math.nan, math.inf, "__import__('os')", {"op": "linear.upsert"}])
def test_semantics_reject_unsafe_values(value: object) -> None:
    payload = composition_artifact_payload()["visual_semantics"]
    payload["entities"][0]["value"] = value  # type: ignore[index]

    with pytest.raises(ValueError, match=r"entities\[0\]\.value"):
        VisualSemantics.from_dict(payload)  # type: ignore[arg-type]


def test_semantics_reject_literal_color() -> None:
    payload = composition_artifact_payload()["visual_semantics"]
    payload["entities"][0]["color"] = "#ff0000"  # type: ignore[index]

    with pytest.raises(ValueError, match="color"):
        VisualSemantics.from_dict(payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "issue_path", "path_fragment"),
    [
        ([1], "$.value", "2D or 3D vector"),
        ([1, 2, 3, 4], "$.value", "2D or 3D vector"),
        ([[1, 2], [3]], "$.value[1]", "equal length"),
        ([[1, 2, 3, 4]], "$.value[0]", "more than 3 columns"),
        ([[1], [2], [3], [4]], "$.value", "more than 3 rows"),
    ],
)
def test_semantic_values_have_bounded_numeric_shapes(
    value: object, issue_path: str, path_fragment: str
) -> None:
    issues = validate_semantic_value(value, "$.value")

    assert len(issues) == 1
    assert issues[0].path == issue_path
    assert path_fragment in issues[0].message


def test_semantics_reject_unknown_vocabulary_and_parameter_expressions() -> None:
    payload = composition_artifact_payload()["visual_semantics"]
    payload["entities"][0]["kind"] = "arrow"  # type: ignore[index]
    with pytest.raises(ValueError, match=r"entities\[0\]\.kind"):
        VisualSemantics.from_dict(payload)  # type: ignore[arg-type]

    payload = composition_artifact_payload()["visual_semantics"]
    payload["relations"][0]["parameters"] = {"scale": "2 + 2"}  # type: ignore[index]
    with pytest.raises(ValueError, match=r"relations\[0\]\.parameters\.scale"):
        VisualSemantics.from_dict(payload)  # type: ignore[arg-type]


def test_vocabulary_is_closed_and_valid_fixture_round_trips() -> None:
    assert ENTITY_KINDS == {"point", "vector", "basis", "matrix", "grid", "region", "area", "volume"}
    assert LAYOUTS == {"overlay", "side_by_side", "sequence"}
    assert "maps_to" in RELATION_KINDS

    payload = composition_artifact_payload()["visual_semantics"]
    assert VisualSemantics.from_dict(payload).to_dict() == payload
