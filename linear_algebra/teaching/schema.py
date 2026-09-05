"""Loading helpers for the versioned teaching-artifact JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_SCHEMA_PATH = Path(__file__).with_name("artifact.schema.json")


def load_artifact_schema() -> dict[str, Any]:
    """Return a fresh copy of the bundled Draft 2020-12 artifact schema."""
    with ARTIFACT_SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    if not isinstance(schema, dict):
        raise ValueError("artifact schema root must be an object")
    return schema


__all__ = ["ARTIFACT_SCHEMA_PATH", "load_artifact_schema"]
