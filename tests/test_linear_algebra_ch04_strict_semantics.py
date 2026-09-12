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

TOPICS=tuple(sorted(TOPIC_SEMANTICS))


def _artifact(topic: str, payload: dict | None = None) -> TeachingArtifact:
    return TeachingArtifact.from_dict(payload or artifact_payload_for(topic))


def _compile(topic: str, payload: dict | None = None):
    return VisualSemanticsCompiler().compile(_artifact(topic,payload),contract_for(topic),RenderContext.default(topic))


def test_every_topic_declares_exact_typed_graph_contract_and_claim_coverage():
    assert len(TOPICS)==16
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
 "ch04.basis.span":("too_many",[[1,0],[0,1]]),
 "ch04.dimension.ladder":("volume",[[1,0,0],[0,1,0],[1,1,0]]),
 "ch04.coordinates.readout":("oblique_coordinates",[2,1]),
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
        "ch04.subspace.col-null":[[1.0,0.0],[0.0,0.0]],
        "ch04.linear-map.definition":[[2.0,1.0],[0.0,1.0]],
        "ch04.linear-map.matrix-columns":[[2.0,-1.0],[1.0,3.0]],
        "ch04.kernel-image":[[1.0,0.0],[0.0,0.0]],
    }
    for topic,matrix in expected.items():
        matrices=[op["matrix"] for op in _compile(topic).plan.operations if op["op"]=="geometry.transformed_grid"]
        assert matrix in matrices
        assert matrices != [[[1.0,0.0],[0.0,1.0]]]
