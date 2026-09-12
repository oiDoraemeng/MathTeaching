"""Recompute the complete Chapter 6 graph before emitting any operation."""
from __future__ import annotations

import json
import numpy as np
from linear_algebra.chapter_06_semantics import spec_for
from ..compiler import CompileIssue, VisualCompileError
from .coordinates import CoordinateFamilyCompiler

TOL = 1e-9


def _equal(actual, expected, name):
    actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.allclose(actual, expected, atol=TOL, rtol=0):
        raise ValueError(f'{name}: disagrees with numerical evidence')


def _validate(topic, semantics):
    spec = spec_for(topic)
    entities = {e.role: e for e in semantics.entities}
    if set(entities) != set(spec.roles) or len(entities) != len(semantics.entities):
        raise ValueError('exact Chapter 6 entity roles required')
    if semantics.scene_kind != '2d' or semantics.scene_family != 'basis_change':
        raise ValueError('Chapter 6 scene kind/family mismatch')
    for descriptor in spec.entities:
        entity = entities[descriptor.role]
        if (entity.id, entity.kind, entity.dimension) != (f'entity.{topic}.{descriptor.role}', descriptor.kind, descriptor.dimension):
            raise ValueError(f'{descriptor.role}: entity identity/type mismatch')
    if tuple(r.id for r in semantics.relations) != tuple(f'relation.{topic}.{r.name}' for r in spec.relations):
        raise ValueError('exact Chapter 6 relation order/identities required')
    relations = {d.name: r for d, r in zip(spec.relations, semantics.relations)}
    for descriptor in spec.relations:
        relation = relations[descriptor.name]
        if (relation.kind, relation.source_ref, relation.target_ref) != (descriptor.kind, entities[descriptor.source_role].id, entities[descriptor.target_role].id):
            raise ValueError(f'{descriptor.name}: relation endpoints/kind mismatch')
        if set(relation.parameters) != set(descriptor.parameter_names):
            raise ValueError(f'{descriptor.name}: exact parameter set required')
    if tuple(s.id for s in semantics.stages) != tuple(s.name for s in spec.stages):
        raise ValueError('exact ordered Chapter 6 stage IDs required')
    for descriptor, stage in zip(spec.stages, semantics.stages):
        if (stage.layout, stage.input_entity_refs, stage.output_entity_refs, stage.relation_refs, stage.expected_invariants) != (
            descriptor.layout, tuple(entities[r].id for r in descriptor.input_roles), tuple(entities[r].id for r in descriptor.output_roles),
            tuple(relations[r].id for r in descriptor.relation_names), descriptor.invariants):
            raise ValueError(f'{stage.id}: stage references/layout/invariants mismatch')

    values = {role: np.asarray(entity.value, dtype=float) for role, entity in entities.items()}
    p, inverse = values['basis_matrix'], values['inverse_basis']
    x, c = values['standard_vector'], values['alternate_coordinates']
    # Reuse the shared solver; singular bases fail here before any plan exists.
    coordinate = CoordinateFamilyCompiler.compile({'basis_matrix': p.tolist(), 'standard_vector': x.tolist()})['evidence']
    _equal(values['standard_basis'], np.eye(2), 'standard basis')
    _equal(inverse, np.linalg.inv(p), 'inverse basis')
    _equal(p @ inverse, np.eye(2), 'P inverse')
    _equal(inverse @ p, np.eye(2), 'inverse P')
    _equal(c, coordinate.alternate_coordinates, 'alternate coordinates')
    _equal(p @ c, x, 'P c = x')
    if np.allclose(p, np.eye(2), atol=TOL):
        raise ValueError('Chapter 6 requires a genuinely different basis')

    similarity = 'similar_operator' in values
    matrix_by_relation = ({'change_basis': p, 'apply_operator': values['operator'], 'change_basis_back': inverse}
                          if similarity else {'forward': p, 'backward': inverse})
    for descriptor in spec.relations:
        if descriptor.name == 'similarity':
            continue
        relation = relations[descriptor.name]
        params = relation.parameters
        matrix = matrix_by_relation[descriptor.name]
        _equal(params['matrix'], matrix, f'{descriptor.name}.matrix')
        _equal(params['input'], values[descriptor.source_role], f'{descriptor.name}.input')
        _equal(params['output'], matrix @ values[descriptor.source_role], f'{descriptor.name}.output')
        _equal(params['output'], values[descriptor.target_role], f'entity.{descriptor.target_role}')

    evidence = {'basis_matrix': p.tolist(), 'inverse_basis': inverse.tolist(), 'standard_vector': x.tolist(),
                'alternate_coordinates': c.tolist(), 'endpoint_error': float(np.linalg.norm(p @ c - x))}
    if similarity:
        a = values['operator']; b = inverse @ a @ p
        y = a @ x; d = inverse @ y
        params = relations['similarity'].parameters
        for name, expected in (('basis_matrix', p), ('inverse_basis', inverse), ('operator', a), ('similar_operator', b)):
            _equal(params[name], expected, f'similarity.{name}')
        _equal(values['similar_operator'], b, 'similar operator')
        _equal(values['standard_output'], y, 'standard output')
        _equal(values['alternate_output'], d, 'alternate output')
        _equal(b @ c, d, 'B c')
        _equal(p @ d, y, 'same geometric endpoint')
        _equal(np.linalg.det(b), np.linalg.det(a), 'determinant')
        _equal(np.trace(b), np.trace(a), 'trace')
        _equal(np.linalg.matrix_rank(b), np.linalg.matrix_rank(a), 'rank')
        _equal(np.poly(b), np.poly(a), 'characteristic polynomial')
        endpoint_error = float(max(np.linalg.norm(b @ c - d), np.linalg.norm(p @ d - y)))
        if endpoint_error >= TOL:
            raise ValueError('similarity endpoint error exceeds tolerance')
        evidence.update(operator=a.tolist(), similar_operator=b.tolist(), standard_output=y.tolist(), alternate_output=d.tolist(),
                        endpoint_error=endpoint_error, determinant=float(np.linalg.det(a)), trace=float(np.trace(a)),
                        rank=int(np.linalg.matrix_rank(a)), characteristic_polynomial=np.poly(a).tolist())
    evidence['invariants'] = {name: True for name in spec.invariants}
    return spec, entities, relations, values, evidence


class _Scene:
    def __init__(self, topic):
        self.topic, self.operations, self.aliases = topic, [], {}

    def add(self, semantic_id, operation):
        self.operations.append(operation)
        self.aliases.setdefault(semantic_id, []).append(operation['alias'])

    def vector(self, semantic_id, value, alias, origin=(0., 0.)):
        end = (np.asarray(origin) + np.asarray(value)).tolist()
        self.operations.extend(({'op': 'point.upsert', 'alias': alias+'__origin', 'coordinates': list(origin), 'name': ''},
                                {'op': 'point.upsert', 'alias': alias+'__end', 'coordinates': end, 'name': ''}))
        self.add(semantic_id, {'op': 'linear.upsert', 'alias': alias, 'start': alias+'__origin', 'end': alias+'__end', 'kind': 'vector'})

    def matrix(self, semantic_id, matrix, alias):
        self.add(semantic_id, {'op': 'geometry.transformed_grid', 'alias': alias,
                               'matrix': matrix.tolist(), 'bounds': [-3., 3., -3., 3.], 'step': 1.})

    def coordinates(self, semantic_id, basis, vector, alias, primitive):
        result = CoordinateFamilyCompiler.compile({'primitive': primitive, 'basis_matrix': basis.tolist(), 'standard_vector': vector.tolist(),
                                                  'alias_prefix': alias, 'bounds': [-8., 8., -8., 8.]})
        self.add(semantic_id, result['operations'][0])

    def transform(self, semantic_id, matrices, vector, alias):
        self.add(semantic_id, {'op': 'geometry.staged_transform', 'alias': alias, 'matrices': [np.asarray(m).tolist() for m in matrices],
                               'points': [np.asarray(vector).tolist()], 'aliases': [alias+'__point']})


def compile_chapter_06(topic, semantics, context=None):
    try:
        spec, entities, relations, values, evidence = _validate(topic, semantics)
        scene = _Scene(topic)
        for role, entity in entities.items():
            alias = f'{topic}__entity__{role}'
            if role in ('standard_basis', 'basis_matrix'):
                scene.coordinates(entity.id, values[role], values['standard_vector'], alias, 'geometry.basis_grid')
                # Separate translated grids make the two bases visibly distinct.
                scene.add(entity.id, {'op': 'geometry.transformed_grid', 'alias': alias+'__lane', 'matrix': values[role].tolist(),
                                      'origin': [-10., 0.] if role == 'standard_basis' else [10., 0.], 'bounds': [-3., 3., -3., 3.], 'step': 1.})
                scene.vector(entity.id, values['standard_vector'], alias+'__same_vector', (-10., 0.) if role == 'standard_basis' else (10., 0.))
            elif entity.kind == 'matrix':
                scene.matrix(entity.id, values[role], alias)
            else:
                scene.vector(entity.id, values[role], alias)
        for descriptor in spec.relations:
            relation = relations[descriptor.name]
            alias = f'{topic}__relation__{descriptor.name}'
            if descriptor.name == 'similarity':
                scene.transform(relation.id, (values['basis_matrix'], values['operator'], values['inverse_basis']), values['alternate_coordinates'], alias)
            else:
                params = relation.parameters
                scene.transform(relation.id, (params['matrix'],), params['input'], alias)
                if descriptor.name in ('forward', 'backward', 'change_basis', 'change_basis_back'):
                    # P maps c to x; inverse readout solves P c = x, in both directions.
                    out = values['standard_output'] if descriptor.name == 'change_basis_back' else values['standard_vector']
                    scene.coordinates(relation.id, values['basis_matrix'], out, alias+'__readout', 'geometry.coordinate_readout')
        stage_evidence = {}
        for descriptor, stage in zip(spec.stages, semantics.stages):
            relation = relations[descriptor.relation_names[0]]
            alias = f'{topic}__stage__{stage.id}'
            params = relation.parameters
            scene.transform(stage.id, (params['matrix'],), params['input'], alias)
            scene.vector(stage.id, params['output'], alias+'__output')
            stage_evidence[stage.id] = {'matrix': np.asarray(params['matrix']).tolist(), 'input': np.asarray(params['input']).tolist(),
                                        'output': np.asarray(params['output']).tolist(), 'relation_id': relation.id}
        evidence['stages'] = stage_evidence
        return {'operations': json.loads(json.dumps(scene.operations)), 'aliases': {key: tuple(vals) for key, vals in scene.aliases.items()}, 'evidence': evidence}
    except (KeyError, ValueError, TypeError, IndexError, np.linalg.LinAlgError) as error:
        if isinstance(error, VisualCompileError):
            raise
        raise VisualCompileError((CompileIssue('invalid_chapter_06_semantics', '$.visual_semantics', str(error)),)) from error
