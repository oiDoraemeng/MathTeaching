"""Immutable typed semantic descriptors for the eight Chapter 5 visuals."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Ch5Spec:
    topic: str; primitive: str; roles: tuple[str,...]; relation: str; params: dict; stages: tuple[str,...]; invariants: tuple[str,...]; operation: str

_TOPICS=("homogeneous.solution-space","affine.solution-set","consistency.geometry","gaussian-elimination","least-squares.projection","fundamental-solution-system","elementary-matrix-elimination","least-squares-derivation")
_SPECS={}
for _id in _TOPICS:
    if _id in ("gaussian-elimination","elementary-matrix-elimination"):
        _SPECS[_id]=Ch5Spec(_id,"geometry.elimination_tableau",("matrix","rhs","tableau"),"maps_to",{"matrix":((1.,2.),(2.,4.)),"rhs":(3.,6.),"operations":((1.,0.),(1.,2.)),"solution_code":2},("initial","eliminated"),("row operations preserve solution set","finite numeric result"),"geometry.elimination_tableau")
    elif _id in ("least-squares.projection","least-squares-derivation"):
        _SPECS[_id]=Ch5Spec(_id,"geometry.least_squares",("data","fit","residual"),"maps_to",{"matrix":((1.,1.),(1.,2.),(1.,3.)),"values":(1.,2.,2.)},("data","projection","residual"),("residual orthogonal to column space","finite numeric result"),"geometry.least_squares")
    elif _id=="consistency.geometry":
        _SPECS[_id]=Ch5Spec(_id,"geometry.elimination_tableau",("matrix","rhs","state"),"maps_to",{"matrix":((1.,0.),(0.,1.)),"rhs":(1.,2.),"solution_code":1},("unique","none","infinite"),("unique/none/infinite executable stages","finite numeric result"),"geometry.elimination_tableau")
    else:
        _SPECS[_id]=Ch5Spec(_id,"geometry.affine_solution",("domain","image","kernel","particular"),"maps_to",{"matrix":((1.,2.),(2.,4.)),"particular":(1.,0.),"nullspace_basis":((-2.,1.),)},("domain","image","kernel","solution"),("domain/image/kernel evidence","finite numeric result"),"geometry.affine_solution")

def spec_for(topic: str)->Ch5Spec:
    return _SPECS[topic]
def specs(): return tuple(_SPECS.values())





