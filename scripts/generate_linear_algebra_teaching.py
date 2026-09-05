"""Generate lecture-grounded teaching drafts without publishing them."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.generation import GenerationRequest, generate_draft, topics_for_request
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate draft linear-algebra teaching artifacts")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--topic", metavar="TOPIC_ID")
    selection.add_argument("--chapter", type=int, choices=(1, 2, 3))
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--source", default=Path(".agents/线性代数讲义.md"), type=Path)
    return parser


def main(argv: Sequence[str] | None = None, *, agent: object | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if agent is None:
        parser.error("a configured ExplanationAgent is required for generation")

    entries = topics_for_request(topic_entries(), topic_id=args.topic, chapter=args.chapter)
    repository = LectureSourceRepository(args.source)
    store = TeachingArtifactStore(args.output_root)
    for entry in entries:
        request = GenerationRequest(
            context=repository.context_for(entry),
            topic=entry,
            profile=profile_for(entry.id),
        )
        draft = generate_draft(agent, request)  # type: ignore[arg-type]
        revision = store.save_draft(
            draft.artifact,
            raw_reply=draft.raw_reply,
        )
        print(
            f'{{"topic_id":"{entry.id}","status":"{draft.artifact.status}","revision":{revision.revision}}}'
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
