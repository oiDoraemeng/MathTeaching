from __future__ import annotations

from agent.conversation import ConversationService
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore


def test_new_turn_after_restore_records_parent_turn(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    service = ConversationService(store)
    session = service.create_session()
    first = service.append_turn(session.id, "画一条曲线", "完成", SceneSnapshot(), SceneSnapshot(curves=({"alias": "f"},)), "completed")
    second = service.append_turn(session.id, "改成直线", "完成", SceneSnapshot(), SceneSnapshot(), "completed", parent_turn_id=first.id)

    assert second.parent_turn_id == first.id
    assert [turn.id for turn in service.timeline(session.id)] == [first.id, second.id]


def test_branch_from_turn_creates_independent_session(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    service = ConversationService(store)
    source = service.create_session("Original")
    turn = service.append_turn(source.id, "画点", "完成", SceneSnapshot(), SceneSnapshot(geometry=({"alias": "P"},)), "completed")

    branch = service.branch_from_turn(turn.id)

    assert branch.id != source.id
    assert branch.parent_session_id == source.id
    assert branch.current_snapshot == turn.scene_after
    assert service.get_session(source.id).title == "Original"


def test_restoring_turn_updates_current_pointer_without_deleting_history(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    service = ConversationService(store)
    session = service.create_session()
    turn = service.append_turn(session.id, "画点", "完成", SceneSnapshot(), SceneSnapshot(geometry=({"alias": "P"},)), "completed")

    restored = service.restore_turn(turn.id)

    assert restored == turn.scene_after
    assert len(service.timeline(session.id)) == 1
    assert store.get_session(session.id).current_turn_id == turn.id
