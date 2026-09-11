from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationContent:
    id: str
    title: str
    summary: str
    formula: str
    steps: tuple[str, ...]
    geometric_meaning: str
    conclusion: str
    searchable_text: tuple[str, ...]
    numeric_example: str = ""
    pitfalls: tuple[str, ...] = ()
    read_guide: tuple[str, ...] = ()
    analogy_boundary: str = ""
