"""Versioned, renderer-independent snapshots of the teaching scene."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import hashlib
import json
from typing import Any


SNAPSHOT_VERSION = 1


def _json_value(value: Any) -> Any:
    """Return a detached JSON-compatible value without renderer objects."""
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ValueError("scene snapshot contains a non-JSON value") from error
    return json.loads(encoded)


def _tuple_records(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be an array")
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} entries must be objects")
        records.append(_json_value(item))
    return tuple(records)


@dataclass(frozen=True)
class SceneSnapshot:
    """Pure data representation used for restore, undo, and branching."""

    version: int = SNAPSHOT_VERSION
    scene_mode: str = "2d"
    curves: tuple[dict[str, Any], ...] = ()
    geometry: tuple[dict[str, Any], ...] = ()
    layers: tuple[dict[str, Any], ...] = ()
    annotations: tuple[dict[str, Any], ...] = ()
    camera: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    # 多窗格扩展；旧字段仍表示活动窗格。
    panes: tuple[dict[str, Any], ...] = ()
    active_pane_id: str | None = None

    def __post_init__(self) -> None:
        if self.version != SNAPSHOT_VERSION:
            raise ValueError(f"unsupported scene snapshot version: {self.version}")
        if self.scene_mode not in {"2d", "3d"}:
            raise ValueError("scene_mode must be 2d or 3d")
        for name in ("curves", "geometry", "layers", "annotations"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or not all(isinstance(item, dict) for item in value):
                raise ValueError(f"{name} must contain object records")
        if not isinstance(self.camera, dict) or not isinstance(self.metadata, dict):
            raise ValueError("camera and metadata must be objects")
        if self.active_pane_id is not None and (not isinstance(self.active_pane_id, str) or not self.active_pane_id.strip()):
            raise ValueError("active_pane_id must be a non-empty string or None")
        # 构造时校验并复制可变嵌套数据。
        object.__setattr__(self, "curves", _tuple_records(self.curves, "curves"))
        object.__setattr__(self, "geometry", _tuple_records(self.geometry, "geometry"))
        object.__setattr__(self, "layers", _tuple_records(self.layers, "layers"))
        object.__setattr__(self, "annotations", _tuple_records(self.annotations, "annotations"))
        object.__setattr__(self, "camera", _json_value(self.camera))
        object.__setattr__(self, "metadata", _json_value(self.metadata))
        object.__setattr__(self, "panes", _tuple_records(self.panes, "panes"))
        for pane in self.panes:
            pane_id = pane.get("pane_id")
            if not isinstance(pane_id, str) or not pane_id.strip():
                raise ValueError("panes entries require a non-empty pane_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "scene_mode": self.scene_mode,
            "curves": copy.deepcopy(list(self.curves)),
            "geometry": copy.deepcopy(list(self.geometry)),
            "layers": copy.deepcopy(list(self.layers)),
            "annotations": copy.deepcopy(list(self.annotations)),
            "camera": copy.deepcopy(self.camera),
            "metadata": copy.deepcopy(self.metadata),
            "panes": copy.deepcopy(list(self.panes)),
            "active_pane_id": self.active_pane_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    def fingerprint(self) -> str:
        """Stable SHA-256 identity used to guard delayed scene execution."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def fingerprint_for_pane(self, pane_id: str) -> str:
        """Guard the requested scene without treating focus/layout as edits."""
        pane = next((item for item in self.panes if item["pane_id"] == pane_id), None)
        if pane is None:
            raise ValueError(f"unknown snapshot pane: {pane_id}")
        scene = pane.get("snapshot", {})
        # 相机移动和选择属于视图交互，不计入场景编辑。
        payload = {key: scene.get(key) for key in
                   ("scene_mode", "curves", "geometry", "layers", "annotations", "metadata")}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SceneSnapshot":
        if not isinstance(payload, dict):
            raise ValueError("scene snapshot must be an object")
        try:
            version = int(payload.get("version", SNAPSHOT_VERSION))
        except (TypeError, ValueError) as error:
            raise ValueError("scene snapshot version must be an integer") from error
        if version != SNAPSHOT_VERSION:
            raise ValueError(f"unsupported scene snapshot version: {version}")
        return cls(
            version=version,
            scene_mode=str(payload.get("scene_mode", "2d")),
            curves=_tuple_records(payload.get("curves", ()), "curves"),
            geometry=_tuple_records(payload.get("geometry", ()), "geometry"),
            layers=_tuple_records(payload.get("layers", ()), "layers"),
            annotations=_tuple_records(payload.get("annotations", ()), "annotations"),
            camera=dict(payload.get("camera", {})),
            metadata=dict(payload.get("metadata", {})),
            panes=_tuple_records(payload.get("panes", ()), "panes"),
            active_pane_id=payload.get("active_pane_id"),
        )

    @classmethod
    def from_json(cls, source: str) -> "SceneSnapshot":
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid scene snapshot JSON: {error.msg}") from error
        return cls.from_dict(payload)
