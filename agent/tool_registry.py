"""Typed math tool registry that only returns validated plans or read-only data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from services.scene_commands import CommandPlan, CommandValidation, SceneCommandService


@dataclass(frozen=True)
class ToolResult:
    data: dict[str, Any] = None  # type: ignore[assignment]
    plan: CommandPlan | None = None
    validation: CommandValidation | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., ToolResult]
    mutating: bool = False


class ToolRegistry:
    def __init__(self, command_service: SceneCommandService | None = None) -> None:
        self.command_service = command_service or SceneCommandService()
        self._tools: dict[str, ToolSpec] = {}
        self._register("inspect_scene", "Inspect the current math scene", {"type": "object"}, self._inspect_scene)
        self._register("calculate_expression", "Calculate a safe mathematical expression", {"type": "object", "required": ["expression"]}, self._calculate_expression)
        self._register("create_curve", "Create a function curve", {"type": "object", "required": ["expression"]}, self._create_curve, mutating=True)
        self._register("create_tangent", "Create a tangent line", {"type": "object", "required": ["expression", "curve_alias", "x"]}, self._create_tangent, mutating=True)
        self._register("create_integral_area", "Create an integral area demonstration", {"type": "object", "required": ["expression", "curve_alias", "interval"]}, self._create_integral_area, mutating=True)
        self._register("create_determinant_demo", "Create a determinant area demonstration", {"type": "object", "required": ["a", "b"]}, self._create_determinant_demo, mutating=True)

    def _register(self, name: str, description: str, schema: dict[str, Any], handler: Callable[..., ToolResult], *, mutating: bool = False) -> None:
        self._tools[name] = ToolSpec(name, description, schema, handler, mutating)

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())

    def call(self, name: str, **arguments: Any) -> ToolResult:
        try:
            tool = self._tools[name]
        except KeyError as error:
            raise ValueError(f"unknown math tool: {name}") from error
        return tool.handler(**arguments)

    def _validated(self, plan: CommandPlan) -> ToolResult:
        validation = self.command_service.preview(plan)
        if not validation.valid:
            raise ValueError("；".join(validation.messages))
        return ToolResult(data={"summary": plan.summary}, plan=plan, validation=validation)

    def _inspect_scene(self, **context: Any) -> ToolResult:
        return ToolResult(data={"scene": context.get("scene", {}), "selected": context.get("selected", {})})

    def _calculate_expression(self, expression: str, **_: Any) -> ToolResult:
        expression = str(expression).strip()
        if not expression or any(token in expression for token in ("__", "import", "exec", "eval")):
            raise ValueError("expression contains unsupported code")
        from sympy import sympify

        try:
            result = sympify(expression, locals={})
        except Exception as error:
            raise ValueError(f"expression is invalid: {error}") from None
        return ToolResult(data={"expression": expression, "result": str(result)})

    def _create_curve(self, expression: str, alias: str = "f", kind: str = "explicit", **_: Any) -> ToolResult:
        if any(token in str(expression) for token in ("__", "import", "exec", "eval")):
            raise ValueError("expression contains unsupported code")
        return self._validated(CommandPlan(summary=f"创建曲线 {alias}", operations=({"op": "curve.create", "alias": alias, "kind": kind, "expression": expression},)))

    def _create_tangent(self, expression: str, curve_alias: str, x: float, **_: Any) -> ToolResult:
        return self._validated(CommandPlan(summary=f"创建 {curve_alias} 在 x={x} 的切线", operations=({"op": "calculus.tangent", "expression": expression, "curve_alias": curve_alias, "x": x},)))

    def _create_integral_area(self, expression: str, curve_alias: str, interval: list[float] | tuple[float, float], **_: Any) -> ToolResult:
        return self._validated(CommandPlan(summary=f"绘制 {curve_alias} 的积分面积", operations=({"op": "calculus.integral_area", "expression": expression, "curve_alias": curve_alias, "interval": list(interval)},)))

    def _create_determinant_demo(self, a: list[float] | tuple[float, float], b: list[float] | tuple[float, float], **_: Any) -> ToolResult:
        return self._validated(CommandPlan(summary="演示行列式面积", operations=({"op": "linear_algebra.determinant_area", "a": list(a), "b": list(b)},)))
