"""Numerical witnesses and failed-publication recovery regression checks."""
from dataclasses import replace
from pathlib import Path

import pytest

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching import compile_resources as release
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.families.chapter_04 import _mathematical_evidence


@pytest.mark.parametrize("role", ["rotation", "stretch", "projection"])
@pytest.mark.parametrize("field", ["origin_image", "image_u", "image_v", "sum_image", "scaled_image"])
def test_linear_examples_recompute_all_three_axioms(role, field):
    topic="ch04.linear-map.compare"
    semantics=TeachingArtifact.from_dict(artifact_payload_for(topic)).visual_semantics
    values={e.role:e for e in semantics.entities}
    evidence=_mathematical_evidence(topic,values,semantics.relations)
    for diagnostic in evidence["linear_diagnostics"].values():
        assert diagnostic["origin"]==[0,0]
        assert diagnostic["sum_image"]==diagnostic["sum_of_images"]
        assert diagnostic["scaled_image"]==diagnostic["scaled_output"]
    relations=tuple(replace(r,parameters={**r.parameters,field:[97,99]}) if r.id.endswith(f"{role}_linear") else r for r in semantics.relations)
    with pytest.raises(VisualCompileError,match="linear_examples_pass_axioms"):
        _mathematical_evidence(topic,values,relations)


def test_oblique_arrows_grid_and_decomposition_share_matrix_columns():
    plan=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.coordinates.readout"))).plan
    operations={op.get("alias"):op for op in plan.operations}
    prefix="ch04__entity__oblique_basis"
    assert [operations[f"{prefix}__generator_{i}__end"]["coordinates"] for i in (1,2)]==[[1,0],[1,1]]
    relation="ch04__relation__oblique_readout"
    assert operations[f"{relation}__grid"]["op"]=="geometry.basis_grid"
    assert operations[f"{relation}__grid"]["basis_matrix"]==[[1,1],[0,1]]
    assert operations[f"{relation}__component_1__end"]["coordinates"]==[1,0]
    assert operations[f"{relation}__component_2__end"]["coordinates"]==operations[relation]["standard_vector"]==[2,1]


def test_dependence_draws_every_weighted_term_as_closed_zero_chain():
    compiled=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.dependence.redundancy")))
    terms=[op for op in compiled.plan.operations if "dependent_combination__term_" in op.get("alias","")]
    assert [op["start"] for op in terms]==[[0,0,0],[1,0,0],[1,1,0]]
    assert [op["end"] for op in terms]==[[1,0,0],[1,1,0],[0,0,0]]


@pytest.mark.parametrize("topic,role,value", [
    ("ch04.dimension.ladder","line",[[0,0,1]]),
    ("ch04.rank-nullity","collapsed",[1,0,0]),
    ("ch04.rank-nullity","nullity",[[1,0,0]]),
    ("ch04.rank-nullity","rank",[[1,0,0],[0,0,1]]),
    ("ch04.rank.collapse","line_image",[[0,1]]),
    ("ch04.linear-map.definition","T_u",[100,100]),
    ("ch04.linear-map.definition","T_v",[100,100]),
])
def test_geometric_bindings_fail_recomputed_invariants(topic,role,value):
    payload=artifact_payload_for(topic)
    next(e for e in payload["visual_semantics"]["entities"] if e["role"]==role)["value"]=value
    semantics=TeachingArtifact.from_dict(payload).visual_semantics
    with pytest.raises(VisualCompileError,match="recomputed invariant is false"):
        _mathematical_evidence(topic,{e.role:e for e in semantics.entities},semantics.relations)


def test_linear_and_nonlinear_examples_have_distinct_geometric_lanes():
    plan=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.linear-map.compare"))).plan
    ops={op.get("alias"):op for op in plan.operations}
    assert [ops[f"ch04__entity__{r}"]["origin"] for r in ("rotation","stretch","projection")]==[[-8,4],[0,4],[8,4]]
    assert ops["ch04__relation__translation_failure__end"]["coordinates"]==[-7,-3]
    assert ops["ch04__relation__constant_failure__end"]["coordinates"]==[8,-2]
    assert ops["ch04__entity__square_map"]["expression"]=="y=(x-(0))^2+(-4)"


def test_col_null_domain_and_codomain_use_separate_origins():
    plan=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.subspace.col-null"))).plan
    ops={op.get("alias"):op for op in plan.operations}
    assert ops["ch04__entity__domain"]["origin"]==[-4,0]
    assert ops["ch04__entity__kernel"]["origin"]==[-4,0]
    assert ops["ch04__entity__column_space"]["origin"]==[4,0]
    assert ops["ch04__entity__codomain"]["origin"]==[4,0]


@pytest.mark.parametrize("kind,nth", [("write",1),("write",10),("write",34),("replace",1),("replace",8),("replace",17)])
@pytest.mark.parametrize("existing", [True,False])
def test_failed_release_restores_every_file_byte_for_byte(tmp_path,monkeypatch,kind,nth,existing):
    output=tmp_path/"compiled"; index=tmp_path/"index.json"
    if existing:
        release.compile_chapter_04(output_root=output,index_path=index)
        # Valid but byte-distinct prior files ensure a partial new release is
        # observable even though its mathematical fixture is unchanged.
        for path in tmp_path.rglob("*.json"):
            path.write_bytes(path.read_bytes()+b" \n")
    before={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    calls=0
    target=Path if kind=="write" else release.os
    name="write_bytes" if kind=="write" else "replace"
    original=getattr(target,name)
    # New destinations have no backup writes, hence only 17 stage writes.
    failure_at=min(nth,17) if not existing and kind=="write" else nth
    def fail_once(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==failure_at:
            raise OSError("injected publication failure")
        return original(*args,**kwargs)
    monkeypatch.setattr(target,name,fail_once)
    with pytest.raises(OSError,match="injected publication failure"):
        release.compile_chapter_04(output_root=output,index_path=index)
    after={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after==before
    assert not list(tmp_path.rglob(".ch04-release-*"))


@pytest.mark.parametrize("kind,nth", [("write",1),("write",32),("write",66),("replace",1),("replace",20),("replace",33)])
@pytest.mark.parametrize("existing", [True,False])
def test_entire_script_rolls_back_reviewed_compiled_and_index(tmp_path,monkeypatch,kind,nth,existing):
    from scripts.release_chapter04 import main
    if existing:
        main(data_root=tmp_path)
        for path in tmp_path.rglob("*.json"):
            path.write_bytes(path.read_bytes()+b" \n")
    before={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    target=Path if kind=="write" else release.os
    name="write_bytes" if kind=="write" else "replace"
    original=getattr(target,name)
    calls=0
    failure_at=min(nth,33) if kind=="write" and not existing else nth
    def fail_once(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==failure_at:
            raise OSError("full release failure")
        return original(*args,**kwargs)
    monkeypatch.setattr(target,name,fail_once)
    with pytest.raises(OSError,match="full release failure"):
        main(data_root=tmp_path)
    assert {str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}==before
    assert not list(tmp_path.rglob(".ch04-release-*"))
