"""Bounded, deterministic verification for typed worked examples.

The verifier intentionally accepts only a small vocabulary of vector and
matrix operations.  ``calculation`` remains explanatory prose; it is never
parsed or executed.  Inputs are read from ``given`` and the claims in
``checks`` are recomputed with explicit arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Mapping, Sequence

from .model import JsonValue, WorkedExample, WorkedExampleCheck


SUPPORTED_KINDS = frozenset(
    {
        "vector_addition",
        "linear_combination",
        "scalar_multiple",
        "cross_product",
        "inner_product",
        "projection",
        "batch_projection",
        "matrix_additive_distributivity",
        "matrix_product",
        "matrix_transform",
        "determinant",
        "oriented_area",
        "oriented_volume",
    }
)

# 校验统一使用绝对和相对容差，兼顾小数稳定性与整数精度。
DEFAULT_TOLERANCE = 1e-9
MAX_DIMENSION = 3


@dataclass(frozen=True)
class ExampleCheck:
    """Result of comparing one declared check with a recomputed value."""

    name: str
    expected: JsonValue
    actual: JsonValue
    tolerance: float
    valid: bool
    code: str


@dataclass(frozen=True)
class ExampleCheckResult:
    """Stable verification outcome for a worked example."""

    valid: bool
    checks: tuple[ExampleCheck, ...] = ()
    manual_review: bool = False
    reason: str = ""

    @classmethod
    def manual(cls, reason: str) -> "ExampleCheckResult":
        return cls(valid=False, manual_review=True, reason=reason)


@dataclass(frozen=True)
class _Calculation:
    value: JsonValue
    named_values: Mapping[str, JsonValue]


def verify_worked_example(example: WorkedExample) -> ExampleCheckResult:
    """Recompute a supported example and compare all of its checks.

    Unsupported kinds, malformed dimensions, zero projection directions, and
    missing checks are deliberately not guessed.  They produce a manual-review
    result instead of evaluating model-provided strings.
    """

    if example.kind not in SUPPORTED_KINDS:
        return ExampleCheckResult.manual("unsupported_example_kind")
    if not example.checks:
        return ExampleCheckResult.manual("missing_numeric_check")
    try:
        calculation = _calculate(example.kind, example.given)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return ExampleCheckResult.manual("invalid_typed_inputs")

    checks = tuple(_compare_check(check, calculation) for check in example.checks)
    return ExampleCheckResult(valid=all(item.valid for item in checks), checks=checks)


def _calculate(kind: str, given: JsonValue) -> _Calculation:
    if kind == "vector_addition":
        left, right = _pair(given, "a", "b")
        a = _vector(left)
        b = _vector(right, dimension=len(a))
        value = tuple(x + y for x, y in zip(a, b))
        return _named(value, result=value, sum=value, output=value)

    if kind == "linear_combination":
        if isinstance(given, Mapping):
            vectors_value = given.get("vectors")
            coefficients_value = given.get("coefficients")
            if vectors_value is None or coefficients_value is None:
                raise ValueError("given mapping is missing vectors or coefficients")
        else:
            vectors_value, coefficients_value = _pair(given, "vectors", "coefficients")
        raw_vectors = _sequence(vectors_value)
        coefficients = _sequence(coefficients_value)
        if len(raw_vectors) not in (2, 3) or len(raw_vectors) != len(coefficients):
            raise ValueError("linear combination requires two or three matching terms")
        vectors = tuple(_vector(vector) for vector in raw_vectors)
        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise ValueError("linear combination vectors must share a dimension")
        scalars = tuple(_number(value) for value in coefficients)
        value = tuple(
            sum(scalars[index] * vectors[index][coordinate] for index in range(len(vectors)))
            for coordinate in range(dimension)
        )
        return _named(value, result=value, linear_combination=value, output=value)

    if kind == "scalar_multiple":
        if isinstance(given, Mapping):
            if "scalar" not in given or "vector" not in given:
                raise ValueError("given mapping is missing scalar/vector operands")
            scalar_value, vector_value = given["scalar"], given["vector"]
        else:
            operands = _sequence(given)
            if len(operands) != 2:
                raise ValueError("expected scalar and vector operands")
            scalar_value, vector_value = operands
        scalar = _number(scalar_value)
        vector = _vector(vector_value)
        value = tuple(scalar * item for item in vector)
        return _named(value, result=value, scalar_multiple=value, output=value)

    if kind == "cross_product":
        left, right = _pair(given, "a", "b")
        a = _vector(left, dimension=3)
        b = _vector(right, dimension=3)
        value = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
        return _named(value, result=value, cross_product=value, output=value)

    if kind == "inner_product":
        left, right = _pair(given, "a", "b")
        a = _vector(left)
        b = _vector(right, dimension=len(a))
        value = float(sum(x * y for x, y in zip(a, b)))
        return _named(value, result=value, inner_product=value, dot=value, dot_product=value)

    if kind == "projection":
        vector_value, direction_value = _pair(given, "vector", "direction")
        vector = _vector(vector_value)
        direction = _vector(direction_value, dimension=len(vector))
        denominator = sum(item * item for item in direction)
        if math.isclose(denominator, 0.0, abs_tol=0.0, rel_tol=0.0):
            raise ValueError("projection direction must be non-zero")
        coefficient = sum(x * y for x, y in zip(vector, direction)) / denominator
        value = tuple(coefficient * item for item in direction)
        residual = tuple(x - y for x, y in zip(vector, value))
        return _named(
            value,
            result=value,
            projection=value,
            coefficient=coefficient,
            residual=residual,
        )

    if kind == "batch_projection":
        if isinstance(given, Mapping):
            vectors_value = given.get("vectors")
            direction_value = given.get("direction")
            if vectors_value is None or direction_value is None:
                raise ValueError("given mapping is missing vectors/direction operands")
        else:
            vectors_value, direction_value = _pair(given, "vectors", "direction")
        vectors = tuple(_vector(value) for value in _sequence(vectors_value))
        if not vectors or len(vectors) > 4:
            raise ValueError("batch projection requires one to four vectors")
        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise ValueError("batch projection vectors must share a dimension")
        direction = _vector(direction_value, dimension=dimension)
        denominator = sum(item * item for item in direction)
        if math.isclose(denominator, 0.0, abs_tol=0.0, rel_tol=0.0):
            raise ValueError("projection direction must be non-zero")
        value = tuple(
            tuple(
                sum(x * y for x, y in zip(vector, direction)) / denominator * item
                for item in direction
            )
            for vector in vectors
        )
        return _named(value, result=value, projection=value, projections=value)

    if kind == "matrix_transform":
        matrix_value, vector_value = _pair(given, "matrix", "vector")
        matrix = _matrix(matrix_value)
        vector = _vector(vector_value, dimension=len(matrix[0]))
        if len(matrix) != len(vector):
            raise ValueError("matrix and vector dimensions do not match")
        value = tuple(float(sum(row[j] * vector[j] for j in range(len(vector)))) for row in matrix)
        return _named(value, result=value, transformed=value, output=value)

    if kind == "matrix_product":
        left_value, right_value = _pair(given, "A", "B")
        left, right = _matrix(left_value), _matrix(right_value)
        if len(left[0]) != len(right):
            raise ValueError("matrix product dimensions do not match")
        product = tuple(
            tuple(sum(row[k] * right[k][j] for k in range(len(right))) for j in range(len(right[0])))
            for row in left
        )
        transpose = lambda matrix: tuple(tuple(row[j] for row in matrix) for j in range(len(matrix[0])))
        left_t, right_t = transpose(left), transpose(right)
        reverse = tuple(
            tuple(sum(row[k] * left_t[k][j] for k in range(len(left_t))) for j in range(len(left_t[0])))
            for row in right_t
        )
        return _named(
            product, result=product, transpose_a=left_t,
            transpose_product=transpose(product), reverse_product=reverse,
        )

    if kind == "matrix_additive_distributivity":
        matrix_a_value, matrix_b_value, vector_value = _triple(given, "A", "B", "x")
        matrix_a = _matrix(matrix_a_value)
        matrix_b = _matrix(matrix_b_value)
        if len(matrix_a) != len(matrix_b) or any(
            len(row_a) != len(row_b) for row_a, row_b in zip(matrix_a, matrix_b)
        ):
            raise ValueError("matrix operands must have matching dimensions")
        vector = _vector(vector_value, dimension=len(matrix_a[0]))
        if len(matrix_a) != len(vector):
            raise ValueError("matrix and vector dimensions do not match")
        matrix_sum = tuple(
            tuple(left + right for left, right in zip(row_a, row_b))
            for row_a, row_b in zip(matrix_a, matrix_b)
        )
        left_path = tuple(
            float(sum(row[index] * vector[index] for index in range(len(vector))))
            for row in matrix_sum
        )
        transformed_a = tuple(
            float(sum(row[index] * vector[index] for index in range(len(vector))))
            for row in matrix_a
        )
        transformed_b = tuple(
            float(sum(row[index] * vector[index] for index in range(len(vector))))
            for row in matrix_b
        )
        right_path = tuple(
            left + right for left, right in zip(transformed_a, transformed_b)
        )
        return _named(
            left_path,
            result=left_path,
            transformed=left_path,
            output=left_path,
            left_path=left_path,
            right_path=right_path,
            transformed_a=transformed_a,
            transformed_b=transformed_b,
        )

    if kind == "determinant":
        matrix = _matrix(_mapping_or_value(given, "matrix"))
        value = _determinant(matrix)
        return _named(value, result=value, determinant=value, det=value)

    if kind == "oriented_area":
        left, right = _pair(given, "a", "b")
        a = _vector(left, dimension=2)
        b = _vector(right, dimension=2)
        value = float(a[0] * b[1] - a[1] * b[0])
        return _named(value, result=value, area=value, determinant=value)

    if kind == "oriented_volume":
        first, second, third = _triple(given, "a", "b", "c")
        a = _vector(first, dimension=3)
        b = _vector(second, dimension=3)
        c = _vector(third, dimension=3)
        cross = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        value = float(sum(a[index] * cross[index] for index in range(3)))
        return _named(value, result=value, volume=value, triple_product=value)

    raise ValueError(f"unsupported example kind: {kind}")


def _named(value: JsonValue, **named_values: JsonValue) -> _Calculation:
    values = dict(named_values)
    values.setdefault("result", value)
    return _Calculation(value=value, named_values=MappingProxyType(values))


def _compare_check(check: WorkedExampleCheck, calculation: _Calculation) -> ExampleCheck:
    expected = _normalise(check.expected)
    actual = calculation.named_values.get(check.name, calculation.value)
    actual = _normalise(actual)
    tolerance = check.tolerance if check.tolerance >= 0 else DEFAULT_TOLERANCE
    valid = _values_close(expected, actual, tolerance)
    return ExampleCheck(
        name=check.name,
        expected=expected,
        actual=actual,
        tolerance=tolerance,
        valid=valid,
        code="ok" if valid else "value_mismatch",
    )


def _values_close(expected: object, actual: object, tolerance: float) -> bool:
    if isinstance(expected, Mapping) or isinstance(actual, Mapping):
        if not isinstance(expected, Mapping) or not isinstance(actual, Mapping):
            return False
        if set(expected) != set(actual):
            return False
        return all(_values_close(expected[key], actual[key], tolerance) for key in expected)
    if isinstance(expected, (tuple, list)) or isinstance(actual, (tuple, list)):
        if not isinstance(expected, (tuple, list)) or not isinstance(actual, (tuple, list)):
            return False
        return len(expected) == len(actual) and all(
            _values_close(left, right, tolerance) for left, right in zip(expected, actual)
        )
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(expected), float(actual), rel_tol=tolerance, abs_tol=tolerance)
    return expected == actual


def _normalise(value: JsonValue) -> JsonValue:
    if isinstance(value, tuple):
        return tuple(_normalise(item) for item in value)
    if isinstance(value, list):
        return tuple(_normalise(item) for item in value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _normalise(item) for key, item in value.items()})
    return value


def _pair(value: JsonValue, first_key: str, second_key: str) -> tuple[JsonValue, JsonValue]:
    if isinstance(value, Mapping):
        if first_key not in value or second_key not in value:
            # 接受常用描述别名，但拒绝任意表达式和可执行载荷。
            aliases = {
                ("vector", "direction"): ("v", "u"),
                ("matrix", "vector"): ("A", "x"),
            }
            pair = aliases.get((first_key, second_key))
            if pair is None or pair[0] not in value or pair[1] not in value:
                raise ValueError("given mapping is missing typed operands")
            return value[pair[0]], value[pair[1]]
        return value[first_key], value[second_key]
    sequence = _sequence(value)
    if len(sequence) != 2:
        raise ValueError("expected two operands")
    return sequence[0], sequence[1]


def _triple(value: JsonValue, first_key: str, second_key: str, third_key: str) -> tuple[JsonValue, JsonValue, JsonValue]:
    if isinstance(value, Mapping):
        if all(key in value for key in (first_key, second_key, third_key)):
            return value[first_key], value[second_key], value[third_key]
        aliases = ("u", "v", "w")
        if all(key in value for key in aliases):
            return value[aliases[0]], value[aliases[1]], value[aliases[2]]
        raise ValueError("given mapping is missing typed operands")
    sequence = _sequence(value)
    if len(sequence) != 3:
        raise ValueError("expected three operands")
    return sequence[0], sequence[1], sequence[2]


def _mapping_or_value(value: JsonValue, key: str) -> JsonValue:
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        if key == "matrix" and "A" in value:
            return value["A"]
        raise ValueError(f"given mapping is missing {key}")
    return value


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, (tuple, list)):
        raise TypeError("expected a JSON array")
    return value


def _vector(value: object, *, dimension: int | None = None) -> tuple[float, ...]:
    values = _sequence(value)
    if len(values) not in (2, 3) or (dimension is not None and len(values) != dimension):
        raise ValueError("expected a 2D or 3D vector")
    result = tuple(_number(item) for item in values)
    return result


def _matrix(value: object) -> tuple[tuple[float, ...], ...]:
    rows = _sequence(value)
    if len(rows) not in (2, 3):
        raise ValueError("expected a 2x2 or 3x3 matrix")
    converted = tuple(_vector(row, dimension=len(rows)) for row in rows)
    return converted


def _determinant(matrix: tuple[tuple[float, ...], ...]) -> float:
    if len(matrix) == 2:
        return float(matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0])
    a, b, c = matrix
    return float(
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise TypeError("expected a finite numeric scalar")
    return float(value)


__all__ = [
    "DEFAULT_TOLERANCE",
    "ExampleCheck",
    "ExampleCheckResult",
    "SUPPORTED_KINDS",
    "verify_worked_example",
]
