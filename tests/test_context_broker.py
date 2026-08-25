from __future__ import annotations

import os

import pytest

from agent.context_broker import AttachmentInput, ContextBroker
from agent.scene_snapshot import SceneSnapshot


def test_context_broker_keeps_recent_messages_and_summarizes_older() -> None:
    broker = ContextBroker(max_tokens=120, recent_message_count=2)
    messages = [f"message-{index} " + ("x" * 40) for index in range(5)]

    package = broker.build(
        scene_snapshot=SceneSnapshot(geometry=({"alias": "P"},)),
        selected_object={"alias": "P", "kind": "point"},
        messages=messages,
    )

    assert package.scene["scene_mode"] == "2d"
    assert package.recent_messages == tuple(messages[-2:])
    assert "message-0" in package.older_summary
    assert package.used_tokens > 0
    assert package.max_tokens == 120
    assert 0 < package.percentage <= 100


def test_context_broker_rejects_attachment_limits(tmp_path) -> None:
    broker = ContextBroker(attachments_root=tmp_path)
    files = []
    for index in range(6):
        path = tmp_path / f"file-{index}.txt"
        path.write_text("data", encoding="utf-8")
        files.append(AttachmentInput(path=path, mime_type="text/plain"))

    with pytest.raises(ValueError, match="five"):
        broker.store_attachments(files)


def test_context_broker_rejects_oversized_image(tmp_path) -> None:
    path = tmp_path / "large.png"
    with path.open("wb") as handle:
        handle.truncate(10 * 1024 * 1024 + 1)

    with pytest.raises(ValueError, match="10 MB"):
        ContextBroker(attachments_root=tmp_path / "stored").store_attachments(
            [AttachmentInput(path=path, mime_type="image/png")]
        )


def test_context_broker_copies_valid_text_attachment_and_hashes_it(tmp_path) -> None:
    source = tmp_path / "note.txt"
    source.write_text("determinant area", encoding="utf-8")
    root = tmp_path / "stored"

    records = ContextBroker(attachments_root=root).store_attachments(
        [AttachmentInput(path=source, mime_type="text/plain")]
    )

    assert records[0].relative_path.startswith("attachments/")
    assert records[0].sha256
    assert (root / records[0].relative_path).exists()
