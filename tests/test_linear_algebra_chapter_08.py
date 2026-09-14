import copy
import json
import numpy as np
import pytest

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler

TOPICS = tuple('ch08.' + name for name in ('quadratic.matrix-form','quadratic.level-sets','principal-axis','definiteness','completing-square','congruence-inertia'))

def compile_topic(topic, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload or artifact_payload_for(topic)))

@pytest.mark.parametrize('topic', TOPICS)
def test_six_quadratic_topics_compile(topic):
    compiled = compile_topic(topic)
    assert compiled.plan.operations
    operations={o['alias']:o for o in compiled.plan.operations if o.get('alias')}
    used=set()
    for category in ('entities','relations','stages'):
        for item in artifact_payload_for(topic)['visual_semantics'][category]:
            bound=set(compiled.aliases_for(item['id']))
            assert bound and not used.intersection(bound)
            assert all(not operations[a]['op'].startswith('annotation.') for a in bound)
            used.update(bound)

def test_principal_axis_is_a_real_three_stage_diagonalization():
    compiled = compile_topic('ch08.principal-axis')
    evidence = compiled.family_evidence
    assert evidence['cross_term_after'] < 1e-9
    assert compiled.evidence.cross_term_after_rotation < 1e-9
    assert evidence['endpoint_error'] < 1e-9
    assert [stage.id for stage in compiled.storyboard] == ['original','axes','standard']

@pytest.mark.parametrize('topic', TOPICS)
def test_every_graph_member_and_numeric_leaf_rejects_mutation(topic):
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    graph = original['visual_semantics']
    for category in ('entities','relations','stages'):
        for index,item in enumerate(graph[category]):
            payload=copy.deepcopy(original); del payload['visual_semantics'][category][index]
            with pytest.raises(ValueError): compile_topic(topic,payload)
            fields=('id','role','kind','label') if category=='entities' else ('id','kind','source_ref','target_ref') if category=='relations' else ('id','title','caption','layout')
            for field in fields:
                payload=copy.deepcopy(original); payload['visual_semantics'][category][index][field]+='__bad'
                with pytest.raises(ValueError): compile_topic(topic,payload)

@pytest.mark.parametrize('topic', TOPICS)
def test_principal_numeric_witnesses_are_recomputed(topic):
    payload=artifact_payload_for(topic)
    for category in ('entities','relations'):
        for index,item in enumerate(payload['visual_semantics'][category]):
            target=item.get('value', item.get('parameters',{}))
            if isinstance(target,dict):
                for key in list(target):
                    altered=copy.deepcopy(payload); value=altered['visual_semantics'][category][index]['parameters'][key]
                    if isinstance(value,(int,float)): altered['visual_semantics'][category][index]['parameters'][key]=value+.37
                    else: continue
                    with pytest.raises(ValueError): compile_topic(topic,altered)


def paths(value, prefix=()):
    if isinstance(value,list):
        for i,x in enumerate(value): yield from paths(x,(*prefix,i))
    else: yield prefix

@pytest.mark.parametrize('topic',TOPICS)
def test_every_numeric_leaf_and_parameter_is_required(topic):
    original=artifact_payload_for(topic); compile_topic(topic,original)
    for category in ('entities','relations'):
        for index,record in enumerate(original['visual_semantics'][category]):
            values={'value':record['value']} if category=='entities' else record['parameters']
            for field,value in values.items():
                altered=copy.deepcopy(original); container=altered['visual_semantics'][category][index]
                if category=='relations': container=container['parameters']
                del container[field]
                with pytest.raises(ValueError): compile_topic(topic,altered)
                for path in paths(value):
                    altered=copy.deepcopy(original); container=altered['visual_semantics'][category][index]
                    if category=='relations': container=container['parameters']
                    if path:
                        dest=container[field]
                        for p in path[:-1]: dest=dest[p]
                        dest[path[-1]]+=.37
                    else: container[field]+=.37
                    with pytest.raises(ValueError): compile_topic(topic,altered)

@pytest.mark.parametrize('topic',TOPICS)
def test_every_stage_reference_and_invariant_fails_before_operations(topic,monkeypatch):
    import linear_algebra.visualizations.families.chapter_08 as family
    original=artifact_payload_for(topic); compile_topic(topic,original)
    monkeypatch.setattr(family.QuadraticFamilyCompiler,'compile',lambda *args,**kw:pytest.fail('invalid stage reached geometry'))
    for index,stage in enumerate(original['visual_semantics']['stages']):
        for field in ('input_entity_refs','output_entity_refs','relation_refs','expected_invariants'):
            assert stage[field]
            for pos in range(len(stage[field])):
                for delete in (False,True):
                    altered=copy.deepcopy(original); value=altered['visual_semantics']['stages'][index][field]
                    if delete: del value[pos]
                    else: value[pos]+='__bad'
                    with pytest.raises(ValueError): compile_topic(topic,altered)

@pytest.mark.parametrize('topic',TOPICS)
def test_actual_mainwindow_executes_replays_and_rolls_back(topic):
    from tests.test_scene_command_dispatch import _pane_window
    from ui.designer_window import _SceneCommandHostProxy,_SceneCommandBridge
    from services.scene_commands import SceneCommandService,CommandPlan,CommandError,replay_extended_plan
    window=_pane_window(); target=window.pane_manager.visible_pane_ids()[0]
    proxy=_SceneCommandHostProxy(_SceneCommandBridge(window),target); plan=compile_topic(topic).plan
    assert SceneCommandService(proxy).execute(plan,pane_id=target).valid
    invalid={'op':'linear.upsert','alias':'broken','start':'missing','end':'missing2','kind':'segment'}
    bad=CommandPlan(scene='2d',operations=(*plan.operations,invalid))
    for replay in (False,True):
        with window._using_pane(target): before=window._capture_scene_command_state()
        with pytest.raises(CommandError):
            if replay: replay_extended_plan(bad,proxy)
            else: SceneCommandService(proxy).execute(bad,pane_id=target)
        with window._using_pane(target): assert window._capture_scene_command_state()==before
    assert replay_extended_plan(plan,proxy).valid

def test_canonical_resources_and_index_preserve_63_non_chapter_one_rows():
    import subprocess
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic,compiled_resource_store
    from linear_algebra.visualizations import recipes_for_topics
    data=Path('linear_algebra/teaching/data'); rows=json.loads((data/'index.json').read_text(encoding='utf8'))['topics']
    baseline=json.loads(subprocess.check_output(['git','show','HEAD:linear_algebra/teaching/data/index.json']).decode('utf8'))['topics']
    old=lambda items:[r for r in items if 2<=r['chapter']<=7]
    assert len(old(rows))==63 and old(rows)==old(baseline)
    assert len(rows)==len({r['topic_id'] for r in rows})==90
    by_id={r['topic_id']:r for r in rows}; recipes=recipes_for_topics()
    for topic in TOPICS:
        assert 'draw.'+topic in recipes
        assert artifact_payload_for(topic)==json.loads((data/'revieweds/ch08'/topic/'r1.json').read_text(encoding='utf8'))
        fresh=compile_reviewed_topic(topic).to_dict(); assert fresh==compiled_resource_store().get(topic).to_dict()
        for field in ('source_hash','artifact_digest','contract_digest','plan_digest','compiler_version','render_profile','scene_family','revision'):
            assert fresh[field]==by_id[topic][field]

def test_release_13_files_rolls_back_at_each_replace_and_empty_bundle(tmp_path,monkeypatch):
    import os
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_chapter_08
    index=tmp_path/'index.json'; index.write_bytes(Path('linear_algebra/teaching/data/index.json').read_bytes())
    args=dict(output_root=tmp_path/'compiled',reviewed_root=tmp_path/'reviewed',index_path=index,reviewed_payloads={t:artifact_payload_for(t) for t in TOPICS})
    compile_chapter_08(**args); before={p:p.read_bytes() for p in tmp_path.rglob('*.json')}; assert len(before)==13
    original=os.replace
    for fail_at in range(1,14):
        calls=0
        def fail(source,dest):
            nonlocal calls
            calls+=1
            if calls==fail_at: raise OSError('injected replacement failure')
            return original(source,dest)
        with monkeypatch.context() as patcher:
            patcher.setattr(os,'replace',fail)
            with pytest.raises(OSError): compile_chapter_08(**args)
        assert {p:p.read_bytes() for p in tmp_path.rglob('*.json')}==before
    with pytest.raises(ValueError): compile_chapter_08(**dict(args,reviewed_payloads={}))
    assert {p:p.read_bytes() for p in tmp_path.rglob('*.json')}==before

def test_principal_axes_geometry_uses_three_different_witnesses():
    compiled=compile_topic('ch08.principal-axis'); ops={o['alias']:o for o in compiled.plan.operations if o.get('alias')}
    original=[ops[a] for a in compiled.aliases_for('original')]; axes=[ops[a] for a in compiled.aliases_for('axes')]; standard=[ops[a] for a in compiled.aliases_for('standard')]
    assert original[0]['matrix']==[[5.,-3.],[-3.,5.]]
    assert standard[0]['matrix']==[[8.,0.],[0.,2.]]
    assert any(o['op']=='geometry.staged_transform' for o in axes)

def test_quadratic_contours_never_draw_negative_level_or_cross_hyperbola_gaps():
    from linear_algebra.visualizations.families.quadratic import QuadraticFamilyCompiler
    for matrix in ([[1.,0.],[0.,-1.]], [[1.,0.],[0.,0.]], [[-1.,0.],[0.,-2.]]):
        op=QuadraticFamilyCompiler.compile({'matrix':matrix,'sample_count':4096})['operations'][0]
        for point in op['contour_vertices']: assert np.asarray(point)@matrix@np.asarray(point)==pytest.approx(1.,abs=1e-9)
        for i,j in op['contour_segments']: assert op['contour_vertices'][i][0]*op['contour_vertices'][j][0]>0

@pytest.mark.parametrize('topic',TOPICS)
def test_topic_worked_examples_are_quadratic_not_generic_scalar_fixture(topic):
    from linear_algebra.teaching.examples import verify_worked_example
    artifact=TeachingArtifact.from_dict(artifact_payload_for(topic))
    assert artifact.explanation.worked_examples
    assert all(e.kind=='determinant' and verify_worked_example(e).valid for e in artifact.explanation.worked_examples)
