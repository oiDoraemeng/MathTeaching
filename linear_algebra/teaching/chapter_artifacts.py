"""Deterministic, unpublished artifact fixtures for chapters 4--8."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.content_validation import lecture_source_repository
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.chapter_04_semantics import semantic_for


_TOPICS = {topic.id: topic for topic in topic_entries() if 4 <= topic.chapter_number <= 8}


def _json_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _topic_entities(topic_id: str, roles: tuple[str, ...], ids: Mapping[str, str], claim_id: str) -> list[dict[str, object]]:
    semantic = semantic_for(topic_id) if topic_id.startswith("ch04.") else None
    values = {
        "origin": [0.0, 0.0], "line": [1.0, 0.0], "plane": [1.0, 1.0], "whole_space": [0.0, 1.0],
        "affine_counterexample": [0.0, 1.0], "subspace_u": [1.0, 0.0], "subspace_v": [0.0, 1.0],
        "intersection": [0.0, 0.0], "union_counterexample": [1.0, 1.0], "domain": [1.0, 0.0],
        "codomain": [1.0, 0.0], "kernel": [0.0, 1.0], "column_space": [1.0, 0.0], "span_1d": [1.0, 0.0],
        "span_2d": [0.0, 1.0], "span_3d": [1.0, 1.0], "dependent_set": [2.0, 2.0],
        "independent_set": [0.0, 1.0], "zero_combination": [0.0, 0.0], "columns": [1.0, 0.0],
        "null_vector": [1.0, -1.0], "trivial_nullspace": [0.0, 0.0], "rank_two": [1.0, 1.0],
        "rank_one": [1.0, 0.0], "rank_zero": [0.0, 0.0], "independent_basis": [1.0, 0.0],
        "spanning_set": [0.0, 1.0], "too_few": [1.0, 0.0], "too_many": [1.0, 1.0], "point": [0.0, 0.0],
        "volume": [1.0, 1.0], "standard_basis": [1.0, 0.0], "oblique_basis": [1.0, 1.0], "same_vector": [2.0, 1.0],
        "map_T": [1.0, 2.0], "sum_test": [1.0, 1.0], "homogeneity_test": [2.0, 0.0], "origin": [0.0, 0.0],
        "linear_case": [1.0, 1.0], "translation": [1.0, 2.0], "square_map": [1.0, 1.0], "constant_shift": [2.0, 2.0],
        "standard_e1": [1.0, 0.0], "standard_e2": [0.0, 1.0], "column_1": [2.0, 0.0], "column_2": [0.0, 3.0],
        "kernel_direction": [0.0, 1.0], "zero": [0.0, 0.0], "image": [1.0, 0.0], "rank": [2.0, 0.0],
        "nullity": [0.0, 1.0], "preserved": [1.0, 1.0], "collapsed": [0.0, 0.0],
    }
    special = semantic.primitive if semantic and semantic.primitive in {"matrix", "basis", "region", "subspace"} else "vector"
    result = []
    for index, role in enumerate(roles):
        kind = special if index >= 2 and special in {"matrix", "basis", "region", "subspace"} else "vector"
        value = [[1.0, 0.0], [0.0, 1.0]] if kind == "matrix" else values.get(role, [1.0, 0.0])
        result.append({"id": ids[role], "kind": kind, "dimension": 2, "value": value, "role": role, "label": role, "claim_refs": [claim_id]})
    return result


def _topic_relation(topic_id: str, semantic: object, ids: Mapping[str, str], relation_id: str, claim_id: str) -> dict[str, object]:
    relation = getattr(semantic, "relation", "maps_to")
    roles = getattr(semantic, "roles", ("vector_a", "transformed_a"))[:2]
    params: dict[str, object] = {}
    if topic_id == "ch04.subspace.col-null": params.update({"matrix": [[1, 0], [0, 0]], "domain_dimension": 2, "codomain_dimension": 2})
    if topic_id in {"ch04.nullspace.test", "ch04.rank.collapse", "ch04.rank-nullity"}: params.update({"matrix": [[1, 0], [0, 0]], "rank": 1, "nullity": 1})
    if topic_id == "ch04.coordinates.readout": params.update({"basis_matrix": [[1, 1], [0, 1]], "standard_coordinates": [2, 1], "oblique_coordinates": [1, 1]})
    if topic_id == "ch04.linear-map.definition": params.update({"matrix": [[1, 1], [0, 1]], "origin_fixed": 1.0, "additivity": 1.0, "homogeneity": 1.0})
    return {"id": relation_id, "kind": relation, "source_ref": ids[roles[0]], "target_ref": ids[roles[1] if len(roles) > 1 else roles[0]], "parameters": params, "claim_refs": [claim_id]}


def _chapter4_visual_payload(topic_id: str, claim_id: str) -> tuple[dict[str, object], list[str], list[str], list[str]]:
    """Materialize the closed chapter-4 descriptor without role-name guesses."""
    semantic = semantic_for(topic_id)
    entity_ids = {item.role: f"entity.{topic_id}.{item.role}" for item in semantic.entities}
    relation_ids = {item.name: f"relation.{topic_id}.{item.name}" for item in semantic.relations}
    stage_ids = {item.name: f"stage.{topic_id}.{item.name}" for item in semantic.stages}
    entities = [
        {
            "id": entity_ids[item.role], "kind": item.kind, "dimension": item.dimension,
            "value": _json_value(item.value), "role": item.role, "label": item.label, "claim_refs": [claim_id],
        }
        for item in semantic.entities
    ]
    relations = [
        {
            "id": relation_ids[item.name], "kind": item.kind,
            "source_ref": entity_ids[item.source_role], "target_ref": entity_ids[item.target_role],
            "parameters": {name: _json_value(value) for name, value in item.parameters}, "claim_refs": [claim_id],
        }
        for item in semantic.relations
    ]
    stages = [
        {
            "id": stage_ids[item.name], "title": item.title, "caption": semantic.formula,
            "layout": item.layout,
            "input_entity_refs": [entity_ids[role] for role in item.input_roles],
            "output_entity_refs": [entity_ids[role] for role in item.output_roles],
            "relation_refs": [relation_ids[name] for name in item.relation_names],
            "expected_invariants": list(item.invariants),
        }
        for item in semantic.stages
    ]
    visual = {
        "scene_kind": semantic.scene_kind, "scene_family": semantic.family,
        "entities": entities, "relations": relations, "stages": stages,
    }
    return visual, list(entity_ids.values()), list(relation_ids.values()), list(stage_ids.values())


def artifact_payload_for(topic_id: str, *, status: str = "reviewed") -> dict[str, object]:
    """Return one deterministic, closed artifact payload without publishing it."""
    topic = _TOPICS.get(topic_id)
    if topic is None:
        raise KeyError(f"unknown chapter 4-8 topic: {topic_id}")
    context = lecture_source_repository().context_for(topic)
    span = context.spans[0]
    claim_id = f"claim.{topic_id}"
    semantic = semantic_for(topic_id) if topic_id.startswith("ch04.") else None
    semantic_roles = semantic.roles if semantic else ("vector_a", "transformed_a")
    entity_ids = {role: f"entity.{topic_id}.{role}" for role in semantic_roles}
    relation_id = f"relation.{topic_id}.{semantic.relation if semantic else 'maps_to'}"
    stage_id = f"stage.{topic_id}.evidence"
    if semantic is not None:
        chapter4_visual, claim_entity_refs, claim_relation_refs, claim_stage_refs = _chapter4_visual_payload(topic_id, claim_id)
    else:
        chapter4_visual = None
        claim_entity_refs = list(entity_ids.values())
        claim_relation_refs = [relation_id]
        claim_stage_refs = [stage_id]
    source_span = {
        "id": span.id, "heading_path": list(span.heading_path), "start_line": span.start_line,
        "end_line": span.end_line, "fingerprint": span.fingerprint, "text": span.text,
    }
    profile = profile_for(topic_id)
    semantic = semantic_for(topic_id) if topic_id.startswith("ch04.") else None
    formula_by_topic = {
        "ch04.space.closure": r"u=(1,0),\ v=(0,1),\ u+v=(1,1),\ 2u=(2,0)",
        "ch04.subspace.col-null": r"A=\operatorname{diag}(1,0),\ A(1,0)=(1,0),\ A(0,1)=0",
        "ch04.dependence.redundancy": r"2u-v=0\quad (u=(1,1),\ v=(2,2))",
        "ch04.nullspace.test": r"A(1,-1,0)^T=0,\quad Ax=0",
        "ch04.rank-nullity": r"\operatorname{rank}(T)+\operatorname{nullity}(T)=\dim V=3",
    }
    formula = semantic.formula if semantic is not None else formula_by_topic.get(topic_id, f"{topic.title}: finite typed semantic evidence")
    claim = {
        "id": claim_id, "statement": f"{topic.title} 的数学主张由显式对象、关系和不变量支持。",
        "formula": formula, "formula_symbols": list(semantic_roles[:2]), "source_refs": [span.id],
        "explanation_refs": ["definition", "formula", "derivation", "worked_examples", "geometric_meaning", "pitfalls", "connections"],
        "entity_refs": claim_entity_refs, "relation_refs": claim_relation_refs, "stage_refs": claim_stage_refs,
    }
    payload = {
        "schema_version": 1, "topic_id": topic_id, "revision": 1, "status": status,
        "source": {"source_path": list(context.source_path), "heading_path": list(context.heading_path),
                    "heading_level": context.heading_level, "occurrence": context.occurrence,
                    "excerpt": context.excerpt, "source_hash": context.source_hash,
                    "spans": [source_span], "neighboring_titles": list(context.neighboring_titles)},
        "teaching_profile": {"minimum_level": int(profile.minimum_level), "required_sections": list(profile.required_sections),
                             "requires_analogy_boundary": profile.requires_analogy_boundary},
        "claims": [claim], "connections": [{"id": f"connection.{topic_id}.prior", "target_topic_id": "ch03.det.ad-bc",
            "relation": "prerequisite", "description": "前置的线性表示与几何关系。", "claim_refs": [claim_id]}],
        "explanation": {"title": topic.title, "summary": f"{topic.title} 的确定性数学语义 artifact。",
            "sections": [{"id": section, "title": section, "text": f"{section}: {topic.title}。", "claim_refs": [claim_id]}
                        for section in profile.required_sections],
            "symbol_roles": {role: role for role in semantic_roles}, "definition": f"{topic.title} 的对象和定义。",
            "formula": formula, "derivation": ["代入 v=(1,2)。", "计算得到 result=(2,4)。"],
            "worked_examples": [{"id": f"example.{topic_id}", "title": "主题数值例",
                "kind": semantic.example_kind if semantic is not None else "scalar_multiple",
                "given": _json_value(semantic.example_given) if semantic is not None else [2, [1, 2]],
                "calculation": [formula],
                "result": _json_value(semantic.example_result) if semantic is not None else [2, 4],
                "checks": [{"name": "result", "expected": _json_value(semantic.example_result) if semantic is not None else [2, 4], "tolerance": 1e-9}], "claim_refs": [claim_id]}],
            "geometric_meaning": "向量在有限维空间中的方向和尺度保持可读。", "conclusion": "数值关系与讲义定义一致。",
            "pitfalls": ["不要混淆对象和坐标。"],
            "invariants": list(semantic.invariants) if semantic is not None else ["finite numeric result"],
            "connections": ["与前置线性表示相连。"], "analogy_boundary": "二维示意推广到有限维时保留代数关系。",
            "transfer_note": "先识别对象，再核对公式和不变量。", "read_guide": ["先定义，再公式，最后读数值例。"],
            "searchable_text": [topic.title, "线性空间", "数值例"]},
        "visual_semantics": chapter4_visual if chapter4_visual is not None else {"scene_kind": "2d", "scene_family": "subspace_region",
            "entities": _topic_entities(topic_id, semantic_roles, entity_ids, claim_id),
            "relations": [_topic_relation(topic_id, semantic, entity_ids, relation_id, claim_id)],
            "stages": [{"id": stage_id, "title": "主题证据", "caption": formula, "layout": "sequence",
                        "input_entity_refs": list(entity_ids.values()), "output_entity_refs": list(entity_ids.values()), "relation_refs": [relation_id], "expected_invariants": ["finite numeric result", *list(semantic.invariants if semantic else ())]}]},
        "generated": {"provider": "deterministic-fixture", "model": "fixture", "prompt_version": "chapter-4-8-v1",
                      "generated_at": "2026-09-12T00:00:00Z", "source_hash": context.source_hash,
                      "raw_reply_digest": "", "artifact_digest": ""},
    }
    _refresh_digests(payload)
    return payload


def _canonical(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _refresh_digests(payload: dict[str, object]) -> None:
    generated = payload["generated"]
    assert isinstance(generated, dict)
    generated["raw_reply_digest"] = "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    generated["artifact_digest"] = ""
    generated["artifact_digest"] = "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def reviewed_artifact_payloads() -> Mapping[str, dict[str, object]]:
    return {topic_id: artifact_payload_for(topic_id) for topic_id in sorted(_TOPICS)}


def load_reviewed_artifacts(root: str | Path | None = None) -> Mapping[str, dict[str, object]]:
    base = Path(root) if root is not None else Path(__file__).with_name("data") / "revieweds"
    result: dict[str, dict[str, object]] = {}
    for topic_id in sorted(_TOPICS):
        # Chapter-4 review payloads are generated from the closed semantic
        # descriptor.  Keeping this in-memory path avoids silently compiling
        # stale pre-family JSON while the publication bundle is regenerated by
        # the release task; chapters 5--8 retain their materialized resources.
        if root is None and topic_id.startswith("ch04."):
            result[topic_id] = artifact_payload_for(topic_id)
            continue
        path = base / topic_id.split(".", 1)[0] / topic_id / "r1.json"
        if path.is_file():
            result[topic_id] = json.loads(path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"missing reviewed artifact resource: {path}")
    return result


def load_draft_artifacts(root: str | Path | None = None) -> Mapping[str, dict[str, object]]:
    base = Path(root) if root is not None else Path(__file__).with_name("data") / "drafts"
    result: dict[str, dict[str, object]] = {}
    for topic_id in sorted(_TOPICS):
        path = base / topic_id.split(".", 1)[0] / topic_id / "r1.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing draft artifact resource: {path}")
        result[topic_id] = json.loads(path.read_text(encoding="utf-8"))
    return result


__all__ = ["artifact_payload_for", "load_draft_artifacts", "load_reviewed_artifacts", "reviewed_artifact_payloads"]
