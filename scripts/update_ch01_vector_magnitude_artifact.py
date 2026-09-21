"""按讲义原文重建 1.1.1“什么是向量”的教学产物。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT_DIR = ROOT / "linear_algebra" / "teaching" / "data" / "drafts" / "ch01" / "ch01.vector.magnitude"
PUBLISHED_DIR = ROOT / "linear_algebra" / "teaching" / "data" / "published" / "ch01" / "ch01.vector.magnitude"

# 保留三项定义原文，确保来源锚点和摘要与展示内容一致。
LECTURE_EXCERPT = (
    "#### 1.1.1 什么是向量\n\n"
    "我们从一个最简单的物理场景出发：\n"
    "从宿舍到食堂，\"向北走300米，再向东走400米\"。\n"
    "这和\"向东走400米，再向北走300米\"的目标位置完全相同。\n"
    "这两个\"走法\"有方向（北偏东）和长度（500米）。它们描述的是同一个位移。\n"
    "把这个直觉翻译成数学语言：\n"
    "定义 1.1（向量） 在平面直角坐标系中，一个向量是一个有向线段，其起点固定为坐标原点 $O(0,0)$。向量由其终点坐标唯一确定。\n"
    "记法：向量一般用粗体小写字母表示，如 v。也常用其终点坐标 $(x, y)$ 来表示。\n"
    "关键约定：在线性代数中，所有向量默认从原点出发。这是整门课最重要的操作约定——正是因为起点统一，向量才能和坐标一一对应，几何才能翻译为代数。\n"
    "定义 1.2（零向量） 长度为零的向量称为零向量，记为 0 或 $(0, 0)$。零向量没有方向，是唯一一个\"既是向量又是点\"的向量。\n"
    "定义 1.3（向量的模） 向量 $v = (x, y)$ 的长度称为模，记为 $|v|$。由勾股定理：\n"
    "$$\n"
    "|v| = \\sqrt{x^{2} + y^{2}}\n"
    "$$\n"
    "例如，$(3, 4)$ 的模为 $\\sqrt{9 + 16} = 5$。"
)

SPAN_TEXT = LECTURE_EXCERPT
SPAN_FINGERPRINT = "sha256:2b53dbe40acf6537f3db65a7393acc792022be98e32f278f8f056dfd8013baca"
SPAN_START = 8
SPAN_END = 24

# 三个定义及其公式保持讲义顺序，省略编号并统一粗体向量符号。
DEFINITION_TEXT = (
    "**（向量）** 在平面直角坐标系中，一个向量是一个有向线段，"
    "其起点固定为坐标原点 $O(0,0)$。向量由其终点坐标唯一确定。\n\n"
    "记法：向量一般用粗体小写字母表示，如 $\\boldsymbol v$。"
    "也常用其终点坐标 $(x, y)$ 来表示。\n\n"
    "关键约定：在线性代数中，所有向量默认从原点出发。"
    "这是整门课最重要的操作约定——正是因为起点统一，"
    "向量才能和坐标一一对应，几何才能翻译为代数。\n\n"
    "**（零向量）** 长度为零的向量称为零向量，"
    "记为 $\\boldsymbol 0$ 或 $(0, 0)$。"
    "零向量没有方向，是唯一一个\"既是向量又是点\"的向量。\n\n"
    "**（向量的模）** 向量 $\\boldsymbol v = (x, y)$ 的长度称为模，记为 $|\\boldsymbol v|$。"
    "由勾股定理：\n\n"
    "$$|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}$$\n\n"
    "例如，$(3, 4)$ 的模为 $\\sqrt{9 + 16} = 5$。"
)

# 物理场景逐句保留讲义原文。
PHYSICAL_SCENARIO = (
    "我们从一个最简单的物理场景出发：\n"
    "从宿舍到食堂，\"向北走300米，再向东走400米\"。\n"
    "这和\"向东走400米，再向北走300米\"的目标位置完全相同。\n"
    "这两个\"走法\"有方向（北偏东）和长度（500米）。\n"
    "它们描述的是同一个位移。"
)

# 摘要末尾保留讲义中的定义衔接句。
BRIDGE_LINE = "把这个直觉翻译成数学语言："


def _entity(entity_id, kind, dimension, value, role, label):
    return {
        "id": entity_id,
        "kind": kind,
        "dimension": dimension,
        "value": value,
        "role": role,
        "label": label,
        "claim_refs": ["claim.ch01.vector.magnitude"],
    }


def build_artifact(status: str, revision: int) -> dict:
    source_span = {
        "id": "第1章 向量与几何测量 / 1.1 向量的几何表示 / 1.1.1 什么是向量::1::" + SPAN_FINGERPRINT,
        "heading_path": ["第1章 向量与几何测量", "1.1 向量的几何表示", "1.1.1 什么是向量"],
        "start_line": SPAN_START,
        "end_line": SPAN_END,
        "fingerprint": SPAN_FINGERPRINT,
        "text": SPAN_TEXT,
    }
    source_record = {
        "source_path": ["第1章 向量与几何测量", "1.1 向量的几何表示", "1.1.1 什么是向量"],
        "heading_path": ["第1章 向量与几何测量", "1.1 向量的几何表示", "1.1.1 什么是向量"],
        "heading_level": 4,
        "occurrence": 1,
        "excerpt": LECTURE_EXCERPT,
        "source_hash": SPAN_FINGERPRINT,
        "spans": [source_span],
        "neighboring_titles": ["1.1.2 向量与点的本质区别"],
    }
    sections = [
        {
            "id": "definition",
            "title": "定义",
            "text": DEFINITION_TEXT,
            "claim_refs": ["claim.ch01.vector.magnitude"],
        },
        {
            "id": "worked_examples",
            "title": "数学案例",
            "text": "例如，$(3, 4)$ 的模为 $\\sqrt{9 + 16} = 5$。",
            "claim_refs": ["claim.ch01.vector.magnitude"],
        },
    ]
    claim = {
        "id": "claim.ch01.vector.magnitude",
        "statement": (
            "**（向量）** 在平面直角坐标系中，一个向量是一个有向线段，"
            "其起点固定为坐标原点 $O(0,0)$，由其终点坐标唯一确定；"
            "**（零向量）** 长度为零的向量称为零向量，"
            "记为 $\\boldsymbol 0$ 或 $(0, 0)$；"
            "**（向量的模）** 向量 $\\boldsymbol v = (x, y)$ 的模由勾股定理 "
            "$|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}$ 给出。"
        ),
        "formula": "|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}",
        "formula_symbols": ["\\boldsymbol v"],
        "source_refs": [source_span["id"]],
        "explanation_refs": ["definition", "worked_examples"],
        "entity_refs": ["v", "v_length"],
        "relation_refs": ["rel.magnitude.nonzero"],
        "stage_refs": ["stage.magnitude.nonzero"],
    }
    worked_examples = [
        {
            "id": "example.magnitude.nonzero",
            "title": "案例一：$\\boldsymbol v=(3,4)$ 的模",
            "kind": "inner_product",
            "given": [[3, 4], [3, 4]],
            "calculation": [
                "$$\\boldsymbol v=(3,4)$$",
                "$$|\\boldsymbol v| = \\sqrt{3^2 + 4^2} = 5$$",
            ],
            "result": 25,
            "checks": [{"name": "result", "expected": 25, "tolerance": 1e-09}],
            "claim_refs": ["claim.ch01.vector.magnitude"],
        },
    ]
    entities = [
        _entity("v", "vector", 2, [3, 4], "vector_a", "v"),
        _entity("v_length", "point", 2, [3, 4], "result", ""),
    ]
    relations = [
        {
            "id": "rel.magnitude.nonzero",
            "kind": "invariant",
            "source_ref": "v",
            "target_ref": "v_length",
            "parameters": {},
            "claim_refs": ["claim.ch01.vector.magnitude"],
        },
    ]
    stages = [
        {
            "id": "stage.magnitude.nonzero",
            "title": "案例一：$\\boldsymbol v=(3,4)$ 的模",
            "caption": "$\\boldsymbol v=(3,4)$ 的模 $|\\boldsymbol v| = 5$。",
            "layout": "overlay",
            "input_entity_refs": ["v"],
            "output_entity_refs": ["v_length"],
            "relation_refs": ["rel.magnitude.nonzero"],
            "expected_invariants": ["nonzero vector length is 5"],
        },
    ]
    case_layout = {
        "cases": [
            {
                "id": "case.magnitude.nonzero",
                "topic_id": "ch01.vector.magnitude",
                "example_ref": "example.magnitude.nonzero",
                "claim_refs": ["claim.ch01.vector.magnitude"],
                "stage_refs": ["stage.magnitude.nonzero"],
                "purpose": "案例一：$\\boldsymbol v=(3,4)$ 的模",
            },
        ],
        "default_pane_count": 1,
    }
    searchable_text = [
        "什么是向量",
        "零向量",
        PHYSICAL_SCENARIO,
        BRIDGE_LINE,
        "定义 1.2（零向量） 长度为零的向量称为零向量，记为 0 或 $(0, 0)$。"
        "零向量没有方向，是唯一一个\"既是向量又是点\"的向量。",
        "|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}",
        DEFINITION_TEXT,
    ]
    # 摘要由讲义中的物理场景和衔接句组成。
    summary_text = PHYSICAL_SCENARIO + "\n" + BRIDGE_LINE
    explanation = {
        "title": "什么是向量",
        "summary": summary_text,
        "sections": sections,
        "symbol_roles": {"\\boldsymbol v": "vector_a"},
        "definition": DEFINITION_TEXT,
        "formula": "|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}",
        "derivation": [],
        "worked_examples": worked_examples,
        # 讲义未提供的分节保持为空。
        "intuition": "",
        "geometric_meaning": "",
        "conclusion": "",
        "pitfalls": [],
        "invariants": [],
        "connections": [],
        "analogy_boundary": "",
        "transfer_note": "",
        "read_guide": [],
        "searchable_text": searchable_text,
        "case_layout": case_layout,
    }
    artifact = {
        "schema_version": 1,
        "topic_id": "ch01.vector.magnitude",
        "revision": revision,
        "status": status,
        "source": source_record,
        "teaching_profile": {
            "minimum_level": 2,
            "required_sections": ["definition", "formula", "worked_examples"],
            "requires_analogy_boundary": False,
        },
        "claims": [claim],
        "connections": [],
        "explanation": explanation,
        "visual_semantics": {
            "scene_kind": "2d",
            "entities": entities,
            "relations": relations,
            "stages": stages,
        },
    }
    return artifact


def _artifact_digest(artifact: dict) -> str:
    payload = json.loads(json.dumps(artifact))
    generated = payload.get("generated", {})
    generated = dict(generated)
    generated["artifact_digest"] = ""
    generated["raw_reply_digest"] = ""
    payload["generated"] = generated
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _wrap(status: str, artifact: dict, raw_reply_payload: str | None) -> dict:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    artifact_no_digest = {key: value for key, value in artifact.items() if key != "generated"}
    raw_reply_text = raw_reply_payload if raw_reply_payload is not None else json.dumps(artifact_no_digest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw_reply_digest = "sha256:" + hashlib.sha256(raw_reply_text.encode("utf-8")).hexdigest()
    artifact_for_digest = {**artifact, "generated": {
        "provider": "math-explanation-sample",
        "model": "lecture-grounded-v2",
        "schema_version": 1,
        "prompt_version": "teaching-artifact-v1",
        "generated_at": generated_at,
        "source_hash": SPAN_FINGERPRINT,
        "raw_reply_digest": raw_reply_digest,
        "artifact_digest": "",
    }}
    artifact_digest = _artifact_digest(artifact_for_digest)
    artifact_final = {**artifact_for_digest, "generated": {**artifact_for_digest["generated"], "artifact_digest": artifact_digest}}
    return {"artifact": artifact_final, "raw_reply": raw_reply_text}


def main() -> int:
    draft_artifact = build_artifact(status="draft", revision=33)
    published_artifact = build_artifact(status="published", revision=27)
    draft_payload = _wrap("draft", draft_artifact, None)
    published_payload = _wrap("published", published_artifact, None)

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    (DRAFT_DIR / "r33.json").write_text(json.dumps(draft_payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (PUBLISHED_DIR / "r27.json").write_text(json.dumps(published_payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    # 清理缺少零向量定义的旧草稿。
    for stale_name in ("r31.json", "r32.json"):
        stale = DRAFT_DIR / stale_name
        if stale.exists():
            stale.unlink()
    print(json.dumps({
        "draft": str(DRAFT_DIR / "r33.json"),
        "published": str(PUBLISHED_DIR / "r27.json"),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
