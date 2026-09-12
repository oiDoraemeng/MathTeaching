"""Immutable, topic-specific quadratic witnesses; matrices are not builder fixtures."""
from dataclasses import dataclass
from math import sqrt
from types import MappingProxyType
from linear_algebra.chapter_04_semantics import EntityDescriptor, RelationDescriptor, StageDescriptor

@dataclass(frozen=True)
class Ch8Spec:
    topic: str
    entities: tuple
    relations: tuple
    stages: tuple
    invariants: tuple
    formula: str
    operations: tuple = ('geometry.quadratic_level_set',)
    @property
    def roles(self): return tuple(e.role for e in self.entities)

def e(role, kind, value): return EntityDescriptor(role,kind,2,value,role)
def r(name, source, target, **params): return RelationDescriptor(name,'maps_to',source,target,tuple(params.items()))
def s(name,title,ins,outs,rels,*invs): return StageDescriptor(name,title,'sequence',ins,outs,rels,invs)
H=1/sqrt(2)
A=((5.,-3.),(-3.,5.)); Q=((H,H),(-H,H)); D=((8.,0.),(0.,2.))

SPECS=MappingProxyType({
 'ch08.quadratic.matrix-form': Ch8Spec('ch08.quadratic.matrix-form',
   (e('matrix','matrix',((2.,1.),(1.,3.))),e('coefficients','region',(2.,2.,3.)),e('point','vector',(1.,2.)),e('image','vector',(4.,7.)),e('value','point',(18.,0.))),
   (r('coefficient_map','coefficients','matrix',matrix=((2.,1.),(1.,3.)),coefficients=(2.,2.,3.)),r('evaluation','point','image',matrix=((2.,1.),(1.,3.)),point=(1.,2.),image=(4.,7.),value=18.)),
   (s('coefficients','交叉项拆到两个非对角元',('coefficients',),('matrix',),('coefficient_map',),'symmetric_coefficients'),s('evaluation','二次型数值',('matrix','point'),('image','value'),('evaluation',),'quadratic_evaluation')),
   ('symmetric_coefficients','quadratic_evaluation'),'2x^2+2xy+3y^2=x^T A x'),
 'ch08.quadratic.level-sets': Ch8Spec('ch08.quadratic.level-sets',
   (e('aligned','matrix',((4.,0.),(0.,1.))),e('tilted','matrix',((2.5,1.5),(1.5,2.5))),e('rotation','matrix',((H,-H),(H,H)))),
   (r('level_comparison','aligned','tilted',aligned=((4.,0.),(0.,1.)),tilted=((2.5,1.5),(1.5,2.5)),rotation=((H,-H),(H,H)),eigenvalues=(1.,4.),signature=(2,0,0),level=1.),),
   (s('aligned','无交叉项的椭圆',('aligned',),('aligned',),('level_comparison',),'same_level_shape'),s('tilted','旋转后的倾斜椭圆',('aligned','rotation'),('tilted',),('level_comparison',),'same_level_shape')),
   ('same_level_shape',),'x^T A x=1; B=R A R^T'),
 'ch08.principal-axis': Ch8Spec('ch08.principal-axis',
   (e('matrix','matrix',A),e('axes','matrix',Q),e('standard','matrix',D),e('point','vector',(2.,1.)),e('coordinates','vector',(H,3*H))),
   (r('orthogonal_axes','matrix','axes',matrix=A,axes=Q,eigenvalues=(8.,2.)),r('rotation','point','coordinates',axes=Q,point=(2.,1.),coordinates=(H,3*H)),r('standard_form','matrix','standard',matrix=A,axes=Q,standard=D,signature=(2,0,0))),
   (s('original','原始倾斜二次型',('matrix','point'),('matrix',),('orthogonal_axes',),'axes_are_eigenvectors'),s('axes','正交主轴坐标',('matrix','axes','point'),('axes','coordinates'),('orthogonal_axes','rotation'),'axes_are_eigenvectors','same_quadratic_value'),s('standard','无交叉项标准形',('matrix','axes','coordinates'),('standard',),('standard_form',),'cross_term_zero','same_quadratic_value')),
   ('axes_are_eigenvectors','same_quadratic_value','cross_term_zero'),'Q^T A Q=diag(8,2); x=Qy',('geometry.quadratic_level_set','geometry.staged_transform')),
 'ch08.definiteness': Ch8Spec('ch08.definiteness',
   (e('positive','matrix',((2.,0.),(0.,1.))),e('indefinite','matrix',((1.,0.),(0.,-1.))),e('semidefinite','matrix',((1.,0.),(0.,0.)))),
   (r('positive','positive','positive',matrix=((2.,0.),(0.,1.)),eigenvalues=(1.,2.),signature=(2,0,0)),r('indefinite','indefinite','indefinite',matrix=((1.,0.),(0.,-1.)),eigenvalues=(-1.,1.),signature=(1,1,0)),r('semidefinite','semidefinite','semidefinite',matrix=((1.,0.),(0.,0.)),eigenvalues=(0.,1.),signature=(1,0,1))),
   tuple(s(name,title,(name,),(name,),(name,),name+'_classification') for name,title in (('positive','正定椭圆'),('indefinite','不定双曲线'),('semidefinite','半正定平行直线'))),
   ('positive_classification','indefinite_classification','semidefinite_classification'),'signature=(positive,negative,zero)'),
 'ch08.completing-square': Ch8Spec('ch08.completing-square',
   (e('matrix','matrix',((2.,2.),(2.,5.))),e('substitution','matrix',((1.,-1.),(0.,1.))),e('standard','matrix',((2.,0.),(0.,3.))),e('point','vector',(1.,1.)),e('coordinates','vector',(2.,1.))),
   (r('complete_square','matrix','standard',matrix=((2.,2.),(2.,5.)),substitution=((1.,-1.),(0.,1.)),standard=((2.,0.),(0.,3.)),square_weights=(2.,3.)),r('substitution','coordinates','point',substitution=((1.,-1.),(0.,1.)),coordinates=(2.,1.),point=(1.,1.),value=11.)),
   (s('original','原始交叉项',('matrix','point'),('matrix',),('complete_square',),'completed_square'),s('substitution','可逆非正交替换',('matrix','substitution','coordinates'),('point',),('substitution',),'value_preserved'),s('squares','两个完全平方',('matrix','substitution'),('standard',),('complete_square',),'completed_square')),
   ('completed_square','value_preserved'),'2x^2+4xy+5y^2=2(x+y)^2+3y^2',('geometry.quadratic_level_set','geometry.staged_transform')),
 'ch08.congruence-inertia': Ch8Spec('ch08.congruence-inertia',
   (e('matrix','matrix',((1.,0.),(0.,-1.))),e('substitution','matrix',((2.,1.),(0.,1.))),e('congruent','matrix',((4.,2.),(2.,0.))),e('point','vector',(4.,2.)),e('coordinates','vector',(1.,2.))),
   (r('congruence','matrix','congruent',matrix=((1.,0.),(0.,-1.)),substitution=((2.,1.),(0.,1.)),congruent=((4.,2.),(2.,0.)),signature=(1,1,0),rank=2),r('substitution','coordinates','point',substitution=((2.,1.),(0.,1.)),coordinates=(1.,2.),point=(4.,2.),value=12.)),
   (s('original','原二次型惯性',('matrix',),('matrix',),('congruence',),'inertia_preserved'),s('congruence','非正交合同替换',('matrix','substitution','coordinates'),('congruent','point'),('congruence','substitution'),'inertia_preserved','value_preserved')),
   ('inertia_preserved','value_preserved'),'B=C^T A C; inertia(A)=inertia(B)',('geometry.quadratic_level_set','geometry.staged_transform')),
})
def spec_for(topic): return SPECS[topic if topic.startswith('ch08.') else 'ch08.'+topic]
def specs(): return tuple(SPECS.values())
