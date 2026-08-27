"""Strict local validation for capability arguments and catalog schemas."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .contracts import CapabilityError, MAX_TOOL_ARGUMENT_BYTES, json_safe


def _schema_children(schema: dict[str, Any]) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        children.extend(item for item in properties.values() if isinstance(item, dict))
    items = schema.get("items")
    if isinstance(items, dict):
        children.append(items)
    for key in ("allOf", "anyOf", "oneOf"):
        items_value = schema.get(key, ())
        if isinstance(items_value, list):
            children.extend(item for item in items_value if isinstance(item, dict))
    return children


def validate_input_schema(schema: dict[str, Any]) -> None:
    """Reject intentionally broad schemas before they enter the local catalog."""
    if not isinstance(schema, dict):
        raise ValueError("capability input schema must be an object")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise ValueError(f"invalid Draft 2020-12 schema: {error}") from None

    def visit(item: dict[str, Any]) -> None:
        type_value = item.get("type")
        types = {type_value} if isinstance(type_value, str) else set(type_value or ())
        if "object" in types:
            if item.get("additionalProperties") is not False:
                raise ValueError("object schemas require additionalProperties: false")
        if "string" in types and "maxLength" not in item:
            raise ValueError("string schemas require maxLength")
        if "array" in types and "maxItems" not in item:
            raise ValueError("array schemas require maxItems")
        if types & {"number", "integer"} and not ({"minimum", "exclusiveMinimum"} & set(item)):
            raise ValueError("number schemas require minimum")
        if types & {"number", "integer"} and not ({"maximum", "exclusiveMaximum"} & set(item)):
            raise ValueError("number schemas require maximum")
        for child in _schema_children(item):
            visit(child)

    visit(schema)


def _field_path(error: Any) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def validate_tool_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> CapabilityError | None:
    """Return a bounded public error; handlers never receive invalid input."""
    if not isinstance(arguments, dict):
        return CapabilityError("invalid_tool_arguments", "arguments must be an object", "$")
    try:
        safe = json_safe(arguments)
        encoded = json.dumps(safe, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except ValueError as error:
        message = str(error)
        path_prefix = message.split(" must", 1)[0]
        field = "$" if not path_prefix.startswith("value") else "$" + path_prefix[len("value") :]
        return CapabilityError("invalid_tool_arguments", message, field)
    if len(encoded) > MAX_TOOL_ARGUMENT_BYTES:
        return CapabilityError("tool_arguments_too_large", "tool arguments exceed the 16 KiB limit", "$")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(safe), key=lambda item: (list(item.absolute_path), item.message))
    if not errors:
        return None
    error = errors[0]
    message = error.message[:512]
    return CapabilityError("invalid_tool_arguments", message, _field_path(error))
