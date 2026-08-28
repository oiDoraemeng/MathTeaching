from __future__ import annotations

from agent.capabilities.registry import build_default_registry


def test_default_catalog_advertises_only_nine_canonical_capabilities() -> None:
    registry = build_default_registry()

    catalog = registry.catalog()

    assert catalog["catalog_version"] == 1
    assert [item["name"] for item in catalog["capabilities"]] == [
        "math.calculate",
        "math.derive",
        "result.export",
        "scene.clear",
        "scene.edit",
        "scene.find",
        "scene.inspect",
        "teaching.explain",
        "view.control",
    ]
    assert {item["category"] for item in catalog["capabilities"]} == {
        "math",
        "result",
        "scene_edit",
        "scene_read",
        "teaching",
        "view",
    }
    assert all("aliases" not in item for item in catalog["capabilities"])


def test_legacy_aliases_resolve_but_are_not_advertised() -> None:
    registry = build_default_registry()

    assert registry.resolve_name("create_curve") == "scene.edit"
    assert registry.resolve_name("inspect_scene") == "scene.inspect"
    assert "create_curve" not in {item["name"] for item in registry.catalog()["capabilities"]}


def test_every_catalog_schema_keeps_the_local_bounded_contract() -> None:
    """Local jsonschema validation is the real safety boundary, not server strict.

    Tool definitions are sent without ``strict`` because these schemas have
    genuinely optional parameters, so this asserts the bounds that
    ``validate_tool_arguments`` enforces per call are still declared.
    """
    catalog = build_default_registry().catalog()["capabilities"]

    assert len(catalog) == 9

    def visit(schema: dict, path: str) -> None:
        types = {schema["type"]} if isinstance(schema.get("type"), str) else set(schema.get("type") or ())
        if "object" in types:
            assert schema.get("additionalProperties") is False, path
        if "string" in types:
            assert "maxLength" in schema, path
        if "array" in types:
            assert "maxItems" in schema, path
        if types & {"number", "integer"}:
            assert {"minimum", "exclusiveMinimum"} & set(schema), path
            assert {"maximum", "exclusiveMaximum"} & set(schema), path
        for name, child in (schema.get("properties") or {}).items():
            visit(child, f"{path}.{name}")
        if isinstance(schema.get("items"), dict):
            visit(schema["items"], f"{path}[]")

    for item in catalog:
        visit(item["input_schema"], item["name"])
