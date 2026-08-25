from __future__ import annotations

from agent.context_broker import AttachmentInput, ContextBroker
from agent.session_store import SessionStore
from agent.ui_projection import build_session_snapshot


def test_web_preferences_attachments_and_closed_history_project_per_session(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    first = store.create_session("One")
    second = store.create_session("Two")
    store.set_session_preferences(first.id, active_mode="Ask", execution_mode="continuous", model="DeepSeek")
    store.set_session_preferences(second.id, active_mode="Plan", execution_mode="confirm", model="Local")
    source = tmp_path / "lesson.txt"
    source.write_text("determinant area", encoding="utf-8")
    attachment = ContextBroker(attachments_root=store.math_root).store_attachments(
        (AttachmentInput(source, "text/plain"),)
    )[0]
    store.add_attachment(first.id, turn_id=None, relative_path=attachment.relative_path, mime_type=attachment.mime_type, byte_size=attachment.byte_size, sha256=attachment.sha256)
    store.close_session(second.id)

    snapshot = build_session_snapshot(store, active_session_id=first.id)
    by_id = {session["id"]: session for session in snapshot["sessions"]}
    assert by_id[first.id]["mode"] == "Ask"
    assert by_id[first.id]["executionMode"] == "continuous"
    assert by_id[first.id]["attachments"][0]["sha256"] == attachment.sha256
    assert by_id[second.id]["closed"] is True
