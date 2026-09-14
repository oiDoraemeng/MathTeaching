"""Lecture-grounded explanation content for the generated teaching artifacts.

The project keeps its authoritative teaching prose in the lecture source
(``.agents/线性代数讲义.md``).  Every reviewed artifact stores the verbatim
excerpt of its own section in ``source.excerpt``, and this module routes that
excerpt back into the ``explanation`` buckets so the published software shows
the lecture instead of the deterministic one-line template.

The heavy lifting lives in :mod:`linear_algebra.teaching.lecture_from_source`,
which is marker-driven and never rewrites a character.  Chapters that have a
hand-authored lesson table (chapter 2) keep their prose because the merge rules
treat already-authored fields as authoritative and only append lecture text.
"""

from __future__ import annotations

from typing import Any


def _sync_sections(explanation: dict[str, Any]) -> None:
    """Refresh ``explanation['sections']`` from the explanation fields."""
    field_text = {
        "definition": explanation.get("definition", ""),
        "formula": explanation.get("formula", ""),
        "derivation": "\n".join(explanation.get("derivation", [])),
        "worked_examples": (
            "\n".join(explanation.get("worked_examples", [{}])[0].get("calculation", []))
            if explanation.get("worked_examples")
            else ""
        ),
        "intuition": explanation.get("intuition", ""),
        "geometric_meaning": explanation.get("geometric_meaning", ""),
        "conclusion": explanation.get("conclusion", ""),
        "pitfalls": "\n".join(explanation.get("pitfalls", [])),
        "invariants": "\n".join(explanation.get("invariants", [])),
        "connections": "\n".join(explanation.get("connections", [])),
        "transfer_note": explanation.get("transfer_note", ""),
        "read_guide": "\n".join(explanation.get("read_guide", [])),
    }
    sections = explanation.get("sections")
    if not isinstance(sections, list):
        sections = []
    by_id = {str(section.get("id")): section for section in sections if isinstance(section, dict)}
    for section_id, text in field_text.items():
        if not str(text).strip():
            continue
        section = by_id.get(section_id)
        if section is None:
            section = {"id": section_id, "title": section_id, "claim_refs": []}
            sections.append(section)
        section["text"] = str(text)
    explanation["sections"] = sections


def _searchable_text(explanation: dict[str, Any]) -> list[str]:
    """Return the de-duplicated, order-preserving search index for a payload."""
    values = [
        explanation.get("title", ""),
        explanation.get("summary", ""),
        explanation.get("formula", ""),
    ]
    for key in (
        "definition",
        "derivation",
        "geometric_meaning",
        "invariants",
        "pitfalls",
        "connections",
        "read_guide",
    ):
        value = explanation.get(key, "")
        values.extend(value if isinstance(value, list) else [value])
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def apply(payload: dict[str, Any]) -> bool:
    """Route the payload's lecture excerpt into its explanation fields.

    Returns True when lecture content was merged, False when the topic is out
    of scope (chapter 1, or a payload without a usable excerpt).
    """
    from linear_algebra.teaching import lecture_from_source

    return lecture_from_source.apply(payload)


__all__ = ["apply"]
