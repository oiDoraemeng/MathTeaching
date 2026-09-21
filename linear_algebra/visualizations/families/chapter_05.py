"""Compile Chapter 5 from checked mathematical witnesses, never role labels alone."""
from __future__ import annotations

import json
import numpy as np
from linear_algebra.chapter_05_semantics import spec_for
from ..compiler import CompileIssue, VisualCompileError
from .tableau import MatrixTableauCompiler, Scale, Eliminate, apply_row_operation
from .least_squares import LeastSquaresFamilyCompiler, least_squares_fit
from .subspace import SubspaceFamilyCompiler

TOL = 1e-9


def _equal(actual, expected, name):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.allclose(a, b, atol=TOL, rtol=0):
        raise ValueError(f'{name}: reviewed value disagrees with computed evidence')


def _state(matrix, rhs):
    rank = int(np.linalg.matrix_rank(matrix, tol=TOL))
    augmented_rank = int(np.linalg.matrix_rank(np.column_stack((matrix, rhs)), tol=TOL))
    state = 'none' if augmented_rank > rank else ('unique' if rank == matrix.shape[1] else 'infinite')
    return state, rank, augmented_rank


def _pivots(matrix):
    work = matrix.copy()
    columns = []
    row = 0
    for col in range(work.shape[1]):
        choices = np.flatnonzero(np.abs(work[row:, col]) > TOL)
        if not len(choices):
            continue
        pivot = row + int(choices[0])
        work[[row, pivot]] = work[[pivot, row]]
        work[row] /= work[row, col]
        for other in range(len(work)):
            if other != row:
                work[other] -= work[other, col] * work[row]
        columns.append(col)
        row += 1
        if row == len(work):
            break
    return columns, work


def _mathematics(topic, semantics):
    """Check the complete graph and recompute every redundant numerical value."""
    spec = spec_for(topic)
    entities = {e.role: e for e in semantics.entities}
    if len(entities) != len(semantics.entities) or set(entities) != set(spec.roles):
        raise ValueError('Chapter 5 requires the exact typed role set')
    if semantics.scene_kind != '2d' or semantics.scene_family != 'affine_solution':
        raise ValueError('Chapter 5 scene kind/family mismatch')
    if len(semantics.relations) != 1:
        raise ValueError('Chapter 5 requires exactly one reviewed relation')
    relation = semantics.relations[0]
    if relation.id != f'relation.{topic}.{spec.relation}' or relation.kind != spec.relation:
        raise ValueError('Chapter 5 relation identity/kind mismatch')
    if (relation.source_ref, relation.target_ref) != (entities[spec.roles[0]].id, entities[spec.roles[-1]].id):
        raise ValueError('Chapter 5 relation endpoint mismatch')
    p = relation.parameters
    if set(p) != set(spec.params):
        raise ValueError('Chapter 5 requires the exact relation parameter set')
    if tuple(s.id for s in semantics.stages) != tuple(f'stage.{topic}.{name}' for name in spec.stages):
        raise ValueError('Chapter 5 stage set or ordering mismatch')
    for stage in semantics.stages:
        if tuple(stage.expected_invariants) != spec.invariants:
            raise ValueError(f'{stage.id}: invariant set mismatch')
        if set(stage.input_entity_refs) != {e.id for e in entities.values()} or set(stage.output_entity_refs) != {e.id for e in entities.values()} or tuple(stage.relation_refs) != (relation.id,):
            raise ValueError(f'{stage.id}: stage evidence references mismatch')
    a = np.asarray(p['matrix'], dtype=float)
    expected = {'matrix': a}
    evidence = {'matrix': a.tolist()}
    if spec.operation == 'geometry.affine_solution':
        b = np.asarray(p['rhs'], dtype=float)
        x = np.asarray(p['particular'], dtype=float)
        n = np.asarray(p['nullspace_basis'], dtype=float)
        _equal(a @ x, b, 'particular')
        _equal(a @ n.T, np.zeros((len(a), len(n))), 'nullspace_basis')
        state, rank, _ = _state(a, b)
        if state != 'infinite' or np.linalg.matrix_rank(n, tol=TOL) != a.shape[1] - rank:
            raise ValueError('nullspace basis is not a complete independent solution basis')
        homogeneous = topic == 'ch05.homogeneous.solution-space'
        _equal(p['solution_code'], 0. if homogeneous else 1., 'solution_code')
        if homogeneous:
            _equal(b, np.zeros(len(a)), 'homogeneous rhs')
            _equal(x, np.zeros(a.shape[1]), 'homogeneous particular')
        elif np.allclose(b, 0., atol=TOL):
            raise ValueError('affine example must have nonzero rhs')
        expected.update(rhs=b, particular=x, nullspace=n, solution_set=x)
        pivots, reduced = _pivots(a)
        if 'pivot_columns' in p:
            mask = np.array([float(i in pivots) for i in range(a.shape[1])])
            _equal(p['pivot_columns'], mask, 'pivot_columns')
            _equal(p['free_variables'], 1. - mask, 'free_variables')
            expected.update(pivot_columns=mask, free_variables=1. - mask)
        evidence.update(rank=rank, nullity=a.shape[1]-rank, particular=x.tolist(),
                        kernel=n.tolist(), image=a[:, pivots].T.tolist(), domain=np.eye(a.shape[1]).tolist(),
                        reduced=reduced.tolist(), rhs=b.tolist())
    elif topic == 'ch05.consistency.geometry':
        cases = []
        codes = []
        for state_name, matrix_key, rhs_key in (('unique', 'matrix', 'rhs'), ('none', 'none_matrix', 'none_rhs'), ('infinite', 'infinite_matrix', 'infinite_rhs')):
            matrix, rhs = np.asarray(p[matrix_key], dtype=float), np.asarray(p[rhs_key], dtype=float)
            computed, rank, augmented_rank = _state(matrix, rhs)
            if computed != state_name:
                raise ValueError(f'{state_name} reviewed system has state {computed}')
            codes.append({'none': 0., 'unique': 1., 'infinite': 2.}[computed])
            expected[matrix_key] = matrix
            expected[rhs_key] = rhs
            cases.append({'matrix': matrix.tolist(), 'rhs': rhs.tolist(), 'state': computed, 'rank': rank, 'augmented_rank': augmented_rank})
        _equal(p['consistency_states'], codes, 'consistency_states')
        expected.update(rhs=p['rhs'], solution_state=codes)
        evidence['cases'] = cases
    elif spec.operation == 'geometry.elimination_tableau':
        b = np.asarray(p['rhs'], dtype=float)
        state, rank, augmented_rank = _state(a, b)
        _equal(p['solution_code'], {'none': 0., 'unique': 1., 'infinite': 2.}[state], 'solution_code')
        matrix, rhs = a.tolist(), b.tolist()
        frames = [(matrix, rhs)]
        operations, elementary = [], []
        for index, raw in enumerate(p['operations']):
            if len(raw) != 3 or raw[0] != int(raw[0]) or raw[1] != int(raw[1]):
                raise ValueError('row operation indices must be integers')
            target, source, factor = int(raw[0]), int(raw[1]), float(raw[2])
            op = Scale(target, factor) if source == -1 else Eliminate(target, source, factor)
            matrix, rhs = apply_row_operation(matrix, rhs, op)
            e, _ = apply_row_operation(np.eye(len(a)).tolist(), [0.] * len(a), op)
            if 'elementary_matrices' in p:
                if index >= len(p['elementary_matrices']):
                    raise ValueError('elementary matrix chain length mismatch')
                _equal(p['elementary_matrices'][index], e, f'elementary_matrices[{index}]')
            elementary.append(e)
            operations.append(op)
            frames.append((matrix, rhs))
        if len(frames) != len(spec.stages):
            raise ValueError('row-operation count differs from storyboard stages')
        if 'elementary_matrices' in p and len(p['elementary_matrices']) != len(operations):
            raise ValueError('elementary matrix chain length mismatch')
        _equal(p['tableau'], matrix, 'tableau')
        if not np.allclose(np.triu(matrix, 1), 0., atol=TOL) or not np.allclose(np.tril(matrix, -1), 0., atol=TOL):
            raise ValueError('elimination must finish with solved diagonal tableau')
        expected.update(rhs=b, tableau=matrix)
        if 'elementary_matrices' in p:
            expected['elementary_matrices'] = elementary[0]
        evidence.update(frames=frames, row_operations=operations, elementary_matrices=elementary,
                        rank=rank, augmented_rank=augmented_rank, state=state, rhs=b.tolist())
    else:
        fit = least_squares_fit(a, p['values'])
        for name in ('coefficients', 'fit', 'residual'):
            _equal(p[name], getattr(fit, name), name)
        expected.update(values=fit.values, fit=fit.fit, residual=fit.residual)
        if 'data' in entities:
            expected['data'] = fit.values
        if 'normal_matrix' in p:
            normal_matrix, normal_rhs = a.T @ a, a.T @ fit.values
            _equal(p['normal_matrix'], normal_matrix, 'normal_matrix')
            _equal(p['normal_rhs'], normal_rhs, 'normal_rhs')
            _equal(normal_matrix @ fit.coefficients, normal_rhs, 'normal equations')
            expected.update(normal_matrix=normal_matrix, normal_rhs=normal_rhs)
        evidence.update(coefficients=fit.coefficients.tolist(), fit=fit.fit.tolist(), residual=fit.residual.tolist(),
                        orthogonality_error=float(np.linalg.norm(a.T @ fit.residual)))
    for role, entity in entities.items():
        if entity.id != f'entity.{topic}.{role}' or entity.kind != spec.kind_for(role) or entity.dimension != spec.dimension_for(role):
            raise ValueError(f'{role}: entity identity/type/dimension mismatch')
        _equal(entity.value, expected[role], f'entity.{role}')
    evidence['invariants'] = {name: True for name in spec.invariants}
    return spec, entities, relation, p, evidence


class _Scene:
    def __init__(self, topic):
        self.topic = topic
        self.operations = []
        self.aliases = {}

    def add(self, semantic_id, operation):
        alias = str(operation['alias'])
        self.operations.append(operation)
        self.aliases.setdefault(semantic_id, []).append(alias)

    def series(self, semantic_id, values, alias):
        values = np.asarray(values, dtype=float).tolist()
        if len(values) == 2:
            points = [[0., 0.], values]
        else:
            points = [[float(index), value] for index, value in enumerate(values)]
        for index, point in enumerate(points):
            self.operations.append({'op': 'point.upsert', 'alias': f'{alias}__point_{index}', 'coordinates': point, 'name': ''})
        for index in range(len(points)-1):
            self.add(semantic_id, {'op': 'linear.upsert', 'alias': alias if index == 0 else f'{alias}__segment_{index}',
                                  'start': f'{alias}__point_{index}', 'end': f'{alias}__point_{index+1}',
                                  'kind': 'vector' if len(values) == 2 else 'segment'})

    def tableau(self, semantic_id, matrix, rhs, alias, operations=(), primitive='geometry.matrix_tableau'):
        compiled = MatrixTableauCompiler.compile({'op': primitive, 'matrix': np.asarray(matrix).tolist(),
                                                  'rhs': np.asarray(rhs).tolist(), 'operations': operations, 'alias_prefix': alias})
        self.add(semantic_id, {**compiled.operations[0], 'alias': alias})

    def affine(self, semantic_id, basis, offset, alias):
        compiled = SubspaceFamilyCompiler.compile({'primitive': 'geometry.affine_solution', 'dimension': 2,
                                                   'basis': np.asarray(basis).tolist(), 'affine_offset': np.asarray(offset).tolist(), 'alias_prefix': alias})
        self.add(semantic_id, dict(compiled.operations[0]))


def compile_chapter_05(topic, semantics):
    try:
        spec, entities, relation, p, evidence = _mathematics(topic, semantics)
        scene = _Scene(topic)
        for role, entity in entities.items():
            alias = f'{topic}__entity__{role}'
            if role == 'nullspace':
                scene.affine(entity.id, entity.value, [0., 0.], alias)
            elif role == 'solution_set':
                scene.affine(entity.id, p['nullspace_basis'], entity.value, alias)
            elif entity.kind == 'matrix':
                if role == 'elementary_matrices':
                    for index, matrix in enumerate(p['elementary_matrices']):
                        scene.tableau(entity.id, matrix, [0., 0.], f'{alias}_{index}')
                else:
                    rhs = p['normal_rhs'] if role == 'normal_matrix' else (evidence['frames'][-1][1] if role == 'tableau' else [0.] * len(entity.value))
                    scene.tableau(entity.id, entity.value, rhs, alias)
            else:
                scene.series(entity.id, entity.value, alias)
        alias = f'{topic}__relation'
        if spec.operation == 'geometry.affine_solution':
            scene.affine(relation.id, p['nullspace_basis'], p['particular'], alias)
            # 定义域、像和核分别使用可执行操作作为证据。
            for name in ('domain', 'image', 'kernel'):
                scene.affine(relation.id, evidence[name], [0., 0.], f'{alias}__{name}')
        elif topic == 'ch05.consistency.geometry':
            for case in evidence['cases']:
                scene.tableau(relation.id, case['matrix'], case['rhs'], f"{alias}__{case['state']}", primitive=spec.operation)
        elif spec.operation == 'geometry.elimination_tableau':
            scene.tableau(relation.id, p['matrix'], p['rhs'], alias, evidence['row_operations'], spec.operation)
        else:
            ls = LeastSquaresFamilyCompiler.compile({'matrix': p['matrix'], 'values': p['values'], 'alias_prefix': alias})
            scene.add(relation.id, ls['operations'][0])
        for index, stage in enumerate(semantics.stages):
            name = spec.stages[index]
            alias = f'{topic}__stage__{name}'
            if topic == 'ch05.consistency.geometry':
                case = evidence['cases'][index]
                scene.tableau(stage.id, case['matrix'], case['rhs'], alias, primitive=spec.operation)
            elif spec.operation == 'geometry.elimination_tableau':
                matrix, rhs = evidence['frames'][index]
                scene.tableau(stage.id, matrix, rhs, alias, primitive=spec.operation)
            elif spec.operation == 'geometry.affine_solution':
                if name == 'domain':
                    scene.affine(stage.id, evidence['domain'], [0., 0.], alias)
                elif name in ('kernel', 'homogeneous'):
                    scene.affine(stage.id, p['nullspace_basis'], [0., 0.], alias)
                elif name == 'echelon':
                    scene.tableau(stage.id, evidence['reduced'], [p['rhs'][0], 0.], alias)
                elif name in ('pivots', 'free_variables'):
                    scene.series(stage.id, p['pivot_columns' if name == 'pivots' else name], alias)
                elif name == 'translation':
                    scene.series(stage.id, p['particular'], alias)
                else:
                    scene.affine(stage.id, p['nullspace_basis'], p['particular'], alias)
            elif name == 'normal_equations':
                scene.tableau(stage.id, p['normal_matrix'], p['normal_rhs'], alias)
            else:
                values = p['values'] if name == 'data' else (p['fit'] if name == 'projection' else p['residual'])
                scene.series(stage.id, values, alias)
        return {'operations': json.loads(json.dumps(scene.operations)), 'aliases': {key: tuple(values) for key, values in scene.aliases.items()}, 'evidence': evidence}
    except (KeyError, TypeError, ValueError, IndexError, np.linalg.LinAlgError) as error:
        if isinstance(error, VisualCompileError):
            raise
        raise VisualCompileError((CompileIssue('invalid_chapter_05_semantics', '$.visual_semantics', str(error)),)) from error
