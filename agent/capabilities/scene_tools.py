"""Pure scene/view/export capability handlers; they never call a GUI host."""

from __future__ import annotations

import re
from typing import Any

from geometry.cas_curve import CurveExpressionError, parse_curve_expression
from geometry.cas_surface import ExpressionError, parse_surface_expression
from services.scene_commands import CommandPlan

from .contracts import CapabilityError, CapabilityResult, ToolCall, validate_alias
from .scene_index import SceneIndex


_SAFE_EXPORT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,123}\.png$", re.IGNORECASE)
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
_SCOPES = {
    "all": None,
    "curves": {"curve"},
    "surfaces": {"surface", "point3d"},
    "geometry": {"point", "line", "segment", "ray", "vector", "area"},
    "annotations": {"annotation"},
}


def _index(context: Any) -> SceneIndex:
    if isinstance(context, SceneIndex):
        return context
    value = context.get("scene_index") if isinstance(context, dict) else getattr(context, "scene_index", None)
    if isinstance(value, SceneIndex):
        return value
    return SceneIndex("2d", {})


def _error(call: ToolCall, code: str, message: str, field: str | None = None) -> CapabilityResult:
    return CapabilityResult.error(call.call_id, call.name, CapabilityError(code, message, field))


def _plan(call: ToolCall, scene: str, summary: str, operations: list[dict[str, Any]]) -> CapabilityResult:
    return CapabilityResult.ok(call, plan=CommandPlan(scene=scene, summary=summary, operations=tuple(operations)).to_dict())


def _type_scope(object_type: str) -> str:
    return "3d" if object_type in {"point3d", "surface"} else "2d"


def scene_inspect(call: ToolCall, context: Any) -> CapabilityResult:
    return CapabilityResult.ok(call, data=_index(context).inspect(**call.arguments))


def scene_find(call: ToolCall, context: Any) -> CapabilityResult:
    return CapabilityResult.ok(call, data=_index(context).find(**call.arguments))


def scene_edit(call: ToolCall, context: Any) -> CapabilityResult:
    arguments = call.arguments
    action = str(arguments["action"])
    object_type = str(arguments["object_type"])
    alias = str(arguments["alias"])
    try:
        validate_alias(alias)
    except ValueError:
        return _error(call, "invalid_alias", "alias must be an ASCII identifier", "alias")
    index = _index(context)
    target_scene = _type_scope(object_type)
    if index.scene_mode != target_scene:
        return _error(call, "scene_scope_mismatch", f"{object_type} requires a {target_scene} scene")
    existing = index.get(alias)
    if existing is not None and existing.get("object_type") != object_type:
        return _error(call, "alias_conflict", "alias already belongs to a different object type", "alias")
    if action in {"update", "delete"} and existing is None:
        return _error(call, "not_found", "the requested alias does not exist", "alias")
    if action == "delete":
        delete_name = "point3d.delete" if object_type == "point3d" else {
            "point": "point.delete",
            "vector": "linear.delete",
            "line": "linear.delete",
            "curve": "curve.delete",
            "surface": "surface.delete",
            "annotation": "annotation.delete",
        }[object_type]
        return _plan(call, target_scene, f"删除 {alias}", [{"op": delete_name, "alias": alias}])
    try:
        operation = _edit_operation(arguments, existing is not None)
    except ValueError as error:
        field = "expression" if object_type in {"curve", "surface"} else None
        return _error(call, "invalid_scene_edit", str(error), field)
    return _plan(call, target_scene, f"编辑 {alias}", [operation])


def _edit_operation(arguments: dict[str, Any], exists: bool) -> dict[str, Any]:
    object_type = str(arguments["object_type"])
    alias = str(arguments["alias"])
    if object_type in {"point", "point3d"}:
        coordinates = arguments.get("coordinates")
        dimensions = 3 if object_type == "point3d" else 2
        if not isinstance(coordinates, list) or len(coordinates) != dimensions:
            raise ValueError(f"{object_type} requires {dimensions} coordinates")
        return {"op": f"{object_type}.upsert", "alias": alias, "coordinates": coordinates}
    if object_type in {"vector", "line"}:
        start, end = arguments.get("start"), arguments.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("line and vector edits require start and end aliases")
        return {"op": "linear.upsert", "alias": alias, "kind": object_type, "start": start, "end": end}
    if object_type in {"curve", "surface"}:
        expression, kind = arguments.get("expression"), str(arguments.get("kind", "explicit"))
        if not isinstance(expression, str):
            raise ValueError(f"{object_type} edits require expression")
        if object_type == "curve":
            parse_curve_expression(expression, kind)
        else:
            parse_surface_expression(expression, kind)
        name = f"{object_type}.update" if exists else f"{object_type}.create"
        return {"op": name, "alias": alias, "kind": kind, "expression": expression}
    if object_type == "annotation":
        text, position = arguments.get("text"), arguments.get("position")
        if not isinstance(text, str) or not isinstance(position, list) or len(position) != 2:
            raise ValueError("annotation edits require text and a two-dimensional position")
        return {"op": "annotation.upsert", "alias": alias, "text": text, "position": position}
    raise ValueError("unsupported scene object type")


def scene_clear(call: ToolCall, context: Any) -> CapabilityResult:
    scope = str(call.arguments["scope"])
    index = _index(context)
    types = _SCOPES[scope]
    if not index.has_object_type(types):
        return CapabilityResult.no_op(call, explanation=f"{scope} is already empty")
    return _plan(call, index.scene_mode, f"清除 {scope}", [{"op": "scene.clear", "scope": scope}])


def view_control(call: ToolCall, context: Any) -> CapabilityResult:
    action = str(call.arguments["action"])
    if action == "set_mode":
        mode = call.arguments.get("mode")
        if mode not in {"2d", "3d"}:
            return _error(call, "invalid_view_mode", "set_mode requires mode 2d or 3d", "mode")
        return _plan(call, str(mode), f"切换到 {mode}", [{"op": "scene.set_mode", "mode": mode}])
    if action == "fit":
        padding = float(call.arguments.get("padding", 1.15))
        return _plan(call, _index(context).scene_mode, "适配当前视图", [{"op": "view.fit", "padding": padding}])
    return _error(call, "unsupported_operation", "only set_mode and fit are available")


def result_export(call: ToolCall, context: Any) -> CapabilityResult:
    filename = str(call.arguments["filename"])
    stem = filename.rsplit(".", 1)[0].upper()
    if not _SAFE_EXPORT.fullmatch(filename) or stem in _WINDOWS_DEVICES:
        return _error(call, "unsafe_export_filename", "filename must be a safe PNG basename", "filename")
    return _plan(call, _index(context).scene_mode, "导出 PNG", [{"op": "scene.export_png", "filename": filename}])


def handlers() -> dict[str, Any]:
    return {
        "scene.inspect": scene_inspect,
        "scene.find": scene_find,
        "scene.edit": scene_edit,
        "scene.clear": scene_clear,
        "view.control": view_control,
        "result.export": result_export,
    }
