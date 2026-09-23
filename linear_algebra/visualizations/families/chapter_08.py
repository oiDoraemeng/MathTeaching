"""Strict Chapter 8 compiler with lecture-specific two-dimensional scenes."""

from __future__ import annotations

import json
from typing import Mapping

import numpy as np

from linear_algebra.chapter_08_semantics import spec_for
from linear_algebra.visualizations.palette import role_color
from .quadratic import QuadraticFamilyCompiler, classify_quadratic
from ..compiler import CompileIssue, VisualCompileError


TOL = 1e-9
BLUE = role_color("vector_a")
ORANGE = role_color("vector_b")
GREEN = role_color("combination")
GRAY = role_color("neutral")


def _equal(actual: object, expected: object, name: str) -> None:
    if isinstance(expected, str):
        if actual != expected:
            raise ValueError(f"{name} disagrees with the reviewed witness")
        return
    try:
        left = np.asarray(actual, dtype=float)
        right = np.asarray(expected, dtype=float)
    except (TypeError, ValueError):
        if actual != expected:
            raise ValueError(f"{name} disagrees with the reviewed witness")
        return
    if left.shape != right.shape or not np.allclose(left, right, atol=TOL, rtol=0):
        raise ValueError(f"{name} disagrees with the reviewed witness")


def _validate_descriptors(topic: str, semantics: object):
    spec = spec_for(topic)
    entities = {entity.role: entity for entity in semantics.entities}
    if tuple(entities) != spec.roles or len(entities) != len(semantics.entities):
        raise ValueError("exact entity roles required")
    if semantics.scene_family != "quadratic_level_set" or semantics.scene_kind != "2d":
        raise ValueError("chapter 8 requires the two-dimensional quadratic scene")
    for descriptor in spec.entities:
        entity = entities[descriptor.role]
        if (entity.id, entity.kind, entity.dimension, entity.label) != (
            f"entity.{topic}.{descriptor.role}", descriptor.kind, descriptor.dimension, descriptor.label
        ):
            raise ValueError("entity descriptor mismatch")
        _equal(entity.value, descriptor.value, f"entity {descriptor.role}")

    relations = {descriptor.name: relation for descriptor, relation in zip(spec.relations, semantics.relations)}
    if tuple(relation.id for relation in semantics.relations) != tuple(
        f"relation.{topic}.{descriptor.name}" for descriptor in spec.relations
    ):
        raise ValueError("relation identities mismatch")
    for descriptor in spec.relations:
        relation = relations[descriptor.name]
        if (relation.kind, relation.source_ref, relation.target_ref, set(relation.parameters)) != (
            descriptor.kind,
            entities[descriptor.source_role].id,
            entities[descriptor.target_role].id,
            set(descriptor.parameter_names),
        ):
            raise ValueError("relation descriptor mismatch")
        for name, expected in descriptor.parameters:
            _equal(relation.parameters[name], expected, f"relation {descriptor.name}.{name}")

    if len(semantics.stages) != len(spec.stages):
        raise ValueError("stage count mismatch")
    for stage, descriptor in zip(semantics.stages, spec.stages):
        if (
            stage.id,
            stage.title,
            stage.caption,
            stage.layout,
            tuple(stage.input_entity_refs),
            tuple(stage.output_entity_refs),
            tuple(stage.relation_refs),
            tuple(stage.expected_invariants),
        ) != (
            f"stage.{topic}.{descriptor.name}",
            descriptor.title,
            "",
            "overlay",
            tuple(entities[role].id for role in descriptor.input_roles),
            tuple(entities[role].id for role in descriptor.output_roles),
            tuple(relations[name].id for name in descriptor.relation_names),
            descriptor.invariants,
        ):
            raise ValueError("stage descriptor mismatch")
    return spec, entities, relations


def _evidence(topic: str, values: Mapping[str, np.ndarray], relations: Mapping[str, object]) -> dict[str, object]:
    evidence: dict[str, object] = {}
    if topic == "ch08.quadratic.matrix-form":
        for role, matrix in values.items():
            _equal(matrix, matrix.T, f"{role} symmetry")
        groups = {
            "diagonal_examples": (("circle_matrix", "circle_coefficients"), ("ellipse_matrix", "ellipse_coefficients")),
            "positive_cross_examples": (("unit_matrix", "unit_coefficients"), ("scaled_matrix", "scaled_coefficients")),
            "negative_cross_example": (("matrix", "coefficients"),),
        }
        for relation_name, pairs in groups.items():
            parameters = relations[relation_name].parameters
            for matrix_name, coefficients_name in pairs:
                matrix = np.asarray(parameters[matrix_name], dtype=float)
                _equal(parameters[coefficients_name], (matrix[0, 0], 2.0 * matrix[0, 1], matrix[1, 1]), coefficients_name)
    elif topic == "ch08.quadratic.level-sets":
        aligned, tilted, rotation = values["aligned"], values["tilted"], values["rotation"]
        _equal(rotation.T @ rotation, np.eye(2), "orthogonal rotation")
        _equal(rotation @ aligned @ rotation.T, tilted, "rotated quadratic")
        _equal(np.linalg.eigvalsh(aligned), np.linalg.eigvalsh(tilted), "shared eigenvalues")
        evidence["eigenvalues"] = tuple(float(value) for value in np.linalg.eigvalsh(tilted))
    elif topic == "ch08.principal-axis":
        matrix, axes, standard = values["matrix"], values["axes"], values["standard"]
        _equal(axes.T @ axes, np.eye(2), "orthogonal axes")
        _equal(axes.T @ matrix @ axes, standard, "principal diagonal")
        _equal(matrix @ axes, axes @ standard, "eigenvector columns")
        _equal(values["coordinates"], axes.T @ values["point"], "rotated coordinates")
        _equal(values["point"] @ matrix @ values["point"], values["coordinates"] @ standard @ values["coordinates"], "quadratic value")
        cross = float(abs(2.0 * (axes.T @ matrix @ axes)[0, 1]))
        evidence.update(
            cross_term_after=cross,
            cross_term_after_rotation=cross,
            endpoint_error=float(np.linalg.norm(axes @ values["coordinates"] - values["point"])),
            classification=classify_quadratic(matrix).classification,
        )
    else:
        classifications: dict[str, str] = {}
        signatures: dict[str, tuple[int, int, int]] = {}
        for role, matrix in values.items():
            result = classify_quadratic(matrix)
            parameters = relations[role].parameters
            _equal(parameters["matrix"], matrix, f"{role} matrix")
            _equal(parameters["eigenvalues"], result.eigenvalues, f"{role} eigenvalues")
            _equal(parameters["signature"], result.signature, f"{role} signature")
            classifications[role] = result.classification
            signatures[role] = result.signature
        evidence.update(classifications=classifications, signatures=signatures)
    evidence["invariants"] = {name: True for name in spec_for(topic).invariants}
    return evidence


class _SceneBuilder:
    def __init__(self, topic: str, values: Mapping[str, np.ndarray]) -> None:
        self.topic = topic
        self.values = values
        self.operations: list[dict[str, object]] = []
        self.aliases: dict[str, list[str]] = {}

    def add(self, owner: str, operation: dict[str, object]) -> None:
        self.operations.append(operation)
        self.aliases.setdefault(owner, []).append(str(operation["alias"]))

    def quadratic(self, owner: str, matrix: object, alias: str, *, color: str = GREEN) -> None:
        operation = dict(QuadraticFamilyCompiler.compile({
            "matrix": np.asarray(matrix, dtype=float).tolist(),
            "bounds": [-3.0, 3.0, -3.0, 3.0],
            "sample_count": 4096,
        })["operations"][0])
        operation.update(alias=alias, aliases=[alias, f"{alias}__principal", f"{alias}__standard"], axis_segments=[], color=color)
        self.add(owner, operation)

    def line(self, owner: str, start: object, end: object, alias: str, *, color: str, label: str = "") -> None:
        start_alias, end_alias = f"{alias}__start", f"{alias}__end"
        self.add(owner, {"op": "point.upsert", "alias": start_alias, "coordinates": np.asarray(start, dtype=float).tolist()})
        self.add(owner, {"op": "point.upsert", "alias": end_alias, "coordinates": np.asarray(end, dtype=float).tolist()})
        operation: dict[str, object] = {"op": "linear.upsert", "alias": alias, "kind": "line", "start": start_alias, "end": end_alias, "color": color}
        if label:
            operation["label"] = label
        self.add(owner, operation)

    def matrix_diagram(self, owner: str, matrix: object, alias: str, *, center_x: float = 0.0) -> None:
        values = np.asarray(matrix, dtype=float)
        diagonal_color, cross_color = BLUE, ORANGE
        for row in range(2):
            for column in range(2):
                value = float(values[row, column])
                text = str(int(value)) if value.is_integer() else f"{value:g}"
                self.add(owner, {
                    "op": "point.upsert",
                    "alias": f"{alias}__value_{row}_{column}",
                    "name": text,
                    "coordinates": [center_x + (column - 0.5) * 0.9, (0.5 - row) * 0.9],
                    "color": diagonal_color if row == column else cross_color,
                })
        segments = (
            ((-0.95, -1.0), (-0.95, 1.0)), ((-0.95, 1.0), (-0.72, 1.0)), ((-0.95, -1.0), (-0.72, -1.0)),
            ((0.95, -1.0), (0.95, 1.0)), ((0.72, 1.0), (0.95, 1.0)), ((0.72, -1.0), (0.95, -1.0)),
        )
        for index, (start, end) in enumerate(segments):
            shifted_start = (start[0] + center_x, start[1])
            shifted_end = (end[0] + center_x, end[1])
            self.line(owner, shifted_start, shifted_end, f"{alias}__bracket_{index}", color=GRAY)

    def transform(self, owner: str, matrix: object, point: object, alias: str) -> None:
        self.add(owner, {
            "op": "geometry.staged_transform",
            "alias": alias,
            "matrices": [np.asarray(matrix, dtype=float).tolist()],
            "points": [np.asarray(point, dtype=float).tolist()],
            "aliases": [f"{alias}__point"],
        })


def _compile_scene(topic: str, semantics: object, entities: Mapping[str, object], relations: Mapping[str, object]) -> tuple[list[dict[str, object]], dict[str, list[str]]]:
    values = {role: np.asarray(entity.value, dtype=float) for role, entity in entities.items()}
    scene = _SceneBuilder(topic, values)

    if topic == "ch08.quadratic.matrix-form":
        for role, entity in entities.items():
            scene.matrix_diagram(entity.id, values[role], f"{topic}__entity__{role}")
        group_roles = {
            "diagonal_examples": ("circle", "aligned_ellipse"),
            "positive_cross_examples": ("positive_unit", "positive_scaled"),
            "negative_cross_example": ("negative_cross",),
        }
        for name, roles in group_roles.items():
            offsets = (-1.65, 1.65) if len(roles) == 2 else (0.0,)
            for role, offset in zip(roles, offsets):
                scene.matrix_diagram(relations[name].id, values[role], f"{topic}__relation__{name}__{role}", center_x=offset)
        for stage, descriptor in zip(semantics.stages, spec_for(topic).stages):
            roles = descriptor.input_roles
            offsets = (-1.65, 1.65) if len(roles) == 2 else (0.0,)
            for role, offset in zip(roles, offsets):
                scene.matrix_diagram(stage.id, values[role], f"{topic}__stage__{descriptor.name}__{role}", center_x=offset)
        return scene.operations, scene.aliases

    colors = {"aligned": BLUE, "tilted": ORANGE, "positive": BLUE, "negative": GRAY, "indefinite": ORANGE, "semidefinite": GREEN}
    for role, entity in entities.items():
        if entity.kind == "matrix" and role not in {"axes", "rotation"}:
            if role == "semidefinite":
                scene.line(entity.id, (-3.0, 3.0), (3.0, -3.0), f"{topic}__entity__{role}", color=colors[role])
            else:
                scene.quadratic(entity.id, values[role], f"{topic}__entity__{role}", color=colors.get(role, GREEN))
        elif role in {"axes", "rotation"}:
            scene.line(entity.id, -3.0 * values[role][:, 0], 3.0 * values[role][:, 0], f"{topic}__entity__{role}__axis_1", color=BLUE)
            scene.line(entity.id, -3.0 * values[role][:, 1], 3.0 * values[role][:, 1], f"{topic}__entity__{role}__axis_2", color=ORANGE)
        else:
            scene.line(entity.id, (0.0, 0.0), values[role], f"{topic}__entity__{role}", color=BLUE)

    if topic == "ch08.quadratic.level-sets":
        owner = relations["level_comparison"].id
        scene.quadratic(owner, values["aligned"], f"{topic}__relation__level_comparison__aligned", color=BLUE)
        scene.quadratic(owner, values["tilted"], f"{topic}__relation__level_comparison__tilted", color=ORANGE)
        for stage, descriptor in zip(semantics.stages, spec_for(topic).stages):
            role = descriptor.name
            scene.quadratic(stage.id, values[role], f"{topic}__stage__{role}", color=colors[role])
    elif topic == "ch08.principal-axis":
        owner = relations["orthogonal_axes"].id
        scene.quadratic(owner, values["matrix"], f"{topic}__relation__orthogonal_axes__form")
        scene.line(owner, -3.0 * values["axes"][:, 0], 3.0 * values["axes"][:, 0], f"{topic}__relation__orthogonal_axes__q1", color=BLUE, label="q1")
        scene.line(owner, -3.0 * values["axes"][:, 1], 3.0 * values["axes"][:, 1], f"{topic}__relation__orthogonal_axes__q2", color=ORANGE, label="q2")
        scene.transform(relations["rotation"].id, values["axes"].T, values["point"], f"{topic}__relation__rotation")
        scene.quadratic(relations["standard_form"].id, values["standard"], f"{topic}__relation__standard_form")
        scene.quadratic(semantics.stages[0].id, values["matrix"], f"{topic}__stage__original")
        axes_owner = semantics.stages[1].id
        scene.quadratic(axes_owner, values["matrix"], f"{topic}__stage__axes__form")
        scene.line(axes_owner, -3.0 * values["axes"][:, 0], 3.0 * values["axes"][:, 0], f"{topic}__stage__axes__q1", color=BLUE, label="q1")
        scene.line(axes_owner, -3.0 * values["axes"][:, 1], 3.0 * values["axes"][:, 1], f"{topic}__stage__axes__q2", color=ORANGE, label="q2")
        scene.transform(axes_owner, values["axes"].T, values["point"], f"{topic}__stage__axes__rotation")
        scene.quadratic(semantics.stages[2].id, values["standard"], f"{topic}__stage__standard")
    else:
        for role, relation in relations.items():
            if role == "semidefinite":
                scene.line(relation.id, (-3.0, 3.0), (3.0, -3.0), f"{topic}__relation__{role}", color=colors[role])
            else:
                scene.quadratic(relation.id, values[role], f"{topic}__relation__{role}", color=colors[role])
        for stage, descriptor in zip(semantics.stages, spec_for(topic).stages):
            role = descriptor.name
            if role == "semidefinite":
                scene.line(stage.id, (-3.0, 3.0), (3.0, -3.0), f"{topic}__stage__{role}", color=colors[role])
            else:
                scene.quadratic(stage.id, values[role], f"{topic}__stage__{role}", color=colors[role])
    return scene.operations, scene.aliases


def compile_chapter_08(topic: str, semantics: object, context: object = None) -> dict[str, object]:
    try:
        spec, entities, relations = _validate_descriptors(topic, semantics)
        values = {role: np.asarray(entity.value, dtype=float) for role, entity in entities.items()}
        evidence = _evidence(topic, values, relations)
        operations, aliases = _compile_scene(topic, semantics, entities, relations)
        return json.loads(json.dumps({"operations": operations, "aliases": aliases, "evidence": evidence}))
    except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as error:
        raise VisualCompileError((CompileIssue("invalid_chapter_08_semantics", "$.visual_semantics", str(error)),)) from error
