"""Single source of stable teaching-role colors."""

from __future__ import annotations

ROLE_COLORS: dict[str, str] = {
    "vector_a": "#2F6BFF",
    "vector_b": "#F08A24",
    "basis_e1": "#2F6BFF",
    "basis_e2": "#F08A24",
    "transformed_a": "#7B61FF",
    "transformed_b": "#D64550",
    "area": "#E09F3E",
    "projection": "#2A9D8F",
    "residual": "#E76F51",
    "direction": "#2A9D8F",
    "foot": "#6B7280",
    "volume": "#2A9D8F",
    "construction": "#6B7280",
    "neutral": "#6B7280",
}


def role_color(role: str) -> str:
    """Return a stable color, falling back to neutral for unknown roles."""

    return ROLE_COLORS.get(str(role), ROLE_COLORS["neutral"])


def known_role(role: str) -> bool:
    return str(role) in ROLE_COLORS


__all__ = ["ROLE_COLORS", "known_role", "role_color"]
