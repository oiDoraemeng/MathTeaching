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
