from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "ui" / "agent_web"


def test_committed_web_manifest_contains_only_local_dist_files() -> None:
    manifest_path = WEB_ROOT / "dist" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dist_root = manifest_path.parent.resolve()
    assert manifest
    for entry in manifest.values():
        for key in ("file", "src"):
            value = entry.get(key) if isinstance(entry, dict) else None
            if value:
                path = (dist_root / value).resolve()
                assert path.is_relative_to(dist_root)


def test_build_script_uses_frozen_pnpm_lockfile() -> None:
    script = (ROOT / "scripts" / "build_agent_web.ps1").read_text(encoding="utf-8")
    assert "pnpm install --frozen-lockfile" in script
    assert "pnpm build" in script
