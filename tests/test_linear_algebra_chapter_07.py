import copy
import numpy as np
import pytest

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler

TOPICS = tuple('ch07.' + name for name in ('eigen.direction', 'characteristic-polynomial', 'eigenspace', 'diagonalization', 'gram-schmidt', 'orthogonal-transform'))


def compile_topic(topic, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload if payload is not None else artifact_payload_for(topic)))


@pytest.mark.parametrize('topic', TOPICS)
def test_six_topics_compile_to_disjoint_real_evidence(topic):
    compiled = compile_topic(topic)
    operations = {op['alias']: op for op in compiled.plan.operations if op.get('alias')}
    used = set()
    graph = artifact_payload_for(topic)['visual_semantics']
    for category in ('entities', 'relations', 'stages'):
        for item in graph[category]:
            aliases = set(compiled.aliases_for(item['id']))
            assert aliases and not used.intersection(aliases)
            assert all(not operations[a]['op'].startswith('annotation.') for a in aliases)
            used.update(aliases)


def test_diagonalization_is_inverse_then_scale_then_basis():
    compiled = compile_topic('ch07.diagonalization')
    evidence = compiled.family_evidence
    assert evidence['endpoint_error'] < 1e-9
    assert np.allclose(evidence['diagonal'], [[3, 0], [0, 2]])
    assert evidence['endpoint'] == [1., 2.]
    assert [s.id.split('.')[-1] for s in compiled.storyboard] == ['change_basis', 'diagonal_scale', 'change_basis_back']


def numeric_paths(value, prefix=()):
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from numeric_paths(child, (*prefix, index))
    else:
        yield prefix


@pytest.mark.parametrize('topic', TOPICS)
def test_every_entity_and_relation_numeric_leaf_is_checked(topic):
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    for kind in ('entities', 'relations'):
        for index, item in enumerate(original['visual_semantics'][kind]):
            witnesses = {'value': item['value']} if kind == 'entities' else item['parameters']
            for field, value in witnesses.items():
                for path in numeric_paths(value):
                    payload = copy.deepcopy(original)
                    obj = payload['visual_semantics'][kind][index]
                    container = obj if kind == 'entities' else obj['parameters']
                    if path:
                        target = container[field]
                        for part in path[:-1]:
                            target = target[part]
                        target[path[-1]] += .37
                    else:
                        container[field] += .37
                    with pytest.raises(ValueError):
                        compile_topic(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_real_mainwindow_host_execute_replay_and_rollback(topic):
    from tests.test_scene_command_dispatch import _pane_window
    from ui.designer_window import _SceneCommandBridge, _SceneCommandHostProxy
    from services.scene_commands import SceneCommandService, CommandPlan, CommandError, replay_extended_plan
    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    if topic == 'ch07.gram-schmidt':
        from models.scene_mode import SceneMode
        from rendering.geometry_3d_scene import Geometry3DSceneController
        with window._using_pane(target):
            window._pane_scene().scene_mode = SceneMode.THREE_D
            window._pane_scene().geometry3d_controller = Geometry3DSceneController(window._pane_renderer(target))
    proxy = _SceneCommandHostProxy(_SceneCommandBridge(window), target)
    plan = compile_topic(topic).plan
    assert SceneCommandService(proxy).execute(plan, pane_id=target).valid
    with window._using_pane(target):
        before = window._capture_scene_command_state()
    invalid = ({'op': 'geometry.intersection', 'alias': 'broken_ch7', 'first': 'missing', 'second': 'also_missing'} if plan.scene == '3d' else
               {'op': 'linear.upsert', 'alias': 'broken_ch7', 'start': 'missing', 'end': 'missing', 'kind': 'segment'})
    with pytest.raises(CommandError):
        SceneCommandService(proxy).execute(CommandPlan(scene=plan.scene, operations=(*plan.operations, invalid)), pane_id=target)
    with window._using_pane(target):
        assert window._capture_scene_command_state() == before
    replay_extended_plan(plan, proxy)
    with window._using_pane(target):
        before_replay = window._capture_scene_command_state()
    with pytest.raises(CommandError):
        replay_extended_plan(CommandPlan(scene=plan.scene, operations=(*plan.operations, invalid)), proxy)
    with window._using_pane(target):
        assert window._capture_scene_command_state() == before_replay


@pytest.mark.parametrize('topic', TOPICS)
def test_exact_graph_and_every_stage_member_fail_before_operations(topic, monkeypatch):
    from linear_algebra.visualizations.families import chapter_07
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    monkeypatch.setattr(chapter_07, '_Scene', lambda *args: pytest.fail('invalid graph reached operations'))
    graph = original['visual_semantics']
    for category in ('entities', 'relations', 'stages'):
        for index, item in enumerate(graph[category]):
            payload = copy.deepcopy(original)
            del payload['visual_semantics'][category][index]
            with pytest.raises(ValueError):
                compile_topic(topic, payload)
            fields = ('id', 'role', 'kind', 'label') if category == 'entities' else ('id', 'kind', 'source_ref', 'target_ref') if category == 'relations' else ('id', 'title', 'caption', 'layout')
            for field in fields:
                payload = copy.deepcopy(original)
                payload['visual_semantics'][category][index][field] += '__tampered'
                with pytest.raises(ValueError):
                    compile_topic(topic, payload)
            if category == 'relations':
                for field in item['parameters']:
                    payload = copy.deepcopy(original)
                    del payload['visual_semantics'][category][index]['parameters'][field]
                    with pytest.raises(ValueError):
                        compile_topic(topic, payload)
            if category == 'stages':
                for field in ('input_entity_refs', 'output_entity_refs', 'relation_refs', 'expected_invariants'):
                    for member in range(len(item[field])):
                        for delete in (True, False):
                            payload = copy.deepcopy(original)
                            refs = payload['visual_semantics'][category][index][field]
                            if delete: del refs[member]
                            else: refs[member] += '__tampered'
                            with pytest.raises(ValueError):
                                compile_topic(topic, payload)


def test_roots_are_bound_to_nullspaces_and_complex_roots_have_no_directions():
    compiled = compile_topic('ch07.characteristic-polynomial')
    evidence = compiled.family_evidence
    assert [r['value'] for r in evidence['roots']] == [2., 3.]
    assert evidence['coefficients'] == [1., -5., 6.]
    assert evidence['complex_roots'] == [[0., -1.], [0., 1.]]
    assert evidence['complex_real_directions'] == []
    a = np.array([[3., 1.], [0., 2.]])
    for root in evidence['roots']:
        basis = np.array(evidence['eigenspaces'][root['eigenspace_id']])
        assert np.allclose((a-root['value']*np.eye(2)) @ basis.T, 0)
    operations = {op['alias']: op for op in compiled.plan.operations if op.get('alias')}
    for key in ('entity.ch07.characteristic-polynomial.complex_roots', 'relation.ch07.characteristic-polynomial.complex_spectrum', 'stage.ch07.characteristic-polynomial.complex'):
        assert all(operations[alias]['op'] in ('curve.create', 'point.upsert') for alias in compiled.aliases_for(key))


def test_gram_schmidt_and_isometry_have_independent_numeric_witnesses():
    gs = compile_topic('ch07.gram-schmidt').family_evidence
    assert gs['projections'] == [[0.,0.,0.], [1.,0.,0.], [1.,1.,0.]]
    assert gs['residuals'] == gs['basis'] == [[1.,0.,0.], [0.,1.,0.], [0.,0.,1.]]
    iso = compile_topic('ch07.orthogonal-transform').family_evidence
    assert iso['squared_lengths'] == [5.,10.]
    assert iso['dot'] == 1.
    assert iso['area'] == pytest.approx(7.)


@pytest.mark.parametrize('topic', TOPICS)
def test_worked_examples_use_topic_math_and_verify(topic):
    from linear_algebra.teaching.examples import verify_worked_example
    artifact = TeachingArtifact.from_dict(artifact_payload_for(topic))
    assert artifact.explanation.worked_examples
    for example in artifact.explanation.worked_examples:
        assert example.kind in ('matrix_transform', 'determinant', 'inner_product')
        assert verify_worked_example(example).valid


def test_alternative_consistent_diagonalization_is_not_fixture_lookup():
    topic = 'ch07.diagonalization'
    payload = artifact_payload_for(topic)
    values = {'standard': [1.,1.], 'coordinates': [2.,1.], 'scaled': [6.,2.], 'endpoint': [4.,2.]}
    for entity in payload['visual_semantics']['entities']:
        if entity['role'] in values: entity['value'] = values[entity['role']]
    for relation in payload['visual_semantics']['relations']:
        source, target = relation['source_ref'].split('.')[-1], relation['target_ref'].split('.')[-1]
        relation['parameters']['input'] = values[source]
        relation['parameters']['output'] = values[target]
    result = compile_topic(topic, payload)
    assert result.family_evidence['endpoint'] == [4.,2.]
    assert result.family_evidence['endpoint_error'] < 1e-9


def test_registry_and_canonical_publication_preserve_prior_57_non_chapter_one_rows():
    import json
    import subprocess
    from pathlib import Path
    from linear_algebra.visualizations import recipes_for_topics
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic, compiled_resource_store
    data = Path('linear_algebra/teaching/data')
    baseline = json.loads(subprocess.check_output(['git','show','HEAD:linear_algebra/teaching/data/index.json']).decode('utf8'))
    rows = json.loads((data/'index.json').read_text(encoding='utf8'))['topics']
    legacy = lambda records: [r for r in records if 2 <= r['chapter'] <= 6]
    assert len(legacy(rows)) == 57
    assert legacy(rows) == legacy(baseline['topics'])
    assert len(rows) == len({r['topic_id'] for r in rows}) == 90
    assert sum(r['chapter'] == 8 for r in rows) == 6
    recipes = recipes_for_topics()
    by_id = {r['topic_id']: r for r in rows}
    for topic in TOPICS:
        assert 'draw.'+topic in recipes
        assert recipes['draw.'+topic].scene == ('3d' if topic.endswith('gram-schmidt') else '2d')
        payload = artifact_payload_for(topic)
        assert json.loads((data/'revieweds/ch07'/topic/'r1.json').read_text(encoding='utf8')) == payload
        resource = compile_reviewed_topic(topic).to_dict()
        assert resource == compiled_resource_store().get(topic).to_dict()
        for key in ('revision','artifact_digest','source_hash','compiler_version','render_profile','plan_digest','contract_digest','scene_family'):
            assert resource[key] == by_id[topic][key]


def test_thirteen_file_release_is_transactional_at_every_replacement(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_chapter_07
    index = tmp_path/'index.json'
    index.write_bytes(Path('linear_algebra/teaching/data/index.json').read_bytes())
    payloads = {t: artifact_payload_for(t) for t in TOPICS}
    args = dict(output_root=tmp_path/'compiled', index_path=index, reviewed_root=tmp_path/'reviewed', reviewed_payloads=payloads)
    compile_chapter_07(**args)
    before = {p:p.read_bytes() for p in tmp_path.rglob('*.json')}
    assert len(before) == 13
    original = os.replace
    for fail_at in range(1,14):
        calls = 0
        def fail(source, destination):
            nonlocal calls
            calls += 1
            if calls == fail_at: raise OSError('injected replacement failure')
            return original(source, destination)
        with monkeypatch.context() as patcher:
            patcher.setattr(os, 'replace', fail)
            with pytest.raises(OSError): compile_chapter_07(**args)
        assert {p:p.read_bytes() for p in tmp_path.rglob('*.json')} == before
    with pytest.raises(ValueError):
        compile_chapter_07(**dict(args, reviewed_payloads={}))
    assert {p:p.read_bytes() for p in tmp_path.rglob('*.json')} == before
