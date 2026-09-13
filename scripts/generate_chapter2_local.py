"""Generate lecture-grounded Chapter 2 teaching drafts.

This local adapter is intentionally limited to mathematical explanation and
visual semantics.  It reuses the reviewed Chapter 1 payload builder, but its
topic table and source contexts are Chapter 2 only.  No renderer commands,
scene operations, or UI data are emitted.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in {None, ""}:  # pragma: no cover - direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linear_algebra.catalog.chapter_02 import TOPICS
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
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for, validate_contract

import generate_chapter1_local as chapter1


_SPEC = {
    "ch02.batch.inner-products": {
        "formula": "(u V)_j=\\sum_i u_i v_{ij}",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0], [0, 1]], "vector": [2, 3]},
        "result": [2.0, 3.0],
        "check": "transformed",
        "statement": "行向量乘矩阵时，结果的每个分量是权重向量与对应列的内积，因此可以一次比较多个方向。",
        "relation": "batch_maps_to",
        "matrix": True,
    },
    "ch02.batch.projection": {
        "formula": "P=uu^T,\\ Pv=(u\\cdot v)u",
        "kind": "projection",
        "given": {"vector": [3, 4], "direction": [1, 0]},
        "result": [3.0, 0.0],
        "check": "projection",
        "statement": "单位方向 u 的投影矩阵 P=uu^T 将每个输入向量压到 u 方向，输出就是沿该方向的分量。",
        "relation": "projection",
        "special": "projection",
    },
    "ch02.matrix.additive-distributivity": {
        "formula": "(A+B)x=Ax+Bx",
        "kind": "matrix_transform",
        "given": {"matrix": [[6, 8], [10, 12]], "vector": [1, 1]},
        "result": [14.0, 22.0],
        "check": "transformed",
        "statement": "矩阵按元素相加与数乘，并继承变换的分配律；先合并矩阵再作用于向量等于分别变换后相加。",
        "relation": "invariant",
        "matrix": True,
    },
    "ch02.matrix.row-column": {
        "formula": "(Ax)_i=\\operatorname{row}_i(A)\\cdot x=\\sum_j x_j A_{:j}",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 2], [3, 4]], "vector": [1, 2]},
        "result": [5.0, 11.0],
        "check": "transformed",
        "statement": "Ax 既可看作每一行与 x 的内积，也可看作矩阵各列按 x 的分量作线性组合；两种视角给出同一输出。",
        "relation": "compare",
        "matrix": True,
    },
    "ch02.matrix.transformed-grid": {
        "formula": "Ax=x_1Ae_1+x_2Ae_2",
        "kind": "matrix_transform",
        "given": {"matrix": [[2, 1], [0, 1]], "vector": [1, 2]},
        "result": [4.0, 2.0],
        "check": "transformed",
        "statement": "矩阵的两列分别是标准基向量的像；知道两列如何移动，就能确定整张坐标网格的拉伸、旋转或剪切。",
        "relation": "invariant",
        "matrix": True,
        "grid": True,
    },
    "ch02.matrix.stretch-rotate-scale": {
        "formula": "A(1,2)^T=(5,11)^T",
        "kind": "matrix_transform",
        "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 2]},
        "result": [2.0, 2.0],
        "check": "transformed",
        "statement": "对角矩阵沿坐标轴拉伸，旋转矩阵改变方向；一般矩阵可把这些几何效应组合为线性变换。",
        "relation": "maps_to",
        "matrix": True,
    },
    "ch02.matrix.composition": {
        "formula": "(AB)x=A(Bx),\\quad AB\\ne BA",
        "kind": "matrix_transform",
        "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 2]},
        "result": [2.0, 2.0],
        "check": "transformed",
        "statement": "矩阵乘法表示变换的复合：AB 先做 B 再做 A；改变先后顺序通常得到不同终点。",
        "relation": "composition_order",
        "matrix": True,
        "composition": True,
    },
    "ch02.matrix.basis": {
        "formula": "[T]_\\mathcal B= S^{-1}AS",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 1], [0, 1]], "vector": [2, 3]},
        "result": [5.0, 3.0],
        "check": "transformed",
        "statement": "同一变换在不同基底下有不同矩阵；矩阵的列是新基向量的像，坐标描述随测量尺改变。",
        "relation": "maps_to",
        "matrix": True,
    },
    "ch02.matrix.powers": {
        "formula": "A^k=A\\cdot A\\cdots A",
        "kind": "matrix_transform",
        "given": {"matrix": [[2, 0], [0, 1]], "vector": [1, 1]},
        "result": [2.0, 1.0],
        "check": "transformed",
        "statement": "矩阵幂表示重复执行同一个方阵变换；转置则交换行列并满足乘积转置的逆序法则。",
        "relation": "invariant",
        "matrix": True,
    },
    "ch02.subspace.independence": {
        "formula": "c_1v_1+c_2v_2=0\\Rightarrow c_1=c_2=0",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0], [0, 1]], "vector": [1, 1]},
        "result": [1.0, 1.0],
        "check": "transformed",
        "statement": "线性无关意味着只有全零系数才能组合出零向量；在平面中两条不共线方向各自都是必要的。",
        "relation": "compare",
        "matrix": True,
    },
    "ch02.subspace.rank": {
        "formula": "\\operatorname{rank}(A)=\\dim\\operatorname{Col}(A)",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 2], [2, 4]], "vector": [1, 1]},
        "result": [3.0, 6.0],
        "check": "transformed",
        "statement": "秩是列空间的真实维数；两列共线的矩阵只能把平面压到一条输出直线。",
        "relation": "collapses_to",
        "matrix": True,
    },
    "ch02.subspace.null": {
        "formula": "\\operatorname{Null}(A)=\\{x\\mid Ax=0\\}",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0], [0, 0]], "vector": [0, 2]},
        "result": [0.0, 0.0],
        "check": "transformed",
        "statement": "零空间由被 A 压到原点的输入方向组成；投影到 x 轴时整条 y 轴都被消除。",
        "relation": "collapses_to",
        "matrix": True,
        "null_space": True,
    },
    "ch02.subspace.column": {
        "formula": "\\operatorname{Col}(A)=\\{Ax\\mid x\\in R^n\\}",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0], [0, 0]], "vector": [2, 3]},
        "result": [2.0, 0.0],
        "check": "transformed",
        "statement": "列空间是所有可能输出的集合；投影到 x 轴时任何输入的输出都落在 x 轴上。",
        "relation": "maps_to",
        "matrix": True,
    },
    "ch02.subspace.rank-nullity": {
        "formula": "\\operatorname{rank}(A)+\\operatorname{nullity}(A)=n",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0], [0, 0]], "vector": [0, 2]},
        "result": [0.0, 0.0],
        "check": "transformed",
        "statement": "秩与零化度把输入维数分成可见输出方向和被压扁方向，两者之和保持为 n。",
        "relation": "invariant",
        "matrix": True,
    },
    "ch02.high-dimensional.analogy": {
        "formula": "T(x)=Ax,\\quad \\operatorname{rank}(A)\\leq\\min(m,n)",
        "kind": "matrix_transform",
        "given": {"matrix": [[1, 0, 0], [0, 2, 0], [0, 0, 3]], "vector": [1, 2, 3]},
        "result": [1.0, 4.0, 9.0],
        "check": "transformed",
        "statement": "二维和三维的分量规则推广到 n 维；高维不再强求直接图像，而用秩、零空间和列空间等不变量理解变换。",
        "relation": "maps_to",
        "matrix": True,
        "scene": "3d",
        "analogy": True,
    },
}


class LocalChapterTwoAgent:
    def generate(self, context, topic, profile, vocabulary):
        chapter1._SPEC = _SPEC
        payload = refine_payload(chapter1.build_payload(context, topic, profile))
        _add_contract_semantics(payload, topic.id)
        from linear_algebra.teaching.model import TeachingArtifact
        from linear_algebra.teaching.agent import TeachingArtifactDraft

        artifact = TeachingArtifact.from_dict(payload)
        raw_reply = json.dumps(artifact.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return TeachingArtifactDraft(artifact=artifact, raw_reply=raw_reply)


def _add_contract_semantics(payload: dict, topic_id: str) -> None:
    """Add only typed graph records required by exceptional visual contracts."""

    visual = payload["visual_semantics"]
    claim = payload["claims"][0]
    claim_id = claim["id"]
    entities = visual["entities"]
    relations = visual["relations"]
    stages = visual["stages"]

    if topic_id == "ch02.matrix.transformed-grid":
        entities.append({"id": "grid", "kind": "grid", "dimension": 2, "value": [[0, 0], [1, 0]], "role": "grid", "label": "coordinate grid", "claim_refs": [claim_id]})
        relations.append({"id": "grid_invariant", "kind": "invariant", "source_ref": "grid", "target_ref": "y", "parameters": {}, "claim_refs": [claim_id]})
        stages.extend([
            {"id": "stage.grid_input", "title": "标准网格", "caption": "标准基向量确定原始网格。", "layout": "side_by_side", "input_entity_refs": ["A", "x", "grid"], "output_entity_refs": [], "relation_refs": [], "expected_invariants": ["grid basis"]},
            {"id": "stage.grid_output", "title": "变换后网格", "caption": "两列的像确定变形后的网格。", "layout": "side_by_side", "input_entity_refs": ["A", "x"], "output_entity_refs": ["y", "grid"], "relation_refs": ["grid_invariant"], "expected_invariants": ["invariant"]},
        ])
        claim["entity_refs"].append("grid")
        claim["relation_refs"].append("grid_invariant")
        claim["stage_refs"].extend(["stage.grid_input", "stage.grid_output"])

    elif topic_id == "ch02.matrix.composition":
        # The concise quality refinement already supplies both ordered paths,
        # their distinct endpoints, and the five contract stages.  Do not add
        # a second copy of the same entities when this local batch generator
        # performs its contract pass.
        if {
            "z",
        } <= {str(entity.get("id", "")) for entity in entities} and {
            "composition_order", "endpoint_diff", "composition_compare",
        } <= {str(relation.get("id", "")) for relation in relations}:
            return
        entities.append({"id": "z", "kind": "vector", "dimension": 2, "value": [1.0, 2.0], "role": "transformed_b", "label": "BAx", "claim_refs": [claim_id]})
        relations.extend([
            {"id": "composition_order", "kind": "composition_order", "source_ref": "x", "target_ref": "y", "parameters": {}, "claim_refs": [claim_id]},
            {"id": "endpoint_diff", "kind": "endpoint_diff", "source_ref": "y", "target_ref": "z", "parameters": {}, "claim_refs": [claim_id]},
            {"id": "composition_compare", "kind": "compare", "source_ref": "y", "target_ref": "z", "parameters": {}, "claim_refs": [claim_id]},
        ])
        stages.clear()
        for index, (title, caption, inputs, outputs, refs, invariant) in enumerate([
            ("输入向量", "同一向量作为两条复合路径的输入。", ["x"], [], [], "input fixed"),
            ("先 B 后 A", "AB 路径按从右到左执行。", ["x"], ["y"], ["composition_order"], "composition order"),
            ("先 A 后 B", "BA 路径改变操作次序。", ["x"], ["z"], ["composition_order"], "composition order"),
            ("终点差异", "两条路径的终点通常不同。", ["y", "z"], [], ["endpoint_diff"], "different endpoints"),
            ("比较", "比较阶段呈现 AB 与 BA 不交换。", ["y", "z"], [], ["composition_compare"], "AB != BA"),
        ]):
            stages.append({"id": f"stage.composition.{index}", "title": title, "caption": caption, "layout": "sequence", "input_entity_refs": inputs, "output_entity_refs": outputs, "relation_refs": refs, "expected_invariants": [invariant]})
        claim["entity_refs"].append("z")
        claim["relation_refs"].extend(["composition_order", "endpoint_diff", "composition_compare"])
        claim["stage_refs"] = [stage["id"] for stage in stages]

    elif topic_id == "ch02.subspace.null":
        relations.append({"id": "collapse_to_origin", "kind": "collapses_to", "source_ref": "x", "target_ref": "y", "parameters": {}, "claim_refs": [claim_id]})
        stages.extend([
            {"id": "stage.null_input", "title": "输入方向", "caption": "选择零空间中的 y 轴方向。", "layout": "side_by_side", "input_entity_refs": ["x"], "output_entity_refs": [], "relation_refs": [], "expected_invariants": ["null direction"]},
            {"id": "stage.null_output", "title": "压到原点", "caption": "A 作用后该方向变成零向量。", "layout": "side_by_side", "input_entity_refs": ["x"], "output_entity_refs": ["y"], "relation_refs": ["collapse_to_origin"], "expected_invariants": ["collapsed to origin"]},
        ])
        claim["relation_refs"].append("collapse_to_origin")
        claim["stage_refs"].extend(["stage.null_input", "stage.null_output"])


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "linear_algebra" / "teaching" / "data"
    repo = LectureSourceRepository(Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md")
    store = TeachingArtifactStore(root)
    agent = LocalChapterTwoAgent()
    summaries = []
    for topic in TOPICS:
        context = repo.context_for(topic)
        request = GenerationRequest(context, topic, profile_for(topic.id))
        draft = generate_draft(agent, request)
        draft_revision = store.save_draft(draft.artifact, raw_reply=draft.raw_reply)
        reviewed_revision = store.review_draft(topic.id, draft_revision.revision, "local-math-review")
        artifact = store.get(topic.id, reviewed_revision.revision, "reviewed").artifact
        issues = (
            *validate_source_evidence(artifact, context, topic),
            *validate_closed_references(artifact),
            *validate_claim_bindings(artifact),
            *validate_teaching_depth(artifact),
            *validate_worked_examples(artifact),
            *validate_contract(artifact, contract_for(topic.id)),
        )
        if issues:
            raise ValueError(f"{topic.id}: " + "; ".join(f"{i.code}:{i.path}" for i in issues))
        VisualSemanticsCompiler().compile(artifact, contract_for(topic.id), RenderContext.default(topic.id))
        published = store.publish(artifact, source_context=context, topic=topic, raw_reply=draft.raw_reply)
        if not published.ok or published.revision is None:
            raise ValueError(f"{topic.id}: " + "; ".join(issue.code for issue in published.issues))
        summaries.append({"topic_id": topic.id, "revision": published.revision.revision, "source_hash": context.source_hash})
    index = root / "index-ch02.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"schema_version": 1, "chapter": 2, "topics": summaries}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"chapter": 2, "published": len(summaries), "index": str(index)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
