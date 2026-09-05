"""Normalize stored artifact revision fields to their revision filenames."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.teaching.store import artifact_digest


def normalize(root: Path) -> int:
    changed = 0
    for state in ("drafts", "revieweds", "published"):
        for path in sorted((root / state).glob("ch*/*/r*.json")):
            match = re.fullmatch(r"r([1-9][0-9]*)\.json", path.name)
            if match is None:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact = payload.get("artifact")
            if not isinstance(artifact, dict):
                continue
            revision = int(match.group(1))
            if artifact.get("revision") == revision:
                continue
            artifact["revision"] = revision
            generated = artifact.get("generated")
            if isinstance(generated, dict):
                generated["artifact_digest"] = ""
                artifact["generated"] = generated
                artifact["generated"]["artifact_digest"] = artifact_digest_from_payload(artifact)
            path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
            changed += 1
    return changed


def artifact_digest_from_payload(payload: dict[str, object]) -> str:
    from linear_algebra.teaching.model import TeachingArtifact

    return artifact_digest(TeachingArtifact.from_dict(payload))


if __name__ == "__main__":
    data_root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    print(f"normalized={normalize(data_root)}")
