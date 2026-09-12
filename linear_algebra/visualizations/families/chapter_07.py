"""Descriptor-gated spectral and orthogonal scenes computed from reviewed data."""
from __future__ import annotations
import json
import numpy as np
from ..compiler import CompileIssue, VisualCompileError
from linear_algebra.chapter_07_semantics import spec_for
from .spectral import spectral_evidence
from .orthogonalization import OrthogonalizationFamilyCompiler
from .chapter_06 import _equal

TOL = 1e-9


def _validate(topic, semantics):
    spec = spec_for(topic)
    entities = {e.role: e for e in semantics.entities}
    if tuple(entities) != spec.roles or len(entities) != len(semantics.entities):
        raise ValueError('exact entity roles required')
    dimension = 3 if topic == 'ch07.gram-schmidt' else 2
    if (semantics.scene_kind, semantics.scene_family) != (f'{dimension}d', 'spectral_orthogonal'):
        raise ValueError('scene descriptor mismatch')
    for d in spec.entities:
        e = entities[d.role]
        if (e.id, e.kind, e.dimension, e.label) != (f'entity.{topic}.{d.role}', d.kind, d.dimension, d.label):
            raise ValueError('entity descriptor mismatch')
    if tuple(r.id for r in semantics.relations) != tuple(f'relation.{topic}.{r.name}' for r in spec.relations):
        raise ValueError('relation identities mismatch')
    relations = {d.name: r for d, r in zip(spec.relations, semantics.relations)}
    for d in spec.relations:
        r = relations[d.name]
        if (r.kind, r.source_ref, r.target_ref, set(r.parameters)) != (d.kind, entities[d.source_role].id, entities[d.target_role].id, set(d.parameter_names)):
            raise ValueError('relation descriptor mismatch')
    if tuple(s.id for s in semantics.stages) != tuple(f'stage.{topic}.{s.name}' for s in spec.stages):
        raise ValueError('stage identities mismatch')
    for s, d in zip(semantics.stages, spec.stages):
        if (s.title, s.caption, s.layout, tuple(s.input_entity_refs), tuple(s.output_entity_refs), tuple(s.relation_refs), tuple(s.expected_invariants)) != (
            d.title, spec.formula, d.layout, tuple(entities[r].id for r in d.input_roles), tuple(entities[r].id for r in d.output_roles), tuple(relations[r].id for r in d.relation_names), d.invariants):
            raise ValueError('stage descriptor mismatch')
    v = {role: np.asarray(e.value, dtype=float) for role, e in entities.items()}
    for d in spec.entities:
        if v[d.role].shape != np.asarray(d.value).shape or not np.isfinite(v[d.role]).all():
            raise ValueError('entity numeric shape/finite mismatch')
    evidence = {}
    if topic == 'ch07.eigen.direction':
        evidence['directions'] = {}
        for d in spec.relations:
            params = relations[d.name].parameters
            a, x, y = v[d.name+'_operator'], v[d.source_role], v[d.target_role]
            lam = float(params['eigenvalue'])
            _equal(params['matrix'], a, 'direction matrix')
            _equal(params['vector'], x, 'direction vector')
            _equal(params['output'], y, 'direction output')
            _equal(v[d.name+'_eigenvalue'], [lam, 0.], 'eigenvalue marker')
            if np.linalg.norm(x) <= TOL:
                raise ValueError('zero vector is not an eigenvector')
            _equal(a @ x, lam*x, 'Av=lambda v')
            _equal(y, a @ x, 'eigen direction output')
            spectral = spectral_evidence(a)
            if not any(abs(root.value-lam) < TOL for root in spectral.roots):
                raise ValueError('missing spectral root')
            evidence['directions'][d.name] = {'eigenvalue': lam, 'output': y.tolist()}
    elif topic in ('ch07.eigenspace', 'ch07.characteristic-polynomial'):
        a = v['operator']; spectral = spectral_evidence(a)
        evidence['roots'] = []; evidence['eigenspaces'] = {}
        for name in ('root_2', 'root_3'):
            params = relations[name].parameters; d = next(d for d in spec.relations if d.name == name)
            lam = float(params['eigenvalue']); basis = v[d.target_role]; shifted = a-lam*np.eye(2)
            _equal(params['matrix'], a, 'root matrix')
            _equal(v[name], [lam, 0.], 'root marker')
            _equal(params['shifted'], shifted, 'A-lambda I')
            _equal(params['basis'], basis, 'nullspace basis')
            _equal(shifted @ basis.T, np.zeros((2, len(basis))), 'nullspace equation')
            if np.linalg.matrix_rank(basis, tol=TOL) != len(basis) or 2-np.linalg.matrix_rank(shifted, tol=TOL) != len(basis):
                raise ValueError('nullspace dimension mismatch')
            evidence['roots'].append({'value': lam, 'eigenspace_id': entities[d.target_role].id})
            evidence['eigenspaces'][entities[d.target_role].id] = basis.tolist()
        _equal(sorted(r.value for r in spectral.roots), sorted(r['value'] for r in evidence['roots']), 'all roots bound')
        if topic.endswith('characteristic-polynomial'):
            for name, matrix_role, poly_role in (('polynomial', 'operator', 'polynomial'), ('complex_spectrum', 'complex_operator', 'complex_polynomial')):
                params = relations[name].parameters; matrix = v[matrix_role]
                coeffs = np.poly(matrix)
                roots = sorted(((float(z.real), float(z.imag)) for z in np.linalg.eigvals(matrix)), key=lambda z: (z[0], z[1]))
                _equal(params['matrix'], matrix, 'polynomial matrix')
                _equal(params['coefficients'], coeffs, 'characteristic coefficients')
                _equal(v[poly_role], coeffs, 'polynomial entity')
                _equal(params['roots'], roots, 'polynomial roots')
                if name == 'complex_spectrum':
                    complex_spectral = spectral_evidence(matrix)
                    if complex_spectral.roots or len(complex_spectral.complex_roots) != 2:
                        raise ValueError('complex scene must have no real eigenvectors')
                    _equal(v['complex_roots'], roots, 'complex markers')
                    evidence['complex_roots'] = roots
                    evidence['complex_real_directions'] = []
            evidence['coefficients'] = v['polynomial'].tolist()
    elif topic == 'ch07.diagonalization':
        a, p, inverse, diagonal = (v[r] for r in ('operator', 'basis', 'inverse_basis', 'diagonal'))
        _equal(inverse, np.linalg.inv(p), 'inverse basis')
        if np.allclose(p, np.eye(2), atol=TOL):
            raise ValueError('nontrivial eigenbasis required')
        _equal(diagonal, inverse @ a @ p, 'diagonal similarity')
        _equal(diagonal, np.diag(np.diag(diagonal)), 'independent diagonal scaling')
        matrices = {'change_basis': inverse, 'diagonal_scale': diagonal, 'change_basis_back': p, 'direct_endpoint': a}
        for d in spec.relations:
            params = relations[d.name].parameters
            _equal(params['matrix'], matrices[d.name], 'path matrix')
            _equal(params['input'], v[d.source_role], 'path input')
            _equal(params['output'], v[d.target_role], 'path output')
            _equal(v[d.target_role], matrices[d.name] @ v[d.source_role], 'path endpoint')
        endpoint_error = float(np.linalg.norm(p @ diagonal @ inverse @ v['standard'] - a @ v['standard']))
        if endpoint_error >= TOL:
            raise ValueError('path endpoints differ')
        evidence.update(diagonal=diagonal.tolist(), endpoint=v['endpoint'].tolist(), endpoint_error=endpoint_error)
    elif topic == 'ch07.gram-schmidt':
        params = relations['orthogonalize'].parameters
        if float(params['tolerance']) != TOL:
            raise ValueError('fixed verification tolerance required')
        result = OrthogonalizationFamilyCompiler.compile({'vectors': v['input_vectors'].tolist(), 'tolerance': TOL})
        gs = result['evidence']
        for param, role, computed in (('vectors', 'input_vectors', v['input_vectors']), ('projections', 'projection', gs.projection_components), ('residuals', 'residual', gs.residuals), ('normalized', 'normalized', gs.basis)):
            _equal(params[param], v[role], 'orthogonalization witness')
            _equal(v[role], computed, 'computed '+role)
        _equal(v['input_vectors'], v['projection']+v['residual'], 'input decomposition')
        _equal(gs.basis @ gs.basis.T, np.eye(3), 'orthonormal basis')
        evidence.update(basis=gs.basis.tolist(), projections=[x.tolist() for x in gs.projection_components], residuals=[x.tolist() for x in gs.residuals], orthogonalization=result)
    else:
        params = relations['isometry'].parameters
        q = v['orthogonal_matrix']; a, b = v['vector_a'], v['vector_b']; qa, qb = q @ a, q @ b
        _equal(params['matrix'], q, 'isometry matrix')
        for role in ('vector_a', 'vector_b', 'transformed_a', 'transformed_b'):
            _equal(params[role], v[role], 'isometry vector witness')
        _equal(v['transformed_a'], qa, 'Qa'); _equal(v['transformed_b'], qb, 'Qb')
        _equal(q.T @ q, np.eye(2), 'Q transpose Q')
        _equal(params['gram'], q.T @ q, 'Gram matrix')
        before = [a @ a, b @ b]; after = [qa @ qa, qb @ qb]
        _equal(params['squared_lengths'], before, 'length witnesses'); _equal(after, before, 'length preservation')
        _equal(params['dot'], a @ b, 'dot witness'); _equal(qa @ qb, a @ b, 'angle preservation')
        area = abs(float(np.linalg.det(np.column_stack((a, b)))))
        _equal(params['area'], area, 'area witness')
        _equal(abs(np.linalg.det(np.column_stack((qa, qb)))), area, 'area preservation')
        evidence.update(squared_lengths=before, dot=float(a @ b), area=area, gram=(q.T@q).tolist())
    evidence['invariants'] = {name: True for name in spec.invariants}
    return spec, entities, relations, v, evidence


class _Scene:
    def __init__(self, topic):
        self.topic, self.operations, self.aliases = topic, [], {}

    def add(self, semantic_id, operation):
        self.operations.append(operation)
        self.aliases.setdefault(semantic_id, []).append(operation['alias'])

    def vector(self, semantic_id, vector, alias):
        vector = np.asarray(vector); dim = len(vector); prefix = '3d' if dim == 3 else ''
        if np.linalg.norm(vector) <= TOL:
            self.add(semantic_id, {'op': 'point'+prefix+'.upsert', 'alias': alias, 'coordinates': vector.tolist(), 'name': '0'})
            return
        self.operations.extend(({'op': 'point'+prefix+'.upsert', 'alias': alias+'__start', 'coordinates': [0.]*dim, 'name': ''},
                                {'op': 'point'+prefix+'.upsert', 'alias': alias+'__end', 'coordinates': vector.tolist(), 'name': ''}))
        self.add(semantic_id, {'op': 'linear'+prefix+'.upsert', 'alias': alias, 'start': [0.]*dim if dim == 3 else alias+'__start', 'end': vector.tolist() if dim == 3 else alias+'__end', 'kind': 'vector'})

    def matrix(self, key, matrix, alias):
        self.add(key, {'op': 'geometry.transformed_grid', 'alias': alias, 'matrix': np.asarray(matrix).tolist(), 'bounds': [-3.,3.,-3.,3.], 'step': 1.})

    def subspace(self, key, basis, alias):
        self.add(key, {'op': 'geometry.subspace_region', 'alias': alias, 'basis': np.asarray(basis).tolist(), 'bounds': [-3.,3.,-3.,3.]})

    def polynomial(self, key, coefficients, alias):
        coeffs = np.asarray(coefficients)
        expression = '+'.join(f'({float(c)})*x**{len(coeffs)-1-i}' for i, c in enumerate(coeffs))
        self.add(key, {'op': 'curve.create', 'alias': alias, 'kind': 'explicit', 'expression': expression})

    def roots(self, key, roots, alias):
        for i, point in enumerate(roots):
            self.add(key, {'op': 'point.upsert', 'alias': alias+f'__root_{i}', 'coordinates': list(point), 'name': 'lambda'})

    def transform(self, key, matrix, vector, alias):
        self.add(key, {'op': 'geometry.staged_transform', 'alias': alias, 'matrices': [np.asarray(matrix).tolist()], 'points': [np.asarray(vector).tolist()], 'aliases': [alias+'__point']})


def compile_chapter_07(topic, semantics, context=None):
    try:
        spec, entities, relations, v, evidence = _validate(topic, semantics)
        scene = _Scene(topic)
        for d in spec.entities:
            key = entities[d.role].id; value = v[d.role]; alias = key.replace('.', '_')
            if d.kind == 'matrix': scene.matrix(key, value, alias)
            elif d.kind == 'subspace': scene.subspace(key, value, alias)
            elif d.kind == 'basis':
                for i, vector in enumerate(value): scene.vector(key, vector, alias+f'__{i}')
            elif d.role.endswith('polynomial'): scene.polynomial(key, value, alias)
            elif d.role == 'complex_roots': scene.roots(key, value, alias)
            elif d.kind == 'point': scene.roots(key, [value], alias)
            else: scene.vector(key, value, alias)

        def relation_ops(name, key, alias):
            params = relations[name].parameters
            d = next(d for d in spec.relations if d.name == name)
            if 'eigenvalue' in params and 'basis' in params:
                scene.subspace(key, params['basis'], alias)
            elif 'eigenvalue' in params:
                scene.transform(key, params['matrix'], params['vector'], alias)
            elif 'coefficients' in params:
                scene.polynomial(key, params['coefficients'], alias+'__polynomial')
                scene.roots(key, params['roots'], alias)
            elif 'input' in params:
                scene.transform(key, params['matrix'], params['input'], alias)
            elif name == 'isometry':
                scene.transform(key, params['matrix'], v['vector_a'], alias+'__a')
                scene.transform(key, params['matrix'], v['vector_b'], alias+'__b')
                for label, a, b in (('before', v['vector_a'], v['vector_b']), ('after', v['transformed_a'], v['transformed_b'])):
                    scene.add(key, {'op': 'geometry.oriented_area', 'alias': alias+'__'+label, 'vectors': [a.tolist(), b.tolist()]})
            else:
                result = evidence['orthogonalization']; op = dict(result['operations'][0])
                op['alias'] = alias
                op['aliases'] = [alias+'__'+n for n in ('input', 'projection', 'residual', 'normalized')]
                op['stages'] = [dict(s, id=alias+f'__step_{i}') for i, s in enumerate(op['stages'])]
                scene.add(key, op)
                for i, (vector, foot, residual) in enumerate(zip(v['input_vectors'], v['projection'], v['residual'])):
                    scene.add(key, {'op': 'geometry.projection3d', 'alias': alias+f'__projection_{i}', 'vector': vector.tolist(), 'foot': foot.tolist(), 'residual': residual.tolist(), 'bounds': [-3.,3.,-3.,3.,-3.,3.], 'tolerance': TOL})
        for d in spec.relations:
            relation_ops(d.name, relations[d.name].id, f'{topic}__relation__{d.name}')
        for d, stage in zip(spec.stages, semantics.stages):
            if topic == 'ch07.gram-schmidt':
                for role in d.output_roles:
                    for i, vector in enumerate(v[role]):
                        scene.vector(stage.id, vector, f'{topic}__stage__{d.name}__{i}')
            else:
                for name in d.relation_names:
                    relation_ops(name, stage.id, f'{topic}__stage__{d.name}__{name}')
        evidence.pop('orthogonalization', None)
        # Disk and freshly compiled operations use the same JSON representation.
        return json.loads(json.dumps({'operations': scene.operations, 'aliases': scene.aliases, 'evidence': evidence}))
    except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as error:
        raise VisualCompileError((CompileIssue('invalid_chapter_07_semantics', '$.visual_semantics', str(error)),)) from error
