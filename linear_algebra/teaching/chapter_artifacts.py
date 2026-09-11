"""Deterministic, unpublished artifact fixtures for chapters 4--8."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.content_validation import lecture_source_repository
from linear_algebra.teaching.profiles import profile_for


_TOPICS = {topic.id: topic for topic in topic_entries() if 4 <= topic.chapter_number <= 8}


def artifact_payload_for(topic_id: str, *, status: str = "reviewed") -> dict[str, object]:
    """Return one deterministic, closed artifact payload without publishing it."""
    topic = _TOPICS.get(topic_id)
    if topic is None:
        raise KeyError(f"unknown chapter 4-8 topic: {topic_id}")
    context = lecture_source_repository().context_for(topic)
    span = context.spans[0]
    claim_id = f"claim.{topic_id}"
    entity_id = f"entity.{topic_id}.v"
    result_id = f"entity.{topic_id}.result"
    relation_id = f"relation.{topic_id}.maps"
    stage_id = f"stage.{topic_id}.input"
    source_span = {
        "id": span.id, "heading_path": list(span.heading_path), "start_line": span.start_line,
        "end_line": span.end_line, "fingerprint": span.fingerprint, "text": span.text,
    }
    profile = profile_for(topic_id)
    formula = r"v=(1,2),\quad 2v=(2,4)"
    claim = {
        "id": claim_id, "statement": f"{topic.title} 的线性表示保持可检验的向量关系。",
        "formula": formula, "formula_symbols": ["v", "result"], "source_refs": [span.id],
        "explanation_refs": ["definition", "formula", "derivation", "worked_examples", "geometric_meaning", "pitfalls", "connections"],
        "entity_refs": [entity_id, result_id], "relation_refs": [relation_id], "stage_refs": [stage_id],
    }
    return {
        "schema_version": 1, "topic_id": topic_id, "revision": 1, "status": status,
        "source": {"source_path": list(context.source_path), "heading_path": list(context.heading_path),
                    "heading_level": context.heading_level, "occurrence": context.occurrence,
                    "excerpt": context.excerpt, "source_hash": context.source_hash,
                    "spans": [source_span], "neighboring_titles": list(context.neighboring_titles)},
        "teaching_profile": {"minimum_level": int(profile.minimum_level), "required_sections": list(profile.required_sections),
                             "requires_analogy_boundary": profile.requires_analogy_boundary},
        "claims": [claim], "connections": [{"id": f"connection.{topic_id}.prior", "target_topic_id": "ch03.det.ad-bc",
            "relation": "prerequisite", "description": "前置的线性表示与几何关系。", "claim_refs": [claim_id]}],
        "explanation": {"title": topic.title, "summary": f"{topic.title} 的确定性讲义 artifact。",
            "sections": [{"id": section, "title": section, "text": f"{section}: {topic.title}。", "claim_refs": [claim_id]}
                        for section in profile.required_sections],
            "symbol_roles": {"v": "vector_a", "result": "transformed_a"}, "definition": f"{topic.title} 的对象和定义。",
            "formula": formula, "derivation": ["代入 v=(1,2)。", "计算得到 result=(2,4)。"],
            "worked_examples": [{"id": f"example.{topic_id}", "title": "数值例", "kind": "scalar_multiple",
                "given": [2, [1, 2]], "calculation": ["2*(1,2)=(2,4)"], "result": [2, 4],
                "checks": [{"name": "result", "expected": [2, 4], "tolerance": 1e-9}], "claim_refs": [claim_id]}],
            "geometric_meaning": "向量在有限维空间中的方向和尺度保持可读。", "conclusion": "数值关系与讲义定义一致。",
            "pitfalls": ["不要混淆对象和坐标。"], "invariants": ["finite numeric result"],
            "connections": ["与前置线性表示相连。"], "analogy_boundary": "二维示意推广到有限维时保留代数关系。",
            "transfer_note": "先识别对象，再核对公式和不变量。", "read_guide": ["先定义，再公式，最后读数值例。"],
            "searchable_text": [topic.title, "线性空间", "数值例"]},
        "visual_semantics": {"scene_kind": "2d", "scene_family": "subspace_region",
            "entities": [{"id": entity_id, "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_a", "label": "v", "claim_refs": [claim_id]},
                         {"id": result_id, "kind": "vector", "dimension": 2, "value": [2, 4], "role": "transformed_a", "label": "result", "claim_refs": [claim_id]}],
            "relations": [{"id": relation_id, "kind": "maps_to", "source_ref": entity_id, "target_ref": result_id, "parameters": {"scalar": 2}, "claim_refs": [claim_id]}],
            "stages": [{"id": stage_id, "title": "输入与结果", "caption": "显示线性关系。", "layout": "sequence",
                        "input_entity_refs": [entity_id], "output_entity_refs": [result_id], "relation_refs": [relation_id], "expected_invariants": ["finite numeric result"]}]},
        "generated": {"provider": "deterministic-fixture", "model": "fixture", "prompt_version": "chapter-4-8-v1",
                      "generated_at": "2026-09-12T00:00:00Z", "source_hash": context.source_hash,
                      "raw_reply_digest": "sha256:fixture", "artifact_digest": "sha256:fixture"},
    }


def reviewed_artifact_payloads() -> Mapping[str, dict[str, object]]:
    return {topic_id: artifact_payload_for(topic_id) for topic_id in sorted(_TOPICS)}


def load_reviewed_artifacts(root: str | Path | None = None) -> Mapping[str, dict[str, object]]:
    base = Path(root) if root is not None else Path(__file__).with_name("data") / "revieweds"
    result: dict[str, dict[str, object]] = {}
    for topic_id in sorted(_TOPICS):
        path = base / topic_id.split(".", 1)[0] / topic_id / "r1.json"
        if path.is_file():
            result[topic_id] = json.loads(path.read_text(encoding="utf-8"))
        else:
            result[topic_id] = artifact_payload_for(topic_id)
    return result


__all__ = ["artifact_payload_for", "load_reviewed_artifacts", "reviewed_artifact_payloads"]
