"""Destructive tests for the closed Chapter 4 semantic family."""
from __future__ import annotations

import copy
import pytest

from linear_algebra.chapter_04_semantics import TOPIC_SEMANTICS, semantic_for
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.families.chapter_04 import Chapter4FamilyCompiler
from services.scene_commands import SceneCommandService
from ui.teaching_case_panes import case_plan

TOPICS=tuple(sorted(TOPIC_SEMANTICS))


def _artifact(topic: str, payload: dict | None = None) -> TeachingArtifact:
    return TeachingArtifact.from_dict(payload or artifact_payload_for(topic))


def _compile(topic: str, payload: dict | None = None):
    return VisualSemanticsCompiler().compile(_artifact(topic,payload),contract_for(topic),RenderContext.default(topic))


def test_every_topic_declares_exact_typed_graph_contract_and_claim_coverage():
    assert len(TOPICS)==14
    for topic in TOPICS:
        spec=semantic_for(topic); artifact=_artifact(topic); contract=contract_for(topic); semantics=artifact.visual_semantics
        assert semantics.scene_kind==spec.scene_kind
        assert [(e.role,e.kind,e.dimension) for e in semantics.entities]==[(e.role,e.kind,e.dimension) for e in spec.entities]
        assert contract.required_entity_roles==spec.roles
        assert contract.required_role_types==tuple((e.role,e.kind,e.dimension) for e in spec.entities)
        assert contract.minimum_stage_count==len(spec.stages)>=2
        assert {kind for _name,kind,_source,_target in contract.required_relation_endpoints}=={r.kind for r in spec.relations}
        assert contract.required_invariants==spec.invariants
        assert contract.expected_operations==spec.expected_operations
        claim=artifact.claims[0]
        assert set(claim.entity_refs)=={e.id for e in semantics.entities}
        assert set(claim.relation_refs)=={r.id for r in semantics.relations}
        assert set(claim.stage_refs)=={s.id for s in semantics.stages}


@pytest.mark.parametrize("topic",TOPICS)
def test_removing_any_required_role_relation_stage_invariant_or_parameter_fails(topic):
    base=artifact_payload_for(topic); visual=base["visual_semantics"]
    for index in range(len(visual["entities"])):
        payload=copy.deepcopy(base); del payload["visual_semantics"]["entities"][index]
        with pytest.raises((VisualCompileError,ValueError)): _compile(topic,payload)
    for index in range(len(visual["relations"])):
        payload=copy.deepcopy(base); del payload["visual_semantics"]["relations"][index]
        with pytest.raises((VisualCompileError,ValueError)): _compile(topic,payload)
    for index in range(len(visual["stages"])):
        payload=copy.deepcopy(base); del payload["visual_semantics"]["stages"][index]
        with pytest.raises((VisualCompileError,ValueError)): _compile(topic,payload)
    for stage_index,stage in enumerate(visual["stages"]):
        for invariant_index in range(len(stage["expected_invariants"])):
            payload=copy.deepcopy(base); del payload["visual_semantics"]["stages"][stage_index]["expected_invariants"][invariant_index]
            with pytest.raises((VisualCompileError,ValueError)): _compile(topic,payload)
    for relation_index,relation in enumerate(visual["relations"]):
        for parameter in relation["parameters"]:
            payload=copy.deepcopy(base); del payload["visual_semantics"]["relations"][relation_index]["parameters"][parameter]
            with pytest.raises((VisualCompileError,ValueError)): _compile(topic,payload)


MUTATIONS={
 "ch04.space.closure":("sum",[2,1]),
 "ch04.subspace.classification":("affine_counterexample",[[1,0,0],[0,1,0],[0,0,0]]),
 "ch04.subspace.intersection":("union_sum",[0,2,1]),
 "ch04.subspace.col-null":("kernel_vector",[1,1]),
 "ch04.span.dimension":("span_3d",[[1,0,0],[0,1,0],[1,1,0]]),
 "ch04.dependence.redundancy":("coefficients",[2,1,-1]),
 "ch04.nullspace.test":("null_vector",[2,1,-1]),
 "ch04.rank.collapse":("rank_one",[[1,0],[0,1]]),
 "ch04.basis.definition":("oblique_basis",[[1,1],[1,1]]),
 "ch04.linear-map.definition":("T_sum",[4,3]),
 "ch04.linear-map.compare":("square_map",[[-1,2],[0,0],[2,4]]),
 "ch04.linear-map.matrix-columns":("column_2",[0,3]),
 "ch04.kernel-image":("sample_output",[3,0]),
 "ch04.rank-nullity":("map_T",[[1,0,0],[0,1,0],[0,0,1]]),
}


@pytest.mark.parametrize("topic",TOPICS)
def test_numeric_tamper_breaks_recomputed_topic_invariant(topic):
    payload=artifact_payload_for(topic); role,value=MUTATIONS[topic]
    entity=next(e for e in payload["visual_semantics"]["entities"] if e["role"]==role); entity["value"]=value
    semantics=_artifact(topic,payload).visual_semantics
    issues=Chapter4FamilyCompiler.validate(topic,semantics)
    assert any(issue.code=="mathematical_invariant" for issue in issues), issues
    with pytest.raises(VisualCompileError): Chapter4FamilyCompiler.compile(topic_id=topic,semantics=semantics,context=RenderContext.default(topic))


def test_dedicated_family_compiler_is_mandatory(monkeypatch):
    def fail(cls,**kwargs): raise RuntimeError("chapter4 family invoked")
    monkeypatch.setattr(Chapter4FamilyCompiler,"compile",classmethod(fail))
    with pytest.raises(RuntimeError,match="chapter4 family invoked"): _compile(TOPICS[0])


@pytest.mark.parametrize("topic",TOPICS)
def test_all_claim_evidence_aliases_are_distinct_real_operations(topic):
    artifact=_artifact(topic); compiled=_compile(topic); claim=artifact.claims[0]
    alias_to_op={operation.get("alias"):operation["op"] for operation in compiled.plan.operations if operation.get("alias")}
    first_aliases=[]
    for semantic_id in (*claim.entity_refs,*claim.relation_refs):
        aliases=compiled.aliases_for(semantic_id)
        assert aliases
        assert all(alias in alias_to_op and not alias_to_op[alias].startswith("annotation.") for alias in aliases)
        first_aliases.append(aliases[0])
    assert len(first_aliases)==len(set(first_aliases))
    assert set(compiled.family_evidence["invariants"])==set(semantic_for(topic).invariants)
    assert all(compiled.family_evidence["invariants"].values())


class _RecordingHost:
    def __init__(self,mode): self.mode=mode; self.pending=[]; self.committed=[]; self.rollbacks=0
    def begin_scene_command_transaction(self): self.pending=[]
    def apply_scene_command(self,operation): self.pending.append(operation)
    def commit_scene_command_transaction(self): self.committed.extend(self.pending); self.pending=[]
    def rollback_scene_command_transaction(self): self.pending=[]; self.rollbacks+=1


@pytest.mark.parametrize("topic",TOPICS)
def test_all_plans_validate_and_execute_transactionally(topic):
    compiled=_compile(topic); host=_RecordingHost(compiled.plan.scene); service=SceneCommandService(host)
    assert service.validate(compiled.plan).valid
    result=service.execute(compiled.plan)
    assert result.valid and host.committed and host.rollbacks==0


def test_non_identity_topics_do_not_use_identity_or_first_vector_fallbacks():
    expected={
        "ch04.linear-map.definition":[[2.0,1.0],[0.0,1.0]],
        "ch04.linear-map.matrix-columns":[[2.0,-1.0],[1.0,3.0]],
        "ch04.kernel-image":[[1.0,0.0],[0.0,0.0]],
    }
    for topic,matrix in expected.items():
        matrices=[op["matrix"] for op in _compile(topic).plan.operations if op["op"]=="geometry.transformed_grid"]
        assert matrix in matrices
        assert matrices != [[[1.0,0.0],[0.0,1.0]]]


def test_col_null_states_both_definitions_with_one_projection_scene():
    """4.1.3 用同一个投影 A 分别讲清列空间与零空间：两个案例各占一个窗格。"""
    compiled=_compile("ch04.subspace.col-null")
    ops={op["alias"]:op for op in compiled.plan.operations if op.get("alias")}
    # 列空间是一张盖住所有输出的平面（压淡作参照），不是实心体。
    plane=ops["ch04__entity__column_space"]
    assert plane["op"]=="plane3d.upsert" and plane["normal"]==[0,0,1]
    assert plane["size"]==5.0 and plane["opacity"]==0.08
    assert plane["algebra_visible"] is True and plane["algebra_label"] == "Col(A)"
    # 零空间方向：在所有竖直向量之外、上下各画一小段虚线表示这条轴继续延伸。
    # 画在轴上任意一段都会被同方向的向量完全盖住，所以不能画在向量之间。
    marks=[ops["ch04__entity__null_space"],ops["ch04__entity__null_space__extent_2"]]
    assert all(mark["op"]=="linear3d.upsert" and mark["kind"]=="segment" and mark["style"]=="dashed" for mark in marks)
    assert [[mark["start"],mark["end"]] for mark in marks]==[[[0,0,3.3],[0,0,4.2]],[[0,0,-3.8],[0,0,-2.9]]]
    # 一支垂直于平面的代表输入说明零空间方向。
    kernel=ops["ch04__entity__kernel_vector"]
    assert kernel["end"]==[0,0,3]
    assert kernel["color"] not in {
        plane["color"],marks[0]["color"],
        ops["ch04__entity__input_vector_a"]["color"],ops["ch04__entity__output_vector_a"]["color"],
    }
    # 它被压到同一点：关系不再补一条与箭头完全重合的虚线，而是画出那个「像」。
    collapse=ops["ch04__relation__collapse"]
    assert collapse["op"]=="point3d.upsert" and collapse["coordinates"]==[0,0,0]
    # 轴外输入仍把平面铺开三个方向，输出全部落在平面上。
    inputs={name:ops[f"ch04__entity__input_vector_{name}"]["end"] for name in ("a","b","c")}
    outputs={name:ops[f"ch04__entity__output_vector_{name}"]["end"] for name in ("a","b","c")}
    assert inputs=={"a":[2,0,3],"b":[-1,2,2],"c":[-1,-2,1]}
    assert outputs=={"a":[2,0,0],"b":[-1,2,0],"c":[-1,-2,0]}
    assert all(end[2]==0 for end in outputs.values())
    assert len({(end[0],end[1]) for end in outputs.values()})==3
    # 每支轴外输入都有一条虚线落差连到自己的输出；派生线跟随源向量取色。
    for name in ("a","b","c"):
        drop=ops[f"ch04__relation__projection_{name}"]
        assert drop["op"]=="linear3d.upsert" and drop["kind"]=="segment" and drop["style"]=="dashed"
        assert [drop["start"],drop["end"]]==[inputs[name],outputs[name]]
        assert drop["color"]==ops[f"ch04__entity__input_vector_{name}"]["color"]
    # 平面、方向虚线、输入族、输出族、被压成零的竖直族各一种颜色。
    palette={role:ops[alias]["color"] for role,alias in (
        ("plane","ch04__entity__column_space"),("stub","ch04__entity__null_space"),
        ("input","ch04__entity__input_vector_a"),("output","ch04__entity__output_vector_a"),
        ("kernel","ch04__entity__kernel_vector"),
    )}
    assert len(set(palette.values()))==len(palette)
    assert [stage.id for stage in compiled.storyboard]==[
        "stage.ch04.subspace.col-null.column_space","stage.ch04.subspace.col-null.null_space",
    ]
    # 列空间案例不能只剩 z=0 平面：它必须同时物化三支输入、三支输出和三条投影线。
    column_plan = case_plan(compiled, "stage.ch04.subspace.col-null.column_space")
    column_aliases = {operation["alias"] for operation in column_plan.operations if operation.get("alias")}
    assert {
        "ch04__entity__column_space",
        "ch04__entity__input_vector_a", "ch04__entity__input_vector_b", "ch04__entity__input_vector_c",
        "ch04__entity__output_vector_a", "ch04__entity__output_vector_b", "ch04__entity__output_vector_c",
        "ch04__relation__projection_a", "ch04__relation__projection_b", "ch04__relation__projection_c",
    } <= column_aliases
    # 零空间窗格只放零空间这条主线的对象：那张平面、一支竖直向量、那条方向虚线、原点。
    # 轴外采样向量一律不出现在这里（它们只在列空间窗格），免得「与平面垂直」被读糊。
    from linear_algebra.visualizations.compiler import storyboard_visibility
    null_visible=set(storyboard_visibility(compiled,"stage.ch04.subspace.col-null.null_space")[1])
    assert {"ch04__entity__kernel_vector"} <= null_visible
    assert {"ch04__entity__column_space","ch04__entity__null_space","ch04__entity__zero"} <= null_visible
    assert not null_visible & {
        "ch04__entity__input_vector_a","ch04__entity__output_vector_a","ch04__relation__projection_a",
        "ch04__entity__input_vector_b","ch04__entity__output_vector_b","ch04__relation__projection_b",
        "ch04__entity__input_vector_c","ch04__entity__output_vector_c","ch04__relation__projection_c",
    }
    assert not [alias for alias in null_visible if "input_vector" in alias or "output_vector" in alias]


def test_oblique_basis_draws_both_generators_and_readout_components():
    operations=_compile("ch04.basis.definition").plan.operations
    generators=[op["coordinates"] for op in operations if op.get("alias", "").startswith("ch04__entity__oblique_basis__generator_") and op.get("alias", "").endswith("__end")]
    assert generators==[[1,1],[1,-1]]
    components=[op["coordinates"] for op in operations if op.get("alias", "").startswith("ch04__relation__oblique_readout__component_") and op.get("alias", "").endswith("__end")]
    assert components==[[4,4],[5,3]]


def test_nullspace_chain_uses_weighted_columns_and_ends_at_computed_zero():
    topic="ch04.nullspace.test"
    artifact=_artifact(topic)
    result=Chapter4FamilyCompiler.compile(topic_id=topic,semantics=artifact.visual_semantics,context=RenderContext.default(topic))
    terms=[op for op in result.operations if "nontrivial_solution__term_" in op.get("alias", "")]
    assert [op["start"] for op in terms]==[[0,0,0],[1,0,0],[1,1,0]]
    assert [op["end"] for op in terms]==[[1,0,0],[1,1,0],[0,0,0]]
    assert result.evidence["columns"]==[[1,0,0],[0,1,0],[1,1,0]]
    assert result.evidence["combination_residual"]==[0,0,0]


@pytest.mark.parametrize("topic,role,value", [
    ("ch04.subspace.classification","origin",[1,0,0]),
    # A nonzero offset lying in the plane still contains the origin.
    ("ch04.subspace.classification","affine_counterexample",[[1,0,0],[0,1,0],[1,0,0]]),
    ("ch04.subspace.col-null","column_space",[[0,1]]),
    ("ch04.subspace.col-null","output_vector_a",[3,0]),
])
def test_final_review_corruption_fails_actual_math_not_only_fixture_equality(topic,role,value):
    from linear_algebra.visualizations.families.chapter_04 import _mathematical_evidence
    payload=artifact_payload_for(topic)
    next(e for e in payload["visual_semantics"]["entities"] if e["role"]==role)["value"]=value
    semantics=_artifact(topic,payload).visual_semantics
    with pytest.raises(VisualCompileError):
        _mathematical_evidence(topic,{e.role:e for e in semantics.entities},semantics.relations)


def test_square_failure_is_computed_from_relation_inputs():
    from dataclasses import replace
    from linear_algebra.visualizations.families.chapter_04 import _mathematical_evidence
    topic="ch04.linear-map.compare"; semantics=_artifact(topic).visual_semantics
    relations=tuple(replace(r,parameters={"inputs":[2,3],"separate_sum":13.0,"sum_image":25.0}) if r.id.endswith("square_failure") else r for r in semantics.relations)
    evidence=_mathematical_evidence(topic,{e.role:e for e in semantics.entities},relations)
    assert evidence["square_sum_image"]==25
    assert evidence["square_separate_sum"]==13
    relations=tuple(replace(r,parameters={"inputs":[0,3],"separate_sum":9.0,"sum_image":9.0}) if r.id.endswith("square_failure") else r for r in relations)
    with pytest.raises(VisualCompileError):
        _mathematical_evidence(topic,{e.role:e for e in semantics.entities},relations)


def test_disk_revieweds_are_canonical_and_legacy_index_rows_match_release_baseline():
    import json
    import shutil
    import tempfile
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_chapter_04, compile_reviewed_topic, compiled_resource_store
    root=Path(__file__).resolve().parents[1]
    data=root/"linear_algebra"/"teaching"/"data"
    current=json.loads((data/"index.json").read_text(encoding="utf-8"))
    legacy=lambda payload: [row for row in payload["topics"] if not row["topic_id"].startswith("ch04.")]
    assert current["topic_count"] == len(current["topics"]) == 72
    assert len({row["topic_id"] for row in current["topics"]}) == current["topic_count"]
    assert len([row for row in current["topics"] if row["topic_id"].startswith("ch04.")]) == 14
    # 重新发布第四章只允许改动 ch04 行；其余章节的行必须逐字节保持。
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp=Path(tmpdir)
        (tmp/"revieweds"/"ch04").mkdir(parents=True)
        shutil.copy(data/"index.json", tmp/"index.json")
        shutil.copytree(data/"compiled", tmp/"compiled")
        payloads={topic: artifact_payload_for(topic) for topic in TOPICS}
        compile_chapter_04(output_root=tmp/"compiled", index_path=tmp/"index.json", reviewed_payloads=payloads, reviewed_root=tmp/"revieweds"/"ch04")
        republished=json.loads((tmp/"index.json").read_text(encoding="utf-8"))
    assert json.dumps(legacy(current),sort_keys=True,ensure_ascii=False).encode()==json.dumps(legacy(republished),sort_keys=True,ensure_ascii=False).encode()
    for topic in TOPICS:
        assert json.loads((data/"revieweds"/"ch04"/topic/"r1.json").read_text(encoding="utf-8"))==artifact_payload_for(topic)
        assert compile_reviewed_topic(topic).to_dict()==compiled_resource_store().get(topic).to_dict()
