"""Pure, non-rendering comparison of normalized teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .model import TeachingArtifact


@dataclass(frozen=True)
class FieldChange:
    path: str
    old: object
    new: object


@dataclass(frozen=True)
class ArtifactDiff:
    changed_sections: tuple[str, ...]
    claim_changes: tuple[FieldChange, ...]
    explanation_changes: tuple[FieldChange, ...]
    visual_changes: tuple[FieldChange, ...]
    render_requested: bool = False


def diff_artifacts(old: TeachingArtifact, new: TeachingArtifact) -> ArtifactDiff:
    """Return deterministic field changes without importing scene services."""

    old_payload = old.to_dict()
    new_payload = new.to_dict()
    changed = tuple(
        key
        for key in old_payload
        if _canonical(_redact(key, old_payload[key])) != _canonical(_redact(key, new_payload.get(key)))
    )
    changed += tuple(key for key in new_payload if key not in old_payload)
    return ArtifactDiff(
        changed_sections=tuple(sorted(set(changed))),
        claim_changes=_diff_keyed("claims", old_payload.get("claims", []), new_payload.get("claims", [])),
        explanation_changes=_diff_tree("$.explanation", old_payload.get("explanation", {}), new_payload.get("explanation", {})),
        visual_changes=_diff_tree("$.visual_semantics", old_payload.get("visual_semantics", {}), new_payload.get("visual_semantics", {})),
    )


def _diff_keyed(section: str, old: object, new: object) -> tuple[FieldChange, ...]:
    old_items = _keyed(old)
    new_items = _keyed(new)
    changes: list[FieldChange] = []
    for key in sorted(set(old_items) | set(new_items)):
        path = f"$.{section}[{key!r}]"
        if key not in old_items:
            changes.append(FieldChange(path, None, _redact(section, new_items[key])))
        elif key not in new_items:
            changes.append(FieldChange(path, _redact(section, old_items[key]), None))
        else:
            changes.extend(_diff_tree(path, old_items[key], new_items[key]))
    return tuple(sorted(changes, key=lambda item: item.path))


def _diff_tree(path: str, old: object, new: object) -> tuple[FieldChange, ...]:
    if isinstance(old, Mapping) and isinstance(new, Mapping):
        changes: list[FieldChange] = []
        for key in sorted(set(old) | set(new)):
            child_path = f"{path}.{key}"
            if key not in old:
                changes.append(FieldChange(child_path, None, _redact(str(key), new[key])))
            elif key not in new:
                changes.append(FieldChange(child_path, _redact(str(key), old[key]), None))
            else:
                changes.extend(_diff_tree(child_path, old[key], new[key]))
        return tuple(changes)
    if _canonical(old) != _canonical(new):
        return (FieldChange(path, _redact(path, old), _redact(path, new)),)
    return ()


def _keyed(value: object) -> dict[str, object]:
    if not isinstance(value, (list, tuple)):
        return {}
    result: dict[str, object] = {}
    for index, item in enumerate(value):
        if isinstance(item, Mapping) and isinstance(item.get("id"), str):
            result[item["id"]] = item
        else:
            result[str(index)] = item
    return result


def _redact(path: str, value: object) -> object:
    if path in {"provider", "model"} or path.endswith(".provider") or path.endswith(".model"):
        return "<redacted>"
    return value


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _canonical(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_canonical(item) for item in value)
    return value


__all__ = ["ArtifactDiff", "FieldChange", "diff_artifacts"]
