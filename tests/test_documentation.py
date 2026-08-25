from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mathagent_web_workflow_documented() -> None:
    docs = "\n".join(
        [
            (ROOT / "docs" / "mathagent-web-sidebar.md").read_text(encoding="utf-8"),
        ]
    )

    for required in (
        "pnpm install --frozen-lockfile",
        "pnpm build",
        "mathagent://app/",
        "QWebChannel",
        "JSON bridge",
        ".math",
        "math-qt",
    ):
        assert required in docs

    forbidden = (
        "can execute arbitrary Python",
        "execute arbitrary Python",
        "run arbitrary Python",
        "允许执行任意 Python",
        "允许终端执行",
    )
    assert not any(term in docs for term in forbidden)
