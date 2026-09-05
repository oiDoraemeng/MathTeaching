"""Teaching-role palette contract tests."""

from linear_algebra.visualizations.palette import ROLE_COLORS, known_role, role_color


def test_palette_covers_core_math_roles_and_unknown_is_neutral() -> None:
    required = {
        "vector_a",
        "vector_b",
        "basis_e1",
        "basis_e2",
        "transformed_a",
        "transformed_b",
        "area",
        "projection",
        "residual",
        "neutral",
    }
    assert required <= set(ROLE_COLORS)
    assert known_role("projection")
    assert not known_role("model-invented-role")
    assert role_color("model-invented-role") == ROLE_COLORS["neutral"]


def test_palette_is_the_only_visualization_hex_color_source() -> None:
    from pathlib import Path
    import re

    root = Path(__file__).parents[1] / "linear_algebra" / "visualizations"
    hex_files = {
        path.name
        for path in root.rglob("*.py")
        if re.search(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8"))
    }
    assert hex_files == {"palette.py"}
