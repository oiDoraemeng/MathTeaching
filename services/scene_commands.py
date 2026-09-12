"""受约束的 2D/3D 场景命令协议与确定性教学宏。

该模块不依赖 Qt，也不执行模型返回的 Python。命令服务只负责验证和把
结构化计划交给一个宿主适配器，因此可以在单元测试、内置助手和本地
MCP 入口之间复用。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Protocol

from .agent_provider import AgentProvider


def _validate_budget(*args: object, **kwargs: object) -> tuple[str, ...]:
    """Load visual budget validation lazily to keep the command protocol acyclic.

    Visualization recipe builders depend on ``CommandPlan``.  Importing their
    package while this module is still defining that class creates a cycle;
    budget validation is only needed when an operation is actually validated.
    """

    from linear_algebra.visualizations.limits import validate_budget

    return validate_budget(*args, **kwargs)


class CommandError(ValueError):
    """场景命令不符合白名单协议或数学约束。"""


@dataclass(frozen=True)
class CommandPlan:
    """可序列化的 Agent 命令计划。"""

    version: int = 1
    scene: str = "2d"
    operations: tuple[dict[str, Any], ...] = ()
    summary: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CommandPlan":
        if not isinstance(payload, dict):
            raise CommandError("命令计划必须是 JSON 对象。")
        operations = payload.get("operations", ())
        if not isinstance(operations, list) or not all(isinstance(operation, dict) for operation in operations):
            raise CommandError("operations 必须是数组。")
        try:
            version = int(payload.get("version", 1))
        except (TypeError, ValueError) as error:
            raise CommandError("version 必须是整数。") from error
        return cls(
            version=version,
            scene=str(payload.get("scene", "2d")),
            operations=tuple(dict(operation) for operation in operations),
            summary=str(payload.get("summary", "")),
        )

    @classmethod
    def from_json(cls, source: str) -> "CommandPlan":
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as error:
            raise CommandError(f"命令计划不是有效 JSON: {error.msg}") from error
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "scene": self.scene,
            "summary": self.summary,
            "operations": [dict(operation) for operation in self.operations],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class CommandValidation:
    valid: bool
    messages: tuple[str, ...] = ()
    expanded_operations: tuple[dict[str, Any], ...] = ()


class _ReplayRegistry:
    """Deterministic operation adapters shared by offline replay and hosts."""

    def __init__(self) -> None:
        self._adapters: dict[str, object] = {}

    def register(self, name: str, adapter: object) -> None:
        self._adapters[name] = adapter

    def has(self, name: str) -> bool:
        return name in self._adapters

    def dispatch(self, host: SceneCommandHost, operation: dict[str, Any]) -> None:
        try:
            adapter = self._adapters[operation["op"]]
        except (KeyError, TypeError) as error:
            raise CommandError(f"replay adapter missing: {operation.get('op')!r}") from error
        adapter(host, operation)  # type: ignore[misc]


replay_registry = _ReplayRegistry()


class SceneCommandHost(Protocol):
    """GUI 宿主需要提供的最小命令适配接口。"""

    def apply_scene_command(self, operation: dict[str, Any]) -> None: ...

    def begin_scene_command_transaction(self) -> None: ...

    def commit_scene_command_transaction(self) -> None: ...

    def rollback_scene_command_transaction(self) -> None: ...

    def check_scene_fingerprint(self, expected: str) -> bool: ...


_ALLOWED_OPERATIONS = frozenset(
    {
        "scene.set_mode",
        "scene.clear",
        "curve.create",
        "curve.update",
        "curve.delete",
        "point.upsert",
        "point3d.upsert",
        "point3d.delete",
        "point.delete",
        "linear.upsert",
        "linear3d.upsert",
        "linear.delete",
        "teach.vector_addition",
        "annotation.upsert",
        "annotation.formula",
        "annotation.delete",
        "view.fit",
        "scene.export_png",
        "surface.create",
        "surface.update",
        "surface.delete",
        "calculus.derivative",
        "calculus.integral_area",
        "area.fill",
        "calculus.tangent",
        "linear_algebra.matrix_transform",
        "linear_algebra.determinant_area",
        "geometry.polygon",
        "geometry.angle_arc",
        "geometry.right_angle_marker",
        "geometry.projection",
        "geometry.transformed_grid",
        "geometry.subspace_region",
        "geometry.subspace3d",
        "geometry.affine_solution",
        "geometry.mapping_bundle",
        "geometry.staged_transform",
        "geometry.oriented_area",
        "geometry.parallelogram3d",
        "geometry.parallelepiped",
        "geometry.oriented_volume",
        "plane3d.upsert",
        "geometry.intersection",
        "geometry.constraint",
        "geometry.matrix_tableau",
        "geometry.elimination_tableau",
        "geometry.basis_grid",
        "geometry.coordinate_readout",
        "geometry.least_squares",
        "geometry.spectrum",
        "geometry.projection3d",
        "geometry.orthogonalization",
        "geometry.quadratic_level_set",
    }
)
_SCENE_VALUES = frozenset({"2d", "3d"})
_KIND_VALUES = frozenset({"line", "segment", "ray", "vector"})
_CURVE_KINDS = frozenset({"explicit", "implicit", "parametric"})
_STYLE_VALUES = frozenset({"solid", "dashed"})
_ROLE_VALUES = frozenset({"primary", "construction", "result"})
_THREE_D_OPERATIONS = frozenset({
    "point3d.upsert", "point3d.delete", "linear3d.upsert", "plane3d.upsert",
    "geometry.parallelogram3d", "geometry.parallelepiped", "geometry.oriented_volume",
    "geometry.subspace3d",
    "surface.create", "surface.update", "surface.delete", "geometry.intersection", "geometry.constraint",
    "geometry.projection3d", "geometry.orthogonalization",
})
_TWO_D_OPERATIONS = frozenset(
    {
        "point.upsert",
        "point.delete",
        "linear.upsert",
        "linear.delete",
        "curve.create",
        "curve.update",
        "curve.delete",
        "annotation.upsert",
        "annotation.delete",
        "teach.vector_addition",
        "calculus.derivative",
        "calculus.integral_area",
        "calculus.tangent",
        "linear_algebra.matrix_transform",
        "linear_algebra.determinant_area",
        "area.fill",
        "geometry.polygon",
        "geometry.angle_arc",
        "geometry.right_angle_marker",
        "geometry.projection",
        "geometry.transformed_grid",
        "geometry.subspace_region",
        "geometry.affine_solution",
        "geometry.mapping_bundle",
        "geometry.staged_transform",
        "geometry.oriented_area",
    }
)


def _validate_scene_scope(scene: str, operation: dict[str, Any]) -> None:
    name = operation.get("op")
    if name == "scene.set_mode" and str(operation.get("mode", scene)) != scene:
        raise CommandError("scene.set_mode.mode 必须与 CommandPlan.scene 一致。")
    if scene == "2d" and name in _THREE_D_OPERATIONS:
        raise CommandError(f"{name} 只能用于 scene=3d。")
    if scene == "3d" and name in _TWO_D_OPERATIONS:
        raise CommandError(f"{name} 只能用于 scene=2d。")


def _matrix_rank_for_command(matrix: list[list[Any]]) -> int:
    rows = [[float(value) for value in row] for row in matrix]
    rank = 0
    for column in range(len(rows[0]) if rows else 0):
        pivot = next((index for index in range(rank, len(rows)) if abs(rows[index][column]) > 1e-9), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][column]
        rows[rank] = [value / scale for value in rows[rank]]
        for index in range(len(rows)):
            if index != rank:
                factor = rows[index][column]
                rows[index] = [left - factor * right for left, right in zip(rows[index], rows[rank])]
        rank += 1
    return rank


def _matrix_determinant(matrix: list[list[Any]]) -> float:
    values = [[float(value) for value in row] for row in matrix]
    if len(values) == 2:
        return values[0][0] * values[1][1] - values[0][1] * values[1][0]
    return (
        values[0][0] * (values[1][1] * values[2][2] - values[1][2] * values[2][1])
        - values[0][1] * (values[1][0] * values[2][2] - values[1][2] * values[2][0])
        + values[0][2] * (values[1][0] * values[2][1] - values[1][1] * values[2][0])
    )


class SceneCommandService:
    """验证、展开并原子执行白名单场景命令。"""

    def __init__(self, host: SceneCommandHost | None = None) -> None:
        self.host = host
        self._last_plan: CommandPlan | None = None

    @property
    def allowed_operations(self) -> frozenset[str]:
        return _ALLOWED_OPERATIONS

    def validate(self, plan: CommandPlan) -> CommandValidation:
        messages: list[str] = []
        expanded: list[dict[str, Any]] = []
        if plan.version != 1:
            messages.append("只支持命令协议 version=1。")
        if plan.scene not in _SCENE_VALUES:
            messages.append("scene 必须是 2d 或 3d。")
        if not plan.operations:
            messages.append("命令计划至少需要一个操作。")
        for index, operation in enumerate(plan.operations):
            try:
                _validate_scene_scope(plan.scene, operation)
                produced = self._validate_operation(operation)
                # 宏命令展开后再次通过原子白名单校验，保证最终交给宿主的每个
                # operation 都有完整字段约束，而不是只验证外层宏名称。
                for generated in produced:
                    _validate_scene_scope(plan.scene, generated)
                    expanded.extend(self._validate_operation(generated))
            except CommandError as error:
                messages.append(f"操作 {index + 1}: {error}")
        if not messages and plan.scene in _SCENE_VALUES:
            # The command host must never infer a target workspace. Normalize
            # all redundant macro/user mode operations to one leading action.
            expanded = [operation for operation in expanded if operation.get("op") != "scene.set_mode"]
            expanded.insert(0, {"op": "scene.set_mode", "mode": plan.scene})
        return CommandValidation(not messages, tuple(messages), tuple(expanded))

    def preview(self, plan: CommandPlan) -> CommandValidation:
        return self.validate(plan)

    def execute(self, plan: CommandPlan, *, expected_scene_fingerprint: str | None = None,
                pane_id: str | None = None, activate_pane: bool = True) -> CommandValidation:
        validation = self.validate(plan)
        if not validation.valid:
            raise CommandError("；".join(validation.messages))
        if self.host is None:
            raise CommandError("命令服务尚未绑定场景宿主。")
        host = self.host
        bind_pane = getattr(host, "for_pane", None)
        if callable(bind_pane):
            # Resolve focus once, before the first mutation, on the host's GUI
            # thread. Every operation and rollback uses that same pane.
            host = bind_pane(pane_id)
        elif pane_id is not None:
            raise CommandError("当前场景宿主不支持 pane_id 路由。")
        # A user tool must never switch a focused pane's mode implicitly.  If
        # the destination pane is in another mode, return a structured
        # unsupported result before opening a transaction or mutating state.
        current_mode = getattr(host, "scene_mode", None)
        if current_mode is None:
            current_mode = getattr(host, "mode", None)
        if current_mode is not None:
            current_mode = getattr(current_mode, "value", current_mode)
            if str(current_mode).lower() != str(plan.scene).lower():
                return CommandValidation(
                    False,
                    (f"unsupported_mode: pane 当前为 {current_mode}，命令需要 {plan.scene}",),
                    (),
                )
        check_fingerprint = getattr(host, "check_scene_fingerprint", None)
        if expected_scene_fingerprint is not None and callable(check_fingerprint) and not check_fingerprint(expected_scene_fingerprint):
            raise CommandError("scene_changed_since_plan")
        # User tools select their explicit destination before mutation. Agent
        # callers can keep a pinned destination without moving user focus.
        activate = getattr(host, "activate_for_tool", None)
        if activate_pane and pane_id is not None and callable(activate):
            activate()
        host.begin_scene_command_transaction()
        try:
            for operation in validation.expanded_operations:
                host.apply_scene_command(operation)
            host.commit_scene_command_transaction()
        except Exception:
            host.rollback_scene_command_transaction()
            raise
        self._last_plan = plan
        return validation

    def undo(self) -> None:
        if self.host is None:
            raise CommandError("命令服务尚未绑定场景宿主。")
        undo = getattr(self.host, "_undo_scene_command", None) or getattr(self.host, "_undo_2d_geometry", None)
        if undo is None:
            raise CommandError("当前场景宿主不支持撤销。")
        undo()

    def _validate_operation(self, operation: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(operation, dict):
            raise CommandError("操作必须是 JSON 对象。")
        name = operation.get("op")
        if name not in _ALLOWED_OPERATIONS:
            raise CommandError(f"不支持的操作: {name!r}。")
        known_keys = {"op", "alias", "coordinates", "name", "kind", "role", "color", "style", "start", "end", "bounds", "matrix", "rhs", "tolerance", "solution_state", "rank", "augmented_rank", "entity_count", "stage_count", "sample_count", "vectors", "stages", "aliases", "eigenvalues", "principal_axes", "signature", "classification", "contour_vertices", "contour_segments", "mesh_vertices", "mesh_faces", "axis_segments", "basis_matrix", "standard_vector", "alternate_coordinates", "basis_alias", "standard_alias", "alternate_alias", "values", "coefficients", "fit", "projection", "residual", "vector", "right_angle", "data_alias", "fit_alias", "projection_alias", "residual_alias", "eigenspaces", "roots", "roots_alias", "complex_roots", "operation_label", "highlight_rows", "scene", "alias_prefix", "basis", "origin", "offset", "opacity", "vertices", "outline", "step", "direction", "foot", "intersection_alias", "state_alias", "domain_basis", "kernel_basis", "image_basis", "lanes", "input_vectors", "output_vectors", "relations", "particular_solution", "nullspace_basis", "translation", "constraints", "intersection", "row_operation", "claim_refs", "stage_id", "data", "dimension"}
        extended_names = {"geometry.subspace_region", "geometry.subspace3d", "geometry.mapping_bundle", "geometry.affine_solution", "geometry.constraint", "geometry.matrix_tableau", "geometry.elimination_tableau", "geometry.basis_grid", "geometry.coordinate_readout", "geometry.least_squares", "geometry.spectrum", "geometry.projection3d", "geometry.orthogonalization", "geometry.quadratic_level_set"}
        if name in extended_names and any(key not in known_keys for key in operation):
            raise CommandError(f"操作包含未知字段: {next(key for key in operation if key not in known_keys)!r}")
        if name == "teach.vector_addition":
            return _expand_vector_addition(operation)
        if name == "linear_algebra.determinant_area":
            return _expand_determinant_area(operation)
        if name == "linear_algebra.matrix_transform":
            return _expand_matrix_transform(operation)
        if name == "calculus.derivative":
            return _expand_derivative(operation)
        if name == "calculus.tangent":
            return _expand_tangent(operation)
        if name == "calculus.integral_area":
            return _expand_integral_area(operation)
        if name == "scene.set_mode":
            if operation.get("mode", "2d") not in _SCENE_VALUES:
                raise CommandError("mode 必须是 2d 或 3d。")
        elif name == "curve.create":
            _require_text(operation, "alias")
            _require_choice(operation, "kind", _CURVE_KINDS)
            _validate_expression_text(_require_text(operation, "expression"))
        elif name == "curve.update":
            _require_text(operation, "alias")
            _require_choice(operation, "kind", _CURVE_KINDS)
            _validate_expression_text(_require_text(operation, "expression"))
        elif name == "linear.upsert":
            _require_text(operation, "alias")
            _require_choice(operation, "kind", _KIND_VALUES)
            _require_text(operation, "start")
            _require_text(operation, "end")
            _require_choice_value(operation, "style", _STYLE_VALUES, default="solid")
            _require_choice_value(operation, "role", _ROLE_VALUES, default="primary")
        elif name == "linear3d.upsert":
            _require_text(operation, "alias")
            _require_choice(operation, "kind", frozenset({"segment", "vector"}))
            start = _require_coordinates(operation.get("start"), dimensions=3)
            end = _require_coordinates(operation.get("end"), dimensions=3)
            if math.sqrt(sum((finish - begin) ** 2 for begin, finish in zip(start, end))) <= 1e-12:
                raise CommandError("linear3d 的起点和终点不能重合。")
            _require_choice_value(operation, "style", _STYLE_VALUES, default="solid")
            _require_choice_value(operation, "role", _ROLE_VALUES, default="primary")
        elif name == "point3d.upsert":
            _require_text(operation, "alias")
            _require_coordinates(operation.get("coordinates"), dimensions=3)
        elif name == "point3d.delete":
            _require_text(operation, "alias")
        elif name == "point.upsert":
            _require_text(operation, "alias")
            _require_point(operation.get("coordinates"))
        elif name == "annotation.upsert":
            _require_text(operation, "alias")
            _require_text(operation, "text")
            _require_point(operation.get("position"), field_name="position")
        elif name == "annotation.formula":
            _require_text(operation, "alias")
            _require_text(operation, "text")
            position = operation.get("position")
            if isinstance(position, (list, tuple)) and len(position) == 3:
                _require_coordinates(position, dimensions=3)
            else:
                _require_point(position, field_name="position")
        elif name in {"surface.create", "surface.update"}:
            _require_text(operation, "alias")
            _require_choice(operation, "kind", _CURVE_KINDS)
            _validate_expression_text(_require_text(operation, "expression"))
        elif name in {"calculus.derivative", "calculus.tangent"}:
            _validate_expression_text(_require_text(operation, "expression"))
            if name == "calculus.tangent":
                _require_finite_number(operation.get("x", 0.0), "x")
            _require_text(operation, "curve_alias")
        elif name == "calculus.integral_area":
            _validate_expression_text(_require_text(operation, "expression"))
            interval = operation.get("interval")
            if not isinstance(interval, (list, tuple)) or len(interval) != 2:
                raise CommandError("integral_area.interval 必须是 [start, end]。")
            _require_finite_number(interval[0], "interval[0]")
            _require_finite_number(interval[1], "interval[1]")
            _require_text(operation, "curve_alias")
        elif name == "area.fill":
            _validate_expression_text(_require_text(operation, "expression"))
            interval = operation.get("interval")
            if not isinstance(interval, (list, tuple)) or len(interval) != 2:
                raise CommandError("area.fill.interval 必须是 [start, end]。")
            _require_finite_number(interval[0], "interval[0]")
            _require_finite_number(interval[1], "interval[1]")
            _require_text(operation, "alias")
        elif name == "geometry.polygon":
            _require_text(operation, "alias")
            vertices = operation.get("vertices")
            if not isinstance(vertices, (list, tuple)) or len(vertices) < 3:
                raise CommandError("geometry.polygon.vertices 至少需要三个顶点。")
            points = tuple(_point(vertex, "geometry.polygon.vertices") for vertex in vertices)
            twice_area = sum(
                points[index][0] * points[(index + 1) % len(points)][1]
                - points[(index + 1) % len(points)][0] * points[index][1]
                for index in range(len(points))
            )
            if abs(twice_area) <= 1e-12:
                raise CommandError("geometry.polygon.vertices 不能退化为共线点。")
            _validate_opacity(operation.get("opacity", 0.24))
        elif name in {"geometry.angle_arc", "geometry.right_angle_marker"}:
            _require_text(operation, "alias")
            _point(operation.get("vertex"), "vertex")
            _point(operation.get("first"), "first")
            _point(operation.get("second"), "second")
            size_key = "radius" if name == "geometry.angle_arc" else "size"
            size = _require_finite_number(operation.get(size_key), size_key)
            if size <= 0:
                raise CommandError(f"{size_key} 必须为正数。")
        elif name == "geometry.projection":
            _require_coordinates(operation.get("vector"), dimensions=2)
            direction = _require_coordinates(operation.get("direction"), dimensions=2)
            if operation.get("origin") is not None:
                _require_coordinates(operation.get("origin"), dimensions=2)
            if math.hypot(*direction) <= 1e-12:
                raise CommandError("geometry.projection.direction 不能是零向量。")
            for key in ("result_alias", "foot_alias", "residual_alias"):
                _require_text(operation, key)
        elif name == "geometry.transformed_grid":
            _validate_matrix_2(operation.get("matrix"), field_name="matrix")
            _validate_bounds(operation.get("bounds"))
            if "origin" in operation:
                _require_coordinates(operation["origin"], dimensions=2)
            step = _require_finite_number(operation.get("step", 1.0), "step")
            if step <= 0:
                raise CommandError("step 必须为正数。")
        elif name == "geometry.subspace_region":
            basis = operation.get("basis")
            if not isinstance(basis, (list, tuple)) or not basis or len(basis) > 2:
                raise CommandError("basis 必须包含 1 到 2 个二维向量。")
            for vector in basis:
                _require_coordinates(vector, dimensions=2)
            if operation.get("origin") is not None:
                _require_coordinates(operation.get("origin"), dimensions=2)
            _validate_bounds(operation.get("bounds"))
            _validate_opacity(operation.get("opacity", 0.2))
        elif name == "geometry.staged_transform":
            matrices = operation.get("matrices")
            points = operation.get("points")
            aliases = operation.get("aliases")
            if not isinstance(matrices, (list, tuple)) or not matrices:
                raise CommandError("matrices 必须是非空矩阵序列。")
            if not isinstance(points, (list, tuple)) or not points:
                raise CommandError("points 必须是非空二维点序列。")
            if not isinstance(aliases, (list, tuple)) or len(aliases) != len(points):
                raise CommandError("aliases 必须与 points 长度一致。")
            for matrix in matrices:
                _validate_matrix_2(matrix, field_name="matrices")
            for point in points:
                _require_coordinates(point, dimensions=2)
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    raise CommandError("aliases 必须包含非空字符串。")
        elif name == "geometry.oriented_area":
            vectors = operation.get("vectors")
            if not isinstance(vectors, (list, tuple)) or len(vectors) != 2:
                raise CommandError("vectors 必须包含两个二维向量。")
            for vector in vectors:
                _require_coordinates(vector, dimensions=2)
            if operation.get("origin") is not None:
                _require_coordinates(operation.get("origin"), dimensions=2)
        elif name == "plane3d.upsert":
            _require_text(operation, "alias")
            _require_coordinates(operation.get("origin"), dimensions=3)
            normal = _require_coordinates(operation.get("normal"), dimensions=3)
            if math.sqrt(sum(value * value for value in normal)) <= 1e-12:
                raise CommandError("plane3d.normal 不能是零向量。")
            size = _require_finite_number(operation.get("size", 2.0), "size")
            if size <= 0:
                raise CommandError("plane3d.size 必须为正数。")
            _validate_opacity(operation.get("opacity", 0.24))
        elif name in {"geometry.parallelogram3d", "geometry.parallelepiped", "geometry.oriented_volume"}:
            _require_text(operation, "alias")
            _require_coordinates(operation.get("origin"), dimensions=3)
            vectors = operation.get("vectors")
            required = 2 if name == "geometry.parallelogram3d" else 3
            if not isinstance(vectors, (list, tuple)) or len(vectors) != required:
                raise CommandError(f"{name}.vectors 必须包含 {required} 个三维向量。")
            for vector in vectors:
                _require_coordinates(vector, dimensions=3)
            if name != "geometry.oriented_volume":
                _validate_opacity(operation.get("opacity", 0.24))
        elif name == "linear_algebra.matrix_transform":
            if "alias" in operation:
                _require_text(operation, "alias")
            matrix = operation.get("matrix")
            if not isinstance(matrix, (list, tuple)) or len(matrix) != 2 or any(
                not isinstance(row, (list, tuple)) or len(row) != 2 for row in matrix
            ):
                raise CommandError("matrix_transform.matrix 必须是 2x2 矩阵。")
            for row in matrix:
                for value in row:
                    _require_finite_number(value, "matrix")
        elif name == "linear_algebra.determinant_area":
            _point(operation.get("a"), "a")
            _point(operation.get("b"), "b")
        elif name == "geometry.intersection":
            _require_text(operation, "first")
            _require_text(operation, "second")
        elif name == "geometry.constraint":
            matrix = operation.get("matrix"); rhs = operation.get("rhs")
            if not isinstance(matrix, (list, tuple)) or len(matrix) not in (2, 3) or not isinstance(rhs, (list, tuple)) or len(rhs) != len(matrix):
                raise CommandError("constraint matrix/rhs dimension mismatch")
            for row in matrix:
                if not isinstance(row, (list, tuple)) or len(row) != len(matrix): raise CommandError("constraint matrix must be square")
                _require_coordinates(row, dimensions=len(matrix))
                _require_coordinates(rhs, dimensions=len(matrix))
            tolerance = operation.get("tolerance", 1e-9)
            _require_finite_number(tolerance, "tolerance")
            if float(tolerance) <= 0: raise CommandError("constraint tolerance must be positive")
            state = operation.get("solution_state")
            if state not in {"unique", "none", "infinite"}: raise CommandError("constraint solution_state is invalid")
            rank = operation.get("rank"); augmented_rank = operation.get("augmented_rank")
            if isinstance(rank, bool) or not isinstance(rank, int) or isinstance(augmented_rank, bool) or not isinstance(augmented_rank, int) or rank < 0 or augmented_rank < rank or augmented_rank > len(matrix):
                raise CommandError("constraint rank evidence is invalid")
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 * len(matrix) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, len(bounds), 2)):
                raise CommandError("constraint bounds are invalid")
            entity_count = operation.get("entity_count", 1)
            stage_count = operation.get("stage_count", 1)
            sample_count = operation.get("sample_count", len(matrix))
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (entity_count, stage_count, sample_count)):
                raise CommandError("constraint budget counts must be non-negative integers")
            budget_errors = _validate_budget("lecture-v1", scene=str(operation.get("scene", "3d" if len(matrix) == 3 else "2d")), entity_count=entity_count, stage_count=stage_count, sample_count=sample_count, bounds=tuple(float(value) for value in bounds))
            if budget_errors:
                raise CommandError("constraint render_budget: " + "; ".join(budget_errors))
        elif name in {"geometry.matrix_tableau", "geometry.elimination_tableau"}:
            matrix = operation.get("matrix")
            rhs = operation.get("rhs")
            if not isinstance(matrix, (list, tuple)) or len(matrix) not in (2, 3) or not isinstance(rhs, (list, tuple)) or len(rhs) != len(matrix):
                raise CommandError("tableau matrix/rhs dimension mismatch")
            width = len(matrix[0]) if matrix and isinstance(matrix[0], (list, tuple)) else 0
            if width not in (2, 3) or any(not isinstance(row, (list, tuple)) or len(row) != width for row in matrix):
                raise CommandError("tableau matrix must be a bounded rectangular matrix")
            for row in matrix:
                for value in row:
                    _require_finite_number(value, "tableau matrix")
            for value in rhs:
                _require_finite_number(value, "tableau rhs")
            state = operation.get("solution_state", "unknown")
            if state not in {"unique", "none", "infinite", "unknown"}:
                raise CommandError("tableau solution_state is invalid")
            rank = operation.get("rank", 0)
            augmented_rank = operation.get("augmented_rank", rank)
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (rank, augmented_rank)) or augmented_rank < rank:
                raise CommandError("tableau rank invariants are invalid")
            stages = operation.get("stages")
            if not isinstance(stages, (list, tuple)) or not stages:
                raise CommandError("tableau stages must be non-empty")
            aliases = []
            prefix = None
            for stage in stages:
                if not isinstance(stage, dict):
                    raise CommandError("tableau stage must be an object")
                _require_text(stage, "alias")
                alias = str(stage["alias"])
                aliases.append(alias)
                if "__stage_" not in alias or not alias.rsplit("__stage_", 1)[1].isdigit():
                    raise CommandError("tableau stage alias is invalid")
                current_prefix = alias.rsplit("__stage_", 1)[0]
                if not current_prefix or (prefix is not None and current_prefix != prefix):
                    raise CommandError("tableau stage aliases must share a prefix")
                prefix = current_prefix
                stage_matrix = stage.get("matrix")
                stage_rhs = stage.get("rhs")
                if not isinstance(stage_matrix, (list, tuple)) or len(stage_matrix) != len(matrix) or any(not isinstance(row, (list, tuple)) or len(row) != width for row in stage_matrix):
                    raise CommandError("tableau stage matrix dimension mismatch")
                if not isinstance(stage_rhs, (list, tuple)) or len(stage_rhs) != len(matrix):
                    raise CommandError("tableau stage rhs dimension mismatch")
                for row in stage_matrix:
                    for value in row:
                        _require_finite_number(value, "tableau stage matrix")
                for value in stage_rhs:
                    _require_finite_number(value, "tableau stage rhs")
                expected_rank = _matrix_rank_for_command(stage_matrix)
                expected_augmented_rank = _matrix_rank_for_command([list(row) + [value] for row, value in zip(stage_matrix, stage_rhs)])
                if stage.get("rank", expected_rank) != expected_rank or stage.get("augmented_rank", expected_augmented_rank) != expected_augmented_rank:
                    raise CommandError("tableau stage rank invariants are inconsistent")
                expected_state = "none" if expected_augmented_rank > expected_rank else ("unique" if expected_rank == width else "infinite")
                if stage.get("solution_state", expected_state) != expected_state or state not in {"unknown", expected_state}:
                    raise CommandError("tableau stage solution_state is inconsistent")
                highlights = stage.get("highlight_rows", ())
                if not isinstance(highlights, (list, tuple)) or any(isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < len(matrix) for row in highlights):
                    raise CommandError("tableau highlight_rows are invalid")
            if len(set(aliases)) != len(aliases):
                raise CommandError("tableau stage aliases must be unique")
        elif name in {"geometry.basis_grid", "geometry.coordinate_readout"}:
            basis = operation.get("basis_matrix")
            vector = operation.get("standard_vector")
            alternate = operation.get("alternate_coordinates")
            if not isinstance(basis, (list, tuple)) or len(basis) not in (2, 3) or any(not isinstance(row, (list, tuple)) or len(row) != len(basis) for row in basis):
                raise CommandError("coordinate basis_matrix must be square 2x2 or 3x3")
            if not isinstance(vector, (list, tuple)) or len(vector) != len(basis) or not isinstance(alternate, (list, tuple)) or len(alternate) != len(basis):
                raise CommandError("coordinate vectors dimension mismatch")
            for row in basis:
                for value in row:
                    _require_finite_number(value, "basis_matrix")
            for values in (vector, alternate):
                for value in values:
                    _require_finite_number(value, "coordinate vector")
            tolerance = operation.get("tolerance", 1e-9)
            _require_finite_number(tolerance, "coordinate tolerance")
            products = [sum(float(row[col]) * float(alternate[col]) for col in range(len(basis))) for row in basis]
            if any(abs(products[index] - float(vector[index])) > max(float(tolerance) * 10, 1e-8) for index in range(len(vector))):
                raise CommandError("coordinate alternate_coordinates do not reconstruct standard_vector")
            determinant = _matrix_determinant(basis)
            if name == "geometry.coordinate_readout" and abs(determinant) <= float(tolerance):
                raise CommandError("coordinate basis_matrix is singular")
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) not in (4, 6) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, len(bounds), 2)):
                raise CommandError("coordinate bounds are invalid")
            budget_errors = _validate_budget("lecture-v1", scene="3d" if len(basis) == 3 else "2d", entity_count=operation.get("entity_count", len(basis) + 2), stage_count=1, sample_count=operation.get("sample_count", len(basis) ** 2), bounds=tuple(float(value) for value in bounds))
            if budget_errors:
                raise CommandError("coordinate render_budget: " + "; ".join(budget_errors))
            _require_text(operation, "basis_alias")
            _require_text(operation, "standard_alias")
            _require_text(operation, "alternate_alias")
        elif name == "geometry.least_squares":
            matrix = operation.get("matrix")
            values = operation.get("values")
            if not isinstance(matrix, (list, tuple)) or not matrix or len(matrix) > 128 or not isinstance(values, (list, tuple)) or len(values) != len(matrix):
                raise CommandError("least_squares matrix/values dimensions are invalid")
            width = len(matrix[0]) if isinstance(matrix[0], (list, tuple)) else 0
            if width < 1 or width > 3 or any(not isinstance(row, (list, tuple)) or len(row) != width for row in matrix):
                raise CommandError("least_squares matrix is invalid")
            for row in matrix:
                for value in row:
                    _require_finite_number(value, "least_squares matrix")
            for value in values:
                _require_finite_number(value, "least_squares values")
            tolerance = operation.get("tolerance", 1e-9)
            _require_finite_number(tolerance, "least_squares tolerance")
            fit = operation.get("fit")
            projection = operation.get("projection")
            residual = operation.get("residual")
            coefficients = operation.get("coefficients")
            if not all(isinstance(item, (list, tuple)) for item in (fit, projection, residual, coefficients)) or len(fit) != len(values) or len(projection) != len(values) or len(residual) != len(values) or len(coefficients) != width:
                raise CommandError("least_squares evidence dimensions are invalid")
            for evidence_values in (fit, projection, residual, coefficients):
                for value in evidence_values:
                    _require_finite_number(value, "least_squares evidence")
            for index in range(len(values)):
                if abs(float(fit[index]) + float(residual[index]) - float(values[index])) > max(float(tolerance) * 10, 1e-8) or abs(float(projection[index]) - float(fit[index])) > max(float(tolerance) * 10, 1e-8):
                    raise CommandError("least_squares fit/projection/residual evidence is inconsistent")
            for column in range(width):
                if abs(sum(float(matrix[row][column]) * float(residual[row]) for row in range(len(matrix)))) > max(float(tolerance) * 10, 1e-8):
                    raise CommandError("least_squares residual is not orthogonal to design columns")
            for field in ("data_alias", "fit_alias", "projection_alias", "residual_alias"):
                _require_text(operation, field)
            bounds = operation.get("bounds", (-2, 2, -2, 2))
            budget_errors = _validate_budget("lecture-v1", scene="2d", entity_count=operation.get("entity_count", width + 4), stage_count=1, sample_count=operation.get("sample_count", len(matrix)), bounds=tuple(float(value) for value in bounds)) if isinstance(bounds, (list, tuple)) else ("bounds: invalid",)
            if budget_errors:
                raise CommandError("least_squares render_budget: " + "; ".join(budget_errors))
        elif name == "geometry.spectrum":
            matrix = operation.get("matrix")
            if not isinstance(matrix, (list, tuple)) or len(matrix) not in (2, 3) or any(not isinstance(row, (list, tuple)) or len(row) != len(matrix) for row in matrix):
                raise CommandError("spectrum matrix must be square 2D/3D")
            for row in matrix:
                for value in row: _require_finite_number(value, "spectrum matrix")
            roots = operation.get("roots", ())
            eigenspaces = operation.get("eigenspaces", {})
            if not isinstance(roots, (list, tuple)) or not isinstance(eigenspaces, dict): raise CommandError("spectrum evidence is invalid")
            for root in roots: _require_finite_number(root, "spectrum root")
            for value in eigenspaces.values():
                if not isinstance(value, (list, tuple)): raise CommandError("spectrum eigenspace is invalid")
            _require_text(operation, "roots_alias")
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 * len(matrix) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, len(bounds), 2)) or any(abs(float(value)) > 100.0 for value in bounds):
                raise CommandError("spectrum bounds are invalid")
            tolerance = operation.get("tolerance", 1e-9)
            if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or float(tolerance) <= 0:
                raise CommandError("spectrum tolerance is invalid")
            budget_errors = _validate_budget("lecture-v1", scene="3d" if len(matrix) == 3 else "2d", entity_count=operation.get("entity_count", len(matrix) + 2), stage_count=operation.get("stage_count", 1), sample_count=operation.get("sample_count", len(matrix) ** 2), bounds=tuple(float(value) for value in bounds))
            if budget_errors: raise CommandError("spectrum render_budget: " + "; ".join(budget_errors))
        elif name == "geometry.projection3d":
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 6 or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, 6, 2)):
                raise CommandError("projection3d bounds are invalid")
            for field in ("vector", "foot", "residual"):
                _require_coordinates(operation.get(field), dimensions=3)
            if not isinstance(operation.get("tolerance", 1e-9), (int, float)) or float(operation.get("tolerance", 1e-9)) <= 0 or not math.isfinite(float(operation.get("tolerance", 1e-9))):
                raise CommandError("projection3d tolerance is invalid")
            _require_text(operation, "alias")
            budget_errors = _validate_budget("lecture-v1", scene="3d", entity_count=operation.get("entity_count", 4), stage_count=operation.get("stage_count", 1), sample_count=operation.get("sample_count", 1), bounds=tuple(float(value) for value in bounds))
            if budget_errors: raise CommandError("projection3d render_budget: " + "; ".join(budget_errors))
        elif name == "geometry.orthogonalization":
            vectors = operation.get("vectors"); stages = operation.get("stages")
            if not isinstance(vectors, (list, tuple)) or not vectors or len(vectors) > 3 or not isinstance(stages, (list, tuple)) or len(stages) != len(vectors):
                raise CommandError("orthogonalization vectors/stages are invalid")
            for vector in vectors: _require_coordinates(vector, dimensions=len(vector))
            for stage in stages:
                if not isinstance(stage, dict): raise CommandError("orthogonalization stage is invalid")
                for field in ("input", "projection", "residual", "normalized"): _require_coordinates(stage.get(field), dimensions=len(stage[field]))
            aliases = operation.get("aliases")
            if not isinstance(aliases, (list, tuple)) or len(set(aliases)) != 4: raise CommandError("orthogonalization aliases are invalid")
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 * len(vectors[0]) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, len(bounds), 2)) or any(abs(float(value)) > 100.0 for value in bounds):
                raise CommandError("orthogonalization bounds are invalid")
            tolerance = operation.get("tolerance", 1e-9)
            if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or float(tolerance) <= 0:
                raise CommandError("orthogonalization tolerance is invalid")
            budget_errors = _validate_budget("lecture-v1", scene="3d" if len(vectors[0]) == 3 else "2d", entity_count=operation.get("entity_count", len(vectors) * 4), stage_count=operation.get("stage_count", len(vectors)), sample_count=operation.get("sample_count", len(vectors)), bounds=tuple(float(value) for value in bounds))
            if budget_errors: raise CommandError("orthogonalization render_budget: " + "; ".join(budget_errors))
        elif name == "geometry.quadratic_level_set":
            matrix = operation.get("matrix")
            if not isinstance(matrix, (list, tuple)) or len(matrix) not in (2, 3) or any(not isinstance(row, (list, tuple)) or len(row) != len(matrix) for row in matrix):
                raise CommandError("quadratic matrix must be square 2D/3D")
            for row in matrix:
                for value in row: _require_finite_number(value, "quadratic matrix")
            if any(abs(float(matrix[i][j]) - float(matrix[j][i])) > float(operation.get("tolerance", 1e-9)) for i in range(len(matrix)) for j in range(len(matrix))):
                raise CommandError("quadratic matrix must be symmetric")
            bounds = operation.get("bounds")
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 * len(matrix) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds) or any(float(bounds[index]) >= float(bounds[index + 1]) for index in range(0, len(bounds), 2)):
                raise CommandError("quadratic bounds are invalid")
            tolerance = operation.get("tolerance", 1e-9)
            if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(float(tolerance)) or float(tolerance) <= 0:
                raise CommandError("quadratic tolerance is invalid")
            budget_errors = _validate_budget("lecture-v1", scene="3d" if len(matrix) == 3 else "2d", entity_count=operation.get("entity_count", 3), stage_count=operation.get("stage_count", 3), sample_count=operation.get("sample_count", 128 * 128 if len(matrix) == 2 else 64 * 64 * 64), bounds=tuple(float(value) for value in bounds))
            if budget_errors: raise CommandError("quadratic render_budget: " + "; ".join(budget_errors))
            aliases = operation.get("aliases")
            if not isinstance(aliases, (list, tuple)) or len(aliases) != 3 or any(not isinstance(alias, str) or not alias for alias in aliases) or len(set(aliases)) != 3:
                raise CommandError("quadratic aliases are invalid")
            if len(matrix) == 2:
                vertices = operation.get("contour_vertices"); segments = operation.get("contour_segments")
                if not isinstance(vertices, (list, tuple)) or not isinstance(segments, (list, tuple)):
                    raise CommandError("quadratic contour geometry is required")
                for point in vertices: _require_coordinates(point, dimensions=2)
            else:
                vertices = operation.get("mesh_vertices"); faces = operation.get("mesh_faces")
                if not isinstance(vertices, (list, tuple)) or not isinstance(faces, (list, tuple)):
                    raise CommandError("quadratic mesh geometry is required")
                for point in vertices: _require_coordinates(point, dimensions=3)
        elif name in {"geometry.subspace3d", "geometry.affine_solution", "geometry.mapping_bundle"}:
            dimension = operation.get("dimension", 3)
            if dimension not in (2, 3):
                raise CommandError("subspace dimension 必须为 2 或 3。")
            for field in ("origin", "offset"):
                if field in operation:
                    _require_coordinates(operation[field], dimensions=int(dimension))
            basis = operation.get("basis")
            if not isinstance(basis, (list, tuple)) or not basis or len(basis) > 3:
                raise CommandError("subspace basis 必须包含 1 到 3 个向量。")
            for vector in basis:
                _require_coordinates(vector, dimensions=int(dimension))
        elif name in {"curve.delete", "point.delete", "linear.delete", "annotation.delete", "surface.delete"}:
            _require_text(operation, "alias")
        elif name == "scene.clear":
            _require_choice(operation, "scope", frozenset({"all", "curves", "surfaces", "geometry", "annotations"}))
        elif name == "view.fit":
            try:
                padding = float(operation.get("padding", 1.15))
            except (TypeError, ValueError) as error:
                raise CommandError("view.fit.padding 必须是数字。") from error
            if padding <= 0:
                raise CommandError("view.fit.padding 必须为正数。")
        elif name == "scene.export_png":
            _require_text(operation, "filename")
        return [dict(operation)]


def replay_extended_plan(plan: CommandPlan, host: SceneCommandHost) -> CommandValidation:
    """Replay a validated plan through deterministic registered adapters."""
    service = SceneCommandService()
    validation = service.validate(plan)
    if not validation.valid:
        raise CommandError("；".join(validation.messages))
    for operation in validation.expanded_operations:
        if operation.get("op") != "scene.set_mode" and not replay_registry.has(str(operation.get("op"))):
            raise CommandError(f"replay adapter missing: {operation.get('op')!r}")
    host.begin_scene_command_transaction()
    try:
        for operation in validation.expanded_operations:
            replay_registry.dispatch(host, operation)
        host.commit_scene_command_transaction()
    except Exception:
        host.rollback_scene_command_transaction()
        raise
    return validation


def _replay_apply(host: SceneCommandHost, operation: dict[str, Any]) -> None:
    host.apply_scene_command(operation)


for _operation_name in _ALLOWED_OPERATIONS:
    replay_registry.register(_operation_name, _replay_apply)


def _expand_vector_addition(operation: dict[str, Any]) -> list[dict[str, Any]]:
    origin = _point(operation.get("origin", [0, 0]), "origin")
    a = _point(operation.get("a"), "a")
    b = _point(operation.get("b"), "b")
    prefix = str(operation.get("alias_prefix", "")).strip()

    def scoped(default: str) -> str:
        return f"{prefix}__{default}" if prefix else default

    aliases = {
        "origin": str(operation.get("origin_alias", scoped("O"))),
        "a_end": str(operation.get("a_alias", scoped("A"))),
        "b_end": str(operation.get("b_alias", scoped("B"))),
        "sum_end": str(operation.get("sum_alias", scoped("C"))),
    }
    if len(set(aliases.values())) != len(aliases):
        raise CommandError("向量加法中的点别名必须互不相同。")
    c = (a[0] + b[0], a[1] + b[1])
    if not all(math.isfinite(value) for point in (origin, a, b, c) for value in point):
        raise CommandError("向量坐标必须是有限数。")
    color = str(operation.get("color", "#2777b6"))
    construction = str(operation.get("construction_color", "#6c7b8d"))
    result = str(operation.get("result_color", "#d64545"))
    ops: list[dict[str, Any]] = [
        {"op": "scene.set_mode", "mode": "2d"},
        {"op": "point.upsert", "alias": aliases["origin"], "coordinates": list(origin), "name": aliases["origin"]},
        {"op": "point.upsert", "alias": aliases["a_end"], "coordinates": [origin[0] + a[0], origin[1] + a[1]], "name": aliases["a_end"]},
        {"op": "point.upsert", "alias": aliases["b_end"], "coordinates": [origin[0] + b[0], origin[1] + b[1]], "name": aliases["b_end"]},
        {"op": "point.upsert", "alias": aliases["sum_end"], "coordinates": [origin[0] + c[0], origin[1] + c[1]], "name": aliases["sum_end"]},
        {"op": "linear.upsert", "alias": str(operation.get("a_vector_alias", scoped("a"))), "kind": "vector", "start": aliases["origin"], "end": aliases["a_end"], "color": color, "label": "a"},
        {"op": "linear.upsert", "alias": str(operation.get("b_vector_alias", scoped("b"))), "kind": "vector", "start": aliases["origin"], "end": aliases["b_end"], "color": color, "label": "b"},
        {"op": "linear.upsert", "alias": scoped("construction_a_to_c"), "kind": "segment", "start": aliases["a_end"], "end": aliases["sum_end"], "style": "dashed", "role": "construction", "color": construction},
        {"op": "linear.upsert", "alias": scoped("construction_b_to_c"), "kind": "segment", "start": aliases["b_end"], "end": aliases["sum_end"], "style": "dashed", "role": "construction", "color": construction},
        {"op": "linear.upsert", "alias": str(operation.get("sum_vector_alias", scoped("a_plus_b"))), "kind": "vector", "start": aliases["origin"], "end": aliases["sum_end"], "color": result, "role": "result", "label": f"a+b=({format_number(c[0])},{format_number(c[1])})"},
        {"op": "annotation.upsert", "alias": scoped("vector_addition_result"), "text": f"a+b=({format_number(c[0])}, {format_number(c[1])})", "position": [origin[0] + c[0] * 0.62, origin[1] + c[1] * 0.62], "color": result},
    ]
    if operation.get("show_triangle_rule", True):
        ops.extend(
            [
                {"op": "linear.upsert", "alias": scoped("triangle_translated_b"), "kind": "vector", "start": aliases["a_end"], "end": aliases["sum_end"], "color": "#2f9e5b", "role": "result", "label": "b"},
                {"op": "annotation.upsert", "alias": scoped("vector_addition_equivalent"), "text": "平行四边形法 = 三角形法", "position": [origin[0] + c[0] * 0.48, origin[1] + c[1] * 0.48 + 0.55], "color": "#2f9e5b"},
            ]
        )
    if not operation.get("show_parallelogram", True):
        ops = [item for item in ops if not item.get("alias", "").startswith(scoped("construction_"))]
    try:
        padding = float(operation.get("padding", 1.15))
    except (TypeError, ValueError) as error:
        raise CommandError("padding 必须是数字。") from error
    if not math.isfinite(padding) or padding <= 0:
        raise CommandError("padding 必须是正的有限数。")
    ops.append({"op": "view.fit", "padding": padding})
    return ops


def _expand_determinant_area(operation: dict[str, Any]) -> list[dict[str, Any]]:
    a = _point(operation.get("a"), "a")
    b = _point(operation.get("b"), "b")
    determinant = a[0] * b[1] - a[1] * b[0]
    area = abs(determinant)
    origin = [0.0, 0.0]
    c = [a[0] + b[0], a[1] + b[1]]
    return [
        {"op": "scene.set_mode", "mode": "2d"},
        {"op": "point.upsert", "alias": "O", "coordinates": origin, "name": "O"},
        {"op": "point.upsert", "alias": "A", "coordinates": list(a), "name": "A"},
        {"op": "point.upsert", "alias": "B", "coordinates": list(b), "name": "B"},
        {"op": "point.upsert", "alias": "C", "coordinates": c, "name": "C"},
        {"op": "linear.upsert", "alias": "det_a", "kind": "vector", "start": "O", "end": "A", "color": "#2777b6", "label": "a"},
        {"op": "linear.upsert", "alias": "det_b", "kind": "vector", "start": "O", "end": "B", "color": "#2f9e5b", "label": "b"},
        {"op": "linear.upsert", "alias": "det_a_to_c", "kind": "segment", "start": "A", "end": "C", "style": "dashed", "role": "construction"},
        {"op": "linear.upsert", "alias": "det_b_to_c", "kind": "segment", "start": "B", "end": "C", "style": "dashed", "role": "construction"},
        {"op": "annotation.upsert", "alias": "determinant_area", "text": f"|det(a,b)| = {format_number(area)}", "position": [c[0] * 0.5, c[1] * 0.5 + 0.45], "color": "#d64545"},
        {"op": "view.fit", "padding": 1.25},
    ]


def _curve_expression(operation: dict[str, Any]) -> str:
    expression = _require_text(operation, "expression")
    _validate_expression_text(expression)
    return expression if "=" in expression else f"y={expression}"


def _differentiate_curve_expression(expression: str) -> str:
    """用受限 SymPy 曲线解析器计算导数，再序列化为安全代数文本。"""
    try:
        import sympy as sp
        from geometry.cas_curve import parse_curve_expression

        parsed = parse_curve_expression(expression, "explicit")
        if parsed.dependent_axis != "y":
            raise ValueError("只支持 y=f(x) 的导数演示")
        derivative = sp.simplify(sp.diff(parsed.simplified, sp.Symbol("x", real=True)))
        return f"y={str(derivative).replace('**', '^')}"
    except Exception as error:
        raise CommandError(f"无法计算函数导数: {error}") from error


def _expand_derivative(operation: dict[str, Any]) -> list[dict[str, Any]]:
    expression = _curve_expression(operation)
    derivative_expression = _differentiate_curve_expression(expression)
    alias = str(operation.get("curve_alias", "f"))
    derived_alias = str(operation.get("derivative_alias", f"{alias}_prime"))
    return [
        {"op": "curve.create", "alias": alias, "kind": "explicit", "expression": expression},
        {"op": "curve.create", "alias": derived_alias, "kind": "explicit", "expression": derivative_expression, "color": "#d64545"},
        {"op": "annotation.upsert", "alias": f"{derived_alias}_label", "text": f"{alias}'(x)", "position": [1.2, 1.2], "color": "#d64545"},
    ]


def _expand_tangent(operation: dict[str, Any]) -> list[dict[str, Any]]:
    expression = _curve_expression(operation)
    source = expression.split("=", 1)[1].strip()
    x_value = _require_finite_number(operation.get("x", 0.0), "x")
    alias = str(operation.get("curve_alias", "f"))
    tangent_alias = str(operation.get("tangent_alias", "tangent"))
    tangent_value = _tangent_expression(expression, x_value)
    return [
        {"op": "curve.create", "alias": alias, "kind": "explicit", "expression": expression},
        {"op": "curve.create", "alias": tangent_alias, "kind": "explicit", "expression": tangent_value, "color": "#d64545"},
        {"op": "annotation.upsert", "alias": f"{tangent_alias}_label", "text": f"切线 x={format_number(x_value)}", "position": [x_value + 0.4, 0.4], "color": "#d64545"},
    ]


def _tangent_expression(expression: str, x_value: float) -> str:
    try:
        import sympy as sp
        from geometry.cas_curve import parse_curve_expression

        parsed = parse_curve_expression(expression, "explicit")
        if parsed.dependent_axis != "y":
            raise ValueError("只支持 y=f(x) 的切线演示")
        x = sp.Symbol("x", real=True)
        value = sp.Float(x_value)
        y_value = sp.simplify(parsed.simplified.subs(x, value))
        slope = sp.simplify(sp.diff(parsed.simplified, x).subs(x, value))
        formula = sp.expand(y_value + slope * (x - value))
        return f"y={str(formula).replace('**', '^')}"
    except Exception as error:
        raise CommandError(f"无法计算切线: {error}") from error


def _expand_integral_area(operation: dict[str, Any]) -> list[dict[str, Any]]:
    expression = _curve_expression(operation)
    interval = operation.get("interval", (-1.0, 1.0))
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        raise CommandError("integral_area.interval 必须是 [start, end]。")
    start = _require_finite_number(interval[0], "interval[0]")
    end = _require_finite_number(interval[1], "interval[1]")
    alias = str(operation.get("curve_alias", "f"))
    area_alias = str(operation.get("area_alias", "integral_area"))
    return [
        {"op": "curve.create", "alias": alias, "kind": "explicit", "expression": expression},
        {"op": "area.fill", "alias": f"{area_alias}_fill", "expression": expression, "interval": [start, end], "color": "#7c5ce3", "opacity": 0.24},
        {"op": "annotation.upsert", "alias": area_alias, "text": f"积分区间 [{format_number(start)}, {format_number(end)}]", "position": [(start + end) / 2, 0.45], "color": "#d64545"},
    ]


def _expand_matrix_transform(operation: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = operation.get("matrix")
    if not isinstance(matrix, (list, tuple)) or len(matrix) != 2:
        raise CommandError("matrix_transform.matrix 必须是 2x2 矩阵。")
    a, b = (float(value) for value in matrix[0])
    c, d = (float(value) for value in matrix[1])
    alias = str(operation.get("alias", "matrix_transform")).strip() or "matrix_transform"
    return _expand_vector_addition(
        {
            "op": "teach.vector_addition",
            "a": [a, c],
            "b": [b, d],
            "alias_prefix": alias,
            "a_alias": f"{alias}__T(e1)",
            "b_alias": f"{alias}__T(e2)",
            "sum_alias": f"{alias}__T(e1+e2)",
            "show_triangle_rule": False,
            "padding": 1.25,
        }
    ) + [
        {"op": "annotation.upsert", "alias": f"{alias}__label", "text": f"T=[[{format_number(a)}, {format_number(b)}], [{format_number(c)}, {format_number(d)}]]", "position": [0.3, -0.7]},
    ]


def _require_text(operation: dict[str, Any], key: str) -> str:
    value = operation.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CommandError(f"{key} 必须是非空字符串。")
    return value.strip()


def _require_choice(operation: dict[str, Any], key: str, choices: frozenset[str]) -> str:
    value = _require_text(operation, key)
    if value not in choices:
        raise CommandError(f"{key} 必须是 {sorted(choices)} 之一。")
    return value


def _require_choice_value(
    operation: dict[str, Any], key: str, choices: frozenset[str], *, default: str
) -> str:
    value = operation.get(key, default)
    if not isinstance(value, str) or value not in choices:
        raise CommandError(f"{key} 必须是 {sorted(choices)} 之一。")
    return value


def _validate_expression_text(expression: str) -> None:
    if "__" in expression or any(character in expression for character in ("'", '"', "\\")):
        raise CommandError("函数表达式包含不安全字符。")
    if len(expression) > 500:
        raise CommandError("函数表达式过长。")


def _require_point(value: Any, *, field_name: str = "coordinates") -> tuple[float, float]:
    return _point(value, field_name)


def _require_coordinates(value: Any, *, dimensions: int) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != dimensions:
        raise CommandError(f"coordinates 必须包含 {dimensions} 个数字。")
    try:
        coordinates = tuple(float(item) for item in value)
    except (TypeError, ValueError) as error:
        raise CommandError("coordinates 必须包含数字。") from error
    if not all(math.isfinite(item) for item in coordinates):
        raise CommandError("coordinates 必须包含有限数。")
    return coordinates


def _point(value: Any, field_name: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise CommandError(f"{field_name} 必须是 [x, y]。")
    try:
        point = (float(value[0]), float(value[1]))
    except (TypeError, ValueError) as error:
        raise CommandError(f"{field_name} 必须包含数字。") from error
    if not all(math.isfinite(item) for item in point):
        raise CommandError(f"{field_name} 必须包含有限数。")
    return point


def _validate_matrix_2(value: Any, *, field_name: str) -> tuple[tuple[float, float], tuple[float, float]]:
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(
        not isinstance(row, (list, tuple)) or len(row) != 2 for row in value
    ):
        raise CommandError(f"{field_name} 必须是 2x2 矩阵。")
    rows = []
    for row in value:
        rows.append(tuple(_require_finite_number(item, field_name) for item in row))
    return rows[0], rows[1]  # type: ignore[return-value]


def _validate_bounds(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise CommandError("bounds 必须是 [xmin, xmax, ymin, ymax]。")
    bounds = tuple(_require_finite_number(item, "bounds") for item in value)
    if bounds[0] >= bounds[1] or bounds[2] >= bounds[3]:
        raise CommandError("bounds 的最小值必须小于最大值。")
    return bounds  # type: ignore[return-value]


def _validate_opacity(value: Any) -> float:
    opacity = _require_finite_number(value, "opacity")
    if not 0 < opacity <= 1:
        raise CommandError("opacity 必须在 (0, 1] 范围内。")
    return opacity


def _require_finite_number(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise CommandError(f"{field_name} 必须是数字。") from error
    if not math.isfinite(number):
        raise CommandError(f"{field_name} 必须是有限数。")
    return number


def format_number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


class RuleBasedAgentProvider:
    """无网络演示 provider；以后可替换为真实模型而不改变命令层。"""

    _VECTOR_PATTERN = re.compile(
        r"a\s*=\s*\(?\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)?"
        r".*b\s*=\s*\(?\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)?",
        re.IGNORECASE | re.DOTALL,
    )

    def create_plan(self, messages: object, scene_context: object = None) -> object:
        legacy_call = isinstance(messages, str)
        if legacy_call:
            prompt = messages
        else:
            prompt = ""
            for message in tuple(messages or ()):
                if getattr(message, "role", None) == "user":
                    prompt = str(getattr(message, "content", ""))
        from .agent_provider import AgentResponse

        match = self._VECTOR_PATTERN.search(prompt)
        is_vector_addition = "向量加法" in prompt or "vector addition" in prompt.lower()
        if match is not None and ("向量" in prompt or "vector" in prompt.lower()):
            values = tuple(float(value) for value in match.groups())
        elif is_vector_addition:
            # Keep the no-parameter teaching request useful and deterministic.
            # These are the documented classroom defaults; explicit coordinates
            # still take precedence above.
            values = (2.0, 1.0, 1.0, 3.0)
        else:
            values = None
        if values is not None:
            plan = CommandPlan(
                summary="生成向量加法的平行四边形法与三角形法教学图",
                operations=(
                    {
                        "op": "teach.vector_addition",
                        "a": [values[0], values[1]],
                        "b": [values[2], values[3]],
                        "show_parallelogram": True,
                        "show_triangle_rule": True,
                    },
                ),
            )
            if legacy_call:
                return plan
            return AgentResponse(
                text="已生成向量加法教学计划，请确认后执行。",
                plan=plan,
                raw_content=plan.to_json(),
            )
        if legacy_call:
            raise CommandError("演示 Agent 目前只能识别包含 a=(x,y)、b=(x,y) 的二维向量加法请求。")
        return AgentResponse(
            text=_rule_based_explanation(prompt),
            plan=None,
            raw_content="",
        )


def _rule_based_explanation(prompt: str) -> str:
    text = str(prompt)
    if "行列式" in text or "面积" in text:
        return "行列式的绝对值表示由两个向量张成的平行四边形面积；符号则记录方向。"
    if "导数" in text or "切线" in text:
        return "导数描述函数在一点附近的瞬时变化率，也就是该点切线的斜率。"
    if "积分" in text:
        return "定积分可以理解为带符号面积的累积；连续小矩形的极限给出积分值。"
    return "我可以解释数学概念，也可以把点、向量、曲线或曲面整理成可审核的 CommandPlan。请给出具体对象或公式。"

