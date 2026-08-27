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


def test_legacy_tool_name_routes_to_canonical_capability() -> None:
    result = ToolRegistry().call("create_curve", expression="x^2", alias="f")

    assert result.canonical_name == "scene.edit"
    assert result.plan is not None
    assert result.plan.operations[0]["expression"] == "y=x^2"


def test_every_legacy_tool_reports_a_catalog_canonical_name() -> None:
    registry = ToolRegistry()
    catalog_names = {item["name"] for item in registry.capabilities.catalog()["capabilities"]}
    results = (
        registry.call("inspect_scene"),
        registry.call("calculate_expression", expression="2+2"),
        registry.call("create_curve", expression="x", alias="f"),
        registry.call("create_tangent", expression="x^2", curve_alias="f", x=1),
        registry.call("create_integral_area", expression="x", curve_alias="f", interval=[0, 1]),
        registry.call("create_determinant_demo", a=[1, 0], b=[0, 1]),
    )

    assert {result.canonical_name for result in results} <= catalog_names


def test_tool_registry_does_not_import_renderers() -> None:
    module = importlib.import_module("agent.tool_registry")
    assert "PySide6" not in module.__dict__
    assert "pyvista" not in module.__dict__


def test_skill_metadata_uses_only_canonical_capability_names() -> None:
    canonical = set(__import__("agent.capabilities.contracts", fromlist=["CANONICAL_CAPABILITY_NAMES"]).CANONICAL_CAPABILITY_NAMES)
    skills = __import__("agent.skill_manager", fromlist=["SkillManager"]).SkillManager().list_skills()

    assert all(set(skill.capabilities) <= canonical for skill in skills)
