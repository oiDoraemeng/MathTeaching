"""Compatibility facade for the legacy math-tool names.

New integrations should use :mod:`agent.capabilities` directly. This module
keeps the names used by the first Provider/MCP integration, while ensuring that
their supported behaviours pass through the same validated capability layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agent.capabilities import CapabilityResult, ToolCall, build_default_registry
from agent.capabilities.scene_index import SceneIndex
from services.scene_commands import CommandPlan, CommandValidation, SceneCommandService


@dataclass(frozen=True)
class ToolResult:
    data: dict[str, Any] | None = None
    plan: CommandPlan | None = None
    validation: CommandValidation | None = None
    canonical_name: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., ToolResult]
    mutating: bool = False


class ToolRegistry:
    """Present old tool names as adapters over the canonical capability API."""

    def __init__(self, command_service: SceneCommandService | None = None) -> None:
        self.command_service = command_service or SceneCommandService()
        self.capabilities = build_default_registry()
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

    def _validated(self, plan: CommandPlan, *, canonical_name: str | None = None) -> ToolResult:
        validation = self.command_service.preview(plan)
        if not validation.valid:
            raise ValueError("；".join(validation.messages))
        return ToolResult(data={"summary": plan.summary}, plan=plan, validation=validation, canonical_name=canonical_name)

    def _capability(self, name: str, arguments: dict[str, Any], *, context: Any = None) -> ToolResult:
        result = self.capabilities.dispatch(ToolCall(f"legacy-{name}", name, arguments), context or SceneIndex("2d", {}))
        return self._from_capability(result)

    def _from_capability(self, result: CapabilityResult) -> ToolResult:
        if result.status == "error":
            error = result.errors[0]
            field = f"{error.field}: " if error.field else ""
            raise ValueError(f"{field}{error.message}")
        if result.plan is not None:
            return self._validated(CommandPlan.from_dict(result.plan), canonical_name=result.name)
        if result.data is not None:
            data = result.data if isinstance(result.data, dict) else {"result": result.data}
            return ToolResult(data=data, canonical_name=result.name)
        return ToolResult(data={"explanation": result.explanation}, canonical_name=result.name)

    @staticmethod
    def _curve_expression(expression: str) -> str:
        value = str(expression).strip()
        return value if "=" in value else f"y={value}"

    def _inspect_scene(self, **context: Any) -> ToolResult:
        return self._capability("scene.inspect", {}, context=context.get("scene_index"))

    def _calculate_expression(self, expression: str, **_: Any) -> ToolResult:
        return self._capability("math.calculate", {"expression": str(expression)})

    def _create_curve(self, expression: str, alias: str = "f", kind: str = "explicit", **_: Any) -> ToolResult:
        return self._capability(
            "scene.edit",
            {"action": "upsert", "object_type": "curve", "alias": alias, "kind": kind, "expression": self._curve_expression(expression)},
        )

    def _create_tangent(self, expression: str, curve_alias: str, x: float, **_: Any) -> ToolResult:
        return self._capability(
            "math.derive",
            {"action": "tangent", "expression": self._curve_expression(expression), "curve_alias": curve_alias, "x": x, "presentation": "draw"},
        )

    def _create_integral_area(self, expression: str, curve_alias: str, interval: list[float] | tuple[float, float], **_: Any) -> ToolResult:
        return self._capability(
            "math.derive",
            {"action": "integral_area", "expression": self._curve_expression(expression), "curve_alias": curve_alias, "interval": list(interval), "presentation": "draw"},
        )

    def _create_determinant_demo(self, a: list[float] | tuple[float, float], b: list[float] | tuple[float, float], **_: Any) -> ToolResult:
        # 旧教学宏尚无对应能力，仍由共享命令校验器约束。
        plan = CommandPlan(summary="演示行列式面积", operations=({"op": "linear_algebra.determinant_area", "a": list(a), "b": list(b)},))
        return self._validated(plan, canonical_name="scene.edit")
