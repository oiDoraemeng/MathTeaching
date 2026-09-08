"""Qt-free runtime state for one ordinary scene pane.

The pane state deliberately keeps renderer/interactor instances out of its
snapshot representation.  This makes the data useful to undo/restore and to
the agent protocol without importing Qt or PyVista.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import json
from typing import Any, ClassVar, Mapping


SNAPSHOT_VERSION = 1


def _json_copy(value: Any, field_name: str) -> Any:
    """Validate and detach a value that is intended for a JSON snapshot."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        return json.loads(encoded)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must contain only JSON-safe values") from error


@dataclass
class ScenePaneState:
    """Independent scene, camera, selection, and algebra state for a pane."""

    pane_id: str
    name: str
    scene_mode: str = "2d"
    scene_2d: dict[str, Any] = field(default_factory=dict)
    scene_3d: dict[str, Any] = field(default_factory=dict)
    camera_2d: dict[str, Any] = field(default_factory=dict)
    camera_3d: dict[str, Any] = field(default_factory=dict)
    selected_object_ids: list[str] = field(default_factory=list)
    algebra_model: dict[str, Any] = field(default_factory=dict)
    # Runtime-only references.  They are intentionally omitted from snapshots.
    renderer_2d: Any = field(default=None, repr=False, compare=False)
    renderer_3d: Any = field(default=None, repr=False, compare=False)

    SNAPSHOT_VERSION: ClassVar[int] = SNAPSHOT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.pane_id, str) or not self.pane_id.strip():
            raise ValueError("pane_id must be a non-empty string")
        if not isinstance(self.name, str):
            raise ValueError("name must be a string")
        if self.scene_mode not in {"2d", "3d"}:
            # StrEnum values compare equal to their string values, so this also
            # accepts models.scene_mode.SceneMode without importing it here.
            raise ValueError("scene_mode must be 2d or 3d")
        for field_name in ("scene_2d", "scene_3d", "camera_2d", "camera_3d", "algebra_model"):
            value = getattr(self, field_name)
            if not isinstance(value, dict):
                raise ValueError(f"{field_name} must be an object")
        if not isinstance(self.selected_object_ids, list) or not all(
            isinstance(item, str) for item in self.selected_object_ids
        ):
            raise ValueError("selected_object_ids must be a list of strings")

    def to_snapshot(self) -> dict[str, Any]:
        """Return a detached JSON-safe snapshot, excluding runtime references."""
        snapshot = {
            "version": self.SNAPSHOT_VERSION,
            "pane_id": self.pane_id,
            "name": self.name,
            "scene_mode": str(self.scene_mode),
            "scene_2d": self.scene_2d,
            "scene_3d": self.scene_3d,
            "camera_2d": self.camera_2d,
            "camera_3d": self.camera_3d,
            "selected_object_ids": self.selected_object_ids,
            "algebra_model": self.algebra_model,
        }
        return _json_copy(snapshot, "scene pane snapshot")

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "ScenePaneState":
        """Construct a pane from a validated JSON-compatible mapping."""
        if not isinstance(snapshot, Mapping):
            raise ValueError("scene pane snapshot must be an object")
        try:
            version = int(snapshot.get("version", cls.SNAPSHOT_VERSION))
        except (TypeError, ValueError) as error:
            raise ValueError("scene pane snapshot version must be an integer") from error
        if version != cls.SNAPSHOT_VERSION:
            raise ValueError(f"unsupported scene pane snapshot version: {version}")
        # Validate the complete input before extracting fields, including any
        # nested values that might otherwise hide a Qt/PyVista object.
        payload = _json_copy(dict(snapshot), "scene pane snapshot")
        required = ("pane_id", "name", "scene_mode", "scene_2d", "scene_3d", "camera_2d", "camera_3d", "selected_object_ids", "algebra_model")
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"scene pane snapshot missing fields: {', '.join(missing)}")
        return cls(
            pane_id=payload["pane_id"],
            name=payload["name"],
            scene_mode=payload["scene_mode"],
            scene_2d=payload["scene_2d"],
            scene_3d=payload["scene_3d"],
            camera_2d=payload["camera_2d"],
            camera_3d=payload["camera_3d"],
            selected_object_ids=payload["selected_object_ids"],
            algebra_model=payload["algebra_model"],
        )

