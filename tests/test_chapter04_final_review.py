"""Numerical witnesses and failed-publication recovery regression checks."""
from dataclasses import replace
from pathlib import Path

import pytest

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching import compile_resources as release
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.families.chapter_04 import _mathematical_evidence


@pytest.mark.parametrize("field", ["image_u", "image_v", "sum_image", "scaled_image"])
def test_linear_stretch_recomputes_additivity_and_homogeneity(field):
    topic="ch04.linear-map.definition"
    semantics=TeachingArtifact.from_dict(artifact_payload_for(topic)).visual_semantics
    values={e.role:e for e in semantics.entities}
    evidence=_mathematical_evidence(topic,values,semantics.relations)
    assert evidence["stretch_sum_image"]==[2,1]
    assert evidence["stretch_scaled_image"]==[4,0]
    relations=tuple(replace(r,parameters={**r.parameters,field:[97,99]}) if r.id.endswith("stretch_case") else r for r in semantics.relations)
    with pytest.raises(VisualCompileError,match="stretch_"):
        _mathematical_evidence(topic,values,relations)


def test_oblique_arrows_grid_and_decomposition_share_matrix_columns():
    compiled=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.basis.definition")))
    plan=compiled.plan
    operations={op.get("alias"):op for op in plan.operations}
    prefix="ch04__entity__oblique_basis"
    assert [operations[f"{prefix}__generator_{i}__end"]["coordinates"] for i in (1,2)]==[[1,1],[1,-1]]
    assert [operations[f"{prefix}__generator_{i}__end"]["name"] for i in (1,2)]==["b_1","b_2"]
    relation="ch04__relation__oblique_readout"
    assert operations[f"{relation}__grid"]["op"]=="geometry.basis_grid"
    assert operations[f"{relation}__grid"]["basis_matrix"]==[[1,1],[1,-1]]
    assert operations[f"{relation}__grid"]["bounds"]==[-5,5,-5,5]
    assert operations[f"{relation}__grid"]["alternate_coordinates"]==[4,1]
    assert operations[f"{relation}__component_1__end"]["coordinates"]==[4,4]
    assert operations[f"{relation}__component_2__end"]["coordinates"]==operations[relation]["standard_vector"]==[5,3]
    assert operations[f"{relation}__component_1"]["label"]=="4b_1"
    assert operations[f"{relation}__component_2"]["label"]=="1b_2"

    standard=next(stage for stage in compiled.storyboard if stage.id.endswith(".standard"))
    oblique=next(stage for stage in compiled.storyboard if stage.id.endswith(".oblique"))
    assert "ch04__entity__standard_basis__generator_1" in standard.visible_aliases
    assert "ch04__entity__oblique_basis__generator_1" not in standard.visible_aliases
    assert "ch04__entity__oblique_basis__generator_1" in oblique.visible_aliases
    assert "ch04__entity__standard_basis__generator_1" not in oblique.visible_aliases


def test_dependence_draws_only_algebra_generators_and_combination_result_points():
    compiled=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.dependence.redundancy")))
    operations={op.get("alias"):op for op in compiled.plan.operations}
    assert not [alias for alias in operations if alias and "__relation__" in alias and "__term_" in alias]
    assert [operations[f"ch04__relation__{name}"]["coordinates"] for name in (
        "line_combination", "plane_combination", "independent_combination", "dependent_combination"
    )]==[[2,0,0],[2,-1,0],[1,1,1],[0,0,0]]

    expected_vectors=(
        ("ch04__entity__span_line__generator_1",),
        ("ch04__entity__span_plane__generator_1","ch04__entity__span_plane__generator_2"),
        ("ch04__entity__independent_set__axis_1","ch04__entity__independent_set__axis_2","ch04__entity__independent_set__axis_3"),
        ("ch04__entity__dependent_set__generator_1","ch04__entity__dependent_set__generator_2","ch04__entity__dependent_set__generator_3"),
    )
    for stage,expected in zip(compiled.storyboard,expected_vectors,strict=True):
        visible_vectors=tuple(
            alias for alias in stage.visible_aliases
            if operations.get(alias,{}).get("op")=="linear3d.upsert"
            and operations[alias].get("kind")=="vector"
        )
        assert visible_vectors==expected


def test_dependence_recomputes_each_span_dimension_and_all_four_case_links():
    artifact=TeachingArtifact.from_dict(artifact_payload_for("ch04.dependence.redundancy"))
    compiled=VisualSemanticsCompiler().compile(artifact)
    evidence=compiled.family_evidence
    assert evidence["line_rank"]==1
    assert evidence["plane_rank"]==2
    assert evidence["independent_rank"]==3
    assert evidence["dependent_rank"]==2
    assert all(evidence["invariants"].values())
    assert artifact.explanation.case_layout is not None
    assert artifact.explanation.case_layout.default_pane_count==4
    assert [case.stage_refs for case in artifact.explanation.case_layout.cases]==[
        ("stage.ch04.dependence.redundancy.line",),
        ("stage.ch04.dependence.redundancy.plane",),
        ("stage.ch04.dependence.redundancy.space",),
        ("stage.ch04.dependence.redundancy.dependent",),
    ]


@pytest.mark.parametrize("topic,role,value", [
    ("ch04.basis.definition","same_vector",[5,4]),
    ("ch04.linear-map.definition","stretch_result",[100,100]),
    ("ch04.linear-map.definition","translation_result",[100,100]),
])
def test_geometric_bindings_fail_recomputed_invariants(topic,role,value):
    payload=artifact_payload_for(topic)
    next(e for e in payload["visual_semantics"]["entities"] if e["role"]==role)["value"]=value
    semantics=TeachingArtifact.from_dict(payload).visual_semantics
    with pytest.raises(VisualCompileError,match="recomputed invariant is false"):
        _mathematical_evidence(topic,{e.role:e for e in semantics.entities},semantics.relations)


def test_linear_and_translation_cases_share_bounds_and_distinguish_failed_results():
    plan=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for("ch04.linear-map.definition"))).plan
    ops={op.get("alias"):op for op in plan.operations}
    stretch_grid=ops["ch04__relation__stretch_case__grid"]
    translation_grid=ops["ch04__relation__translation_case__grid"]
    assert stretch_grid["bounds"]==translation_grid["bounds"]
    assert stretch_grid["matrix"]==[[2,0],[0,1]]
    assert translation_grid["origin"]==[1,0]
    assert ops["ch04__relation__translation_case__direct__end"]["coordinates"]==[2,1]
    assert ops["ch04__relation__translation_case__separate__end"]["coordinates"]==[3,1]
    assert ops["ch04__relation__translation_case__direct"]["color"] != ops["ch04__relation__translation_case__separate"]["color"]


def test_col_null_scene_draws_each_object_once_on_the_same_origin():
    """四·一·三 把「所有可能的输出」与「被压到零的输入」画在同一个原点上的同一幅图里。"""
    payload=artifact_payload_for("ch04.subspace.col-null")
    artifact=TeachingArtifact.from_dict(payload)
    plan=VisualSemanticsCompiler().compile(artifact).plan
    ops=[op for op in plan.operations if op.get("alias")]
    planes=[op["alias"] for op in ops if op["op"]=="plane3d.upsert"]
    # 列空间只有一张平面：矩阵本身不再画成一个重合的平面。
    assert planes==["ch04__entity__column_space"]
    # 三支轴外输入 + 三支轴外输出 + 一支垂直于平面的输入都从同一个原点出发。
    vectors=[op for op in ops if op["op"]=="linear3d.upsert" and op["kind"]=="vector"]
    assert len(vectors)==7
    assert all(op["start"]==[0.0,0.0,0.0] for op in vectors)
    # 两个案例各绑定一个舞台，首屏并排显示同一步图形。
    layout=artifact.explanation.case_layout
    assert layout is not None and layout.default_pane_count==2
    assert [case.stage_refs for case in layout.cases]==[
        ("stage.ch04.subspace.col-null.column_space",),
        ("stage.ch04.subspace.col-null.null_space",),
    ]
    assert [(case.id, case.example_ref) for case in layout.cases]==[
        ("case.ch04.subspace.col-null.column-space","example.ch04.subspace.col-null.column-space"),
        ("case.ch04.subspace.col-null.null-space","example.ch04.subspace.col-null.null-space"),
    ]


@pytest.mark.parametrize("kind,nth", [("write",1),("write",3),("write",5),("replace",1),("replace",3),("replace",5)])
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
    # Four compiled resources plus the index produce five staged writes.
    failure_at=min(nth,5) if not existing and kind=="write" else nth
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


@pytest.mark.parametrize("kind,nth", [("write",1),("write",5),("write",9),("replace",1),("replace",5),("replace",9)])
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
    # The complete Chapter 4 release has four reviewed artifacts, four
    # compiled resources, and one aggregate-index write.
    failure_at=min(nth,9) if kind=="write" and not existing else nth
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
