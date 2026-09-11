"""Versioned, filesystem-backed storage for normalized teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Literal
from collections.abc import Mapping

from .model import ArtifactStatus, TeachingArtifact
from .validation import (
    ArtifactValidationError,
    ValidationIssue,
    validate_artifact_payload,
    validate_claim_bindings,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)


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


@dataclass(frozen=True)
class LoadedArtifact:
    artifact: TeachingArtifact
    stale: bool
    diagnostic: tuple[str, str, str] | None = None


@dataclass(frozen=True)
class RawReplyAudit:
    """Audit record kept outside the runtime artifact payload."""

    reply_digest: str
    raw_reply: str | None
    error_code: str | None
    message: str
    topic_id: str = ""
    revision: int | None = None


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    revision: ArtifactRevision | None = None
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class ReviewRecord:
    topic_id: str
    revision: int
    reviewer: str
    decision: str
    timestamp: str


def reply_digest(raw_reply: str) -> str:
    return "sha256:" + hashlib.sha256(raw_reply.encode("utf-8")).hexdigest()


def artifact_digest(artifact: TeachingArtifact) -> str:
    """Hash the semantic artifact without circular generation metadata."""

    payload = artifact.to_dict()
    generated = payload.get("generated")
    if isinstance(generated, dict):
        generated = dict(generated)
        generated["artifact_digest"] = ""
        generated["raw_reply_digest"] = ""
        payload["generated"] = generated
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class TeachingArtifactStore:
    """Persist drafts and review states under one configured root directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def index_payload(self) -> dict[str, object]:
        """Read the chapter index, preserving the legacy empty-store shape."""
        path = self.root / "index.json"
        if not path.is_file():
            return {"schema_version": 1, "topics": []}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("topics", []), list):
            raise ValueError("index payload must contain a topics array")
        return payload

    def publish_chapter(self, chapter: int, revisions: Mapping[str, int]) -> dict[str, object]:
        """Atomically replace index entries for one chapter after full validation."""
        if isinstance(chapter, bool) or not isinstance(chapter, int) or chapter < 1:
            raise ValueError("chapter must be a positive integer")
        if not isinstance(revisions, Mapping):
            raise TypeError("revisions must be a mapping")
        entries: list[dict[str, object]] = []
        for topic_id, revision in revisions.items():
            self._validate_topic_id(topic_id)
            if topic_id.split(".", 1)[0] != f"ch{chapter:02d}":
                raise ValueError(f"topic {topic_id!r} does not belong to chapter {chapter}")
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise ValueError(f"invalid revision for {topic_id!r}")
            try:
                stored = self.get(topic_id, revision, "published")
            except FileNotFoundError as error:
                raise ValueError(str(error)) from error
            artifact = stored.artifact
            if artifact.status != "published" or artifact.revision != revision:
                raise ValueError(f"published revision mismatch for {topic_id!r}")
            entries.append({"topic_id": topic_id, "published_revision": revision, "source_hash": artifact.source.source_hash})
        payload = self.index_payload()
        old_topics = [item for item in payload.get("topics", []) if isinstance(item, dict)]
        prefix = f"ch{chapter:02d}."
        payload["topics"] = [item for item in old_topics if not str(item.get("topic_id", "")).startswith(prefix)] + entries
        self._write_stable_json(self.root / "index.json", payload)
        return payload

    def unpublish_chapter(self, chapter: int) -> dict[str, object]:
        if isinstance(chapter, bool) or not isinstance(chapter, int) or chapter < 1:
            raise ValueError("chapter must be a positive integer")
        payload = self.index_payload()
        prefix = f"ch{chapter:02d}."
        payload["topics"] = [item for item in payload.get("topics", []) if not (isinstance(item, dict) and str(item.get("topic_id", "")).startswith(prefix))]
        self._write_stable_json(self.root / "index.json", payload)
        return payload

    def save_draft(self, artifact: TeachingArtifact, *, raw_reply: str) -> ArtifactRevision:
        return self._save("draft", artifact, raw_reply=raw_reply)

    def save_reviewed(self, artifact: TeachingArtifact, *, raw_reply: str) -> ArtifactRevision:
        return self._save("reviewed", artifact, raw_reply=raw_reply)

    def save_published(self, artifact: TeachingArtifact, *, raw_reply: str | None = None) -> ArtifactRevision:
        return self._save("published", artifact, raw_reply=raw_reply)

    def get(self, topic_id: str, revision: int, state: StoreState) -> StoredArtifact:
        path = self._path(state, topic_id, revision)
        if state == "published" and not path.is_file():
            flat_path = self._flat_published_path(topic_id)
            if flat_path.is_file():
                path = flat_path
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

    def load_published(self, topic_id: str, *, current_context: object) -> LoadedArtifact | None:
        stored = self.published(topic_id)
        if stored is None:
            return None
        current_hash = getattr(current_context, "source_hash", None)
        if not isinstance(current_hash, str):
            raise TypeError("current_context must provide source_hash")
        old_hash = stored.artifact.source.source_hash
        stale = old_hash != current_hash
        diagnostic = ("stale_source", old_hash, current_hash) if stale else None
        return LoadedArtifact(artifact=stored.artifact, stale=stale, diagnostic=diagnostic)

    def get_published_payload(self, revision: ArtifactRevision) -> dict[str, object]:
        if revision.state != "published":
            raise ValueError("published payload requires a published revision")
        return self.get(revision.topic_id, revision.revision, "published").artifact.to_dict()

    def audit_raw_reply(self, revision: ArtifactRevision) -> RawReplyAudit:
        path = self._audit_path(revision.topic_id, revision.revision)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"missing raw reply audit for {revision.topic_id!r} revision {revision.revision}") from error
        return _audit_from_payload(payload)

    def save_rejection(self, *, topic_id: str, raw_reply: str, code: str, message: str) -> RawReplyAudit:
        self._validate_topic_id(topic_id)
        if not isinstance(raw_reply, str) or not isinstance(code, str) or not isinstance(message, str):
            raise TypeError("rejection audit fields must be text")
        audit = RawReplyAudit(
            reply_digest=reply_digest(raw_reply),
            raw_reply=None,
            error_code=code,
            message=message[:512],
            topic_id=topic_id,
        )
        directory = self.root / "audit" / "rejections" / topic_id.split(".", 1)[0] / topic_id
        existing = sorted(directory.glob("r*.json")) if directory.exists() else []
        next_revision = 1
        if existing:
            numbers = [int(match.group(1)) for path in existing if (match := re.fullmatch(r"r([1-9][0-9]*)\.json", path.name))]
            next_revision = max(numbers, default=0) + 1
        self._write_stable_json(directory / f"r{next_revision}.json", _audit_to_payload(audit))
        return audit

    def review_draft(self, topic_id: str, revision: int, reviewer: str) -> ArtifactRevision:
        """Copy one draft into reviewed state after an explicit reviewer action."""

        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("reviewer must be non-empty")
        stored = self.get(topic_id, revision, "draft")
        reviewed = self.save_reviewed(stored.artifact, raw_reply=stored.raw_reply or "")
        self._write_review_record(
            ReviewRecord(
                topic_id=topic_id,
                revision=reviewed.revision,
                reviewer=reviewer,
                decision="review",
                timestamp=_utc_timestamp(),
            )
        )
        return reviewed

    def publish(
        self,
        artifact: TeachingArtifact,
        *,
        source_context: object,
        topic: object,
        raw_reply: str | None = None,
    ) -> PublishResult:
        """Validate and atomically add a published revision."""

        if artifact.status != "reviewed":
            return PublishResult(
                ok=False,
                issues=(
                    ValidationIssue(
                        "review_required",
                        "$.status",
                        "publish requires an explicitly reviewed revision",
                    ),
                ),
            )
        try:
            validate_artifact_payload(artifact.to_dict())
        except ArtifactValidationError as error:
            return PublishResult(ok=False, issues=error.issues)
        issues = (
            *validate_source_evidence(artifact, source_context, topic),  # type: ignore[arg-type]
            *validate_teaching_depth(artifact),
            *validate_worked_examples(artifact),
            *validate_claim_bindings(artifact),
        )
        if issues:
            return PublishResult(ok=False, issues=tuple(sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message))))
        published = replace(artifact, status="published")
        revision = self.save_published(published, raw_reply=raw_reply)
        return PublishResult(ok=True, revision=revision)

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
            if current_state == "published":
                flat_path = self._flat_published_path(topic_id)
                if flat_path.is_file():
                    try:
                        payload = json.loads(flat_path.read_text(encoding="utf-8"))
                        artifact_payload = payload.get("artifact", payload) if isinstance(payload, dict) else {}
                        revision = artifact_payload.get("revision", 1) if isinstance(artifact_payload, dict) else 1
                        if isinstance(revision, int) and revision >= 1:
                            result.append(ArtifactRevision(topic_id, revision, current_state))
                    except (OSError, ValueError, TypeError, json.JSONDecodeError):
                        pass
        return tuple(sorted(result, key=lambda item: (item.state, item.revision)))

    def _save(self, state: StoreState, artifact: TeachingArtifact, *, raw_reply: str | None) -> ArtifactRevision:
        if raw_reply is not None and not isinstance(raw_reply, str):
            raise TypeError("raw_reply must be text")
        normalized = replace(artifact, status=state)
        revision = self._next_revision(state, normalized.topic_id)
        # The on-disk revision is the artifact revision exposed to readers.
        # Keeping these values identical prevents rN files from masquerading as r1.
        normalized = replace(normalized, revision=revision)
        receipt = normalized.generated
        if raw_reply is not None and (
            receipt.raw_reply_digest == "sha256:pending"
            or state in {"reviewed", "published"}
        ):
            receipt = replace(receipt, raw_reply_digest=reply_digest(raw_reply))
        if receipt.artifact_digest == "sha256:pending" or receipt is not normalized.generated or revision != artifact.revision:
            normalized = replace(normalized, generated=replace(receipt, artifact_digest=artifact_digest(normalized)))
        payload: dict[str, object] = {"artifact": normalized.to_dict()}
        if state == "draft" and raw_reply is not None:
            payload["raw_reply"] = raw_reply
        self._write_stable_json(self._path(state, normalized.topic_id, revision), payload)
        if raw_reply is not None and state in {"reviewed", "published"}:
            self._write_stable_json(
                self._audit_path(normalized.topic_id, revision),
                _audit_to_payload(
                    RawReplyAudit(
                        reply_digest=reply_digest(raw_reply),
                        raw_reply=raw_reply,
                        error_code=None,
                        message="accepted",
                        topic_id=normalized.topic_id,
                        revision=revision,
                    )
                ),
            )
        return ArtifactRevision(normalized.topic_id, revision, state)

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
        # ``published`` is already a natural collection name.  Keep the
        # historical plural directories for drafts/reviews for compatibility,
        # while avoiding the accidental ``publisheds`` path that made runtime
        # audits unable to discover released artifacts.
        directory_name = "published" if state == "published" else f"{state}s"
        return self.root / directory_name / chapter / topic_id

    def _flat_published_path(self, topic_id: str) -> Path:
        """Return the plan-compatible flat published resource path."""

        self._validate_topic_id(topic_id)
        chapter = topic_id.split(".", 1)[0]
        return self.root / "published" / chapter / f"{topic_id}.json"

    def _audit_path(self, topic_id: str, revision: int) -> Path:
        self._validate_topic_id(topic_id)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("revision must be a positive integer")
        return self.root / "audit" / topic_id.split(".", 1)[0] / topic_id / f"r{revision}.json"

    def _write_review_record(self, record: ReviewRecord) -> None:
        path = self.root / "audit" / "reviews" / record.topic_id.split(".", 1)[0] / record.topic_id / f"r{record.revision}.json"
        self._write_stable_json(path, {
            "topic_id": record.topic_id,
            "revision": record.revision,
            "reviewer": record.reviewer,
            "decision": record.decision,
            "timestamp": record.timestamp,
        })

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


__all__ = [
    "ArtifactRevision",
    "LoadedArtifact",
    "PublishResult",
    "RawReplyAudit",
    "ReviewRecord",
    "StoredArtifact",
    "TeachingArtifactStore",
    "artifact_digest",
    "reply_digest",
]


def _audit_to_payload(audit: RawReplyAudit) -> dict[str, object]:
    return {
        "reply_digest": audit.reply_digest,
        "raw_reply": audit.raw_reply,
        "error_code": audit.error_code,
        "message": audit.message,
        "topic_id": audit.topic_id,
        "revision": audit.revision,
    }


def _audit_from_payload(payload: object) -> RawReplyAudit:
    if not isinstance(payload, dict):
        raise ValueError("audit payload must be an object")
    return RawReplyAudit(
        reply_digest=str(payload.get("reply_digest", "")),
        raw_reply=payload.get("raw_reply") if isinstance(payload.get("raw_reply"), str) else None,
        error_code=payload.get("error_code") if isinstance(payload.get("error_code"), str) else None,
        message=str(payload.get("message", "")),
        topic_id=str(payload.get("topic_id", "")),
        revision=payload.get("revision") if isinstance(payload.get("revision"), int) else None,
    )


def _utc_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
