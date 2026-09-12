"""Immutable, numerically closed Chapter 7 semantic descriptors."""
from dataclasses import dataclass
from types import MappingProxyType
from linear_algebra.chapter_04_semantics import EntityDescriptor, RelationDescriptor, StageDescriptor

@dataclass(frozen=True)
class Ch7Spec:
    topic: str
    entities: tuple[EntityDescriptor, ...]
    relations: tuple[RelationDescriptor, ...]
    stages: tuple[StageDescriptor, ...]
    invariants: tuple[str, ...]
    formula: str
    operations: tuple[str, ...]
    @property
    def roles(self):
        return tuple(e.role for e in self.entities)

def _e(role, kind, value, dim=2):
    return EntityDescriptor(role, kind, dim, value, role)
def _r(name, source, target, **params):
    return RelationDescriptor(name, 'maps_to', source, target, tuple(params.items()))
def _s(name, title, ins, outs, rels, inv):
    return StageDescriptor(name, title, 'sequence', ins, outs, rels, inv)

A = ((3., 1.), (0., 2.))
P = ((1., -1.), (0., 1.))
PI = ((1., 1.), (0., 1.))
D = ((3., 0.), (0., 2.))
ROT = ((0., -1.), (1., 0.))
INPUT = ((1., 0., 0.), (1., 1., 0.), (1., 1., 1.))
PROJ = ((0., 0., 0.), (1., 0., 0.), (1., 1., 0.))
ORTH = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
Q = ((.6, -.8), (.8, .6))

def _direction():
    entities, relations, stages = [], [], []
    for name, matrix, vector, value in (
        ('stretch', ((2., 0.), (0., -1.)), (1., 0.), 2.),
        ('reverse', ((2., 0.), (0., -1.)), (0., 1.), -1.),
        ('collapse', ((1., 0.), (0., 0.)), (0., 1.), 0.),
    ):
        out = tuple(value * x for x in vector)
        roles = tuple(name + '_' + r for r in ('operator', 'vector', 'output', 'eigenvalue'))
        entities.extend((_e(roles[0], 'matrix', matrix), _e(roles[1], 'vector', vector), _e(roles[2], 'vector', out), _e(roles[3], 'point', (value, 0.))))
        relations.append(_r(name, roles[1], roles[2], matrix=matrix, vector=vector, output=out, eigenvalue=value))
        stages.append(_s(name, {'stretch': '正特征值拉伸', 'reverse': '负特征值反向', 'collapse': '零特征值消失'}[name], (roles[0], roles[1], roles[3]), (roles[2],), (name,), ('Av_equals_lambda_v',)))
    return Ch7Spec('ch07.eigen.direction', tuple(entities), tuple(relations), tuple(stages), ('Av_equals_lambda_v',), 'Av=lambda v', ('geometry.transformed_grid', 'geometry.staged_transform'))

def _spectrum(topic, characteristic):
    entities = [_e('operator', 'matrix', A), _e('root_2', 'point', (2., 0.)), _e('root_3', 'point', (3., 0.)), _e('space_2', 'subspace', ((-1., 1.),)), _e('space_3', 'subspace', ((1., 0.),))]
    relations = [_r('root_2', 'root_2', 'space_2', matrix=A, eigenvalue=2., shifted=((1., 1.), (0., 0.)), basis=((-1., 1.),)), _r('root_3', 'root_3', 'space_3', matrix=A, eigenvalue=3., shifted=((0., 1.), (0., -1.)), basis=((1., 0.),))]
    stages = [_s('nullspace', '特征根对应零空间', ('operator', 'root_2', 'root_3'), ('space_2', 'space_3'), ('root_2', 'root_3'), ('roots_bind_nullspaces',))]
    invariants = ['roots_bind_nullspaces']
    operations = ['geometry.subspace_region']
    if characteristic:
        entities.extend((_e('polynomial', 'region', (1., -5., 6.)), _e('complex_operator', 'matrix', ROT), _e('complex_polynomial', 'region', (1., 0., 1.)), _e('complex_roots', 'region', ((0., -1.), (0., 1.)))))
        relations.extend((_r('polynomial', 'operator', 'polynomial', matrix=A, coefficients=(1., -5., 6.), roots=((2., 0.), (3., 0.))), _r('complex_spectrum', 'complex_operator', 'complex_roots', matrix=ROT, coefficients=(1., 0., 1.), roots=((0., -1.), (0., 1.)))))
        stages.extend((_s('polynomial', '特征多项式实根', ('operator', 'polynomial'), ('root_2', 'root_3'), ('polynomial', 'root_2', 'root_3'), ('polynomial_roots',)), _s('complex', '复根不生成实特征方向', ('complex_operator', 'complex_polynomial'), ('complex_roots',), ('complex_spectrum',), ('complex_has_no_real_directions',))))
        invariants.extend(('polynomial_roots', 'complex_has_no_real_directions'))
        operations.append('curve.create')
    return Ch7Spec(topic, tuple(entities), tuple(relations), tuple(stages), tuple(invariants), 'E_lambda=Null(A-lambda I); p(lambda)=det(A-lambda I)', tuple(operations))

_S = {
    'ch07.eigen.direction': _direction(),
    'ch07.characteristic-polynomial': _spectrum('ch07.characteristic-polynomial', True),
    'ch07.eigenspace': _spectrum('ch07.eigenspace', False),
    'ch07.diagonalization': Ch7Spec('ch07.diagonalization',
        (_e('operator', 'matrix', A), _e('basis', 'matrix', P), _e('inverse_basis', 'matrix', PI), _e('diagonal', 'matrix', D), _e('standard', 'vector', (0., 1.)), _e('coordinates', 'vector', (1., 1.)), _e('scaled', 'vector', (3., 2.)), _e('endpoint', 'vector', (1., 2.))),
        (_r('change_basis', 'standard', 'coordinates', matrix=PI, input=(0., 1.), output=(1., 1.)), _r('diagonal_scale', 'coordinates', 'scaled', matrix=D, input=(1., 1.), output=(3., 2.)), _r('change_basis_back', 'scaled', 'endpoint', matrix=P, input=(3., 2.), output=(1., 2.)), _r('direct_endpoint', 'standard', 'endpoint', matrix=A, input=(0., 1.), output=(1., 2.))),
        (_s('change_basis', '换到特征基', ('standard', 'basis', 'inverse_basis'), ('coordinates',), ('change_basis',), ('inverse_coordinates',)), _s('diagonal_scale', '特征值独立缩放', ('coordinates', 'diagonal', 'operator'), ('scaled',), ('diagonal_scale',), ('diagonal_similarity',)), _s('change_basis_back', '换回标准坐标', ('scaled', 'basis'), ('endpoint',), ('change_basis_back', 'direct_endpoint'), ('endpoint_matches_direct',))),
        ('inverse_coordinates', 'diagonal_similarity', 'endpoint_matches_direct'), 'A=PDP^{-1}', ('geometry.staged_transform', 'geometry.transformed_grid')),
    'ch07.gram-schmidt': Ch7Spec('ch07.gram-schmidt', tuple(_e(r, 'basis', v, 3) for r, v in (('input_vectors', INPUT), ('projection', PROJ), ('residual', ORTH), ('normalized', ORTH))),
        (_r('orthogonalize', 'input_vectors', 'normalized', vectors=INPUT, projections=PROJ, residuals=ORTH, normalized=ORTH, tolerance=1e-9),),
        tuple(_s(name, title, ins, (out,), ('orthogonalize',), (inv,)) for name, title, ins, out, inv in (('input', '原始三维向量', ('input_vectors',), 'input_vectors', 'input_preserved'), ('projection', '投影分量', ('input_vectors', 'normalized'), 'projection', 'projection_subtracted'), ('residual', '正交残差', ('input_vectors', 'projection'), 'residual', 'residual_orthogonal'), ('normalized', '归一化', ('residual',), 'normalized', 'orthonormal_basis'))),
        ('input_preserved', 'projection_subtracted', 'residual_orthogonal', 'orthonormal_basis'), 'u_i=v_i-sum_j proj_qj(v_i); q_i=u_i/||u_i||', ('geometry.orthogonalization', 'geometry.projection3d', 'linear3d.upsert')),
    'ch07.orthogonal-transform': Ch7Spec('ch07.orthogonal-transform',
        (_e('orthogonal_matrix', 'matrix', Q), _e('vector_a', 'vector', (2., 1.)), _e('vector_b', 'vector', (-1., 3.)), _e('transformed_a', 'vector', (.4, 2.2)), _e('transformed_b', 'vector', (-3., 1.))),
        (_r('isometry', 'vector_a', 'transformed_a', matrix=Q, vector_a=(2., 1.), vector_b=(-1., 3.), transformed_a=(.4, 2.2), transformed_b=(-3., 1.), squared_lengths=(5., 10.), dot=1., area=7., gram=((1., 0.), (0., 1.))),),
        (_s('isometry', '正交变换保持长度夹角面积', ('orthogonal_matrix', 'vector_a', 'vector_b'), ('transformed_a', 'transformed_b'), ('isometry',), ('orthogonal_matrix', 'length_preserved', 'angle_preserved', 'area_abs_preserved')),),
        ('orthogonal_matrix', 'length_preserved', 'angle_preserved', 'area_abs_preserved'), 'Q^TQ=I; <Qx,Qy>=<x,y>', ('geometry.transformed_grid', 'geometry.oriented_area')),
}
SPECS = MappingProxyType(_S)
def spec_for(topic):
    return SPECS[topic if topic.startswith('ch07.') else 'ch07.' + topic]
def specs():
    return tuple(SPECS.values())
