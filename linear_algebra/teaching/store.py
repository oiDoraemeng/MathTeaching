"""Versioned, filesystem-backed storage for normalized teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Literal

from .model import ArtifactStatus, TeachingArtifact
from .validation import validate_artifact_payload


StoreState = Literal["draft", "reviewed", "published"]
_TOPIC_ID = re.compile(r"^ch\d{2}\.[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class ArtifactRevision:
    topic_id: str
    revision: int
    state: StoreState


@dataclass(frozen=True)
class StoredArtifact:
    artifact: TeachingArtifact
    raw_reply: str | None = None

    @classmethod
    def from_payload(cls, payload: object) -> "StoredArtifact":
        if not isinstance(payload, dict):
            raise ValueError("stored payload must be an object")
        artifact_payload = payload.get("artifact", payload)
        if not isinstance(artifact_payload, dict):
            raise ValueError("stored artifact must be an object")
        artifact = validate_artifact_payload(artifact_payload)
        raw_reply = payload.get("raw_reply")
        if raw_reply is not None and not isinstance(raw_reply, str):
            raise ValueError("stored raw_reply must be text")
        return cls(artifact=artifact, raw_reply=raw_reply)


class TeachingArtifactStore:
    """Persist drafts and review states under one configured root directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_draft(self, artifact: TeachingArtifact, *, raw_reply: str) -> ArtifactRevision:
        return self._save("draft", artifact, raw_reply=raw_reply)

    def save_reviewed(self, artifact: TeachingArtifact, *, raw_reply: str) -> ArtifactRevision:
        return self._save("reviewed", artifact, raw_reply=raw_reply)

    def save_published(self, artifact: TeachingArtifact, *, raw_reply: str | None = None) -> ArtifactRevision:
        return self._save("published", artifact, raw_reply=raw_reply)

    def get(self, topic_id: str, revision: int, state: StoreState) -> StoredArtifact:
        path = self._path(state, topic_id, revision)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"missing {state} artifact {topic_id!r} revision {revision}") from error
        return StoredArtifact.from_payload(payload)

    def published(self, topic_id: str) -> StoredArtifact | None:
        revisions = self.list_revisions(topic_id, "published")
        if not revisions:
            return None
        return self.get(topic_id, revisions[-1].revision, "published")

    def list_revisions(self, topic_id: str, state: StoreState | None = None) -> tuple[ArtifactRevision, ...]:
        self._validate_topic_id(topic_id)
        states = (state,) if state is not None else ("draft", "reviewed", "published")
        result: list[ArtifactRevision] = []
        for current_state in states:
            directory = self._topic_directory(current_state, topic_id)
            if not directory.exists():
                continue
            for path in directory.glob("r*.json"):
                match = re.fullmatch(r"r([1-9][0-9]*)\.json", path.name)
                if match:
                    result.append(ArtifactRevision(topic_id, int(match.group(1)), current_state))
        return tuple(sorted(result, key=lambda item: (item.state, item.revision)))

    def _save(self, state: StoreState, artifact: TeachingArtifact, *, raw_reply: str | None) -> ArtifactRevision:
        if artifact.status != state:
            raise ValueError(f"artifact status {artifact.status!r} does not match {state!r}")
        if raw_reply is not None and not isinstance(raw_reply, str):
            raise TypeError("raw_reply must be text")
        revision = self._next_revision(state, artifact.topic_id)
        payload: dict[str, object] = {"artifact": artifact.to_dict()}
        if raw_reply is not None:
            payload["raw_reply"] = raw_reply
        self._write_stable_json(self._path(state, artifact.topic_id, revision), payload)
        return ArtifactRevision(artifact.topic_id, revision, state)

    def _next_revision(self, state: StoreState, topic_id: str) -> int:
        existing = self.list_revisions(topic_id, state)
        return (existing[-1].revision + 1) if existing else 1

    def _path(self, state: StoreState, topic_id: str, revision: int) -> Path:
        if state not in {"draft", "reviewed", "published"}:
            raise ValueError(f"unknown artifact state: {state!r}")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("revision must be a positive integer")
        self._validate_topic_id(topic_id)
        path = self._topic_directory(state, topic_id) / f"r{revision}.json"
        if self.root not in path.resolve().parents:
            raise ValueError("artifact path escapes store root")
        return path

    def _topic_directory(self, state: StoreState, topic_id: str) -> Path:
        chapter = topic_id.split(".", 1)[0]
        return self.root / f"{state}s" / chapter / topic_id

    @staticmethod
    def _validate_topic_id(topic_id: str) -> None:
        if not isinstance(topic_id, str) or not _TOPIC_ID.fullmatch(topic_id):
            raise ValueError(f"unsafe topic id: {topic_id!r}")

    @staticmethod
    def _write_stable_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


__all__ = ["ArtifactRevision", "StoredArtifact", "TeachingArtifactStore"]
