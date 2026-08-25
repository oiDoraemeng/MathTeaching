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


class SceneCommandHost(Protocol):
    """GUI 宿主需要提供的最小命令适配接口。"""

    def apply_scene_command(self, operation: dict[str, Any]) -> None: ...

    def begin_scene_command_transaction(self) -> None: ...

    def commit_scene_command_transaction(self) -> None: ...

    def rollback_scene_command_transaction(self) -> None: ...


_ALLOWED_OPERATIONS = frozenset(
    {
        "scene.set_mode",
        "scene.clear",
        "curve.create",
        "curve.update",
        "curve.delete",
        "point.upsert",
        "point3d.upsert",
        "point.delete",
        "linear.upsert",
        "linear.delete",
        "teach.vector_addition",
        "annotation.upsert",
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
        "geometry.intersection",
    }
)
_SCENE_VALUES = frozenset({"2d", "3d"})
_KIND_VALUES = frozenset({"line", "segment", "ray", "vector"})
_CURVE_KINDS = frozenset({"explicit", "implicit", "parametric"})
_STYLE_VALUES = frozenset({"solid", "dashed"})
_ROLE_VALUES = frozenset({"primary", "construction", "result"})
_THREE_D_OPERATIONS = frozenset({"point3d.upsert", "surface.create", "surface.update", "surface.delete", "geometry.intersection"})
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
        # 场景是计划级别的执行上下文；3D 计划自动显式切换到 3D，避免
        # 宿主在错误的渲染工作区中解释 surface/point3d 命令。
        if plan.scene == "3d":
            expanded.append({"op": "scene.set_mode", "mode": "3d"})
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
        return CommandValidation(not messages, tuple(messages), tuple(expanded))

    def preview(self, plan: CommandPlan) -> CommandValidation:
        return self.validate(plan)

    def execute(self, plan: CommandPlan) -> CommandValidation:
        validation = self.validate(plan)
        if not validation.valid:
            raise CommandError("；".join(validation.messages))
        if self.host is None:
            raise CommandError("命令服务尚未绑定场景宿主。")
        self.host.begin_scene_command_transaction()
        try:
            for operation in validation.expanded_operations:
                self.host.apply_scene_command(operation)
            self.host.commit_scene_command_transaction()
        except Exception:
            self.host.rollback_scene_command_transaction()
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
        elif name == "point3d.upsert":
            _require_text(operation, "alias")
            _require_coordinates(operation.get("coordinates"), dimensions=3)
        elif name == "point.upsert":
            _require_text(operation, "alias")
            _require_point(operation.get("coordinates"))
        elif name == "annotation.upsert":
            _require_text(operation, "alias")
            _require_text(operation, "text")
            _require_point(operation.get("position"), field_name="position")
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
        elif name == "linear_algebra.matrix_transform":
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
        elif name in {"curve.delete", "point.delete", "linear.delete", "annotation.delete", "surface.delete"}:
            _require_text(operation, "alias")
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


def _expand_vector_addition(operation: dict[str, Any]) -> list[dict[str, Any]]:
    origin = _point(operation.get("origin", [0, 0]), "origin")
    a = _point(operation.get("a"), "a")
    b = _point(operation.get("b"), "b")
    aliases = {
        "origin": str(operation.get("origin_alias", "O")),
        "a_end": str(operation.get("a_alias", "A")),
        "b_end": str(operation.get("b_alias", "B")),
        "sum_end": str(operation.get("sum_alias", "C")),
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
        {"op": "linear.upsert", "alias": str(operation.get("a_vector_alias", "a")), "kind": "vector", "start": aliases["origin"], "end": aliases["a_end"], "color": color, "label": "a"},
        {"op": "linear.upsert", "alias": str(operation.get("b_vector_alias", "b")), "kind": "vector", "start": aliases["origin"], "end": aliases["b_end"], "color": color, "label": "b"},
        {"op": "linear.upsert", "alias": "construction_a_to_c", "kind": "segment", "start": aliases["a_end"], "end": aliases["sum_end"], "style": "dashed", "role": "construction", "color": construction},
        {"op": "linear.upsert", "alias": "construction_b_to_c", "kind": "segment", "start": aliases["b_end"], "end": aliases["sum_end"], "style": "dashed", "role": "construction", "color": construction},
        {"op": "linear.upsert", "alias": str(operation.get("sum_vector_alias", "a_plus_b")), "kind": "vector", "start": aliases["origin"], "end": aliases["sum_end"], "color": result, "role": "result", "label": f"a+b=({format_number(c[0])},{format_number(c[1])})"},
        {"op": "annotation.upsert", "alias": "vector_addition_result", "text": f"a+b=({format_number(c[0])}, {format_number(c[1])})", "position": [origin[0] + c[0] * 0.62, origin[1] + c[1] * 0.62], "color": result},
    ]
    if operation.get("show_triangle_rule", True):
        ops.extend(
            [
                {"op": "linear.upsert", "alias": "triangle_translated_b", "kind": "vector", "start": aliases["a_end"], "end": aliases["sum_end"], "color": "#2f9e5b", "role": "result", "label": "b"},
                {"op": "annotation.upsert", "alias": "vector_addition_equivalent", "text": "平行四边形法 = 三角形法", "position": [origin[0] + c[0] * 0.48, origin[1] + c[1] * 0.48 + 0.55], "color": "#2f9e5b"},
            ]
        )
    if not operation.get("show_parallelogram", True):
        ops = [item for item in ops if not item.get("alias", "").startswith("construction_")]
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
    return _expand_vector_addition(
        {
            "op": "teach.vector_addition",
            "a": [a, c],
            "b": [b, d],
            "a_alias": "T(e1)",
            "b_alias": "T(e2)",
            "sum_alias": "T(e1+e2)",
            "show_triangle_rule": False,
            "padding": 1.25,
        }
    ) + [
        {"op": "annotation.upsert", "alias": "matrix_transform_label", "text": f"T=[[{format_number(a)}, {format_number(b)}], [{format_number(c)}, {format_number(d)}]]", "position": [0.3, -0.7]},
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
        if match is not None and ("向量" in prompt or "vector" in prompt.lower()):
            values = tuple(float(value) for value in match.groups())
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
