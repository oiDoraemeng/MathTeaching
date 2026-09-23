"""Recompute the complete Chapter 6 graph before emitting any operation."""

from __future__ import annotations

import json

import numpy as np

from linear_algebra.chapter_06_semantics import spec_for

from ..compiler import CompileIssue, VisualCompileError
from ..palette import role_color


TOL = 1e-9
GRID_BOUNDS = (-6.0, 6.0, -6.0, 6.0)


def _equal(actual, expected, name):
    actual_array = np.asarray(actual, dtype=float)
    expected_array = np.asarray(expected, dtype=float)
    if (
        actual_array.shape != expected_array.shape
        or not np.isfinite(actual_array).all()
        or not np.allclose(actual_array, expected_array, atol=TOL, rtol=0)
    ):
        raise ValueError(f"{name}: disagrees with numerical evidence")


def _validate(topic, semantics):
    spec = spec_for(topic)
    entities = {entity.role: entity for entity in semantics.entities}
    if set(entities) != set(spec.roles) or len(entities) != len(semantics.entities):
        raise ValueError("exact Chapter 6 entity roles required")
    if semantics.scene_kind != "2d" or semantics.scene_family != "basis_change":
        raise ValueError("Chapter 6 scene kind/family mismatch")

    values = {}
    for descriptor in spec.entities:
        entity = entities[descriptor.role]
        if (entity.id, entity.kind, entity.dimension) != (
            f"entity.{topic}.{descriptor.role}",
            descriptor.kind,
            descriptor.dimension,
        ):
            raise ValueError(f"{descriptor.role}: entity identity/type mismatch")
        _equal(entity.value, descriptor.value, f"entity.{descriptor.role}")
        values[descriptor.role] = np.asarray(entity.value, dtype=float)

    expected_relation_ids = tuple(f"relation.{topic}.{item.name}" for item in spec.relations)
    if tuple(relation.id for relation in semantics.relations) != expected_relation_ids:
        raise ValueError("exact Chapter 6 relation order/identities required")
    relations = {descriptor.name: relation for descriptor, relation in zip(spec.relations, semantics.relations)}
    for descriptor in spec.relations:
        relation = relations[descriptor.name]
        if (relation.kind, relation.source_ref, relation.target_ref) != (
            descriptor.kind,
            entities[descriptor.source_role].id,
            entities[descriptor.target_role].id,
        ):
            raise ValueError(f"{descriptor.name}: relation endpoints/kind mismatch")
        if set(relation.parameters) != set(descriptor.parameter_names):
            raise ValueError(f"{descriptor.name}: exact parameter set required")
        for name, expected in descriptor.parameters:
            _equal(relation.parameters[name], expected, f"{descriptor.name}.{name}")

    expected_stage_ids = tuple(f"stage.{topic}.{descriptor.name}" for descriptor in spec.stages)
    if tuple(stage.id for stage in semantics.stages) != expected_stage_ids:
        raise ValueError("exact ordered Chapter 6 stage IDs required")
    for descriptor, stage in zip(spec.stages, semantics.stages):
        if stage.title != descriptor.title or stage.caption != "":
            raise ValueError(f"{stage.id}: stage title/caption mismatch")
        expected_references = (
            tuple(entities[role].id for role in descriptor.input_roles),
            tuple(entities[role].id for role in descriptor.output_roles),
            tuple(relations[name].id for name in descriptor.relation_names),
            descriptor.invariants,
        )
        actual_references = (
            stage.input_entity_refs,
            stage.output_entity_refs,
            stage.relation_refs,
            stage.expected_invariants,
        )
        if stage.layout != "overlay" or actual_references != expected_references:
            raise ValueError(f"{stage.id}: stage references/layout/invariants mismatch")

    basis = values["basis_matrix"]
    inverse = values["inverse_basis"]
    _equal(inverse, np.linalg.inv(basis), "inverse basis")
    _equal(basis @ inverse, np.eye(2), "P inverse")
    _equal(inverse @ basis, np.eye(2), "inverse P")

    evidence = {
        "basis_matrix": basis.tolist(),
        "inverse_basis": inverse.tolist(),
        "invariants": {name: True for name in spec.invariants},
    }
    if topic == "ch06.basis-change.coordinates":
        _equal(basis @ values["forward_coordinates"], values["forward_vector"], "P c = x")
        _equal(inverse @ values["inverse_vector"], values["inverse_coordinates"], "P inverse x = c")
        _equal(values["identity_basis"], np.eye(2), "standard basis matrix")
        evidence.update(
            forward_coordinates=values["forward_coordinates"].tolist(),
            forward_vector=values["forward_vector"].tolist(),
            inverse_vector=values["inverse_vector"].tolist(),
            inverse_coordinates=values["inverse_coordinates"].tolist(),
            endpoint_error=float(
                max(
                    np.linalg.norm(basis @ values["forward_coordinates"] - values["forward_vector"]),
                    np.linalg.norm(inverse @ values["inverse_vector"] - values["inverse_coordinates"]),
                )
            ),
        )
    else:
        operator = values["operator"]
        similar = values["similar_operator"]
        _equal(inverse @ operator @ basis, similar, "B = P inverse A P")
        _equal(operator @ values["basis_v1"], values["image_v1"], "A v1")
        _equal(operator @ values["basis_v2"], values["image_v2"], "A v2")
        _equal(values["image_v1"], 3.0 * values["basis_v1"], "A v1 = 3 v1")
        _equal(values["image_v2"], values["basis_v2"], "A v2 = v2")
        _equal(np.linalg.det(similar), np.linalg.det(operator), "determinant")
        _equal(np.trace(similar), np.trace(operator), "trace")
        _equal(np.linalg.matrix_rank(similar), np.linalg.matrix_rank(operator), "rank")
        _equal(np.poly(similar), np.poly(operator), "characteristic polynomial")
        evidence.update(
            operator=operator.tolist(),
            similar_operator=similar.tolist(),
            determinant=float(np.linalg.det(operator)),
            trace=float(np.trace(operator)),
            rank=int(np.linalg.matrix_rank(operator)),
            characteristic_polynomial=np.poly(operator).tolist(),
            endpoint_error=0.0,
        )
    return spec, entities, relations, values, evidence


class _Scene:
    def __init__(self, topic):
        self.topic = topic
        self.operations = []
        self.aliases = {}

    def add(self, semantic_id, operation):
        self.operations.append(operation)
        self.aliases.setdefault(semantic_id, []).append(operation["alias"])

    def grid(self, semantic_id, matrix, alias, *, color=None):
        operation = {
            "op": "geometry.transformed_grid",
            "alias": alias,
            "matrix": np.asarray(matrix, dtype=float).tolist(),
            "bounds": list(GRID_BOUNDS),
            "step": 1.0,
        }
        if color is not None:
            operation["color"] = color
        self.add(semantic_id, operation)

    def vector(self, semantic_id, value, alias, *, color, label):
        origin = f"{alias}__origin"
        end = f"{alias}__end"
        self.operations.extend(
            (
                {"op": "point.upsert", "alias": origin, "coordinates": [0.0, 0.0], "name": "O", "color": color},
                {"op": "point.upsert", "alias": end, "coordinates": np.asarray(value, dtype=float).tolist(), "name": label, "color": color},
            )
        )
        self.add(
            semantic_id,
            {"op": "linear.upsert", "alias": alias, "start": origin, "end": end, "kind": "vector", "role": "primary", "color": color},
        )

    def transform(self, semantic_id, matrix, vector, alias):
        self.add(
            semantic_id,
            {
                "op": "geometry.staged_transform",
                "alias": alias,
                "matrices": [np.asarray(matrix, dtype=float).tolist()],
                "points": [np.asarray(vector, dtype=float).tolist()],
                "aliases": [f"{alias}__point"],
            },
        )


def _entity_color(role):
    if role in {"basis_v1", "image_v1"}:
        return role_color("vector_a")
    if role in {"basis_v2", "image_v2"}:
        return role_color("vector_b")
    return role_color("combination")


def _compile_basis_stages(scene, topic, values, stage_ids):
    basis = values["basis_matrix"]
    v1, v2 = basis[:, 0], basis[:, 1]
    blue = role_color("vector_a")
    orange = role_color("vector_b")
    green = role_color("combination")

    forward, backward, identity = stage_ids
    scene.grid(forward, basis, f"{topic}__stage__forward__grid", color=role_color("neutral"))
    scene.vector(forward, v1, f"{topic}__stage__forward__v1", color=blue, label="v1")
    scene.vector(forward, v2, f"{topic}__stage__forward__v2", color=orange, label="v2")
    scene.vector(forward, values["forward_vector"], f"{topic}__stage__forward__x", color=green, label="x")

    scene.grid(backward, basis, f"{topic}__stage__backward__grid", color=role_color("neutral"))
    scene.vector(backward, v1, f"{topic}__stage__backward__v1", color=blue, label="v1")
    scene.vector(backward, v2, f"{topic}__stage__backward__v2", color=orange, label="v2")
    scene.vector(backward, values["inverse_vector"], f"{topic}__stage__backward__x", color=green, label="x")

    scene.grid(identity, values["standard_basis"], f"{topic}__stage__identity__grid", color=role_color("neutral"))
    scene.vector(identity, (1.0, 0.0), f"{topic}__stage__identity__e1", color=blue, label="e1")
    scene.vector(identity, (0.0, 1.0), f"{topic}__stage__identity__e2", color=orange, label="e2")


def _compile_similarity_stages(scene, topic, values, stage_ids):
    blue = role_color("vector_a")
    orange = role_color("vector_b")
    neutral = role_color("neutral")
    change_basis, apply_operator, change_back = stage_ids

    scene.grid(change_basis, values["basis_matrix"], f"{topic}__stage__change_basis__grid", color=neutral)
    scene.vector(change_basis, values["basis_v1"], f"{topic}__stage__change_basis__v1", color=blue, label="v1")
    scene.vector(change_basis, values["basis_v2"], f"{topic}__stage__change_basis__v2", color=orange, label="v2")

    scene.grid(apply_operator, values["operator"], f"{topic}__stage__apply_operator__grid", color=neutral)
    scene.vector(apply_operator, values["basis_v1"], f"{topic}__stage__apply_operator__v1", color=blue, label="v1")
    scene.vector(apply_operator, values["basis_v2"], f"{topic}__stage__apply_operator__v2", color=orange, label="v2")
    scene.vector(apply_operator, values["image_v1"], f"{topic}__stage__apply_operator__av1", color=blue, label="Av1")
    scene.vector(apply_operator, values["image_v2"], f"{topic}__stage__apply_operator__av2", color=orange, label="Av2")

    scene.grid(change_back, values["similar_operator"], f"{topic}__stage__change_basis_back__grid", color=neutral)
    scene.vector(change_back, (3.0, 0.0), f"{topic}__stage__change_basis_back__be1", color=blue, label="3e1")
    scene.vector(change_back, (0.0, 1.0), f"{topic}__stage__change_basis_back__be2", color=orange, label="e2")


def compile_chapter_06(topic, semantics, context=None):
    try:
        spec, entities, relations, values, evidence = _validate(topic, semantics)
        scene = _Scene(topic)

        for role, entity in entities.items():
            alias = f"{topic}__entity__{role}"
            if entity.kind == "matrix":
                scene.grid(entity.id, values[role], alias)
            else:
                scene.vector(entity.id, values[role], alias, color=_entity_color(role), label=role)

        for descriptor in spec.relations:
            relation = relations[descriptor.name]
            alias = f"{topic}__relation__{descriptor.name}"
            parameters = relation.parameters
            if "input" in parameters and np.asarray(parameters["input"]).shape == (2,):
                scene.transform(relation.id, parameters["matrix"], parameters["input"], alias)
            elif descriptor.name == "similarity":
                scene.grid(relation.id, parameters["similar_operator"], alias)
            else:
                scene.grid(relation.id, parameters["output"], alias)

        stage_ids = tuple(stage.id for stage in semantics.stages)
        if topic == "ch06.basis-change.coordinates":
            _compile_basis_stages(scene, topic, values, stage_ids)
            evidence["stages"] = {
                stage_ids[0]: {"matrix": values["basis_matrix"].tolist(), "input": values["forward_coordinates"].tolist(), "output": values["forward_vector"].tolist()},
                stage_ids[1]: {"matrix": values["inverse_basis"].tolist(), "input": values["inverse_vector"].tolist(), "output": values["inverse_coordinates"].tolist()},
                stage_ids[2]: {"matrix": values["standard_basis"].tolist(), "output": values["identity_basis"].tolist()},
            }
        else:
            _compile_similarity_stages(scene, topic, values, stage_ids)
            evidence["stages"] = {
                stage_ids[0]: {"matrix": values["basis_matrix"].tolist(), "basis": [values["basis_v1"].tolist(), values["basis_v2"].tolist()]},
                stage_ids[1]: {"matrix": values["operator"].tolist(), "output": [values["image_v1"].tolist(), values["image_v2"].tolist()]},
                stage_ids[2]: {"matrix": values["similar_operator"].tolist(), "output": [[3.0, 0.0], [0.0, 1.0]]},
            }

        return {
            "operations": json.loads(json.dumps(scene.operations)),
            "aliases": {key: tuple(items) for key, items in scene.aliases.items()},
            "evidence": evidence,
        }
    except (KeyError, ValueError, TypeError, IndexError, np.linalg.LinAlgError) as error:
        if isinstance(error, VisualCompileError):
            raise
        raise VisualCompileError(
            (CompileIssue("invalid_chapter_06_semantics", "$.visual_semantics", str(error)),)
        ) from error


__all__ = ["compile_chapter_06"]
