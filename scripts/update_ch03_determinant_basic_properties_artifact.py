"""Regenerate, compile and activate only the Chapter 3 basic-properties topic."""

from __future__ import annotations

import update_ch03_determinant_core_artifacts as updater


if __name__ == "__main__":  # pragma: no cover - direct script invocation
    updater.TOPIC_IDS = ("ch03.det.basic-properties",)
    raise SystemExit(updater.main())
