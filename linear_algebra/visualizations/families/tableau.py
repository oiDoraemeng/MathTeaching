"""Deterministic augmented-matrix elimination storyboards."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from ..compiler import CompileIssue, VisualCompileError


def _number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


@dataclass(frozen=True)
class Swap:
    first: int
    second: int
    label: str = "交换行"


@dataclass(frozen=True)
class Scale:
    row: int
    factor: float
    label: str = "缩放行"


@dataclass(frozen=True)
class Eliminate:
    target: int
    source: int
    factor: float
    label: str = "消元"


RowOperation = Swap | Scale | Eliminate


def _validate_index(index: object, rows: int, field: str) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < rows:
        raise ValueError(f"{field} row index is invalid")
    return index


def _normal_matrix(matrix: object) -> list[list[float]]:
    if not isinstance(matrix, (list, tuple)) or not matrix or len(matrix) > 3:
        raise ValueError("matrix must have 1 to 3 rows")
    if not all(isinstance(row, (list, tuple)) for row in matrix):
        raise ValueError("matrix must be rectangular")
    width = len(matrix[0])
    if width < 1 or width > 3 or any(len(row) != width for row in matrix):
        raise ValueError("matrix must be rectangular and bounded")
    return [[_number(value, "matrix") for value in row] for row in matrix]


def _normal_rhs(rhs: object, rows: int) -> list[float]:
    if not isinstance(rhs, (list, tuple)) or len(rhs) != rows:
        raise ValueError("rhs dimension mismatch")
    return [_number(value, "rhs") for value in rhs]


def _operation_from_mapping(operation: Mapping[str, object]) -> RowOperation:
    kind = operation.get("kind", operation.get("op"))
    try:
        if kind == "swap":
            return Swap(int(operation["first"]), int(operation["second"]), str(operation.get("label", "交换行")))
        if kind == "scale":
            return Scale(int(operation["row"]), _number(operation["factor"], "factor"), str(operation.get("label", "缩放行")))
        if kind == "eliminate":
            return Eliminate(int(operation["target"]), int(operation["source"]), _number(operation["factor"], "factor"), str(operation.get("label", "消元")))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("row operation is invalid") from error
    raise ValueError("row operation kind is invalid")


def apply_row_operation(matrix: Sequence[Sequence[object]], rhs: Sequence[object], operation: RowOperation | Mapping[str, object]) -> tuple[list[list[float]], list[float]]:
    result = _normal_matrix(matrix)
    right = _normal_rhs(rhs, len(result))
    op = _operation_from_mapping(operation) if isinstance(operation, Mapping) else operation
    if isinstance(op, Swap):
        first = _validate_index(op.first, len(result), "first")
        second = _validate_index(op.second, len(result), "second")
        result[first], result[second] = result[second], result[first]
        right[first], right[second] = right[second], right[first]
    elif isinstance(op, Scale):
        row = _validate_index(op.row, len(result), "row")
        factor = _number(op.factor, "factor")
        if factor == 0:
            raise ValueError("factor must be nonzero")
        result[row] = [factor * value for value in result[row]]
        right[row] *= factor
    elif isinstance(op, Eliminate):
        target = _validate_index(op.target, len(result), "target")
        source = _validate_index(op.source, len(result), "source")
        if target == source:
            raise ValueError("target and source rows must differ")
        factor = _number(op.factor, "factor")
        result[target] = [a - factor * b for a, b in zip(result[target], result[source])]
        right[target] -= factor * right[source]
    else:
        raise ValueError("row operation is invalid")
    return result, right


@dataclass(frozen=True)
class TableauStage:
    alias: str
    matrix: tuple[tuple[float, ...], ...]
    rhs: tuple[float, ...]
    operation_label: str
    highlight_rows: tuple[int, ...]
    title: str
    caption: str
    solution_state: str
    rank: int
    augmented_rank: int


@dataclass(frozen=True)
class TableauCompileResult:
    stages: tuple[TableauStage, ...]
    operations: tuple[dict[str, object], ...]
    aliases: tuple[str, ...]
    solution_state: str
    rank: int
    augmented_rank: int


def _rank(matrix: Sequence[Sequence[float]], tolerance: float = 1e-9) -> int:
    rows = [list(row) for row in matrix]
    result = 0
    for column in range(len(rows[0]) if rows else 0):
        pivot = next((i for i in range(result, len(rows)) if abs(rows[i][column]) > tolerance), None)
        if pivot is None:
            continue
        rows[result], rows[pivot] = rows[pivot], rows[result]
        scale = rows[result][column]
        rows[result] = [value / scale for value in rows[result]]
        for i in range(len(rows)):
            if i != result:
                factor = rows[i][column]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[result])]
        result += 1
    return result


class MatrixTableauCompiler:
    @classmethod
    def compile(cls, payload: Mapping[str, object]) -> TableauCompileResult:
        try:
            matrix = _normal_matrix(payload.get("matrix"))
            rhs = _normal_rhs(payload.get("rhs"), len(matrix))
            state = payload.get("solution_state", "unknown")
            if state not in {"unique", "none", "infinite", "unknown"}:
                raise ValueError("solution_state is invalid")
            rank = payload.get("rank", _rank(matrix))
            augmented_rank = payload.get("augmented_rank", _rank([row + [value] for row, value in zip(matrix, rhs)]))
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (rank, augmented_rank)):
                raise ValueError("rank invariants are invalid")
            if augmented_rank < rank:
                raise ValueError("augmented rank must be at least rank")
            operations_raw = payload.get("operations", ())
            if not isinstance(operations_raw, (list, tuple)) or len(operations_raw) > 8:
                raise ValueError("operations must be a bounded sequence")
            operations = tuple(_operation_from_mapping(item) if isinstance(item, Mapping) else item for item in operations_raw)
            prefix = str(payload.get("alias_prefix", "tableau")) or "tableau"
            stages: list[TableauStage] = []
            current_matrix, current_rhs = matrix, rhs

            def add_stage(index: int, label: str, highlights: tuple[int, ...]) -> None:
                stages.append(TableauStage(f"{prefix}__stage_{index}", tuple(tuple(row) for row in current_matrix), tuple(current_rhs), label, highlights, f"第 {index + 1} 阶段", label or "读取增广矩阵", str(state), int(rank), int(augmented_rank)))

            add_stage(0, "初始增广矩阵", ())
            for index, operation in enumerate(operations, start=1):
                current_matrix, current_rhs = apply_row_operation(current_matrix, current_rhs, operation)
                if isinstance(operation, Swap):
                    highlights = (operation.first, operation.second)
                    label = operation.label
                elif isinstance(operation, Scale):
                    highlights = (operation.row,)
                    label = operation.label
                elif isinstance(operation, Eliminate):
                    highlights = (operation.target, operation.source)
                    label = operation.label
                else:
                    raise ValueError("row operation is invalid")
                add_stage(index, label, highlights)
            stage_payloads = tuple({"alias": stage.alias, "matrix": stage.matrix, "rhs": stage.rhs, "operation_label": stage.operation_label, "highlight_rows": stage.highlight_rows, "title": stage.title, "caption": stage.caption, "solution_state": stage.solution_state, "rank": stage.rank, "augmented_rank": stage.augmented_rank} for stage in stages)
            operation = {"op": "geometry.matrix_tableau", "matrix": tuple(tuple(row) for row in matrix), "rhs": tuple(rhs), "stages": stage_payloads, "solution_state": str(state), "rank": int(rank), "augmented_rank": int(augmented_rank), "aliases": tuple(stage.alias for stage in stages)}
            return TableauCompileResult(tuple(stages), (operation,), tuple(stage.alias for stage in stages), str(state), int(rank), int(augmented_rank))
        except (TypeError, ValueError) as error:
            raise VisualCompileError((CompileIssue("invalid_tableau", "$.tableau", str(error)),)) from error


__all__ = ["Swap", "Scale", "Eliminate", "RowOperation", "TableauStage", "TableauCompileResult", "apply_row_operation", "MatrixTableauCompiler"]
