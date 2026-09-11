"""Atomic teaching-topic load phases and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


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


class LoadTransaction:
    _ALLOWED: ClassVar[dict[LoadPhase, frozenset[LoadPhase]]] = {
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
    }
    _ERROR_CODES: ClassVar[frozenset[str]] = frozenset({
        "source_stale", "contract_missing_evidence", "unsupported_scene_family",
        "numeric_invalid", "layout_overflow", "plan_invalid", "renderer_unavailable",
    })

    def __init__(self, topic_id: str, *, previous_revision: int | None = None) -> None:
        if not isinstance(topic_id, str) or not topic_id:
            raise ValueError("topic_id must be non-empty")
        self.topic_id = topic_id
        self.previous_revision = previous_revision
        self.phase = LoadPhase.IDLE
        self.diagnostic: LoadDiagnostic | None = None

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
        if code not in self._ERROR_CODES:
            raise ValueError(f"unknown diagnostic code: {code}")
        diagnostic = LoadDiagnostic(code, self.topic_id, LoadPhase(phase), field, message)
        self.diagnostic = diagnostic
        self.phase = LoadPhase.REJECTED
        return diagnostic

    def snapshot(self) -> LoadSnapshot:
        return LoadSnapshot(self.topic_id, self.phase, self.previous_revision, self.diagnostic)


__all__ = ["LoadPhase", "LoadDiagnostic", "LoadSnapshot", "LoadTransaction"]
