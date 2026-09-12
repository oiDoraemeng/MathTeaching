"""Negative audits operate on the reviewed graph before any scene host call."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from linear_algebra.chapter_05_semantics import specs
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler, VisualCompileError
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.common import RenderContext

TOPICS = tuple('ch05.' + spec.topic for spec in specs())


def compile_payload(topic, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload or artifact_payload_for(topic)),
                                             contract_for(topic), RenderContext.default(topic))


def numeric_leaves(value, path=()):
    if isinstance(value, (int, float)):
        return [path]
    return [leaf for index, item in enumerate(value) for leaf in numeric_leaves(item, (*path, index))]


PARAM_CASES = [(topic, field, path) for topic in TOPICS
               for field, value in artifact_payload_for(topic)['visual_semantics']['relations'][0]['parameters'].items()
               for path in numeric_leaves(value)]
ENTITY_CASES = [(topic, index, path) for topic in TOPICS
                for index, entity in enumerate(artifact_payload_for(topic)['visual_semantics']['entities'])
                for path in numeric_leaves(entity['value'])]


def mutate_leaf(value, path):
    if not path:
        return value + .75
    value = deepcopy(value)
    container = value
    for index in path[:-1]:
        container = container[index]
    container[path[-1]] += .75
    return value


@pytest.mark.parametrize('topic,field,path', PARAM_CASES)
def test_every_relation_numeric_leaf_is_checked(topic, field, path):
    payload = artifact_payload_for(topic)
    params = payload['visual_semantics']['relations'][0]['parameters']
    params[field] = mutate_leaf(params[field], path)
    with pytest.raises((ValueError, VisualCompileError)):
        compile_payload(topic, payload)


@pytest.mark.parametrize('topic,index,path', ENTITY_CASES)
def test_every_entity_numeric_leaf_is_checked(topic, index, path):
    payload = artifact_payload_for(topic)
    entity = payload['visual_semantics']['entities'][index]
    entity['value'] = mutate_leaf(entity['value'], path)
    with pytest.raises((ValueError, VisualCompileError)):
        compile_payload(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_every_required_field_and_stage_invariant_is_checked(topic):
    original = artifact_payload_for(topic)
    for field in original['visual_semantics']['relations'][0]['parameters']:
        payload = deepcopy(original)
        del payload['visual_semantics']['relations'][0]['parameters'][field]
        with pytest.raises((ValueError, VisualCompileError)):
            compile_payload(topic, payload)
    for index, stage in enumerate(original['visual_semantics']['stages']):
        for invariant in stage['expected_invariants']:
            payload = deepcopy(original)
            payload['visual_semantics']['stages'][index]['expected_invariants'].remove(invariant)
            with pytest.raises((ValueError, VisualCompileError)):
                compile_payload(topic, payload)
    for category in ('entities', 'relations', 'stages'):
        for index in range(len(original['visual_semantics'][category])):
            payload = deepcopy(original)
            del payload['visual_semantics'][category][index]
            with pytest.raises((ValueError, VisualCompileError)):
                compile_payload(topic, payload)


@pytest.mark.parametrize('topic', TOPICS)
def test_all_roles_relations_and_stages_have_disjoint_real_operations(topic):
    compiled = compile_payload(topic)
    payload = artifact_payload_for(topic)
    operations = {op['alias']: op for op in compiled.plan.operations if op.get('alias')}
    used = set()
    for category in ('entities', 'relations', 'stages'):
        for item in payload['visual_semantics'][category]:
            aliases = compiled.aliases_for(item['id'])
            assert aliases
            assert not used.intersection(aliases), (topic, item['id'], aliases)
            used.update(aliases)
            assert all(alias in operations and not operations[alias]['op'].startswith('annotation.') for alias in aliases)
    claim = compiled.evidence.for_claim(f'claim.{topic}')
    assert set(claim.entity_ids) == {e['id'] for e in payload['visual_semantics']['entities']}
    assert set(claim.relation_ids) == {r['id'] for r in payload['visual_semantics']['relations']}
    assert set(claim.stage_ids) == {s['id'] for s in payload['visual_semantics']['stages']}
    for stage in compiled.storyboard:
        assert set(compiled.aliases_for(stage.id)) <= set(stage.visible_aliases)


def test_row_operations_are_distinct_and_elementary_matrices_reproduce_every_frame():
    plans = [compile_payload('ch05.' + name) for name in ('gaussian-elimination', 'elementary-matrix-elimination')]
    assert plans[0].family_evidence['frames'] != plans[1].family_evidence['frames']
    for compiled in plans:
        evidence = compiled.family_evidence
        for index, elementary in enumerate(evidence['elementary_matrices']):
            a, b = evidence['frames'][index]
            next_a, next_b = evidence['frames'][index+1]
            assert np.allclose(np.asarray(elementary) @ a, next_a)
            assert np.allclose(np.asarray(elementary) @ b, next_b)
        stage_ops = [next(op for op in compiled.plan.operations if op.get('alias') == compiled.aliases_for(stage.id)[0]) for stage in compiled.storyboard]
        assert [op['matrix'] for op in stage_ops] == [a for a, b in evidence['frames']]


def test_reviewed_snapshot_and_index_digests_match_and_preserve_legacy():
    import subprocess
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic, compiled_resource_store
    root = Path(__file__).resolve().parents[1]
    data = root / 'linear_algebra/teaching/data'
    current = json.loads((data / 'index.json').read_text(encoding='utf-8'))
    baseline = json.loads(subprocess.check_output(['git', 'show', 'de12b80^:linear_algebra/teaching/data/index.json'], cwd=root).decode('utf-8'))
    legacy = lambda rows: [r for r in rows if r['topic_id'].startswith(('ch01.', 'ch02.', 'ch03.', 'ch04.'))]
    assert len(legacy(current['topics'])) == 70
    assert legacy(current['topics']) == legacy(baseline['topics'])
    rows = {row['topic_id']: row for row in current['topics']}
    assert len([topic for topic in rows if topic.startswith('ch05.')]) == 8
    for topic in TOPICS:
        assert json.loads((data / 'revieweds/ch05' / topic / 'r1.json').read_text(encoding='utf-8')) == artifact_payload_for(topic)
        resource = compile_reviewed_topic(topic).to_dict()
        assert resource == compiled_resource_store().get(topic).to_dict()
        for field in ('artifact_digest', 'plan_digest', 'contract_digest', 'source_hash', 'revision'):
            assert resource[field] == rows[topic][field]


def test_all_seventeen_publication_writes_roll_back(tmp_path, monkeypatch):
    import os
    from linear_algebra.teaching.compile_resources import compile_chapter_05
    data = Path('linear_algebra/teaching/data')
    index = tmp_path / 'index.json'
    index.write_bytes((data / 'index.json').read_bytes())
    reviewed = tmp_path / 'reviewed'
    compiled = tmp_path / 'compiled'
    payloads = {topic: artifact_payload_for(topic) for topic in TOPICS}
    compile_chapter_05(output_root=compiled, reviewed_root=reviewed, index_path=index, reviewed_payloads=payloads)
    files = {path: path.read_bytes() for path in tmp_path.rglob('*.json')}
    assert len(files) == 17
    original = os.replace
    for failure_index in range(1, 18):
        calls = [0]
        def failing(source, target):
            calls[0] += 1
            if calls[0] == failure_index:
                raise OSError('injected release failure')
            return original(source, target)
        with monkeypatch.context() as patcher:
            patcher.setattr(os, 'replace', failing)
            with pytest.raises(OSError):
                compile_chapter_05(output_root=compiled, reviewed_root=reviewed, index_path=index, reviewed_payloads=payloads)
        assert {path: path.read_bytes() for path in tmp_path.rglob('*.json')} == files


def test_empty_release_does_not_fall_back_to_disk_or_write(tmp_path):
    from linear_algebra.teaching.compile_resources import compile_chapter_05
    with pytest.raises(ValueError, match='exactly 8'):
        compile_chapter_05(output_root=tmp_path / 'compiled', reviewed_root=tmp_path / 'reviewed', reviewed_payloads={})
    assert list(tmp_path.rglob('*')) == []


@pytest.mark.parametrize('topic', TOPICS)
def test_host_execute_replay_and_mid_plan_rollback(topic):
    from services.scene_commands import SceneCommandService, replay_extended_plan
    class Host:
        def __init__(self, fail_at=None):
            self.mode = '2d'
            self.committed = [{'op': 'existing-scene'}]
            self.pending = []
            self.fail_at = fail_at
        def begin_scene_command_transaction(self):
            self.pending = []
        def apply_scene_command(self, operation):
            self.pending.append(deepcopy(operation))
            if len(self.pending) == self.fail_at:
                raise RuntimeError('injected renderer failure')
        def commit_scene_command_transaction(self):
            self.committed += self.pending
            self.pending = []
        def rollback_scene_command_transaction(self):
            self.pending = []
    plan = compile_payload(topic).plan
    executed, replayed = Host(), Host()
    SceneCommandService(executed).execute(plan)
    replay_extended_plan(plan, replayed)
    assert executed.committed == replayed.committed
    assert len(executed.committed) > len(plan.operations)
    for runner in (lambda host: SceneCommandService(host).execute(plan), lambda host: replay_extended_plan(plan, host)):
        host = Host(fail_at=len(plan.operations)//2)
        with pytest.raises(RuntimeError, match='injected renderer failure'):
            runner(host)
        assert host.committed == [{'op': 'existing-scene'}]
        assert host.pending == []
