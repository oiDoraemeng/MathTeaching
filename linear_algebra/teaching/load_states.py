"""Atomic teaching-topic load phases and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Callable, ClassVar


class LoadPhase(str, Enum):
    IDLE = "idle"
    RESOLVING = "resolving"
    SOURCE_CHECKED = "source_checked"
    ARTIFACT_CHECKED = "artifact_checked"
    CONTRACT_CHECKED = "contract_checked"
    COMPILED = "compiled"
    PLAN_VALIDATED = "plan_validated"
    STAGED = "staged"
    COMMITTED = "committed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class LoadDiagnostic:
    code: str
    topic_id: str
    phase: LoadPhase
    field: str
    message: str


@dataclass(frozen=True)
class LoadSnapshot:
    topic_id: str
    phase: LoadPhase
    previous_revision: int | None
    diagnostic: LoadDiagnostic | None


def fingerprint(value: object) -> str:
    """Return a stable fingerprint for staged explanation metadata.

    The loader never fingerprints Qt objects.  Payloads are deliberately
    reduced to JSON-compatible values before this helper is called, so a
    failed topic selection can compare the old and new explanation without
    serialising renderer state or command objects.
    """

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class LoadTransaction:
    _ALLOWED: ClassVar[MappingProxyType] = MappingProxyType({
        LoadPhase.IDLE: frozenset({LoadPhase.RESOLVING}),
        LoadPhase.RESOLVING: frozenset({LoadPhase.SOURCE_CHECKED}),
        LoadPhase.SOURCE_CHECKED: frozenset({LoadPhase.ARTIFACT_CHECKED}),
        LoadPhase.ARTIFACT_CHECKED: frozenset({LoadPhase.CONTRACT_CHECKED}),
        LoadPhase.CONTRACT_CHECKED: frozenset({LoadPhase.COMPILED}),
        LoadPhase.COMPILED: frozenset({LoadPhase.PLAN_VALIDATED}),
        LoadPhase.PLAN_VALIDATED: frozenset({LoadPhase.STAGED}),
        LoadPhase.STAGED: frozenset({LoadPhase.COMMITTED}),
        LoadPhase.COMMITTED: frozenset(),
        LoadPhase.REJECTED: frozenset(),
    })
    _ERROR_CODES: ClassVar[frozenset[str]] = frozenset({
        "source_stale", "contract_missing_evidence", "unsupported_scene_family",
        "numeric_invalid", "layout_overflow", "plan_invalid", "renderer_unavailable",
        "bundle_mismatch", "missing_artifact", "missing_compiled", "missing_snapshot",
        "host_failure", "explanation_publish_failed",
    })

    def __init__(self, topic_id: str, *, previous_revision: int | None = None) -> None:
        if not isinstance(topic_id, str) or not topic_id:
            raise ValueError("topic_id must be non-empty")
        self.topic_id = topic_id
        self.previous_revision = previous_revision
        self.phase = LoadPhase.IDLE
        self.diagnostic: LoadDiagnostic | None = None
        self.bundle: Any | None = None
        self.plan: Any | None = None
        self.explanation: Any | None = None
        self.pane_id: str | None = None
        self.previous_scene_fingerprint: str | None = None
        self.previous_explanation_fingerprint: str | None = None
        self.explanation_fingerprint: str | None = None

    def advance(self, phase: LoadPhase, *, field: str = "", message: str = "") -> LoadPhase:
        phase = LoadPhase(phase)
        if self.phase is LoadPhase.REJECTED:
            raise ValueError("cannot advance a rejected transaction")
        if self.phase is LoadPhase.COMMITTED:
            raise ValueError("cannot advance a committed transaction")
        if phase not in self._ALLOWED[self.phase]:
            if phase is LoadPhase.COMMITTED:
                raise ValueError("committed phase requires staged")
            raise ValueError(f"invalid transition from {self.phase.value} to {phase.value}")
        self.phase = phase
        return self.phase

    def reject(self, code: str, phase: LoadPhase, field: str, message: str = "") -> LoadDiagnostic:
        if self.phase is LoadPhase.COMMITTED:
            raise ValueError("cannot reject a committed transaction")
        if self.phase is LoadPhase.REJECTED:
            raise ValueError("cannot reject a rejected transaction")
        phase = LoadPhase(phase)
        if phase is not self.phase:
            raise ValueError("rejection phase must match current transaction phase")
        if code not in self._ERROR_CODES:
            raise ValueError(f"unknown diagnostic code: {code}")
        diagnostic = LoadDiagnostic(code, self.topic_id, phase, field, message)
        self.diagnostic = diagnostic
        self.phase = LoadPhase.REJECTED
        return diagnostic

    def stage(
        self,
        *,
        bundle: Any,
        plan: Any,
        explanation: Any,
        pane_id: str | None = None,
        previous_scene_fingerprint: str | None = None,
        previous_explanation_fingerprint: str | None = None,
    ) -> None:
        """Attach both teaching surfaces after validation, before host commit."""

        if self.phase is not LoadPhase.PLAN_VALIDATED:
            raise ValueError("bundle can only be staged after plan validation")
        self.bundle = bundle
        self.plan = plan
        self.explanation = explanation
        self.pane_id = pane_id
        self.previous_scene_fingerprint = previous_scene_fingerprint
        self.previous_explanation_fingerprint = previous_explanation_fingerprint
        try:
            value = explanation.to_dict() if hasattr(explanation, "to_dict") else explanation
            self.explanation_fingerprint = fingerprint(value)
        except Exception:
            self.explanation_fingerprint = fingerprint(repr(explanation))
        self.advance(LoadPhase.STAGED)

    def commit_host(
        self,
        execute: Callable[..., Any],
        *,
        expected_scene_fingerprint: str | None = None,
        finalize: bool = True,
    ) -> Any | None:
        """Execute the already-staged scene through one host transaction.

        ``execute`` is normally ``SceneCommandService.execute``.  Keeping the
        callable at this boundary makes the state machine independent of Qt and
        lets tests inject failures without mutating explanation state first.
        """

        if self.phase is not LoadPhase.STAGED or self.plan is None:
            raise ValueError("host commit requires a staged bundle")
        try:
            result = execute(
                self.plan,
                pane_id=self.pane_id,
                expected_scene_fingerprint=expected_scene_fingerprint,
            )
        except Exception as error:
            # SceneCommandService owns the host rollback.  We only preserve a
            # structured diagnostic and leave the transaction rejected.
            self.reject("host_failure", LoadPhase.STAGED, "scene", str(error))
            raise
        if getattr(result, "valid", True) is not True:
            messages = tuple(getattr(result, "messages", ()))
            self.reject("host_failure", LoadPhase.STAGED, "scene", "；".join(str(item) for item in messages))
            return result
        if finalize:
            self.advance(LoadPhase.COMMITTED)
        return result

    def snapshot(self) -> LoadSnapshot:
        return LoadSnapshot(self.topic_id, self.phase, self.previous_revision, self.diagnostic)


__all__ = ["LoadPhase", "LoadDiagnostic", "LoadSnapshot", "LoadTransaction"]
