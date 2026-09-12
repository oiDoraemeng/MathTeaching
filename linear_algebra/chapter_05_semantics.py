"""Typed, topic-specific semantic descriptors for Chapter 5."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Ch5Spec:
    topic: str
    primitive: str
    roles: tuple[str, ...]
    role_kinds: tuple[tuple[str, str], ...]
    relation: str
    params: dict[str, Any]
    stages: tuple[str, ...]
    invariants: tuple[str, ...]
    operation: str
    def kind_for(self, role: str) -> str:
        return dict(self.role_kinds)[role]

def _s(topic, primitive, roles, kinds, relation, params, stages, invariants, operation):
    return Ch5Spec(topic, primitive, tuple(roles), tuple(kinds.items()), relation, params, tuple(stages), tuple(invariants), operation)

_SPECS = {
"homogeneous.solution-space": _s("homogeneous.solution-space","geometry.affine_solution",("matrix","rhs","nullspace","solution_set"),{"matrix":"matrix","rhs":"vector","nullspace":"basis","solution_set":"affine_set"},"null_solution",{"matrix":[[1.,2.],[2.,4.]],"rhs":[0.,0.],"nullspace_basis":[[-2.,1.]],"particular":[0.,0.],"solution_code":0.},("domain","kernel","solution"),("domain/image/kernel evidence","homogeneous solutions satisfy A x = 0","finite numeric result"),"geometry.affine_solution"),
"affine.solution-set": _s("affine.solution-set","geometry.affine_solution",("matrix","rhs","particular","nullspace","solution_set"),{"matrix":"matrix","rhs":"vector","particular":"vector","nullspace":"basis","solution_set":"affine_set"},"affine_translation",{"matrix":[[1.,2.],[2.,4.]],"rhs":[3.,6.],"nullspace_basis":[[-2.,1.]],"particular":[3.,0.],"solution_code":1.},("homogeneous","translation","solution"),("domain/image/kernel evidence","A x = b is x_p + ker(A)","finite numeric result"),"geometry.affine_solution"),
"consistency.geometry": _s("consistency.geometry","geometry.elimination_tableau",("matrix","rhs","solution_state"),{"matrix":"matrix","rhs":"vector","solution_state":"constraint"},"constraint_state",{"matrix":[[1.,0.],[0.,1.]],"rhs":[1.,2.],"consistency_states":[[1.,0.,1.],[1.,0.,2.],[1.,1.,1.]]},("unique","none","infinite"),("unique/none/infinite executable stages","rank and augmented-rank classify consistency","finite numeric result"),"geometry.elimination_tableau"),
"gaussian-elimination": _s("gaussian-elimination","geometry.elimination_tableau",("matrix","rhs","tableau"),{"matrix":"matrix","rhs":"vector","tableau":"matrix"},"row_operation",{"matrix":[[1.,2.],[2.,4.]],"rhs":[3.,6.],"operations":[[0.,1.,-2.],[1.,0.,1.]],"solution_code":2.},("initial","eliminate","normalize","back_substitute"),("row operations preserve solution set","each tableau is the previous tableau transformed","finite numeric result"),"geometry.elimination_tableau"),
"least-squares.projection": _s("least-squares.projection","geometry.least_squares",("matrix","values","data","fit","residual"),{"matrix":"matrix","values":"vector","data":"vector","fit":"vector","residual":"vector"},"projects_to",{"matrix":[[1.,1.],[1.,2.],[1.,3.]],"values":[1.,2.,2.],"coefficients":[2./3.,.5],"fit":[1.1666666667,1.6666666667,2.1666666667],"residual":[-.1666666667,.3333333333,-.1666666667]},("data","projection","residual","orthogonality"),("residual orthogonal to column space","projection plus residual equals data","finite numeric result"),"geometry.least_squares"),
"fundamental-solution-system": _s("fundamental-solution-system","geometry.affine_solution",("matrix","rhs","pivot_columns","free_variables","nullspace","particular","solution_set"),{"matrix":"matrix","rhs":"vector","pivot_columns":"vector","free_variables":"vector","nullspace":"basis","particular":"vector","solution_set":"affine_set"},"null_solution",{"matrix":[[1.,2.],[2.,4.]],"rhs":[3.,6.],"pivot_columns":[0.,0.],"free_variables":[1.,0.],"nullspace_basis":[[-2.,1.]],"particular":[3.,0.]},("echelon","pivots","free_variables","solution"),("pivot/free variables determine all solutions","particular plus nullspace basis","finite numeric result"),"geometry.affine_solution"),
"elementary-matrix-elimination": _s("elementary-matrix-elimination","geometry.elimination_tableau",("matrix","rhs","elementary_matrices","tableau"),{"matrix":"matrix","rhs":"vector","elementary_matrices":"basis","tableau":"matrix"},"row_operation",{"matrix":[[1.,2.],[2.,4.]],"rhs":[3.,6.],"operations":[[0.,1.,-2.],[1.,0.,1.]],"elementary_matrices":[[[1.,0.],[-2.,1.]],[[1.,0.],[0.,1.]]],"solution_code":2.},("initial","elementary_1","elementary_2","final"),("each elementary matrix realizes one row operation","row operations preserve solution set","finite numeric result"),"geometry.elimination_tableau"),
"least-squares-derivation": _s("least-squares-derivation","geometry.least_squares",("matrix","values","normal_matrix","normal_rhs","fit","residual"),{"matrix":"matrix","values":"vector","normal_matrix":"matrix","normal_rhs":"vector","fit":"vector","residual":"vector"},"projects_to",{"matrix":[[1.,1.],[1.,2.],[1.,3.]],"values":[1.,2.,2.],"normal_matrix":[[3.,6.],[6.,14.]],"normal_rhs":[5.,11.],"coefficients":[2./3.,.5],"fit":[1.1666666667,1.6666666667,2.1666666667],"residual":[-.1666666667,.3333333333,-.1666666667]},("data","normal_equations","projection","residual"),("normal equations A^T A c = A^T b","residual orthogonal to column space","finite numeric result"),"geometry.least_squares"),
}
def spec_for(topic: str) -> Ch5Spec: return _SPECS[topic]
def specs() -> tuple[Ch5Spec, ...]: return tuple(_SPECS.values())
__all__ = ["Ch5Spec","spec_for","specs"]
