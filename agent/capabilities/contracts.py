"""JSON-only contracts shared by capability handlers, providers, and the UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
import re
from typing import Any, Mapping


CAPABILITY_CATALOG_VERSION = 1
CANONICAL_CAPABILITY_NAMES = (
    "scene.inspect",
    "scene.find",
    "scene.edit",
    "scene.clear",
    "math.calculate",
    "math.derive",
    "view.control",
    "result.export",
    "teaching.explain",
)
CAPABILITY_CATEGORIES = ("scene_read", "scene_edit", "math", "view", "result", "teaching")
MAX_TOOL_ARGUMENT_BYTES = 16 * 1024
MAX_TOOL_RESULT_BYTES = 32 * 1024
MAX_TOOL_CALLS = 8
MAX_MUTATING_CALLS = 4
MAX_RAW_PLAN_OPERATIONS = 32
MAX_EXPANDED_PLAN_OPERATIONS = 128
MAX_IDENTICAL_TOOL_CALLS = 2
MAX_EVENT_STRING_LENGTH = 512
_ALIAS_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class SceneScope(str, Enum):
    TWO_D = "2d"
    THREE_D = "3d"
    BOTH = "both"


class CapabilityStatus(str, Enum):
    OK = "ok"
    NO_OP = "no_op"
    ERROR = "error"


def validate_alias(value: str) -> str:
    """Validate a machine-facing, case-sensitive object/capability alias."""
    if not isinstance(value, str) or not _ALIAS_PATTERN.fullmatch(value):
        raise ValueError("alias must match [A-Za-z][A-Za-z0-9_-]{0,63}")
    return value


def _json_safe(value: Any, *, path: str = "value") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain finite numbers")
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value, path=path)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item, path=f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_safe(value.to_dict(), path=path)
    raise ValueError(f"{path} is not JSON serializable")


def json_safe(value: Any) -> Any:
    """Detach and validate a value before it crosses a provider/UI boundary."""
    safe = _json_safe(value)
    json.dumps(safe, ensure_ascii=False, allow_nan=False)
    return safe


def _bounded_text(value: str, *, field: str) -> str:
    text = str(value)
    if len(text) > MAX_EVENT_STRING_LENGTH:
        return text[:MAX_EVENT_STRING_LENGTH]
    return text


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    category: str
    description: str
    input_schema: dict[str, Any]
    result_kind: str
    scene_scope: SceneScope = SceneScope.BOTH
    mutating: bool = False
    aliases: tuple[str, ...] = ()
    catalog_version: int = CAPABILITY_CATALOG_VERSION
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.catalog_version != CAPABILITY_CATALOG_VERSION:
            raise ValueError("unsupported capability catalog version")
        if not self.name or not self.category or not self.result_kind:
            raise ValueError("capability name, category, and result_kind are required")
        if not isinstance(self.input_schema, dict):
            raise ValueError("input_schema must be an object")
        for alias in self.aliases:
            validate_alias(alias)
        json_safe(self.input_schema)

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "name": self.name,
            "category": self.category,
            "description": _bounded_text(self.description, field="description"),
            "input_schema": json_safe(self.input_schema),
            "result_kind": self.result_kind,
            "scene_scope": self.scene_scope.value,
            "mutating": self.mutating,
            "aliases": list(self.aliases),
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.call_id or not self.name:
            raise ValueError("call_id and name are required")
        if not isinstance(self.arguments, dict):
            raise ValueError("arguments must be an object")
        json_safe(self.arguments)

    def to_dict(self) -> dict[str, Any]:
        return {"call_id": self.call_id, "name": self.name, "arguments": json_safe(self.arguments)}

    def normalized_key(self) -> str:
        return json.dumps({"name": self.name, "arguments": self.arguments}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class CapabilityError:
    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "code": _bounded_text(self.code, field="code"),
            "message": _bounded_text(self.message, field="message"),
        }
        if self.field:
            payload["field"] = _bounded_text(self.field, field="field")
        return payload


@dataclass(frozen=True)
class CapabilityResult:
    call_id: str
    name: str
    status: str = CapabilityStatus.OK.value
    data: Any = None
    plan: Any = None
    explanation: str | None = None
    errors: tuple[CapabilityError, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {item.value for item in CapabilityStatus}:
            raise ValueError("unsupported capability result status")
        payload_count = sum(item is not None for item in (self.data, self.plan, self.explanation))
        if self.status in {CapabilityStatus.OK.value, CapabilityStatus.NO_OP.value} and payload_count != 1:
            raise ValueError("successful result requires exactly one payload")
        if self.status == CapabilityStatus.ERROR.value and (payload_count or not self.errors):
            raise ValueError("error result requires errors and no success payload")
        json_safe(self.data) if self.data is not None else None
        json_safe(self.plan) if self.plan is not None else None
        if self.explanation is not None:
            _bounded_text(self.explanation, field="explanation")

    @classmethod
    def ok(cls, call: ToolCall, *, data: Any = None, plan: Any = None, explanation: str | None = None) -> "CapabilityResult":
        return cls(call.call_id, call.name, data=data, plan=plan, explanation=explanation)

    @classmethod
    def no_op(cls, call: ToolCall, *, explanation: str) -> "CapabilityResult":
        return cls(call.call_id, call.name, status=CapabilityStatus.NO_OP.value, explanation=explanation)

    @classmethod
    def error(cls, call_id: str, name: str, error: CapabilityError) -> "CapabilityResult":
        return cls(call_id, name, status=CapabilityStatus.ERROR.value, errors=(error,))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"call_id": self.call_id, "name": self.name, "status": self.status}
        if self.data is not None:
            payload["data"] = json_safe(self.data)
        if self.plan is not None:
            payload["plan"] = json_safe(self.plan)
        if self.explanation is not None:
            payload["explanation"] = _bounded_text(self.explanation, field="explanation")
        if self.errors:
            payload["errors"] = [item.to_dict() for item in self.errors]
        return payload
