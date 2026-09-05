import pytest

from linear_algebra.teaching.examples import verify_worked_example
from linear_algebra.teaching.model import TeachingArtifact, WorkedExample, WorkedExampleCheck
from linear_algebra.teaching.validation import (
    ArtifactValidationError,
    validate_artifact_payload,
    validate_worked_examples,
)
from tests.teaching_fixtures import composition_artifact_payload


def _example(kind: str, given: object, expected: object, *, name: str = "result", tolerance: float = 1e-9) -> WorkedExample:
    return WorkedExample(
        kind=kind,
        given=given,
        calculation=("typed arithmetic",),
        result=expected,
        checks=(WorkedExampleCheck(name=name, expected=expected, tolerance=tolerance),),
    )


def test_matrix_transform_example_is_recomputed() -> None:
    example = _example("matrix_transform", ([[0, -1], [1, 0]], [1, 2]), (-2.0, 1.0))

    result = verify_worked_example(example)

    assert result.valid is True
    assert result.checks[0].expected == (-2.0, 1.0)
    assert result.checks[0].actual == (-2.0, 1.0)


def test_wrong_determinant_is_rejected() -> None:
    example = _example("determinant", [[1, 2], [3, 4]], 6.0, name="determinant")

    result = verify_worked_example(example)

    assert result.valid is False
    assert result.checks[0].code == "value_mismatch"
    assert result.checks[0].actual == -2.0


@pytest.mark.parametrize(
    ("kind", "given", "expected", "name"),
    [
        ("vector_addition", ([1, 2], [3, 4]), (4.0, 6.0), "sum"),
        ("inner_product", ([1, 2], [3, 4]), 11.0, "dot"),
        ("projection", ([3, 4], [1, 0]), (3.0, 0.0), "projection"),
        ("oriented_area", ([1, 0], [0, 2]), 2.0, "area"),
        ("oriented_volume", ([1, 0, 0], [0, 2, 0], [0, 0, 3]), 6.0, "volume"),
    ],
)
def test_supported_vector_and_geometry_kinds(kind: str, given: object, expected: object, name: str) -> None:
    result = verify_worked_example(_example(kind, given, expected, name=name))

    assert result.valid is True


def test_tolerance_is_applied_to_nested_values() -> None:
    example = _example("vector_addition", ([1, 2], [3, 4]), (4.0001, 6.0), name="sum", tolerance=1e-3)

    result = verify_worked_example(example)

    assert result.valid is True


def test_unsupported_or_malformed_examples_require_manual_review() -> None:
    unsupported = verify_worked_example(_example("symbolic_solve", ([1, 2],), 0.0))
    malformed = verify_worked_example(_example("projection", ([1, 2], [0, 0]), (0.0, 0.0)))

    assert unsupported.manual_review is True
    assert unsupported.reason == "unsupported_example_kind"
    assert malformed.manual_review is True
    assert malformed.reason == "invalid_typed_inputs"


def test_validate_worked_examples_reports_mismatch_and_manual_review() -> None:
    payload = composition_artifact_payload()
    payload["explanation"]["worked_examples"] = [  # type: ignore[index]
        {
            "kind": "determinant",
            "given": [[1, 2], [3, 4]],
            "calculation": ["determinant"],
            "result": 6.0,
            "checks": [{"name": "determinant", "expected": 6.0, "tolerance": 1e-9}],
        },
        {
            "kind": "symbolic_solve",
            "given": None,
            "calculation": ["x = ..."],
            "result": None,
            "checks": [{"name": "result", "expected": None, "tolerance": 0.0}],
        },
    ]
    artifact = TeachingArtifact.from_dict(payload)

    issues = validate_worked_examples(artifact)

    assert [(issue.code, issue.path) for issue in issues] == [
        ("worked_example_mismatch", "$.explanation.worked_examples[0]"),
        ("manual_review_required", "$.explanation.worked_examples[1]"),
    ]


def test_artifact_payload_validation_rejects_wrong_numeric_claim() -> None:
    payload = composition_artifact_payload()
    payload["explanation"]["worked_examples"] = [  # type: ignore[index]
        {
            "kind": "determinant",
            "given": [[1, 2], [3, 4]],
            "calculation": ["determinant"],
            "result": 6.0,
            "checks": [{"name": "determinant", "expected": 6.0, "tolerance": 1e-9}],
        }
    ]

    with pytest.raises(ArtifactValidationError) as raised:
        validate_artifact_payload(payload)
    assert raised.value.issues[0].code == "worked_example_mismatch"
