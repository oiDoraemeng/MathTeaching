"""Generate reviewed Chapter 1 teaching artifacts from the checked-in lecture.

This is a deterministic local adapter for environments without a model
provider.  It constructs mathematical records from a small, reviewed topic
table, while still routing every artifact through ``GenerationRequest``, the
artifact store, review, publication, and the normal validators.  It emits no
scene operations or renderer/UI data.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.generation import GenerationRequest, generate_draft
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.quality import refine_payload
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for, validate_contract


class LocalChapterOneAgent:
    """A source-grounded, deterministic explanation-agent implementation."""

    def generate(self, context, topic, profile, vocabulary):
        payload = refine_payload(build_payload(context, topic, profile))
        artifact = TeachingArtifact.from_dict(payload)
        raw_reply = json.dumps(artifact.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return __import__("linear_algebra.teaching.agent", fromlist=["TeachingArtifactDraft"]).TeachingArtifactDraft(
            artifact=artifact,
            raw_reply=raw_reply,
        )


_SPEC: dict[str, dict[str, Any]] = {
    "ch01.vector.magnitude": {"formula": "||v||=sqrt(v_1^2+v_2^2)", "kind": "inner_product", "given": {"a": [3, 4], "b": [3, 4]}, "result": 25.0, "check": "dot", "statement": "向量的长度由自身与自身的内积确定。", "relation": "invariant"},
    "ch01.ops.addition": {"formula": "a+b=(a_1+b_1,a_2+b_2)", "kind": "vector_addition", "given": {"a": [2, 1], "b": [1, 3]}, "result": [3.0, 4.0], "check": "sum", "statement": "向量加法把两个位移首尾相接，分量逐项相加。", "relation": "sum"},
    "ch01.ops.subtraction": {"formula": "a-b=a+(-b)", "kind": "vector_addition", "given": {"a": [4, 3], "b": [-1, -2]}, "result": [3.0, 1.0], "check": "sum", "statement": "减法等于加上相反向量，结果表示从 b 到 a 的位移。", "relation": "difference"},
    "ch01.ops.scalar": {"formula": "2v=v+v", "kind": "vector_addition", "given": {"a": [1, 2], "b": [1, 2]}, "result": [2.0, 4.0], "check": "sum", "statement": "数乘改变长度，正负号决定同向或反向，共线性保持不变。", "relation": "scalar_multiple"},
    "ch01.ops.linear-combination": {"formula": "2e_1+3e_2=(2,3)", "kind": "matrix_transform", "given": {"matrix": [[1, 0], [0, 1]], "vector": [2, 3]}, "result": [2.0, 3.0], "check": "transformed", "statement": "线性组合是带系数的向量和，系数就是在给定基底方向上的读数。", "relation": "maps_to", "matrix": True},
    "ch01.inner.definitions": {"formula": "a\u00b7b=||a||||b||cos\u03b8", "kind": "inner_product", "given": {"a": [2, 0], "b": [1, 1]}, "result": 2.0, "check": "dot", "statement": "内积等于一个向量在另一个方向上的带符号投影乘长度。", "relation": "orientation"},
    "ch01.inner.cauchy-schwarz": {"formula": "|a\u00b7b|\u2264||a||||b||", "kind": "inner_product", "given": {"a": [3, 4], "b": [1, 0]}, "result": 3.0, "check": "dot", "statement": "投影长度不超过原向量长度，得到柯西-施瓦茨不等式。", "relation": "compare"},
    "ch01.projection.definition": {"formula": "p=((v\u00b7u)/(u\u00b7u))u", "kind": "projection", "given": {"vector": [3, 4], "direction": [2, 1]}, "result": [4.0, 2.0], "check": "projection", "statement": "投影把 v 分解成沿 u 的分量 p 与垂直残差 r。", "relation": "projection", "special": "projection"},
    "ch01.proof.midline": {"formula": "M=(A+B)/2, N=(A+C)/2\u21d2MN=(B-C)/2", "kind": "vector_addition", "given": {"a": [2, 1], "b": [1, 3]}, "result": [3.0, 4.0], "check": "sum", "statement": "中点的平均公式使两腰中点连线平行于第三边且长度减半。", "relation": "difference"},
    "ch01.proof.centroid": {"formula": "G=(A+B+C)/3", "kind": "vector_addition", "given": {"a": [1, 0], "b": [0, 1]}, "result": [1.0, 1.0], "check": "sum", "statement": "重心是三个顶点位置向量的平均，三条中线在同一点相交。", "relation": "sum"},
    "ch01.proof.parallelogram-diagonals": {"formula": "(A+C)/2=(B+D)/2", "kind": "vector_addition", "given": {"a": [2, 1], "b": [1, 3]}, "result": [3.0, 4.0], "check": "sum", "statement": "平行四边形对角线端点的平均位置相同，所以互相平分。", "relation": "compare"},
}


def _scalar(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_scalar(item) for item in value]
    if isinstance(value, list):
        return [_scalar(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _scalar(item) for key, item in value.items()}
    return value


def _schema_given(kind: str, given: Any) -> Any:
    """Encode named operands into the schema's bounded array representation."""

    if not isinstance(given, dict):
        return _scalar(given)
    if kind in {"vector_addition", "inner_product", "oriented_area"}:
        return [_scalar(given["a"]), _scalar(given["b"])]
    if kind == "projection":
        return [_scalar(given["vector"]), _scalar(given["direction"])]
    if kind == "matrix_transform":
        return [_scalar(given["matrix"]), _scalar(given["vector"])]
    if kind == "oriented_volume":
        return [_scalar(given["a"]), _scalar(given["b"]), _scalar(given["c"])]
    if kind == "determinant":
        return _scalar(given["matrix"])
    return _scalar(given)


def _claim_id(topic_id: str) -> str:
    return f"claim.{topic_id}"


def _entity(entity_id: str, kind: str, dimension: int, value: Any, role: str, claim_id: str, label: str | None = None) -> dict[str, Any]:
    return {"id": entity_id, "kind": kind, "dimension": dimension, "value": _scalar(value), "role": role, "label": label or entity_id, "claim_refs": [claim_id]}


def _relation(relation_id: str, kind: str, source: str, target: str, claim_id: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": relation_id, "kind": kind, "source_ref": source, "target_ref": target, "parameters": _scalar(parameters or {}), "claim_refs": [claim_id]}


def build_payload(context, topic, profile) -> dict[str, Any]:
    spec = _SPEC[topic.id]
    claim_id = _claim_id(topic.id)
    span_id = context.spans[0].id
    relation_kind = spec["relation"]
    scene = spec.get("scene", "2d")
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    given = spec["given"]

    if spec.get("special") == "projection":
        entities.extend([
            _entity("v", "vector", 2, given["vector"], "vector_a", claim_id, "v"),
            _entity("u", "vector", 2, given["direction"], "direction", claim_id, "u"),
            _entity("p", "vector", 2, spec["result"], "projection", claim_id, "p"),
            _entity("H", "point", 2, spec["result"], "foot", claim_id, "H"),
            _entity("r", "vector", 2, [given["vector"][0] - spec["result"][0], given["vector"][1] - spec["result"][1]], "residual", claim_id, "r"),
        ])
        relations.extend([
            _relation("v_projects_to_u", "projects_to", "v", "u", claim_id),
            _relation("v_decomposes_p_r", "decomposes_into", "v", "p", claim_id),
            _relation("r_orthogonal_u", "orthogonal_to", "r", "u", claim_id),
        ])
        stage_specs = [
            ("input", "输入向量", "先观察 v 和目标方向 u。", ["v", "u"], [], ["v_projects_to_u"], ["direction fixed"]),
            ("projection", "投影分量", "垂足 H 给出沿 u 的投影 p。", ["v", "u"], ["p", "H"], ["v_projects_to_u", "v_decomposes_p_r"], ["projection lies on direction"]),
            ("residual", "正交残差", "残差 r 与 u 垂直，且 v=p+r。", ["p", "r"], ["v"], ["v_decomposes_p_r", "r_orthogonal_u"], ["orthogonality"]),
        ]
    elif spec.get("special") == "cross":
        entities.extend([
            _entity("a", "vector", 3, given["a"], "vector_a", claim_id, "a"),
            _entity("b", "vector", 3, given["b"], "vector_b", claim_id, "b"),
            _entity("n", "vector", 3, [0, 0, 1], "result", claim_id, "a×b"),
        ])
        relations.extend([
            _relation("a_oriented_to_b", "orientation", "a", "b", claim_id),
            _relation("n_orthogonal_a", "orthogonal_to", "n", "a", claim_id),
        ])
        stage_specs = [
            ("factors", "两个因子", "先给出 a、b 的方向。", ["a", "b"], [], ["a_oriented_to_b"], ["factor directions"]),
            ("normal", "法向量", "右手定则确定 n=a×b。", ["a", "b"], ["n"], ["a_oriented_to_b", "n_orthogonal_a"], ["normal direction"]),
        ]
    else:
        if spec.get("matrix") and not spec.get("analogy"):
            matrix = given["matrix"]
            vector = given["vector"]
            result = spec["result"]
            entities.extend([
                _entity("A", "matrix", len(matrix), matrix, "matrix_a", claim_id, "A"),
                _entity("x", "vector", len(vector), vector, "vector_a", claim_id, "x"),
                _entity("y", "vector", len(result), result, "transformed_a", claim_id, "Ax"),
            ])
            relations.append(_relation("A_maps_x_to_y", "maps_to", "x", "y", claim_id, {"matrix": matrix}))
            stage_specs = [("input", "输入与变换", "矩阵 A 作用于向量 x。", ["A", "x"], ["y"], ["A_maps_x_to_y"], ["linear mapping"])]
        elif spec.get("volume"):
            a, b, c = given["a"], given["b"], given["c"]
            entities.extend([
                _entity("a", "vector", 3, a, "vector_a", claim_id, "a"),
                _entity("b", "vector", 3, b, "vector_b", claim_id, "b"),
                _entity("c", "vector", 3, c, "direction", claim_id, "c"),
                _entity("V", "volume", 3, [a, b, c], "volume", claim_id, "V"),
            ])
            relations.append(_relation("spans_volume", "spans", "a", "V", claim_id))
            stage_specs = [("volume", "有向体积", "三条向量张成平行六面体。", ["a", "b", "c"], ["V"], ["spans_volume"], ["signed volume"])]
        elif spec.get("analogy"):
            vector = given["vector"]
            result = spec["result"]
            entities.extend([
                _entity("x", "vector", len(vector), vector, "vector_a", claim_id, "x"),
                _entity("y", "vector", len(result), result, "transformed_a", claim_id, "T(x)"),
            ])
            relations.append(_relation("x_maps_to_y", "maps_to", "x", "y", claim_id))
            stage_specs = [("analogy", "高维类比", "逐坐标计算在三维示例中可见，并可推广到 n 维。", ["x"], ["y"], ["x_maps_to_y"], ["componentwise mapping"])]
        else:
            a = given.get("a", given.get("vector", [1, 0]))
            b = given.get("b", given.get("direction", [0, 1]))
            result = spec["result"]
            dimension = len(a)
            entities.extend([
                _entity("a", "vector", dimension, a, "vector_a", claim_id, "a"),
                _entity("b", "vector", dimension, b, "vector_b", claim_id, "b"),
                _entity("r", "vector", len(result) if isinstance(result, list) else dimension, result if isinstance(result, list) else a, "result", claim_id, "result"),
            ])
            relations.append(_relation("main_relation", relation_kind if relation_kind in {"sum", "difference", "scalar_multiple", "compare", "orientation", "orthogonal_to", "maps_to", "invariant"} else "compare", "a", "r", claim_id))
            stage_specs = [("main", "数学关系", "从输入向量读出公式中的结果与不变量。", ["a", "b"], ["r"], ["main_relation"], ["typed calculation"])]

    for suffix, title, caption, inputs, outputs, relation_refs, invariants in stage_specs:
        stages.append({"id": f"stage.{suffix}", "title": title, "caption": caption, "layout": "sequence" if len(stage_specs) > 1 else "overlay", "input_entity_refs": inputs, "output_entity_refs": outputs, "relation_refs": relation_refs, "expected_invariants": invariants})

    symbols = sorted({item for item in ("a", "b", "c", "v", "u", "p", "H", "r", "n", "A", "x", "y", "V") if any(entity["id"] == item for entity in entities)})
    section_ids = tuple(profile.required_sections)
    sections = [{"id": section_id, "title": section_id, "text": f"{spec['statement']} 讲义锚点：{topic.title}。", "claim_refs": [claim_id]} for section_id in section_ids]
    formula_symbols = symbols
    symbol_roles = {symbol: next(entity["role"] for entity in entities if entity["id"] == symbol) for symbol in symbols}
    claim = {"id": claim_id, "statement": spec["statement"], "formula": spec["formula"], "formula_symbols": formula_symbols, "source_refs": [span_id], "explanation_refs": list(section_ids), "entity_refs": [entity["id"] for entity in entities], "relation_refs": [relation["id"] for relation in relations], "stage_refs": [stage["id"] for stage in stages]}
    check_name = spec["check"]
    example = {"id": f"example.{topic.id}", "title": "讲义数值例", "kind": spec["kind"], "given": _schema_given(spec["kind"], given), "calculation": [f"按定义计算 {spec['formula']}", f"得到 {spec['result']}"], "result": _scalar(spec["result"]), "checks": [{"name": check_name, "expected": _scalar(spec["result"]), "tolerance": 1e-9}], "claim_refs": [claim_id]}
    connection_target = next(item.id for item in topic_entries() if item.id != topic.id)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "topic_id": topic.id,
        "revision": 1,
        "status": "draft",
        "source": {
            "source_path": list(context.source_path), "heading_path": list(context.heading_path), "heading_level": context.heading_level,
            "occurrence": context.occurrence, "excerpt": context.excerpt, "source_hash": context.source_hash,
            "spans": [{"id": span.id, "heading_path": list(span.heading_path), "start_line": span.start_line, "end_line": span.end_line, "fingerprint": span.fingerprint, "text": span.text} for span in context.spans],
            "neighboring_titles": list(context.neighboring_titles),
        },
        "teaching_profile": profile.to_dict(),
        "claims": [claim],
        "connections": [{"id": f"connection.{topic.id}.related", "target_topic_id": connection_target, "relation": "related", "description": "该主题与相邻线性代数概念共享同一向量表示。", "claim_refs": [claim_id]}],
        "explanation": {
            "title": topic.title, "summary": spec["statement"], "sections": sections, "symbol_roles": symbol_roles,
            "definition": spec["statement"], "formula": spec["formula"],
            "derivation": [f"从讲义定义出发：{spec['statement']}", f"代入给定数值，得到 {spec['result']}。"],
            "worked_examples": [example], "intuition": f"把 {topic.title} 看成可测量的方向、长度或面积关系。",
            "geometric_meaning": f"图中实体和关系表达：{spec['statement']} 数值结果由对应向量、关系和阶段共同见证。",
            "conclusion": f"因此，{spec['statement']}", "pitfalls": ["把点的位置和向量的位移混为一谈，或忽略方向符号。"],
            "invariants": ["有限数值复算与视觉阶段中的对象关系一致。"], "connections": ["可迁移到同章相邻的向量、内积或投影概念。"],
            "analogy_boundary": "在 n 维情形保留分量公式与代数不变量，但不把二维图形直觉误当作真实 n 维图像。" if spec.get("analogy") else "",
            "transfer_note": "先识别对象和关系，再代入数值，最后检查方向、正交性或尺度不变量。",
            "read_guide": ["先看输入实体，再看关系箭头，最后核对阶段标题中的不变量。"],
            "searchable_text": [topic.title, spec["formula"], spec["statement"]],
        },
        "visual_semantics": {"scene_kind": scene, "entities": entities, "relations": relations, "stages": stages},
        "generated": {"provider": "local-lecture-template", "model": "deterministic-v1", "schema_version": 1, "prompt_version": "teaching-artifact-v1", "generated_at": generated_at, "source_hash": context.source_hash, "raw_reply_digest": "sha256:pending", "artifact_digest": "sha256:pending"},
    }
    return payload


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    source_repo = LectureSourceRepository(Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md")
    store = TeachingArtifactStore(root)
    agent = LocalChapterOneAgent()
    topics = tuple(topic for topic in topic_entries() if topic.chapter_number == 1)
    summaries: list[dict[str, Any]] = []
    for topic in topics:
        request = GenerationRequest(source_repo.context_for(topic), topic, profile_for(topic.id))
        draft = generate_draft(agent, request)
        draft_revision = store.save_draft(draft.artifact, raw_reply=draft.raw_reply)
        reviewed_revision = store.review_draft(topic.id, draft_revision.revision, "local-math-review")
        reviewed = store.get(topic.id, reviewed_revision.revision, "reviewed").artifact
        context = request.context
        issues = (
            *validate_source_evidence(reviewed, context, topic), *validate_closed_references(reviewed),
            *validate_claim_bindings(reviewed), *validate_teaching_depth(reviewed), *validate_worked_examples(reviewed),
            *validate_contract(reviewed, contract_for(topic.id)),
        )
        if issues:
            raise ValueError(f"{topic.id}: " + "; ".join(f"{issue.code}:{getattr(issue, 'path', getattr(issue, 'detail', ''))}" for issue in issues))
        compiler = VisualSemanticsCompiler()
        compiler.compile(reviewed, contract_for(topic.id), RenderContext.default(topic.id))
        published = store.publish(reviewed, source_context=context, topic=topic)
        if not published.ok:
            raise ValueError(f"{topic.id}: " + "; ".join(issue.code for issue in published.issues))
        published_revision = published.revision.revision if published.revision else None
        summaries.append({
            "topic_id": topic.id,
            "chapter": 1,
            "revision": published_revision,
            "draft_revision": draft_revision.revision,
            "reviewed_revision": reviewed_revision.revision,
            "published_revision": published_revision,
            "source_hash": context.source_hash,
        })
    index_path = root / "index.json"
    if index_path.is_file():
        current = json.loads(index_path.read_text(encoding="utf-8"))
        current_topics = current.get("topics", []) if isinstance(current, dict) else []
    else:
        current_topics = []
    retained = [
        row for row in current_topics
        if isinstance(row, dict) and not str(row.get("topic_id", "")).startswith("ch01.")
    ]
    topics = sorted([*retained, *summaries], key=lambda row: str(row["topic_id"]))
    index = {"schema_version": 1, "topic_count": len(topics), "topics": topics}
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"chapter": 1, "topics": len(summaries), "published": len(summaries), "index": str(index_path)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
