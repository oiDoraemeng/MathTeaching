"""Deterministic context packing and local attachment handling."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from .scene_snapshot import SceneSnapshot


IMAGE_LIMIT = 10 * 1024 * 1024
DOCUMENT_LIMIT = 20 * 1024 * 1024
MAX_ATTACHMENTS = 5


@dataclass(frozen=True)
class AttachmentInput:
    path: Path
    mime_type: str


@dataclass(frozen=True)
class StoredAttachment:
    relative_path: str
    mime_type: str
    byte_size: int
    sha256: str
    text: str = ""


@dataclass(frozen=True)
class ContextPackage:
    scene: dict[str, Any]
    selected_object: dict[str, Any]
    recent_messages: tuple[str, ...]
    older_summary: str
    attachments: tuple[StoredAttachment, ...]
    used_tokens: int
    max_tokens: int

    @property
    def percentage(self) -> float:
        if self.max_tokens <= 0:
            return 0.0
        return min(100.0, round(self.used_tokens / self.max_tokens * 100.0, 1))


class ContextBroker:
    def __init__(
        self,
        *,
        max_tokens: int = 8192,
        recent_message_count: int = 8,
        attachments_root: str | Path | None = None,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.max_tokens = max_tokens
        self.recent_message_count = max(1, recent_message_count)
        self.attachments_root = Path(attachments_root) if attachments_root is not None else Path.home() / ".local" / "share" / "Math3DTeaching" / ".math"

    def build(
        self,
        *,
        scene_snapshot: SceneSnapshot | Mapping[str, Any] | None,
        selected_object: Mapping[str, Any] | None = None,
        messages: Sequence[str] = (),
        attachments: Sequence[StoredAttachment] = (),
    ) -> ContextPackage:
        snapshot = scene_snapshot if isinstance(scene_snapshot, SceneSnapshot) else SceneSnapshot.from_dict(dict(scene_snapshot or {}))
        scene = {
            "scene_mode": snapshot.scene_mode,
            "curves": list(snapshot.curves),
            "geometry": list(snapshot.geometry),
            "layers": list(snapshot.layers),
            "annotations": list(snapshot.annotations),
        }
        recent = tuple(str(message) for message in messages[-self.recent_message_count:])
        older = tuple(str(message) for message in messages[:-self.recent_message_count])
        older_summary = "；".join(message[:160] for message in older)
        text_parts = [str(scene), str(selected_object or {}), *recent, older_summary]
        text_parts.extend(item.text for item in attachments if item.text)
        used_tokens = max(1, math.ceil(sum(len(part) for part in text_parts) / 4))
        return ContextPackage(
            scene=scene,
            selected_object=dict(selected_object or {}),
            recent_messages=recent,
            older_summary=older_summary,
            attachments=tuple(attachments),
            used_tokens=used_tokens,
            max_tokens=self.max_tokens,
        )

    def store_attachments(self, inputs: Iterable[AttachmentInput]) -> tuple[StoredAttachment, ...]:
        values = tuple(inputs)
        if len(values) > MAX_ATTACHMENTS:
            raise ValueError("at most five attachments are allowed per turn")
        destination = self.attachments_root / "attachments"
        destination.mkdir(parents=True, exist_ok=True)
        records: list[StoredAttachment] = []
        for item in values:
            path = Path(item.path)
            if not path.is_file():
                raise ValueError(f"attachment does not exist: {path}")
            size = path.stat().st_size
            mime = item.mime_type.lower().strip()
            limit = IMAGE_LIMIT if mime.startswith("image/") else DOCUMENT_LIMIT
            if size > limit:
                label = "10 MB" if mime.startswith("image/") else "20 MB"
                raise ValueError(f"attachment exceeds {label} limit")
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            target_name = f"{uuid4().hex}_{path.name}"
            target = destination / target_name
            shutil.copy2(path, target)
            text = ""
            if mime.startswith("text/"):
                text = target.read_text(encoding="utf-8", errors="replace")[:100_000]
            records.append(StoredAttachment(f"attachments/{target_name}", mime, size, digest.hexdigest(), text))
        return tuple(records)
