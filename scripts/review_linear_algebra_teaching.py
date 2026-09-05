"""Interactive review entry point for draft teaching artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review one teaching artifact draft")
    parser.add_argument("--store-root", required=True, type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--topic")
    selection.add_argument("--chapter", type=int, choices=(1, 2, 3))
    parser.add_argument("--revision", type=int)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", choices=("review", "reject"), required=True)
    parser.add_argument("--publish", action="store_true", help="publish each reviewed revision after validation")
    parser.add_argument("--source", default=Path(".agents/线性代数讲义.md"), type=Path)
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
    if args.topic is not None:
        if args.revision is None:
            parser.error("--revision is required with --topic")
        topics = (args.topic,)
        revisions = {args.topic: args.revision}
    else:
        topics = tuple(topic.id for topic in topic_entries() if topic.chapter_number == args.chapter)
        revisions = {
            topic_id: store.list_revisions(topic_id, "draft")[-1].revision
            for topic_id in topics
            if store.list_revisions(topic_id, "draft")
        }
    source_repo = LectureSourceRepository(args.source)
    published = 0
    reviewed = 0
    errors: list[str] = []
    catalog_by_id = {topic.id: topic for topic in topic_entries()}
    for topic_id in topics:
        revision_number = revisions.get(topic_id)
        if revision_number is None:
            errors.append(f"{topic_id}: missing draft")
            continue
        try:
            reviewed_revision = store.review_draft(topic_id, revision_number, args.reviewer)
            reviewed += 1
            if args.publish:
                topic = catalog_by_id[topic_id]
                context = source_repo.context_for(topic)
                reviewed_artifact = store.get(topic_id, reviewed_revision.revision, "reviewed")
                result = store.publish(
                    reviewed_artifact.artifact,
                    source_context=context,
                    topic=topic,
                    raw_reply=reviewed_artifact.raw_reply,
                )
                if not result.ok:
                    errors.extend(f"{topic_id}: {issue.code} {issue.path}: {issue.message}" for issue in result.issues)
                else:
                    published += 1
        except (FileNotFoundError, KeyError, OSError, ValueError) as error:
            errors.append(f"{topic_id}: {error}")
    if args.chapter is not None:
        print(f"chapter={args.chapter} topics={len(topics)} reviewed={reviewed} published={published} errors={len(errors)}")
    else:
        print(f"reviewed {args.topic} revision {revisions[args.topic]}")
        if args.publish:
            print(f"published {args.topic}")
    if errors:
        for error in errors:
            print(error)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
