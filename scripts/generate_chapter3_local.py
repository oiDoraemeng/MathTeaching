"""Generate lecture-grounded Chapter 3 teaching artifacts.

The adapter is intentionally local and deterministic for environments without
an external explanation provider.  It stores only mathematical explanations,
typed worked examples, and closed visual semantics; renderer commands and UI
data are outside this boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.chapter_03 import TOPICS
from linear_algebra.teaching.generation import GenerationRequest, generate_draft
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
from linear_algebra.visualizations.contracts import contract_for, validate_contract

import generate_chapter1_local as chapter1


_SPEC = {
    "ch03.det.oriented-area": {"formula": "det(A)=ad-bc", "kind": "oriented_area", "given": {"a": [2, 1], "b": [1, 3]}, "result": 5.0, "check": "area", "statement": "行列式等于以矩阵两列为邻边的平行四边形的有向面积；单位正方形因此变成面积 5 的平行四边形。", "relation": "same_measure"},
    "ch03.det.basic-properties": {"formula": "det(A')=\\pm k\\,det(A)", "kind": "determinant", "given": {"matrix": [[3, 4], [1, 2]]}, "result": 2.0, "check": "determinant", "statement": "交换、数乘和行叠分别改变有向面积的方向、比例或形状。", "relation": "same_measure"},
    "ch03.det.multiplicativity": {"formula": "det(AB)=det(A)det(B)", "kind": "determinant", "given": {"matrix": [[2, 0], [0, 3]]}, "result": 6.0, "check": "determinant", "statement": "复合变换的面积倍率等于两个阶段倍率的乘积。", "relation": "same_measure", "multiplicativity": True},
    "ch03.det.transpose": {"formula": "det(A^T)=det(A)", "kind": "determinant", "given": {"matrix": [[2, 2], [1, 3]]}, "result": 4.0, "check": "determinant", "statement": "矩阵转置后，有向面积的数值保持不变。", "relation": "same_measure"},
    "ch03.cramer.area-ratio": {"formula": "x_i=det(A_i)/det(A)", "kind": "oriented_area", "given": {"a": [2, 1], "b": [1, 3]}, "result": 5.0, "check": "area", "statement": "克拉默法则把未知量表示为替换一列后的有向面积与原面积之比。", "relation": "same_measure"},
    "ch03.inverse.undo": {"formula": "AA^{-1}=I", "kind": "matrix_transform", "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 2]}, "result": [2.0, 2.0], "check": "transformed", "statement": "逆矩阵撤销原变换；行列式非零时每个输出都能沿唯一轨迹追溯到输入。", "relation": "composition_order", "inverse": True, "matrix": True},
    "ch03.adjugate.matrix": {"formula": "A adj(A)=det(A)I", "kind": "matrix_transform", "given": {"matrix": [[1, 0], [0, 1]], "vector": [1, 1]}, "result": [1.0, 1.0], "check": "transformed", "statement": "伴随矩阵满足 A adj(A)=det(A)I。", "relation": "invariant", "matrix": True},
    "ch03.det.zero.equivalence": {"formula": "det(A)=0⇔rank(A)<n", "kind": "determinant", "given": {"matrix": [[1, 2], [2, 4]]}, "result": 0.0, "check": "determinant", "statement": "det=0、列线性相关、秩下降和存在非零零空间是同一压扁现象的等价描述。", "relation": "collapses_to"},
}


class LocalChapterThreeAgent:
    def generate(self, context, topic, profile, vocabulary):
        chapter1._SPEC = _SPEC
        payload = refine_payload(chapter1.build_payload(context, topic, profile))
        if topic_required_capabilities(topic.id) and topic.id not in {"ch03.det.basic-properties", "ch03.det.multiplicativity", "ch03.det.transpose"}:
            _normalize_visual(payload, topic.id)
        from linear_algebra.teaching.model import TeachingArtifact
        from linear_algebra.teaching.agent import TeachingArtifactDraft

        artifact = TeachingArtifact.from_dict(payload)
        raw_reply = json.dumps(artifact.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return TeachingArtifactDraft(artifact=artifact, raw_reply=raw_reply)


def _entity(entity_id, kind, dimension, value, role, claim_id, label=None):
    return {"id": entity_id, "kind": kind, "dimension": dimension, "value": value, "role": role, "label": label or entity_id, "claim_refs": [claim_id]}


def _relation(relation_id, kind, source, target, claim_id, parameters=None):
    return {"id": relation_id, "kind": kind, "source_ref": source, "target_ref": target, "parameters": parameters or {}, "claim_refs": [claim_id]}


def _stage(stage_id, title, caption, inputs, outputs, relations, invariant, layout="sequence"):
    return {"id": stage_id, "title": title, "caption": caption, "layout": layout, "input_entity_refs": inputs, "output_entity_refs": outputs, "relation_refs": relations, "expected_invariants": [invariant]}


def _normalize_visual(payload: dict, topic_id: str) -> None:
    """Make determinant/area/volume graphs match their mathematical objects."""

    spec = _SPEC[topic_id]
    claim = payload["claims"][0]
    claim_id = claim["id"]
    visual = payload["visual_semantics"]
    entities = visual["entities"]
    relations = visual["relations"]
    stages = visual["stages"]

    if spec["kind"] == "oriented_area":
        a, b = spec["given"]["a"], spec["given"]["b"]
        area = _entity("area", "area", 2, [a, b], "area", claim_id, "oriented area")
        # 质量适配器可能已经给出面积实体（并与单位正方形对照一起发布），
        # 这里按 id 去重后再补，避免同一 id 出现两次。
        entities[:] = [item for item in entities if item["id"] not in {"r", "area"}]
        entities.append(area)
        for relation in relations:
            if relation["target_ref"] == "r":
                relation["target_ref"] = "area"
        for stage in stages:
            stage["input_entity_refs"] = ["area" if ref == "r" else ref for ref in stage["input_entity_refs"]]
            stage["output_entity_refs"] = ["area" if ref == "r" else ref for ref in stage["output_entity_refs"]]
        claim["entity_refs"] = [item["id"] for item in entities]
        claim["formula_symbols"] = ["a", "b", "area"]
        payload["explanation"]["symbol_roles"] = {"a": "vector_a", "b": "vector_b", "area": "area"}
        if relations:
            relations[0]["kind"] = spec["relation"] if spec["relation"] in {"same_measure", "invariant", "orientation"} else "same_measure"
        claim["relation_refs"] = [item["id"] for item in relations]

    elif spec["kind"] == "determinant":
        matrix = spec["given"]["matrix"]
        columns = [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]]
        # 同时保留矩阵和两列向量，供面积图元及讲解使用。
        entities[:] = [
            _entity("A", "matrix", 2, matrix, "matrix_a", claim_id, "A"),
            _entity("a", "vector", 2, columns[0], "vector_a", claim_id, "column a"),
            _entity("b", "vector", 2, columns[1], "vector_b", claim_id, "column b"),
            _entity("area", "area", 2, columns, "area", claim_id, "det(A)"),
        ]
        relations[:] = [_relation("det_maps_to_area", "maps_to", "A", "area", claim_id, {"matrix": matrix})]
        claim["entity_refs"] = ["A", "a", "b", "area"]
        claim["relation_refs"] = ["det_maps_to_area"]
        claim["formula_symbols"] = ["A", "a", "b", "area"]
        payload["explanation"]["symbol_roles"] = {"A": "matrix_a", "a": "vector_a", "b": "vector_b", "area": "area"}
        stages[:] = [
            _stage("stage.det.input", "矩阵两列", "把矩阵两列看作平行四边形的两条邻边。", ["A", "a", "b"], [], [], "columns as sides"),
            _stage("stage.det.measure", "有向面积", "行列式给出有向面积及方向符号。", ["a", "b"], ["area"], ["det_maps_to_area"], "signed area"),
        ]
        claim["stage_refs"] = [item["id"] for item in stages]

        # 类型化矩阵列表由编译器生成有界的分阶段变换。
        if "staged_transform" in topic_required_capabilities(topic_id):
            relations.append(_relation("det_stage", "composition_order", "a", "b", claim_id, {"matrix": matrix}))
            stages.append(_stage("stage.det.transform", "变换阶段", "比较变换前后的两条列向量，观察有向面积如何变化。", ["a", "b"], ["area"], ["det_stage"], "staged transform"))
            claim["relation_refs"].append("det_stage")
            claim["stage_refs"] = [item["id"] for item in stages]

        if topic_id == "ch03.det.zero.equivalence":
            entities.append(_entity("region", "region", 2, columns, "result", claim_id, "collapsed subspace"))
            relations.append(_relation("collapse_region", "collapses_to", "a", "region", claim_id))
            claim["entity_refs"].append("region")
            claim["relation_refs"].append("collapse_region")
            claim["formula_symbols"].append("region")
            payload["explanation"]["symbol_roles"]["region"] = "result"
            stages.append(_stage("stage.det.region", "退化子空间", "两列共线时，平行四边形坍缩为一条子空间区域。", ["a", "b"], ["region"], ["collapse_region"], "collapsed subspace"))
            claim["stage_refs"] = [item["id"] for item in stages]

    if spec.get("volume"):
        a, b, c = spec["given"]["a"], spec["given"]["b"], spec["given"]["c"]
        entities[:] = [_entity("a", "vector", 3, a, "vector_a", claim_id, "a"), _entity("b", "vector", 3, b, "vector_b", claim_id, "b"), _entity("c", "vector", 3, c, "direction", claim_id, "c"), _entity("V", "volume", 3, [a, b, c], "volume", claim_id, "oriented volume")]
        relations[:] = [_relation("spans_volume", "spans", "a", "V", claim_id)]
        claim["entity_refs"] = ["a", "b", "c", "V"]
        claim["relation_refs"] = ["spans_volume"]
        claim["formula_symbols"] = ["a", "b", "c", "V"]
        payload["explanation"]["symbol_roles"] = {"a": "vector_a", "b": "vector_b", "c": "direction", "V": "volume"}

    if spec.get("multiplicativity"):
        relations[:] = [
            _relation("same_measure", "same_measure", "a", "area", claim_id),
            _relation("composition_order", "composition_order", "a", "b", claim_id, {"matrix": spec["given"]["matrix"]}),
        ]
        stages[:] = [_stage("stage.measure.input", "初始面积", "先记录单位平行四边形。", ["A"], [], [], "initial area"), _stage("stage.measure.first", "第一阶段", "第一矩阵贡献一个面积比例。", ["A"], ["area"], ["composition_order"], "first scale"), _stage("stage.measure.final", "乘法守恒", "两个阶段的比例相乘得到总比例。", ["A", "area"], [], ["same_measure"], "product of scales")]
        claim["relation_refs"] = ["same_measure", "composition_order"]
        claim["stage_refs"] = [item["id"] for item in stages]

    if spec.get("inverse"):
        existing = next((item for item in entities if item["id"] == "x"), None)
        target = next((item for item in entities if item["id"] == "y"), None)
        if existing and target:
            relations.extend([
                _relation("inverse_order", "composition_order", "x", "y", claim_id, {"matrix": spec["given"]["matrix"]}),
                _relation("inverse_compare", "compare", "x", "y", claim_id),
            ])
            stages[:] = [_stage("stage.inverse.input", "原变换", "记录输入向量和原矩阵。", ["x"], ["y"], ["A_maps_x_to_y"], "forward transform"), _stage("stage.inverse.undo", "撤销", "按逆矩阵执行反向变换。", ["x", "y"], [], ["inverse_order"], "undo transform"), _stage("stage.inverse.identity", "回到输入", "复合结果应表现为单位变换。", ["x", "y"], [], ["inverse_compare"], "identity")]
            claim["relation_refs"] = [item["id"] for item in relations]
            claim["stage_refs"] = [item["id"] for item in stages]


def topic_required_capabilities(topic_id: str) -> frozenset[str]:
    """Return catalog capabilities without coupling generation to the registry."""

    return frozenset(
        capability
        for topic in TOPICS
        if topic.id == topic_id
        for capability in topic.required_capabilities
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    repo = LectureSourceRepository(Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md")
    store = TeachingArtifactStore(root)
    agent = LocalChapterThreeAgent()
    summaries = []
    for topic in TOPICS:
        context = repo.context_for(topic)
        draft = generate_draft(agent, GenerationRequest(context, topic, profile_for(topic.id)))
        artifact = draft.artifact
        issues = (
            *validate_source_evidence(artifact, context, topic),
            *validate_closed_references(artifact),
            *validate_claim_bindings(artifact),
            *validate_teaching_depth(artifact),
            *validate_worked_examples(artifact),
            *validate_contract(artifact, contract_for(topic.id)),
        )
        if issues:
            raise ValueError(f"{topic.id}: " + "; ".join(f"{item.code}:{getattr(item, 'path', getattr(item, 'detail', ''))}" for item in issues))
        revision = store.save_draft(artifact, raw_reply=draft.raw_reply)
        reviewed = store.review_draft(topic.id, revision.revision, "local-math-review")
        reviewed_artifact = store.get(topic.id, reviewed.revision, "reviewed").artifact
        published = store.publish(reviewed_artifact, source_context=context, topic=topic)
        if not published.ok:
            raise ValueError(f"{topic.id}: " + "; ".join(f"{item.code}:{item.path}" for item in published.issues))
        summaries.append({"topic_id": topic.id, "draft_revision": revision.revision, "reviewed_revision": reviewed.revision, "published_revision": published.revision.revision if published.revision else None, "source_hash": context.source_hash})
    index = root / "index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"schema_version": 1, "chapter": 3, "topics": summaries}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"chapter": 3, "drafts": len(summaries), "published": len(summaries), "index": str(index)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
