"""Conversation domain operations over the session repository."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .scene_snapshot import SceneSnapshot
from .session_store import SessionRecord, SessionStore, TurnRecord


@dataclass(frozen=True)
class ConversationBranch:
    session: SessionRecord
    source_turn_id: str
    current_snapshot: SceneSnapshot | None

    @property
    def id(self) -> str:
        return self.session.id

    @property
    def parent_session_id(self) -> str | None:
        return self.session.parent_session_id


class ConversationService:
    def __init__(self, store: SessionStore) -> None:
        self.store = store

    def create_session(self, title: str = "New Chat", *, model: str = "", active_mode: str = "Agent", execution_mode: str = "confirm") -> SessionRecord:
        return self.store.create_session(title, model=model, active_mode=active_mode, execution_mode=execution_mode)

    def get_session(self, session_id: str) -> SessionRecord:
        return self.store.get_session(session_id)

    def timeline(self, session_id: str) -> list[TurnRecord]:
        return self.store.list_turns(session_id)

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        scene_before: SceneSnapshot | Mapping[str, Any] | None,
        scene_after: SceneSnapshot | Mapping[str, Any] | None,
        status: str,
        *,
        command_plan: Mapping[str, Any] | None = None,
        parent_turn_id: str | None = None,
        branch_id: str | None = None,
    ) -> TurnRecord:
        turn_id = self.store.append_turn(
            session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            scene_before=scene_before,
            scene_after=scene_after,
            command_plan=command_plan,
            status=status,
            parent_turn_id=parent_turn_id,
            branch_id=branch_id,
        )
        return self.store.get_turn(turn_id)

    def restore_turn(self, turn_id: str) -> SceneSnapshot | None:
        turn = self.store.get_turn(turn_id)
        self.store.set_current_turn(turn.session_id, turn.id)
        return turn.scene_after

    def undo_turn(self, turn_id: str) -> SceneSnapshot | None:
        turn = self.store.get_turn(turn_id)
        return turn.scene_before

    def branch_from_turn(self, turn_id: str) -> ConversationBranch:
        turn = self.store.get_turn(turn_id)
        source = self.store.get_session(turn.session_id)
        branch = self.store.create_session(
            f"{source.title} · 分支",
            model=source.model,
            active_mode=source.active_mode,
            execution_mode=source.execution_mode,
            parent_session_id=source.id,
        )
        # Copy only the selected history prefix. The new session starts at the
        # selected snapshot and can diverge without mutating the source rows.
        for prior in self.store.list_turns(source.id):
            if prior.turn_index > turn.turn_index:
                break
            self.store.append_turn(
                branch.id,
                user_message=prior.user_message,
                assistant_message=prior.assistant_message,
                scene_before=prior.scene_before,
                scene_after=prior.scene_after,
                command_plan=prior.command_plan,
                validation=prior.validation,
                status=prior.execution_status,
                agent_mode=prior.agent_mode,
                execution_mode=prior.execution_mode,
                parent_turn_id=prior.parent_turn_id,
                branch_id=source.id,
                preview_path=prior.preview_path,
            )
        return ConversationBranch(self.store.get_session(branch.id), turn.id, turn.scene_after)
