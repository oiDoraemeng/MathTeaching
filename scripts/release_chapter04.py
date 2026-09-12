"""Regenerate and validate the canonical Chapter 4 reviewed release bundle."""
from pathlib import Path
from linear_algebra.chapter_04_semantics import TOPIC_SEMANTICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_04


def main(data_root: Path | None = None):
    root=data_root or Path(__file__).resolve().parents[1]/"linear_algebra"/"teaching"/"data"
    payloads={topic:artifact_payload_for(topic) for topic in sorted(TOPIC_SEMANTICS)}
    resources=compile_chapter_04(output_root=root/"compiled",index_path=root/"index.json",reviewed_payloads=payloads,reviewed_root=root/"revieweds"/"ch04")
    print(f"released {len(resources)} reviewed and compiled Chapter 4 topics")


if __name__=="__main__":
    main()
