from __future__ import annotations

import json
import math

import pytest

from agent.capabilities.contracts import (
    CAPABILITY_CATALOG_VERSION,
    CapabilityError,
    CapabilityResult,
    CapabilitySpec,
    SceneScope,
    ToolCall,
    validate_alias,
)
from agent.capabilities.validation import validate_input_schema, validate_tool_arguments


def test_capability_contracts_round_trip_as_json_safe_values() -> None:
    spec = CapabilitySpec(
        name="scene.inspect",
        category="scene_read",
        description="Inspect the staged scene",
        input_schema={"type": "object", "additionalProperties": False},
        result_kind="data",
        scene_scope=SceneScope.BOTH,
        mutating=False,
        aliases=("inspect_scene",),
    )
    call = ToolCall(call_id="call-1", name=spec.name, arguments={})
    result = CapabilityResult.ok(call, data={"count": 1})

    payload = {"spec": spec.to_dict(), "call": call.to_dict(), "result": result.to_dict()}

    assert json.loads(json.dumps(payload, allow_nan=False))["spec"]["catalog_version"] == CAPABILITY_CATALOG_VERSION
    assert payload["result"]["status"] == "ok"
    assert payload["result"]["data"] == {"count": 1}


def test_success_result_requires_exactly_one_success_payload() -> None:
    call = ToolCall(call_id="call-1", name="scene.inspect", arguments={})

    with pytest.raises(ValueError, match="exactly one"):
        CapabilityResult(call_id=call.call_id, name=call.name, status="ok", data={}, plan={}, explanation="x")


def test_error_result_uses_bounded_machine_fields() -> None:
    error = CapabilityError(code="invalid_tool_arguments", message="bad input", field="expression")
    result = CapabilityResult.error("call-1", "math.calculate", error)

    assert result.to_dict()["errors"] == [{"code": "invalid_tool_arguments", "message": "bad input", "field": "expression"}]
    assert "data" not in result.to_dict()


@pytest.mark.parametrize("value", ["", "a/b", "__bad", "1alias", "a" * 65, "é"])
def test_aliases_are_ascii_bounded_identifiers(value: str) -> None:
    with pytest.raises(ValueError):
        validate_alias(value)


def test_json_safe_rejects_non_finite_values() -> None:
    call = ToolCall(call_id="call-1", name="scene.inspect", arguments={})
    with pytest.raises(ValueError, match="finite"):
        CapabilityResult.ok(call, data={"value": math.inf})


def test_schema_validation_rejects_unknown_fields_and_non_finite_arguments() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "expression": {"type": "string", "maxLength": 32},
            "x": {"type": "number", "minimum": -10, "maximum": 10},
        },
        "required": ["expression"],
    }

    validate_input_schema(schema)

    unknown = validate_tool_arguments(schema, {"expression": "x", "extra": True})
    non_finite = validate_tool_arguments(schema, {"expression": "x", "x": math.inf})

    assert unknown.code == "invalid_tool_arguments"
    assert unknown.field == "$"
    assert non_finite.code == "invalid_tool_arguments"
    assert non_finite.field == "$.x"


def test_schema_validation_rejects_unbounded_or_incomplete_first_party_schema() -> None:
    with pytest.raises(ValueError, match="additionalProperties"):
        validate_input_schema({"type": "object", "properties": {"name": {"type": "string"}}})
    with pytest.raises(ValueError, match="maxLength"):
        validate_input_schema(
            {"type": "object", "additionalProperties": False, "properties": {"name": {"type": "string"}}}
        )


def test_tool_arguments_reject_payload_over_fixed_byte_limit() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"text": {"type": "string", "maxLength": 20000}},
        "required": ["text"],
    }

    error = validate_tool_arguments(schema, {"text": "x" * (16 * 1024)})

    assert error.code == "tool_arguments_too_large"
