import numpy as np
import pytest
import copy

from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.chapter_06 import RECIPES
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


def compile_topic(topic, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload or artifact_payload_for(topic)))


def test_chapter6_has_exact_three_recipes():
    assert tuple(recipe.id for recipe in RECIPES) == (
        "draw.ch06.basis-change.motivation",
        "draw.ch06.basis-change.coordinates",
        "draw.ch06.similarity-transform",
    )


def test_similarity_has_exact_coordinate_path_and_endpoint_evidence():
    compiled = compile_topic('ch06.similarity-transform')
    assert tuple(stage.id for stage in compiled.storyboard) == ("change_basis", "apply_operator", "change_basis_back")
    evidence = compiled.family_evidence
    assert evidence['endpoint_error'] < 1e-9
    assert compiled.evidence.endpoint_error < 1e-9
    p, a, b = (np.asarray(evidence[name]) for name in ('basis_matrix', 'operator', 'similar_operator'))
    np.testing.assert_allclose(b, np.linalg.inv(p) @ a @ p, atol=1e-9)


@pytest.mark.parametrize("topic", ["ch06.basis-change.motivation", "ch06.basis-change.coordinates"])
def test_basis_change_rejects_singular_basis(topic):
    payload = artifact_payload_for(topic)
    entity = next(e for e in payload['visual_semantics']['entities'] if e['role'] == 'basis_matrix')
    entity['value'] = [[1, 1], [2, 2]]
    with pytest.raises(ValueError):
        compile_topic(topic, payload)

@pytest.mark.parametrize('topic,field', [('ch06.basis-change.coordinates','matrix'),('ch06.similarity-transform','operator')])
def test_chapter6_corrupted_parameter_rejected(topic,field):
    payload=copy.deepcopy(artifact_payload_for(topic))
    relations=payload['visual_semantics']['relations']
    for rel in relations:
        if field in rel['parameters']:
            rel['parameters'][field][0][0]+=0.37
    with pytest.raises((ValueError, KeyError)):
        compile_topic(topic,payload)

def test_chapter6_index_has_three_rows_and_preserves_previous_chapters():
    import json
    rows=json.loads(open('linear_algebra/teaching/data/index.json',encoding='utf8').read())['topics']
    assert len(rows)==90
    assert sum(row['topic_id'].startswith('ch06.') for row in rows)==3
    assert sum(row['topic_id'].startswith(('ch01.','ch02.','ch03.','ch04.','ch05.')) for row in rows)==75


TOPICS = ('ch06.basis-change.motivation', 'ch06.basis-change.coordinates', 'ch06.similarity-transform')


def bump(value):
    if isinstance(value, list):
        value[0] = bump(value[0])
        return value
    return value + .37


@pytest.mark.parametrize('topic', TOPICS)
def test_all_numeric_witnesses_and_required_graph_parts_reject_mutation(topic):
    original = artifact_payload_for(topic)
    graph = original['visual_semantics']
    # Changing/deleting any reviewed witness must fail, independent of labels.
    for category in ('entities', 'relations', 'stages'):
        for index, record in enumerate(graph[category]):
            payload = copy.deepcopy(original)
            del payload['visual_semantics'][category][index]
            with pytest.raises(ValueError):
                compile_topic(topic, payload)
            if category == 'entities':
                payload = copy.deepcopy(original)
                payload['visual_semantics'][category][index]['value'] = bump(payload['visual_semantics'][category][index]['value'])
                with pytest.raises(ValueError, match='disagrees|invalid|basis'):
                    compile_topic(topic, payload)
            elif category == 'relations':
                for key in record['parameters']:
                    for delete in (False, True):
                        payload = copy.deepcopy(original)
                        params = payload['visual_semantics'][category][index]['parameters']
                        if delete:
                            del params[key]
                        else:
                            params[key] = bump(params[key])
                        with pytest.raises(ValueError):
                            compile_topic(topic, payload)
            else:
                for key in ('input_entity_refs', 'output_entity_refs', 'relation_refs', 'expected_invariants'):
                    members = record[key]
                    assert members, f'{topic} stage {record["id"]} must expose {key}'
                    for member_index in range(len(members)):
                        payload = copy.deepcopy(original)
                        del payload['visual_semantics'][category][index][key][member_index]
                        with pytest.raises(ValueError):
                            compile_topic(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
@pytest.mark.parametrize('field', ('input_entity_refs', 'output_entity_refs', 'relation_refs', 'expected_invariants'))
@pytest.mark.parametrize('action', ('delete', 'mutate'))
def test_every_stage_member_is_checked_before_scene_generation(topic, field, action, monkeypatch):
    from linear_algebra.visualizations.families import chapter_06

    def forbidden_scene(*args, **kwargs):
        pytest.fail('invalid stage reached scene operation generation')

    monkeypatch.setattr(chapter_06, '_Scene', forbidden_scene)
    original = artifact_payload_for(topic)
    for stage_index, stage in enumerate(original['visual_semantics']['stages']):
        assert stage[field], f'{stage["id"]} requires {field}'
        for member_index in range(len(stage[field])):
            payload = copy.deepcopy(original)
            members = payload['visual_semantics']['stages'][stage_index][field]
            if action == 'delete':
                del members[member_index]
            else:
                members[member_index] += '__tampered'
            with pytest.raises(ValueError):
                compile_topic(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_each_graph_object_binds_disjoint_executable_witnesses(topic):
    compiled = compile_topic(topic)
    graph = artifact_payload_for(topic)['visual_semantics']
    operations = {op['alias']: op for op in compiled.plan.operations if op.get('alias')}
    used = set()
    for category in ('entities', 'relations', 'stages'):
        for record in graph[category]:
            aliases = compiled.aliases_for(record['id'])
            assert aliases and not used.intersection(aliases)
            used.update(aliases)
            assert all(a in operations and not operations[a]['op'].startswith('annotation.') for a in aliases)
    for stage in compiled.storyboard:
        assert set(compiled.aliases_for(stage.id)) <= set(stage.visible_aliases)
    claim = compiled.evidence.for_claim(f'claim.{topic}')
    assert len(claim.entity_ids) == len(graph['entities'])
    assert len(claim.relation_ids) == len(graph['relations'])
    assert len(claim.stage_ids) == len(graph['stages'])


def test_similarity_stages_execute_the_three_correct_matrices():
    compiled = compile_topic('ch06.similarity-transform')
    evidence = compiled.family_evidence
    assert evidence['standard_vector'] == [-1., 3.]
    assert evidence['standard_output'] == [1., 5.]
    assert evidence['alternate_output'] == [3., 2.]
    operations = {op['alias']: op for op in compiled.plan.operations if op.get('alias')}
    expected = ([[1., -1.], [1., 1.]], [[2., 1.], [1., 2.]], [[.5, .5], [-.5, .5]])
    for stage, matrix in zip(compiled.storyboard, expected):
        op = operations[compiled.aliases_for(stage.id)[0]]
        assert op['op'] == 'geometry.staged_transform'
        assert op['matrices'] == [matrix]


def test_different_consistent_example_is_computed_from_artifact():
    topic = 'ch06.basis-change.coordinates'
    payload = artifact_payload_for(topic)
    graph = payload['visual_semantics']
    # A new consistent reading (c=(2,1), x=(5,5)) is not a fixture lookup.
    for e in graph['entities']:
        if e['role'] == 'alternate_coordinates': e['value'] = [2., 1.]
        if e['role'] == 'standard_vector': e['value'] = [5., 5.]
    forward, backward = graph['relations']
    forward['parameters'].update(input=[2., 1.], output=[5., 5.])
    backward['parameters'].update(input=[5., 5.], output=[2., 1.])
    evidence = compile_topic(topic, payload).family_evidence
    assert evidence['alternate_coordinates'] == [2., 1.]
    assert evidence['standard_vector'] == [5., 5.]


def test_canonical_resources_index_and_prior_54_non_chapter_one_rows_are_preserved():
    import json
    import subprocess
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic, compiled_resource_store
    data = Path('linear_algebra/teaching/data')
    baseline = json.loads(subprocess.check_output(['git', 'show', 'HEAD:linear_algebra/teaching/data/index.json']).decode('utf8'))
    rows = json.loads((data/'index.json').read_text(encoding='utf8'))['topics']
    legacy = lambda rs: [r for r in rs if r['topic_id'].startswith(('ch02.', 'ch03.', 'ch04.', 'ch05.'))]
    assert len(legacy(rows)) == 54
    assert legacy(rows) == legacy(baseline['topics'])
    assert len(rows) == len({r['topic_id'] for r in rows}) == 90
    assert sum(r['topic_id'].startswith('ch07.') for r in rows) == 6
    assert sum(r['topic_id'].startswith('ch08.') for r in rows) == 6
    by_id = {r['topic_id']: r for r in rows}
    for topic in TOPICS:
        assert json.loads((data/'revieweds/ch06'/topic/'r1.json').read_text(encoding='utf8')) == artifact_payload_for(topic)
        resource = compile_reviewed_topic(topic).to_dict()
        assert resource == compiled_resource_store().get(topic).to_dict()
        for key in ('revision', 'artifact_digest', 'source_hash', 'compiler_version', 'render_profile', 'plan_digest', 'contract_digest', 'scene_family'):
            assert resource[key] == by_id[topic][key]


def test_seven_file_release_restores_bytes_after_every_replacement_failure(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    from linear_algebra.teaching.compile_resources import compile_chapter_06
    index = tmp_path/'index.json'
    index.write_bytes(Path('linear_algebra/teaching/data/index.json').read_bytes())
    payloads = {topic: artifact_payload_for(topic) for topic in TOPICS}
    args = dict(output_root=tmp_path/'compiled', index_path=index, reviewed_root=tmp_path/'reviewed', reviewed_payloads=payloads)
    compile_chapter_06(**args)
    before = {path: path.read_bytes() for path in tmp_path.rglob('*.json')}
    assert len(before) == 7
    original_replace = os.replace
    for fail_at in range(1, 8):
        calls = 0
        def replace(source, destination):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise OSError('injected replacement failure')
            return original_replace(source, destination)
        with monkeypatch.context() as patcher:
            patcher.setattr(os, 'replace', replace)
            with pytest.raises(OSError):
                compile_chapter_06(**args)
        assert {path: path.read_bytes() for path in tmp_path.rglob('*.json')} == before


@pytest.mark.parametrize('topic', TOPICS)
def test_actual_mainwindow_host_execute_replay_and_rollback(topic):
    from tests.test_scene_command_dispatch import _pane_window
    from ui.designer_window import _SceneCommandBridge, _SceneCommandHostProxy
    from services.scene_commands import SceneCommandService, CommandPlan, CommandError, replay_extended_plan
    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    proxy = _SceneCommandHostProxy(_SceneCommandBridge(window))
    plan = compile_topic(topic).plan
    SceneCommandService(proxy).execute(plan, pane_id=target)
    with window._using_pane(target):
        before = window._capture_scene_command_state()
    assert before
    invalid = {'op': 'linear.upsert', 'alias': 'broken_ch6', 'start': 'missing', 'end': 'missing_too', 'kind': 'segment'}
    with pytest.raises(CommandError):
        SceneCommandService(proxy).execute(CommandPlan(scene='2d', operations=(*plan.operations, invalid)), pane_id=target)
    with window._using_pane(target):
        assert window._capture_scene_command_state() == before
    # Replay uses the same actual MainWindow proxy (active pane), not a recorder.
    replay_extended_plan(plan, proxy)


def numeric_paths(value, prefix=()):
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from numeric_paths(item, (*prefix, index))
    else:
        yield prefix


@pytest.mark.parametrize('topic', TOPICS)
def test_every_relation_numeric_leaf_is_a_checked_witness(topic):
    original = artifact_payload_for(topic)
    for index, relation in enumerate(original['visual_semantics']['relations']):
        for name, value in relation['parameters'].items():
            for path in numeric_paths(value):
                payload = copy.deepcopy(original)
                target = payload['visual_semantics']['relations'][index]['parameters'][name]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] += .37
                with pytest.raises(ValueError):
                    compile_topic(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_stage_title_and_caption_are_descriptor_bound(topic):
    original = artifact_payload_for(topic)
    for index in range(len(original['visual_semantics']['stages'])):
        for field, value in (('title', 'tampered title'), ('caption', 'tampered caption')):
            payload = copy.deepcopy(original)
            payload['visual_semantics']['stages'][index][field] = value
            with pytest.raises(ValueError, match='title/caption'):
                compile_topic(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_worked_examples_show_the_reviewed_coordinate_calculations(topic):
    from linear_algebra.teaching.examples import verify_worked_example
    artifact = TeachingArtifact.from_dict(artifact_payload_for(topic))
    assert all(e.kind == 'matrix_transform' for e in artifact.explanation.worked_examples)
    assert all(verify_worked_example(e).valid for e in artifact.explanation.worked_examples)


def test_empty_release_rejected_before_writing(tmp_path):
    from linear_algebra.teaching.compile_resources import compile_chapter_06
    with pytest.raises(ValueError, match='exactly 3'):
        compile_chapter_06(output_root=tmp_path/'compiled', reviewed_payloads={})
    assert list(tmp_path.rglob('*')) == []
