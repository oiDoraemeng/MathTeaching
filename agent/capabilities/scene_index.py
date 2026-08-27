"""Renderer-free staged view of a serializable :class:`SceneSnapshot`."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from agent.scene_snapshot import SceneSnapshot


MAX_INSPECT_RESULTS = 50
MAX_FIND_RESULTS = 20


def _alias(record: dict[str, Any]) -> str:
    return str(record.get("agent_alias") or record.get("alias") or record.get("name") or "")


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    value = {"alias": _alias(record), "object_type": str(record.get("object_type") or record.get("kind") or "object")}
    for field in ("coordinates", "expression", "kind", "text", "start", "end", "position"):
        if field in record:
            value[field] = deepcopy(record[field])
    if "x" in record and "y" in record:
        value["coordinates"] = [record["x"], record["y"]]
    return value


@dataclass
class SceneIndex:
    scene_mode: str
    _objects: dict[str, dict[str, Any]]

    @classmethod
    def from_snapshot(cls, snapshot: SceneSnapshot) -> "SceneIndex":
        objects: dict[str, dict[str, Any]] = {}

        def add(record: dict[str, Any], object_type: str) -> None:
            value = deepcopy(record)
            value["object_type"] = object_type
            alias = _alias(value)
            if alias:
                objects[alias] = value

        for record in snapshot.curves:
            add(record, "curve")
        for record in snapshot.layers:
            add(record, "surface")
        for record in snapshot.geometry:
            object_type = str(record.get("object_type") or record.get("kind") or "object")
            if object_type == "linear":
                object_type = str(record.get("kind") or "line")
            add(record, object_type)
        for record in snapshot.annotations:
            add(record, "annotation")
        for item in snapshot.metadata.get("points3d", []):
            if isinstance(item, dict):
                add(item, "point3d")
            elif isinstance(item, (tuple, list)) and len(item) == 2:
                add({"alias": str(item[0]), "coordinates": list(item[1])}, "point3d")
        for item in snapshot.metadata.get("areas", []):
            if isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[1], dict):
                add({"alias": str(item[0]), **item[1]}, "area")
        return cls(snapshot.scene_mode, objects)

    def clone(self) -> "SceneIndex":
        return SceneIndex(self.scene_mode, deepcopy(self._objects))

    def inspect(self, *, limit: int = MAX_INSPECT_RESULTS) -> dict[str, Any]:
        bounded = max(1, min(int(limit), MAX_INSPECT_RESULTS))
        values = [_summary(self._objects[key]) for key in sorted(self._objects)]
        return {
            "scene_mode": self.scene_mode,
            "objects": values[:bounded],
            "truncated": len(values) > bounded,
            "omitted_count": max(0, len(values) - bounded),
        }

    def find(
        self,
        *,
        alias: str | None = None,
        object_types: Iterable[str] | None = None,
        expression_contains: str | None = None,
        limit: int = MAX_FIND_RESULTS,
    ) -> dict[str, Any]:
        bounded = max(1, min(int(limit), MAX_FIND_RESULTS))
        allowed_types = {str(item) for item in object_types or ()}
        needle = str(expression_contains or "")
        values: list[dict[str, Any]] = []
        for key in sorted(self._objects):
            record = self._objects[key]
            if alias is not None and key != alias:
                continue
            if allowed_types and record.get("object_type") not in allowed_types:
                continue
            if needle and needle not in str(record.get("expression", "")):
                continue
            values.append(_summary(record))
        return {"objects": values[:bounded], "truncated": len(values) > bounded, "omitted_count": max(0, len(values) - bounded)}

    def get(self, alias: str) -> dict[str, Any] | None:
        value = self._objects.get(alias)
        return deepcopy(value) if value is not None else None

    def has_object_type(self, object_types: set[str] | None = None) -> bool:
        """Check staged membership without exposing an unbounded collection."""
        return any(object_types is None or value.get("object_type") in object_types for value in self._objects.values())

    def apply_operations(self, operations: Iterable[dict[str, Any]]) -> None:
        for operation in operations:
            name = str(operation.get("op", ""))
            if name == "scene.set_mode":
                self.scene_mode = str(operation.get("mode", self.scene_mode))
            elif name == "scene.clear":
                self._clear(str(operation.get("scope", "all")))
            elif name in {"point.upsert", "point3d.upsert"}:
                self._upsert(operation, "point3d" if name.startswith("point3d") else "point")
            elif name == "linear.upsert":
                self._upsert(operation, str(operation.get("kind", "line")))
            elif name in {"curve.create", "curve.update"}:
                self._upsert(operation, "curve")
            elif name in {"surface.create", "surface.update"}:
                self._upsert(operation, "surface")
            elif name == "annotation.upsert":
                self._upsert(operation, "annotation")
            elif name == "area.fill":
                self._upsert(operation, "area")
            elif name.endswith(".delete"):
                self._objects.pop(str(operation.get("alias", "")), None)

    def _upsert(self, operation: dict[str, Any], object_type: str) -> None:
        alias = str(operation.get("alias", ""))
        if not alias:
            return
        value = deepcopy(operation)
        value["object_type"] = object_type
        self._objects[alias] = value

    def _clear(self, scope: str) -> None:
        types_by_scope = {
            "all": None,
            "curves": {"curve"},
            "surfaces": {"surface", "point3d"},
            "geometry": {"point", "line", "segment", "ray", "vector", "area"},
            "annotations": {"annotation"},
        }
        types = types_by_scope.get(scope)
        if types is None:
            self._objects.clear()
            return
        for alias in [key for key, value in self._objects.items() if value.get("object_type") in types]:
            self._objects.pop(alias, None)
