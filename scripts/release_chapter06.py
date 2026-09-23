"""Atomically publish the two reviewed Chapter 6 visual bundles."""
from pathlib import Path
from linear_algebra.catalog.chapter_06 import TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_06


def main(data_root=None):
    root = Path(data_root) if data_root is not None else Path(__file__).resolve().parents[1]/'linear_algebra'/'teaching'/'data'
    payloads = {topic.id: artifact_payload_for(topic.id) for topic in TOPICS}
    resources = compile_chapter_06(output_root=root/'compiled', reviewed_root=root/'revieweds'/'ch06', index_path=root/'index.json', reviewed_payloads=payloads)
    print(f'released {len(resources)} Chapter 6 reviewed and compiled resources')


if __name__ == '__main__':
    main()
