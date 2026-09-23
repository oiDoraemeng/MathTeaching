"""Regenerate, compile and activate the Chapter 2 matrix-powers artifact."""

from __future__ import annotations

import update_ch02_additive_distributivity_artifact as updater


if __name__ == "__main__":  # pragma: no cover - direct script invocation
    updater.TOPIC_ID = "ch02.matrix.powers"
    raise SystemExit(updater.main())
