"""Capability registration, catalog projection, alias resolution, and dispatch."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .contracts import CapabilityError, CapabilityResult, CapabilitySpec, SceneScope, ToolCall
from .validation import validate_input_schema, validate_tool_arguments


CapabilityHandler = Callable[[ToolCall, Any], CapabilityResult]


def _number_schema() -> dict[str, Any]:
    return {"type": "number", "minimum": -1_000_000, "maximum": 1_000_000}


def _coordinates_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 2,
        "maxItems": 3,
        "items": _number_schema(),
    }


def _specifications() -> tuple[CapabilitySpec, ...]:
    closed = {"type": "object", "additionalProperties": False}
    return (
        CapabilitySpec(
            "scene.inspect",
            "scene_read",
            "Summarize the staged mathematical scene.",
            {**closed, "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}},
            "data",
            aliases=("inspect_scene",),
        ),
        CapabilitySpec(
            "scene.find",
            "scene_read",
            "Find staged objects by literal aliases, types, or expression fragments.",
            {
                **closed,
                "properties": {
                    "alias": {"type": "string", "maxLength": 64},
                    "object_types": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string", "maxLength": 24, "enum": ["point", "point3d", "vector", "line", "curve", "surface", "annotation"]},
                    },
                    "expression_contains": {"type": "string", "maxLength": 128},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
            },
            "data",
            aliases=("find_scene",),
        ),
        CapabilitySpec(
            "scene.edit",
            "scene_edit",
            "Create, update, or delete a supported scene object without raw renderer operations.",
            {
                **closed,
                "properties": {
                    "action": {"type": "string", "maxLength": 8, "enum": ["upsert", "update", "delete"]},
                    "object_type": {"type": "string", "maxLength": 16, "enum": ["point", "point3d", "vector", "line", "curve", "surface", "annotation"]},
                    "alias": {"type": "string", "maxLength": 64},
                    "coordinates": _coordinates_schema(),
                    "start": {"type": "string", "maxLength": 64},
                    "end": {"type": "string", "maxLength": 64},
                    "expression": {"type": "string", "maxLength": 500},
                    "kind": {"type": "string", "maxLength": 16},
                    "text": {"type": "string", "maxLength": 512},
                    "position": _coordinates_schema(),
                },
                "required": ["action", "object_type", "alias"],
            },
            "plan",
            mutating=True,
            aliases=("create_curve", "create_point", "create_surface"),
        ),
        CapabilitySpec(
            "scene.clear",
            "scene_edit",
            "Clear all or one supported scope from the staged scene.",
            {**closed, "properties": {"scope": {"type": "string", "maxLength": 16, "enum": ["all", "curves", "surfaces", "geometry", "annotations"]}}, "required": ["scope"]},
            "plan",
            mutating=True,
            aliases=("clear_scene",),
        ),
        CapabilitySpec(
            "math.calculate",
            "math",
            "Evaluate a bounded scalar mathematical expression using the controlled parser.",
            {**closed, "properties": {"expression": {"type": "string", "maxLength": 500}}, "required": ["expression"]},
            "data",
            aliases=("calculate_expression",),
        ),
        CapabilitySpec(
            "math.derive",
            "math",
            "Derive a curve or supported 3D relationship as data or a drawing plan.",
            {
                **closed,
                "properties": {
                    "action": {"type": "string", "maxLength": 16, "enum": ["derivative", "tangent", "integral_area", "intersection"]},
                    "expression": {"type": "string", "maxLength": 500},
                    "curve_alias": {"type": "string", "maxLength": 64},
                    "x": _number_schema(),
                    "interval": {"type": "array", "minItems": 2, "maxItems": 2, "items": _number_schema()},
                    "first": {"type": "string", "maxLength": 64},
                    "second": {"type": "string", "maxLength": 64},
                    "presentation": {"type": "string", "maxLength": 8, "enum": ["data", "draw"]},
                },
                "required": ["action"],
            },
            "data_or_plan",
            mutating=True,
            aliases=("create_tangent", "create_integral_area"),
        ),
        CapabilitySpec(
            "view.control",
            "view",
            "Set a scene mode or fit the view; arbitrary camera controls are unavailable.",
            {
                **closed,
                "properties": {
                    "action": {"type": "string", "maxLength": 8, "enum": ["set_mode", "fit"]},
                    "mode": {"type": "string", "maxLength": 2, "enum": ["2d", "3d"]},
                    "padding": {"type": "number", "minimum": 0.1, "maximum": 10},
                },
                "required": ["action"],
            },
            "plan",
            mutating=True,
            aliases=("fit_view",),
        ),
        CapabilitySpec(
            "result.export",
            "result",
            "Export the composed result as a managed PNG basename.",
            {**closed, "properties": {"filename": {"type": "string", "maxLength": 128}}, "required": ["filename"]},
            "plan",
            mutating=True,
            aliases=("export_png",),
        ),
        CapabilitySpec(
            "teaching.explain",
            "teaching",
            "Give a concise teaching explanation grounded in bounded prior results.",
            {
                **closed,
                "properties": {
                    "question": {"type": "string", "maxLength": 512},
                    "references": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 64}},
                },
                "required": ["question"],
            },
            "explanation",
            aliases=("explain_math",),
        ),
    )


class CapabilityRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, CapabilitySpec] = {}
        self._handlers: dict[str, CapabilityHandler] = {}
        self._aliases: dict[str, str] = {}

    def register(self, spec: CapabilitySpec, handler: CapabilityHandler) -> None:
        validate_input_schema(spec.input_schema)
        if spec.name in self._specs or spec.name in self._aliases:
            raise ValueError(f"duplicate capability name: {spec.name}")
        for alias in spec.aliases:
            if alias in self._specs or alias in self._aliases:
                raise ValueError(f"duplicate capability alias: {alias}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
        self._aliases.update({alias: spec.name for alias in spec.aliases})

    def resolve_name(self, name: str) -> str:
        canonical = self._aliases.get(name, name)
        if canonical not in self._specs:
            raise ValueError(f"unknown capability: {name}")
        return canonical

    def get(self, name: str) -> CapabilitySpec:
        return self._specs[self.resolve_name(name)]

    def catalog(self) -> dict[str, Any]:
        capabilities: list[dict[str, Any]] = []
        for spec in sorted(self._specs.values(), key=lambda item: item.name):
            item = spec.to_dict()
            item.pop("aliases", None)
            capabilities.append(item)
        return {"catalog_version": 1, "capabilities": capabilities}

    def dispatch(self, call: ToolCall, context: Any = None) -> CapabilityResult:
        try:
            canonical = self.resolve_name(call.name)
        except ValueError:
            return CapabilityResult.error(call.call_id, call.name, CapabilityError("unknown_capability", "unknown capability"))
        spec = self._specs[canonical]
        normalized_call = ToolCall(call.call_id, canonical, call.arguments)
        error = validate_tool_arguments(spec.input_schema, normalized_call.arguments)
        if error is not None:
            return CapabilityResult.error(normalized_call.call_id, normalized_call.name, error)
        try:
            result = self._handlers[canonical](normalized_call, context)
        except ValueError as handler_error:
            return CapabilityResult.error(
                normalized_call.call_id,
                normalized_call.name,
                CapabilityError("capability_rejected", str(handler_error)[:512]),
            )
        if result.call_id != normalized_call.call_id or result.name != canonical:
            raise ValueError("capability handler returned a mismatched result")
        return result


def build_default_registry() -> CapabilityRegistry:
    from .math_tools import handlers as math_handlers
    from .scene_tools import handlers as scene_handlers

    registry = CapabilityRegistry()
    handlers = {**scene_handlers(), **math_handlers()}
    for spec in _specifications():
        registry.register(spec, handlers[spec.name])
    return registry
