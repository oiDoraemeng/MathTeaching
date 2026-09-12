from __future__ import annotations
from pathlib import Path
from linear_algebra.catalog.chapter_07 import TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_07


def main() -> int:
    payloads = {topic.id: artifact_payload_for(topic.id) for topic in TOPICS}
    resources = compile_chapter_07(reviewed_payloads=payloads)
    print(f'released {len(resources)} Chapter 7 reviewed and compiled resources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
