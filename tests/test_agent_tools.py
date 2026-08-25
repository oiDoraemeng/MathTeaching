from __future__ import annotations

import importlib

import pytest

from agent.tool_registry import ToolRegistry
from services.scene_commands import SceneCommandService


def test_registry_exposes_math_tools_with_schemas() -> None:
    registry = ToolRegistry()

    names = {tool.name for tool in registry.list_tools()}

    assert {"inspect_scene", "calculate_expression", "create_curve", "create_tangent", "create_integral_area", "create_determinant_demo"} <= names
    assert all(isinstance(tool.input_schema, dict) for tool in registry.list_tools())


def test_mutating_tool_returns_plan_and_preview_does_not_execute() -> None:
    service = SceneCommandService()
    registry = ToolRegistry(command_service=service)

    result = registry.call("create_curve", expression="x^2", alias="f")

    assert result.plan is not None
    assert result.validation.valid
    assert service._last_plan is None


def test_invalid_tool_arguments_are_rejected() -> None:
    with pytest.raises(ValueError, match="expression"):
        ToolRegistry().call("create_curve", expression="__import__('os')", alias="f")


def test_tool_registry_does_not_import_renderers() -> None:
    module = importlib.import_module("agent.tool_registry")
    assert "PySide6" not in module.__dict__
    assert "pyvista" not in module.__dict__
