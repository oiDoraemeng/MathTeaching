"""Immutable mathematical witnesses and stage contracts for Chapter 6."""
from dataclasses import dataclass
from types import MappingProxyType
from linear_algebra.chapter_04_semantics import EntityDescriptor, RelationDescriptor, StageDescriptor

@dataclass(frozen=True)
class Ch6Spec:
    topic: str; entities: tuple[EntityDescriptor,...]; relations: tuple[RelationDescriptor,...]; stages: tuple[StageDescriptor,...]; invariants: tuple[str,...]; formula: str; operations: tuple[str,...]
    @property
    def roles(self): return tuple(e.role for e in self.entities)
    @property
    def relation(self): return self.relations[0].kind

def _entity(role,value,kind='vector'): return EntityDescriptor(role,kind,2,value,role)
def _rel(name,source,target,matrix,input_value,output): return RelationDescriptor(name,'maps_to',source,target,(('matrix',matrix),('input',input_value),('output',output)))
def _make(topic,p,inv,c,x,a=None,b=None,y=None,d=None):
    base=("P inverse P = I","P c = x","P inverse x = c")
    entities=(_entity('standard_basis',((1.,0.),(0.,1.)),'matrix'),_entity('basis_matrix',p,'matrix'),_entity('inverse_basis',inv,'matrix'),_entity('alternate_coordinates',c),_entity('standard_vector',x))
    if a is None:
        rels=(_rel('forward','alternate_coordinates','standard_vector',p,c,x),_rel('backward','standard_vector','alternate_coordinates',inv,x,c))
        stages=(StageDescriptor('forward','新坐标 → 标准坐标','side_by_side',('alternate_coordinates','basis_matrix'),('standard_vector',),('forward',),base),StageDescriptor('backward','标准坐标 → 新坐标','side_by_side',('standard_vector','inverse_basis'),('alternate_coordinates',),('backward',),base))
        return Ch6Spec(topic,entities,rels,stages,base,r'x=Pc,\quad c=P^{-1}x',('geometry.basis_grid','geometry.coordinate_readout'))
    invs=base+("B = P inverse A P","P B c = A P c","similarity preserves determinant rank trace and spectrum")
    entities += (_entity('operator',a,'matrix'),_entity('similar_operator',b,'matrix'),_entity('standard_output',y),_entity('alternate_output',d))
    rels=(_rel('change_basis','alternate_coordinates','standard_vector',p,c,x),_rel('apply_operator','standard_vector','standard_output',a,x,y),_rel('change_basis_back','standard_output','alternate_output',inv,y,d),RelationDescriptor('similarity','composition_order','operator','similar_operator',(('basis_matrix',p),('inverse_basis',inv),('operator',a),('similar_operator',b))))
    stages=tuple(StageDescriptor(n,t,'sequence',i,o,r,invs) for n,t,i,o,r in (('change_basis','P：翻译为标准坐标',('alternate_coordinates','basis_matrix'),('standard_vector',),('change_basis',)),('apply_operator','A：执行线性变换',('standard_vector','operator'),('standard_output',),('apply_operator',)),('change_basis_back','P⁻¹：翻译回新基',('standard_output','inverse_basis'),('alternate_output','similar_operator'),('change_basis_back','similarity'))))
    return Ch6Spec(topic,entities,rels,stages,invs,r'B=P^{-1}AP,\quad c\to Pc\to APc\to P^{-1}APc',('geometry.staged_transform',))

_SPECS=MappingProxyType({'ch06.basis-change.motivation':_make('ch06.basis-change.motivation',((1.,-1.),(1.,1.)),((.5,.5),(-.5,.5)),(2.,3.),(-1.,5.)), 'ch06.basis-change.coordinates':_make('ch06.basis-change.coordinates',((2.,1.),(1.,3.)),((.6,-.2),(-.2,.4)),(1.,2.),(4.,7.)), 'ch06.similarity-transform':_make('ch06.similarity-transform',((1.,-1.),(1.,1.)),((.5,.5),(-.5,.5)),(1.,2.),(-1.,3.),((2.,1.),(1.,2.)),((3.,0.),(0.,1.)),(1.,5.),(3.,2.))})
def spec_for(topic): return _SPECS[topic if topic.startswith('ch06.') else f'ch06.{topic}']
def specs(): return tuple(_SPECS.values())
