"""Regenerate and validate the canonical Chapter 4 reviewed release bundle."""
from pathlib import Path
from linear_algebra.chapter_04_semantics import TOPIC_SEMANTICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.validation import validate_artifact_payload
from linear_algebra.teaching.compile_resources import _atomic_write_json, compile_chapter_04
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


def main():
    root=Path(__file__).resolve().parents[1]/"linear_algebra"/"teaching"/"data"/"revieweds"/"ch04"
    payloads={topic:artifact_payload_for(topic) for topic in sorted(TOPIC_SEMANTICS)}
    for payload in payloads.values():
        VisualSemanticsCompiler().compile(validate_artifact_payload(payload))
    for topic,payload in payloads.items():
        _atomic_write_json(root/topic/"r1.json",payload)
    resources=compile_chapter_04()
    print(f"released {len(resources)} reviewed and compiled Chapter 4 topics")


if __name__=="__main__":
    main()
