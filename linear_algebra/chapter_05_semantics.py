"""Chapter 5 numerical examples and closed visual contracts.

The five published topics follow lecture sections 5.1--5.5. Row-operation
records use ``[target, source, factor]`` and mean
``R_target <- R_target - factor * R_source``. A transition may contain more
than one row operation so the first Gaussian-elimination arrow can reproduce
the two row updates printed in the lecture.
"""

from copy import deepcopy
from dataclasses import dataclass


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

    def kind_for(self, role: str) -> str:
        return dict(self.role_kinds)[role]

    def dimension_for(self, role: str) -> int:
        return 2


def _spec(topic, operation, roles, relation, params, stages, invariants):
    kinds = {
        "matrix": "matrix",
        "none_matrix": "matrix",
        "tableau": "matrix",
        "nullspace": "basis",
        "solution_set": "affine_set",
        "solution_state": "constraint",
    }
    return Ch5Spec(
        topic,
        operation,
        tuple(roles),
        tuple((role, kinds.get(role, "vector")) for role in roles),
        relation,
        params,
        tuple(stages),
        (*invariants, "finite numeric result"),
        operation,
    )


_SPECS = {
    "homogeneous.solution-space": _spec(
        "homogeneous.solution-space",
        "geometry.affine_solution",
        ("matrix", "rhs", "particular", "nullspace", "solution_set"),
        "null_solution",
        {
            "matrix": [[1.0, 2.0], [2.0, 4.0]],
            "rhs": [0.0, 0.0],
            "nullspace_basis": [[-2.0, 1.0]],
            "particular": [0.0, 0.0],
            "solution_code": 0.0,
        },
        ("solution",),
        (
            "A x = 0 for every displayed solution",
            "the solution line passes through the origin",
            "rank plus nullity equals the number of columns",
        ),
    ),
    "affine.solution-set": _spec(
        "affine.solution-set",
        "geometry.affine_solution",
        ("matrix", "rhs", "particular", "nullspace", "solution_set"),
        "affine_translation",
        {
            "matrix": [[1.0, 2.0], [2.0, 4.0]],
            "rhs": [3.0, 6.0],
            "nullspace_basis": [[-2.0, 1.0]],
            "particular": [3.0, 0.0],
            "solution_code": 1.0,
        },
        ("homogeneous", "solution"),
        (
            "A x_p = b and A z = 0",
            "the affine solution set is the nullspace translated by x_p",
        ),
    ),
    "consistency.geometry": _spec(
        "consistency.geometry",
        "geometry.elimination_tableau",
        ("matrix", "rhs", "none_matrix", "none_rhs", "solution_state"),
        "constraint_state",
        {
            "matrix": [[1.0, 2.0], [2.0, 4.0]],
            "rhs": [1.0, 2.0],
            "none_matrix": [[1.0, 2.0], [2.0, 4.0]],
            "none_rhs": [1.0, 0.0],
            "nullspace_basis": [[-2.0, 1.0]],
            "particular": [1.0, 0.0],
            "consistency_states": [2.0, 0.0],
        },
        ("column_membership", "infinite_solutions", "no_solution"),
        (
            "b in Col(A) is equivalent to existence",
            "a nontrivial nullspace makes every consistent solution nonunique",
        ),
    ),
    "gaussian-elimination": _spec(
        "gaussian-elimination",
        "geometry.elimination_tableau",
        ("matrix", "rhs", "tableau"),
        "row_operation",
        {
            "matrix": [[1.0, 2.0, 1.0], [2.0, 5.0, 2.0], [1.0, 1.0, -1.0]],
            "rhs": [3.0, 8.0, -1.0],
            "operations": [[1.0, 0.0, 2.0], [2.0, 0.0, 1.0], [2.0, 1.0, -1.0]],
            "transition_sizes": [2.0, 1.0],
            "tableau": [[1.0, 2.0, 1.0], [0.0, 1.0, 0.0], [0.0, 0.0, -2.0]],
            "solution_code": 1.0,
        },
        ("initial", "eliminate", "triangular"),
        (
            "row operations preserve the solution set",
            "each displayed tableau follows from the previous tableau",
        ),
    ),
    "least-squares.projection": _spec(
        "least-squares.projection",
        "geometry.least_squares",
        ("matrix", "values", "data", "fit", "residual"),
        "projects_to",
        {
            "matrix": [[1.0], [0.0]],
            "values": [2.0, 1.0],
            "fit": [2.0, 0.0],
            "residual": [0.0, 1.0],
        },
        ("projection",),
        (
            "the residual is orthogonal to Col(A)",
            "A x_hat plus the residual equals b",
        ),
    ),
}


def spec_for(topic: str) -> Ch5Spec:
    return deepcopy(_SPECS[topic.removeprefix("ch05.")])


def specs() -> tuple[Ch5Spec, ...]:
    return tuple(spec_for(topic) for topic in _SPECS)
