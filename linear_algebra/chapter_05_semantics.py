"""Chapter 5 numerical examples and closed visual contracts.

Row-operation records are [target, source, factor]. Source -1 denotes a
nonzero row scaling; other records subtract factor times the source row.
"""
from dataclasses import dataclass
from copy import deepcopy


@dataclass(frozen=True)
class Ch5Spec:
    topic: str
    primitive: str
    roles: tuple[str, ...]
    role_kinds: tuple[tuple[str, str], ...]
    relation: str
    params: dict
    stages: tuple[str, ...]
    invariants: tuple[str, ...]
    operation: str

    def kind_for(self, role):
        return dict(self.role_kinds)[role]

    def dimension_for(self, role):
        return 3 if self.operation == 'geometry.least_squares' and role in ('values', 'data', 'fit', 'residual') else 2


def _spec(topic, operation, roles, relation, params, stages, invariants):
    kinds = {'matrix': 'matrix', 'normal_matrix': 'matrix', 'none_matrix': 'matrix', 'infinite_matrix': 'matrix', 'tableau': 'matrix',
             'nullspace': 'basis', 'solution_set': 'affine_set', 'elementary_matrices': 'matrix',
             'solution_state': 'constraint'}
    return Ch5Spec(topic, operation, tuple(roles), tuple((role, kinds.get(role, 'vector')) for role in roles),
                   relation, params, tuple(stages), (*invariants, 'finite numeric result'), operation)


_SPECS = {}
for topic, homogeneous in (('homogeneous.solution-space', True), ('affine.solution-set', False), ('fundamental-solution-system', False)):
    particular = [0., 0.] if homogeneous else [3., 0.]
    params = {'matrix': [[1., 2.], [2., 4.]], 'rhs': [0., 0.] if homogeneous else [3., 6.],
              'nullspace_basis': [[-2., 1.]], 'particular': particular, 'solution_code': 0. if homogeneous else 1.}
    roles = ['matrix', 'rhs', 'particular', 'nullspace', 'solution_set']
    stages = ('domain', 'kernel', 'solution') if homogeneous else ('homogeneous', 'translation', 'solution')
    invariants = ('domain/image/kernel evidence', 'A x_p = b and A N = 0', 'nullspace basis is complete')
    if topic == 'fundamental-solution-system':
        params.update(pivot_columns=[1., 0.], free_variables=[0., 1.])
        roles[2:2] = ['pivot_columns', 'free_variables']
        stages = ('echelon', 'pivots', 'free_variables', 'solution')
        invariants += ('pivot/free variables determine all solutions',)
    _SPECS[topic] = _spec(topic, 'geometry.affine_solution', roles,
                          'null_solution' if homogeneous else 'affine_translation', params, stages, invariants)

_SPECS['consistency.geometry'] = _spec(
    'consistency.geometry', 'geometry.elimination_tableau', ('matrix', 'rhs', 'none_matrix', 'none_rhs', 'infinite_matrix', 'infinite_rhs', 'solution_state'), 'constraint_state',
    {'matrix': [[1., 0.], [0., 1.]], 'rhs': [1., 2.],
     'none_matrix': [[1., 0.], [1., 0.]], 'none_rhs': [1., 2.],
     'infinite_matrix': [[1., 0.], [2., 0.]], 'infinite_rhs': [1., 2.],
     'consistency_states': [1., 0., 2.]}, ('unique', 'none', 'infinite'),
    ('unique/none/infinite executable stages', 'rank and augmented-rank classify consistency'))

_SPECS['gaussian-elimination'] = _spec(
    'gaussian-elimination', 'geometry.elimination_tableau', ('matrix', 'rhs', 'tableau'), 'row_operation',
    {'matrix': [[2., 1.], [4., 3.]], 'rhs': [5., 11.],
     'operations': [[1., 0., 2.], [0., -1., .5], [0., 1., .5]],
     'tableau': [[1., 0.], [0., 1.]], 'solution_code': 1.},
    ('initial', 'eliminate', 'normalize', 'back_substitute'),
    ('row operations preserve solution set', 'each tableau is the previous tableau transformed'))

_SPECS['elementary-matrix-elimination'] = _spec(
    'elementary-matrix-elimination', 'geometry.elimination_tableau',
    ('matrix', 'rhs', 'elementary_matrices', 'tableau'), 'row_operation',
    {'matrix': [[1., 2.], [2., 5.]], 'rhs': [3., 8.],
     'operations': [[0., -1., 2.], [1., 0., 1.], [0., 1., 4.]],
     'elementary_matrices': [[[2., 0.], [0., 1.]], [[1., 0.], [-1., 1.]], [[1., -4.], [0., 1.]]],
     'tableau': [[2., 0.], [0., 1.]], 'solution_code': 1.},
    ('initial', 'elementary_1', 'elementary_2', 'final'),
    ('each elementary matrix realizes one row operation', 'row operations preserve solution set'))

for topic in ('least-squares.projection', 'least-squares-derivation'):
    params = {'matrix': [[1., 1.], [1., 2.], [1., 3.]], 'values': [1., 2., 2.],
              'coefficients': [2./3., .5], 'fit': [7./6., 5./3., 13./6.], 'residual': [-1./6., 1./3., -1./6.]}
    roles = ['matrix', 'values', 'data', 'fit', 'residual']
    stages = ('data', 'projection', 'residual', 'orthogonality')
    invariants = ('residual orthogonal to column space', 'projection plus residual equals data')
    if topic == 'least-squares-derivation':
        params.update(normal_matrix=[[3., 6.], [6., 14.]], normal_rhs=[5., 11.])
        roles = ['matrix', 'values', 'normal_matrix', 'normal_rhs', 'fit', 'residual']
        stages = ('data', 'normal_equations', 'projection', 'residual')
        invariants += ('normal equations A^T A c = A^T b',)
    _SPECS[topic] = _spec(topic, 'geometry.least_squares', roles, 'projects_to', params, stages, invariants)


def spec_for(topic):
    return deepcopy(_SPECS[topic.removeprefix('ch05.')])


def specs():
    return tuple(spec_for(topic) for topic in _SPECS)
