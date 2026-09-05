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
    "ch03.det.oriented-area": {"formula": "det(A)=ad-bc", "kind": "oriented_area", "given": {"a": [2, 1], "b": [1, 3]}, "result": 5.0, "check": "area", "statement": "二维行列式是以矩阵两列为邻边的平行四边形有向面积；符号记录方向是否翻转。", "relation": "same_measure"},
    "ch03.det.ad-bc": {"formula": "det([[a,b],[c,d]])=ad-bc", "kind": "determinant", "given": {"matrix": [[3, 1], [2, 4]]}, "result": 10.0, "check": "determinant", "statement": "2×2 行列式按 ad-bc 计算，其中 ad 是主对角方向面积，bc 是交叉项修正。", "relation": "invariant"},
    "ch03.det.sign-zero-one": {"formula": "det(A)>0,=0,<0", "kind": "determinant", "given": {"matrix": [[1, 2], [2, 4]]}, "result": 0.0, "check": "determinant", "statement": "行列式正负表示方向是否保持，零表示面积退化为零，绝对值为一表示面积不变。", "relation": "invariant"},
    "ch03.det.examples": {"formula": "det(A)=ad-bc", "kind": "determinant", "given": {"matrix": [[3, 1], [2, 4]]}, "result": 10.0, "check": "determinant", "statement": "通过分层例题可把行列式数值直接解释为面积缩放因子，并识别退化变换。", "relation": "maps_to"},
    "ch03.det.row-swap": {"formula": "det(PA)=-det(A)", "kind": "determinant", "given": {"matrix": [[1, 2], [3, 4]]}, "result": -2.0, "check": "determinant", "statement": "交换两行会翻转两列的有向平行四边形方向，因此行列式变号而绝对面积不变。", "relation": "orientation"},
    "ch03.det.scaling": {"formula": "det(A')=k\\,det(A)", "kind": "determinant", "given": {"matrix": [[2, 0], [0, 3]]}, "result": 6.0, "check": "determinant", "statement": "某一行乘以 k 等价于沿一个方向拉伸 k 倍，行列式也乘以 k。", "relation": "same_measure"},
    "ch03.det.shear": {"formula": "det([[1,k],[0,1]])=1", "kind": "determinant", "given": {"matrix": [[1, 2], [0, 1]]}, "result": 1.0, "check": "determinant", "statement": "切变只改变平行四边形的倾斜，不改变底和高的乘积，所以面积保持不变。", "relation": "invariant"},
    "ch03.det.multiplicativity": {"formula": "det(AB)=det(A)det(B)", "kind": "determinant", "given": {"matrix": [[2, 0], [0, 3]]}, "result": 6.0, "check": "determinant", "statement": "复合变换的总面积缩放等于两个阶段缩放因子的乘积，体现 det(AB)=det(A)det(B)。", "relation": "same_measure", "multiplicativity": True},
    "ch03.cramer.area-ratio": {"formula": "x_i=det(A_i)/det(A)", "kind": "oriented_area", "given": {"a": [2, 1], "b": [1, 3]}, "result": 5.0, "check": "area", "statement": "克拉默法则把未知量表示为替换一列后的有向面积与原面积之比。", "relation": "same_measure"},
    "ch03.inverse.undo": {"formula": "AA^{-1}=I", "kind": "matrix_transform", "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 2]}, "result": [2.0, 2.0], "check": "transformed", "statement": "逆矩阵撤销原变换；行列式非零时每个输出都能沿唯一轨迹追溯到输入。", "relation": "composition_order", "inverse": True, "matrix": True},
    "ch03.inverse.formula": {"formula": "A^{-1}=1/(ad-bc)[[d,-b],[-c,a]]", "kind": "determinant", "given": {"matrix": [[3, 1], [2, 4]]}, "result": 10.0, "check": "determinant", "statement": "2×2 求逆公式先交换主对角元、反转副对角元，再除以非零行列式。", "relation": "invariant"},
    "ch03.inverse.examples": {"formula": "det(A)≠0⇔A^{-1}存在", "kind": "matrix_transform", "given": {"matrix": [[2, 0], [0, 1]], "vector": [3, 4]}, "result": [6.0, 4.0], "check": "transformed", "statement": "可逆变换保留全部维度且能撤销；行列式为零的退化变换丢失信息，无法唯一还原。", "relation": "maps_to", "inverse": True, "matrix": True},
    "ch03.det.zero.equivalence": {"formula": "det(A)=0⇔rank(A)<n", "kind": "determinant", "given": {"matrix": [[1, 2], [2, 4]]}, "result": 0.0, "check": "determinant", "statement": "det=0、列线性相关、秩下降和存在非零零空间是同一压扁现象的等价描述。", "relation": "collapses_to"},
    "ch03.det.high-dimensional-volume": {"formula": "det(A)=\\text{oriented n-volume}", "kind": "oriented_volume", "given": {"a": [1, 0, 0], "b": [0, 2, 0], "c": [0, 0, 3]}, "result": 6.0, "check": "volume", "statement": "n 阶行列式把二维有向面积、三维有向体积推广到 n 维有向体积，并保留同样的乘法与退化规律。", "relation": "same_measure", "scene": "3d", "volume": True, "analogy": True},
    "ch03.inverse.reverse-order": {"formula": "(AB)^{-1}=B^{-1}A^{-1}", "kind": "matrix_transform", "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 2]}, "result": [2.0, 2.0], "check": "transformed", "statement": "复合变换的逆必须按相反顺序撤销：先撤销 A，再撤销 B，故 (AB)^{-1}=B^{-1}A^{-1}。", "relation": "composition_order", "inverse": True, "matrix": True},
}


class LocalChapterThreeAgent:
    def generate(self, context, topic, profile, vocabulary):
        chapter1._SPEC = _SPEC
        payload = chapter1.build_payload(context, topic, profile)
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
        entities[:] = [item for item in entities if item["id"] not in {"r"}]
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
        entities[:] = [_entity("A", "matrix", 2, matrix, "matrix_a", claim_id, "A"), _entity("area", "area", 2, columns, "area", claim_id, "det(A)")]
        relations[:] = [_relation("det_maps_to_area", "maps_to", "A", "area", claim_id, {"matrix": matrix})]
        claim["entity_refs"] = ["A", "area"]
        claim["relation_refs"] = ["det_maps_to_area"]
        claim["formula_symbols"] = ["A", "area"]
        payload["explanation"]["symbol_roles"] = {"A": "matrix_a", "area": "area"}
        stages[:] = [_stage("stage.det.input", "矩阵两列", "把矩阵两列看作平行四边形的两条邻边。", ["A"], [], [], "columns as sides"), _stage("stage.det.measure", "有向面积", "行列式给出有向面积及方向符号。", ["A"], ["area"], ["det_maps_to_area"], "signed area")]
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
            _relation("same_measure", "same_measure", "A", "area", claim_id),
            _relation("composition_order", "composition_order", "A", "area", claim_id),
        ]
        stages[:] = [_stage("stage.measure.input", "初始面积", "先记录单位平行四边形。", ["A"], [], [], "initial area"), _stage("stage.measure.first", "第一阶段", "第一矩阵贡献一个面积比例。", ["A"], ["area"], ["composition_order"], "first scale"), _stage("stage.measure.final", "乘法守恒", "两个阶段的比例相乘得到总比例。", ["A", "area"], [], ["same_measure"], "product of scales")]
        claim["relation_refs"] = ["same_measure", "composition_order"]
        claim["stage_refs"] = [item["id"] for item in stages]

    if spec.get("inverse"):
        existing = next((item for item in entities if item["id"] == "x"), None)
        target = next((item for item in entities if item["id"] == "y"), None)
        if existing and target:
            relations.extend([
                _relation("inverse_order", "composition_order", "x", "y", claim_id),
                _relation("inverse_compare", "compare", "x", "y", claim_id),
            ])
            stages[:] = [_stage("stage.inverse.input", "原变换", "记录输入向量和原矩阵。", ["x"], ["y"], ["A_maps_x_to_y"], "forward transform"), _stage("stage.inverse.undo", "撤销", "按逆矩阵执行反向变换。", ["x", "y"], [], ["inverse_order"], "undo transform"), _stage("stage.inverse.identity", "回到输入", "复合结果应表现为单位变换。", ["x", "y"], [], ["inverse_compare"], "identity")]
            claim["relation_refs"] = [item["id"] for item in relations]
            claim["stage_refs"] = [item["id"] for item in stages]


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
