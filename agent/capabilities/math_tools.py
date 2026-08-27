"""Controlled mathematical capability handlers built on existing safe parsers."""

from __future__ import annotations

from typing import Any

import sympy as sp

from geometry.cas_curve import CurveExpressionError, parse_curve_expression

from .contracts import CapabilityError, CapabilityResult, ToolCall
from .scene_index import SceneIndex


def _error(call: ToolCall, code: str, message: str, field: str | None = None) -> CapabilityResult:
    return CapabilityResult.error(call.call_id, call.name, CapabilityError(code, message, field))


def _expression(expression: str):
    try:
        parsed = parse_curve_expression(f"y={expression}", "explicit")
    except CurveExpressionError as error:
        raise ValueError("unsafe_expression") from error
    value = parsed.simplified
    if getattr(value, "free_symbols", set()):
        raise ValueError("free_symbols_not_allowed")
    return value


def math_calculate(call: ToolCall, _context: Any) -> CapabilityResult:
    expression = str(call.arguments["expression"])
    try:
        value = _expression(expression)
    except ValueError as error:
        return _error(call, "unsafe_expression", "expression is not a supported scalar expression", "expression")
    return CapabilityResult.ok(call, data={"expression": expression, "result": str(sp.simplify(value)).replace("**", "^")})


def math_derive(call: ToolCall, context: Any) -> CapabilityResult:
    arguments = call.arguments
    action = str(arguments["action"])
    presentation = str(arguments.get("presentation", "draw"))
    scene_mode = context.scene_mode if isinstance(context, SceneIndex) else getattr(context, "scene_mode", "2d")
    if action == "intersection":
        if scene_mode != "3d":
            return _error(call, "unsupported_operation", "only 3D intersections are available", "action")
        first, second = arguments.get("first"), arguments.get("second")
        if not isinstance(first, str) or not isinstance(second, str):
            return _error(call, "invalid_tool_arguments", "intersection requires first and second aliases")
        return CapabilityResult.ok(call, plan={"version": 1, "scene": "3d", "summary": "计算三维交线", "operations": [{"op": "geometry.intersection", "first": first, "second": second}]})
    expression = arguments.get("expression")
    if not isinstance(expression, str):
        return _error(call, "invalid_tool_arguments", "derivation requires expression", "expression")
    try:
        parsed = parse_curve_expression(expression, "explicit")
    except CurveExpressionError:
        return _error(call, "unsafe_expression", "expression is not a supported curve", "expression")
    if parsed.dependent_axis != "y":
        return _error(call, "unsupported_operation", "only y=f(x) curve derivations are available")
    if action == "derivative" and presentation == "data":
        derivative = sp.simplify(sp.diff(parsed.simplified, sp.Symbol("x", real=True)))
        return CapabilityResult.ok(call, data={"expression": parsed.source, "derivative": f"y={str(derivative).replace('**', '^')}"})
    alias = str(arguments.get("curve_alias", "f"))
    operation: dict[str, Any]
    if action == "derivative":
        operation = {"op": "calculus.derivative", "expression": parsed.source, "curve_alias": alias}
    elif action == "tangent":
        if "x" not in arguments:
            return _error(call, "invalid_tool_arguments", "tangent requires x", "x")
        operation = {"op": "calculus.tangent", "expression": parsed.source, "curve_alias": alias, "x": arguments["x"]}
    elif action == "integral_area":
        interval = arguments.get("interval")
        if not isinstance(interval, list) or len(interval) != 2:
            return _error(call, "invalid_tool_arguments", "integral_area requires interval", "interval")
        operation = {"op": "calculus.integral_area", "expression": parsed.source, "curve_alias": alias, "interval": interval}
    else:
        return _error(call, "unsupported_operation", "unsupported derivation action", "action")
    return CapabilityResult.ok(call, plan={"version": 1, "scene": "2d", "summary": "生成微积分教学图", "operations": [operation]})


def teaching_explain(call: ToolCall, _context: Any) -> CapabilityResult:
    question = str(call.arguments["question"]).strip()
    return CapabilityResult.ok(call, explanation=f"{question}：请结合当前图形的对象、定义域与局部变化率逐步说明。")


def handlers() -> dict[str, Any]:
    return {"math.calculate": math_calculate, "math.derive": math_derive, "teaching.explain": teaching_explain}
