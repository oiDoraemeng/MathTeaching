from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "ui" / "agent_web"


def test_agent_web_dist_contains_local_manifest_and_assets() -> None:
    index = WEB_ROOT / "dist" / "index.html"
    manifest = WEB_ROOT / "dist" / "manifest.json"
    assert index.is_file()
    assert manifest.is_file()
    references = json.loads(manifest.read_text(encoding="utf-8"))
    assert references
    for value in references.values():
        for key in ("file", "src"):
            path = value.get(key) if isinstance(value, dict) else None
            if path:
                assert not path.startswith(("http:", "https:", "file:"))
                assert not Path(path).is_absolute()


def test_agent_web_declares_required_local_dependencies() -> None:
    package = json.loads((WEB_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    for name in ("react", "markdown-it", "dompurify", "katex", "lucide-react"):
        assert name in dependencies
