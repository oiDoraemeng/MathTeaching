from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_branch_uses_web_sidebar_without_legacy_panel_imports() -> None:
    runtime_sources = [
        ROOT / "ui" / "designer_window.py",
        ROOT / "ui" / "agent_sidebar.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in runtime_sources)
    assert "from ui.agent_panel" not in text
    assert "import ui.agent_panel" not in text
    assert "mathagent.web_ui_enabled" not in text
    assert "AgentSidebarWeb" in text
    assert not (ROOT / "ui" / "agent_panel.py").exists()


def test_legacy_panel_remains_on_backup_branch() -> None:
    import subprocess

    result = subprocess.run(
        ["git", "show", "math-qt:ui/agent_panel.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert "class AgentPanel" in result.stdout
