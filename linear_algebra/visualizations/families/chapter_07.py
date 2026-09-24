"""Recompute the complete Chapter 7 graph before emitting any operation."""

from __future__ import annotations

import json

import numpy as np

from linear_algebra.chapter_07_semantics import spec_for

from ..compiler import CompileIssue, VisualCompileError
from ..palette import role_color


TOL = 1e-9
BOUNDS = (-4.0, 4.0, -4.0, 4.0)


def _equal(actual, expected, name):
    actual_array = np.asarray(actual, dtype=float)
    expected_array = np.asarray(expected, dtype=float)
    if actual_array.shape != expected_array.shape or not np.isfinite(actual_array).all() or not np.allclose(actual_array, expected_array, atol=TOL, rtol=0):
        raise ValueError(f"{name}: disagrees with numerical evidence")


def _validate_descriptors(topic, semantics):
    spec = spec_for(topic)
    entities = {entity.role: entity for entity in semantics.entities}
    if tuple(entities) != spec.roles or len(entities) != len(semantics.entities):
        raise ValueError("exact Chapter 7 entity roles/order required")
    if (semantics.scene_kind, semantics.scene_family) != ("2d", "spectral_orthogonal"):
        raise ValueError("Chapter 7 scene descriptor mismatch")

    values = {}
    for descriptor in spec.entities:
        entity = entities[descriptor.role]
        if (entity.id, entity.kind, entity.dimension, entity.label) != (f"entity.{topic}.{descriptor.role}", descriptor.kind, descriptor.dimension, descriptor.label):
            raise ValueError(f"{descriptor.role}: entity descriptor mismatch")
        _equal(entity.value, descriptor.value, f"entity.{descriptor.role}")
        values[descriptor.role] = np.asarray(entity.value, dtype=float)

    expected_relation_ids = tuple(f"relation.{topic}.{item.name}" for item in spec.relations)
    if tuple(relation.id for relation in semantics.relations) != expected_relation_ids:
        raise ValueError("exact Chapter 7 relation order/identities required")
    relations = {descriptor.name: relation for descriptor, relation in zip(spec.relations, semantics.relations)}
    for descriptor in spec.relations:
        relation = relations[descriptor.name]
        if (relation.kind, relation.source_ref, relation.target_ref) != (descriptor.kind, entities[descriptor.source_role].id, entities[descriptor.target_role].id):
            raise ValueError(f"{descriptor.name}: relation endpoints/kind mismatch")
        if set(relation.parameters) != set(descriptor.parameter_names):
            raise ValueError(f"{descriptor.name}: exact parameter set required")
        for name, expected in descriptor.parameters:
            _equal(relation.parameters[name], expected, f"{descriptor.name}.{name}")

    expected_stage_ids = tuple(f"stage.{topic}.{item.name}" for item in spec.stages)
    if tuple(stage.id for stage in semantics.stages) != expected_stage_ids:
        raise ValueError("exact ordered Chapter 7 stage IDs required")
    for descriptor, stage in zip(spec.stages, semantics.stages):
        expected_refs = (
            tuple(entities[role].id for role in descriptor.input_roles),
            tuple(entities[role].id for role in descriptor.output_roles),
            tuple(relations[name].id for name in descriptor.relation_names),
            descriptor.invariants,
        )
        actual_refs = (stage.input_entity_refs, stage.output_entity_refs, stage.relation_refs, stage.expected_invariants)
        if (stage.title, stage.caption, stage.layout) != (descriptor.title, "", "overlay") or actual_refs != expected_refs:
            raise ValueError(f"{stage.id}: stage descriptor mismatch")
    return spec, entities, relations, values


def _validate_math(topic, spec, relations, values):
    evidence = {"invariants": {name: True for name in spec.invariants}}
    if topic == "ch07.eigen.direction":
        directions = {}
        counterexamples = {}
        for descriptor in spec.relations:
            params = relations[descriptor.name].parameters
            matrix = np.asarray(params["matrix"], dtype=float)
            vector = np.asarray(params["vector"], dtype=float)
            output = np.asarray(params["output"], dtype=float)
            _equal(matrix @ vector, output, f"{descriptor.name}: A v")
            if "eigenvalue" in params:
                eigenvalue = float(params["eigenvalue"])
                _equal(output, eigenvalue * vector, f"{descriptor.name}: lambda v")
                directions[descriptor.name] = {"eigenvalue": eigenvalue, "output": output.tolist()}
            elif descriptor.name == "rotation":
                _equal(np.poly(matrix), params["characteristic"], "rotation characteristic polynomial")
                if float(params["discriminant"]) >= 0 or any(abs(value.imag) < TOL for value in np.linalg.eigvals(matrix)):
                    raise ValueError("quarter turn must have no real eigenvector")
            else:
                _equal(matrix @ vector, output, f"{descriptor.name}: A v")
                if np.linalg.matrix_rank(np.column_stack((vector, output)), tol=TOL) < 2:
                    raise ValueError(f"{descriptor.name}: counterexample image must change direction")
                counterexamples[descriptor.name] = {"output": output.tolist(), "direction_changed": True}
        if np.linalg.norm(values["projection_operator"] @ values["projection_y"]) >= TOL:
            raise ValueError("lambda zero direction must lie in Null(A)")
        evidence["directions"] = directions
        evidence["counterexamples"] = counterexamples
        evidence["rotation_real_directions"] = []

    elif topic == "ch07.characteristic-polynomial":
        spectra = {}
        for name in ("real_spectrum", "complex_spectrum"):
            params = relations[name].parameters
            matrix = np.asarray(params["matrix"], dtype=float)
            coefficients = np.poly(matrix)
            roots = sorted(((float(value.real), float(value.imag)) for value in np.linalg.eigvals(matrix)), key=lambda value: (value[0], value[1]))
            _equal(coefficients, params["coefficients"], f"{name}: coefficients")
            _equal(roots, params["roots"], f"{name}: roots")
            spectra[name] = {"coefficients": coefficients.tolist(), "roots": roots}
        real = relations["real_spectrum"].parameters
        matrix = np.asarray(real["matrix"], dtype=float)
        for eigenvalue, key in ((3.0, "basis_3"), (1.0, "basis_1")):
            basis = np.asarray(real[key], dtype=float)
            _equal((matrix - eigenvalue * np.eye(2)) @ basis.T, np.zeros((2, len(basis))), key)
        if float(relations["complex_spectrum"].parameters["discriminant"]) >= 0:
            raise ValueError("complex example requires a negative discriminant")
        evidence["spectra"] = spectra
        evidence["complex_real_directions"] = []

    elif topic == "ch07.eigenspace":
        operator = values["operator"]
        spaces = {}
        for name in ("space_3", "space_1", "shear_space"):
            params = relations[name].parameters
            matrix = np.asarray(params["matrix"], dtype=float)
            eigenvalue = float(params["eigenvalue"])
            shifted = matrix - eigenvalue * np.eye(2)
            basis = np.asarray(params["basis"], dtype=float)
            _equal(shifted, params["shifted"], f"{name}: A-lambda I")
            _equal(shifted @ basis.T, np.zeros((2, len(basis))), f"{name}: nullspace")
            if 2 - np.linalg.matrix_rank(shifted, tol=TOL) != len(basis):
                raise ValueError(f"{name}: eigenspace dimension mismatch")
            spaces[name] = basis.tolist()
        shear = relations["shear_space"].parameters
        if not float(shear["geometric_multiplicity"]) < float(shear["algebraic_multiplicity"]):
            raise ValueError("defective example must have too few eigenvectors")
        if np.linalg.matrix_rank(np.column_stack((values["space_3"][0], values["space_1"][0])), tol=TOL) != 2:
            raise ValueError("distinct eigendirections must be independent")
        invariant = relations["invariants"].parameters
        _equal(np.linalg.det(operator), invariant["determinant"], "determinant")
        _equal(np.trace(operator), invariant["trace"], "trace")
        eigenvalues = sorted(np.linalg.eigvals(operator).real, reverse=True)
        _equal(eigenvalues, invariant["eigenvalues"], "eigenvalues")
        _equal(np.prod(eigenvalues), invariant["determinant"], "product of eigenvalues")
        _equal(np.sum(eigenvalues), invariant["trace"], "sum of eigenvalues")
        evidence.update(eigenspaces=spaces, determinant=float(np.linalg.det(operator)), trace=float(np.trace(operator)))

    else:
        operator, basis, inverse, diagonal = (values[name] for name in ("operator", "basis", "inverse_basis", "diagonal"))
        _equal(inverse, np.linalg.inv(basis), "P inverse")
        _equal(inverse @ operator @ basis, diagonal, "P inverse A P")
        _equal(basis @ diagonal @ inverse, operator, "P D P inverse")
        for name in ("diagonal_v1", "diagonal_v2", "eigen_v1", "eigen_v2"):
            params = relations[name].parameters
            matrix = np.asarray(params["matrix"], dtype=float)
            vector = np.asarray(params["vector"], dtype=float)
            output = np.asarray(params["output"], dtype=float)
            _equal(matrix @ vector, output, f"{name}: matrix-vector product")
            _equal(output, float(params["eigenvalue"]) * vector, f"{name}: independent scaling")
        evidence.update(diagonal=diagonal.tolist(), basis=basis.tolist(), endpoint_error=float(np.linalg.norm(basis @ diagonal @ inverse - operator)))
    return evidence


class _Scene:
    def __init__(self, topic):
        self.topic = topic
        self.operations = []
        self.aliases = {}

    def add(self, semantic_id, operation):
        self.operations.append(operation)
        self.aliases.setdefault(semantic_id, []).append(operation["alias"])

    def grid(self, semantic_id, matrix, alias, *, color):
        self.add(semantic_id, {"op": "geometry.transformed_grid", "alias": alias, "matrix": np.asarray(matrix, dtype=float).tolist(), "bounds": list(BOUNDS), "step": 1.0, "color": color})

    def vector(self, semantic_id, value, alias, *, color, label):
        vector = np.asarray(value, dtype=float)
        if np.linalg.norm(vector) <= TOL:
            self.add(semantic_id, {"op": "point.upsert", "alias": alias, "coordinates": vector.tolist(), "name": label, "color": color})
            return
        origin, endpoint = f"{alias}__origin", f"{alias}__end"
        self.operations.extend((
            {"op": "point.upsert", "alias": origin, "coordinates": [0.0, 0.0], "name": "O", "color": color},
            {"op": "point.upsert", "alias": endpoint, "coordinates": vector.tolist(), "name": label, "color": color},
        ))
        self.add(semantic_id, {"op": "linear.upsert", "alias": alias, "start": origin, "end": endpoint, "kind": "vector", "role": "primary", "color": color})

    def subspace(self, semantic_id, basis, alias, *, color):
        self.add(semantic_id, {"op": "geometry.subspace_region", "alias": alias, "basis": np.asarray(basis, dtype=float).tolist(), "bounds": list(BOUNDS), "color": color})

    def curve(self, semantic_id, coefficients, alias, *, color):
        coefficients = np.asarray(coefficients, dtype=float)
        expression = "+".join(f"({float(value)})*x**{len(coefficients) - index - 1}" for index, value in enumerate(coefficients))
        self.add(semantic_id, {"op": "curve.create", "alias": alias, "kind": "explicit", "expression": expression, "color": color})

    def points(self, semantic_id, points, alias, *, colors):
        for index, point in enumerate(np.asarray(points, dtype=float)):
            self.add(semantic_id, {"op": "point.upsert", "alias": f"{alias}__{index}", "coordinates": point.tolist(), "name": f"lambda{index + 1}", "color": colors[index % len(colors)]})


def _role_color(role):
    if any(token in role for token in ("x", "plus", "space_3", "v1", "e1")):
        return role_color("vector_a")
    if any(token in role for token in ("y", "minus", "space_1", "v2", "e2")):
        return role_color("vector_b")
    return role_color("combination")


def _emit_entity(scene, entity, value, alias):
    color = _role_color(entity.role)
    if entity.kind == "matrix":
        scene.grid(entity.id, value, alias, color=role_color("neutral"))
    elif entity.kind == "eigenspace":
        scene.subspace(entity.id, value, alias, color=color)
    elif entity.role.endswith("polynomial"):
        scene.curve(entity.id, value, alias, color=role_color("neutral"))
    elif "roots" in entity.role or entity.role == "invariant_values":
        scene.points(entity.id, value, alias, colors=(role_color("vector_a"), role_color("vector_b")))
    else:
        scene.vector(entity.id, value, alias, color=color, label=entity.role)


def _emit_relation(scene, topic, descriptor, relation, values, alias):
    params = relation.parameters
    if "vector" in params:
        scene.vector(relation.id, params["output"], alias, color=_role_color(descriptor.source_role), label=descriptor.target_role)
    elif "basis" in params:
        scene.subspace(relation.id, params["basis"], alias, color=_role_color(descriptor.target_role))
    elif "coefficients" in params:
        scene.curve(relation.id, params["coefficients"], alias, color=role_color("neutral"))
    elif descriptor.name == "similarity":
        scene.grid(relation.id, params["diagonal"], alias, color=role_color("combination"))
    else:
        scene.points(relation.id, values[descriptor.target_role], alias, colors=(role_color("vector_a"), role_color("vector_b")))


def _stage_direction(scene, topic, stage_id, matrix, vectors):
    scene.grid(stage_id, np.eye(2), f"{topic}__stage__{stage_id.rsplit('.', 1)[-1]}__original", color=role_color("neutral"))
    scene.grid(stage_id, matrix, f"{topic}__stage__{stage_id.rsplit('.', 1)[-1]}__transformed", color=role_color("combination"))
    for index, (vector, output, label) in enumerate(vectors):
        color = role_color("vector_a" if index == 0 else "vector_b")
        scene.vector(stage_id, vector, f"{topic}__stage__{stage_id.rsplit('.', 1)[-1]}__v{index + 1}", color=color, label=label)
        scene.vector(stage_id, output, f"{topic}__stage__{stage_id.rsplit('.', 1)[-1]}__av{index + 1}", color=color, label=f"A{label}")


def _emit_stages(scene, topic, semantics, values):
    blue, orange = role_color("vector_a"), role_color("vector_b")
    stage_ids = [stage.id for stage in semantics.stages]
    if topic == "ch07.eigen.direction":
        _stage_direction(scene, topic, stage_ids[0], values["stretch_operator"], ((values["stretch_x"], values["stretch_x_image"], "v"), (values["stretch_diagonal"], values["stretch_diagonal_image"], "u")))
        _stage_direction(scene, topic, stage_ids[1], values["projection_operator"], ((values["projection_x"], values["projection_x_image"], "v1"), (values["projection_y"], values["projection_y_image"], "v2")))
        _stage_direction(scene, topic, stage_ids[2], values["rotation_operator"], ((values["rotation_vector"], values["rotation_image"], "v"),))
        _stage_direction(scene, topic, stage_ids[3], values["reflection_operator"], ((values["reflection_plus"], values["reflection_plus_image"], "v1"), (values["reflection_minus"], values["reflection_minus_image"], "v2")))
    elif topic == "ch07.characteristic-polynomial":
        scene.grid(stage_ids[0], values["real_operator"], f"{topic}__stage__real__grid", color=role_color("combination"))
        scene.curve(stage_ids[0], values["real_polynomial"], f"{topic}__stage__real__polynomial", color=role_color("neutral"))
        scene.points(stage_ids[0], values["real_roots"], f"{topic}__stage__real__roots", colors=(blue, orange))
        scene.subspace(stage_ids[0], values["space_3"], f"{topic}__stage__real__space3", color=blue)
        scene.subspace(stage_ids[0], values["space_1"], f"{topic}__stage__real__space1", color=orange)
        scene.grid(stage_ids[1], values["complex_operator"], f"{topic}__stage__complex__grid", color=role_color("combination"))
        scene.curve(stage_ids[1], values["complex_polynomial"], f"{topic}__stage__complex__polynomial", color=role_color("neutral"))
        scene.points(stage_ids[1], values["complex_roots"], f"{topic}__stage__complex__roots", colors=(blue, orange))
    elif topic == "ch07.eigenspace":
        scene.grid(stage_ids[0], values["operator"], f"{topic}__stage__spaces__grid", color=role_color("combination"))
        scene.subspace(stage_ids[0], values["space_3"], f"{topic}__stage__spaces__space3", color=blue)
        scene.subspace(stage_ids[0], values["space_1"], f"{topic}__stage__spaces__space1", color=orange)
        scene.grid(stage_ids[1], values["shear_operator"], f"{topic}__stage__defective__grid", color=role_color("combination"))
        scene.subspace(stage_ids[1], values["shear_space"], f"{topic}__stage__defective__space", color=blue)
        scene.grid(stage_ids[2], values["operator"], f"{topic}__stage__invariants__grid", color=role_color("combination"))
        scene.vector(stage_ids[2], values["space_3"][0], f"{topic}__stage__invariants__v1", color=blue, label="v1")
        scene.vector(stage_ids[2], values["space_1"][0], f"{topic}__stage__invariants__v2", color=orange, label="v2")
    else:
        scene.grid(stage_ids[0], values["basis"], f"{topic}__stage__change_basis__grid", color=role_color("neutral"))
        scene.vector(stage_ids[0], values["basis_v1"], f"{topic}__stage__change_basis__v1", color=blue, label="v1")
        scene.vector(stage_ids[0], values["basis_v2"], f"{topic}__stage__change_basis__v2", color=orange, label="v2")
        scene.grid(stage_ids[1], values["diagonal"], f"{topic}__stage__diagonal__grid", color=role_color("combination"))
        scene.vector(stage_ids[1], values["coordinate_e1"], f"{topic}__stage__diagonal__e1", color=blue, label="e1")
        scene.vector(stage_ids[1], values["scaled_e1"], f"{topic}__stage__diagonal__de1", color=blue, label="3e1")
        scene.vector(stage_ids[1], values["coordinate_e2"], f"{topic}__stage__diagonal__e2", color=orange, label="e2")
        scene.vector(stage_ids[1], values["scaled_e2"], f"{topic}__stage__diagonal__de2", color=orange, label="e2")
        scene.grid(stage_ids[2], values["operator"], f"{topic}__stage__change_back__grid", color=role_color("combination"))
        scene.vector(stage_ids[2], values["basis_v1"], f"{topic}__stage__change_back__v1", color=blue, label="v1")
        scene.vector(stage_ids[2], values["image_v1"], f"{topic}__stage__change_back__av1", color=blue, label="Av1")
        scene.vector(stage_ids[2], values["basis_v2"], f"{topic}__stage__change_back__v2", color=orange, label="v2")
        scene.vector(stage_ids[2], values["image_v2"], f"{topic}__stage__change_back__av2", color=orange, label="Av2")


def compile_chapter_07(topic, semantics, context=None):
    try:
        spec, entities, relations, values = _validate_descriptors(topic, semantics)
        evidence = _validate_math(topic, spec, relations, values)
        scene = _Scene(topic)
        for role, entity in entities.items():
            _emit_entity(scene, entity, values[role], f"{topic}__entity__{role}")
        for descriptor in spec.relations:
            _emit_relation(scene, topic, descriptor, relations[descriptor.name], values, f"{topic}__relation__{descriptor.name}")
        _emit_stages(scene, topic, semantics, values)
        evidence["stages"] = {stage.id: {"title": stage.title} for stage in semantics.stages}
        return json.loads(json.dumps({"operations": scene.operations, "aliases": scene.aliases, "evidence": evidence}))
    except (KeyError, ValueError, TypeError, IndexError, np.linalg.LinAlgError) as error:
        if isinstance(error, VisualCompileError):
            raise
        raise VisualCompileError((CompileIssue("invalid_chapter_07_semantics", "$.visual_semantics", str(error)),)) from error


__all__ = ["compile_chapter_07"]
