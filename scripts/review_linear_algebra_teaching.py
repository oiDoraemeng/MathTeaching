"""Interactive review entry point for draft teaching artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from linear_algebra.teaching.store import TeachingArtifactStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review one teaching artifact draft")
    parser.add_argument("--store-root", required=True, type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", choices=("review", "reject"), required=True)
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="confirm that the reviewer inspected source, explanation, claims, checks, and visual semantics",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.interactive:
        parser.error("review requires an interactive confirmation")
    store = TeachingArtifactStore(args.store_root)
    if args.decision == "reject":
        print("rejected draft; no reviewed or published artifact was written")
        return 0
    revision = store.review_draft(args.topic, args.revision, args.reviewer)
    print(f"reviewed {revision.topic_id} revision {revision.revision}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
