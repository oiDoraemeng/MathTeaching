"""Compile lecture-grounded visual semantics into validated scene plans.

The compiler is deliberately a one-way boundary.  It consumes immutable
mathematical records and emits a ``CommandPlan``; it never imports Qt, a
renderer, or a scene host, and it never executes a command.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping

from linear_algebra.teaching.model import TeachingArtifact, VisualEntity, VisualRelation, VisualSemantics
from linear_algebra.teaching.validation import (
    ArtifactValidationError,
    validate_artifact_payload,
    validate_claim_bindings,
)
from services.scene_commands import CommandPlan, SceneCommandService

from .common import RenderContext
from .contracts import VisualContract, contract_for, validate_contract_semantics


COMPILER_VERSION = "visual-compiler-v1"
_SAFE_ALIAS = re.compile(r"[^A-Za-z0-9_.:-]+")


@dataclass(frozen=True)
class CompileIssue:
    code: str
    path: str
    message: str


class VisualCompileError(ValueError):
    """Raised before a renderer can be reached when compilation is unsafe."""

    def __init__(self, issues: tuple[CompileIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))


@dataclass(frozen=True)
class CompiledVisualization:
    """A deterministic, validated plan plus semantic-to-alias evidence."""

    topic_id: str
    compiler_version: str
    render_profile: str
    plan: CommandPlan
    plan_digest: str
    aliases: tuple[tuple[str, tuple[str, ...]], ...] = ()
    evidence: object | None = None

    def aliases_for(self, semantic_id: str) -> tuple[str, ...]:
        for key, values in self.aliases:
            if key == semantic_id:
                return values
        return ()


class VisualSemanticsCompiler:
    """Compile an artifact or a standalone semantic graph without a host."""

    def __init__(self, *, compiler_version: str = COMPILER_VERSION) -> None:
        self.compiler_version = compiler_version

    def compile(
        self,
        source: TeachingArtifact | VisualSemantics,
        contract: VisualContract | None = None,
        context: RenderContext | None = None,
        *,
        topic_id: str | None = None,
    ) -> CompiledVisualization:
        artifact = source if isinstance(source, TeachingArtifact) else None
        semantics = source.visual_semantics if artifact is not None else source
        resolved_topic = topic_id or (artifact.topic_id if artifact is not None else None)
        if contract is None:
            if resolved_topic is None:
                raise ValueError("standalone visual semantics requires contract or topic_id")
            contract = contract_for(resolved_topic)
        resolved_topic = resolved_topic or contract.topic_id
        context = context or RenderContext.default(resolved_topic)

        issues = self._validate_input(artifact, semantics, contract, context, resolved_topic)
        if issues:
            raise VisualCompileError(tuple(sorted(issues, key=lambda issue: (issue.code, issue.path, issue.message))))

        operations: list[dict[str, Any]] = []
        aliases: dict[str, list[str]] = {}
        for entity in semantics.entities:
            entity_operations, entity_aliases = self._compile_entity(entity, semantics.scene_kind, context)
            operations.extend(entity_operations)
            aliases.setdefault(entity.id, []).extend(entity_aliases)

        for relation in semantics.relations:
            relation_operations, relation_aliases = self._compile_relation(
                relation, semantics, context, aliases
            )
            operations.extend(relation_operations)
            aliases.setdefault(relation.id, []).extend(relation_aliases)

        operations.append({"op": "view.fit", "padding": 1.15})
        summary = artifact.explanation.title if artifact is not None else f"visual semantics: {resolved_topic}"
        plan = CommandPlan(scene=semantics.scene_kind, operations=tuple(operations), summary=summary)
        validation = SceneCommandService().validate(plan)
        if not validation.valid:
            raise VisualCompileError(
                tuple(
                    CompileIssue("scene_scope", f"$.operations[{index}]", message)
                    for index, message in enumerate(validation.messages)
                )
            )
        digest_payload = {
            "compiler_version": self.compiler_version,
            "render_profile": context.render_profile,
            "plan": plan.to_dict(),
        }
        digest_source = json.dumps(digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        plan_digest = "sha256:" + hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        compiled = CompiledVisualization(
            topic_id=resolved_topic,
            compiler_version=self.compiler_version,
            render_profile=context.render_profile,
            plan=plan,
            plan_digest=plan_digest,
            aliases=tuple((key, tuple(values)) for key, values in sorted(aliases.items())),
        )
        if artifact is not None:
            from .evidence import build_evidence_ledger

            ledger, evidence_issues = build_evidence_ledger(artifact, compiled)
            if evidence_issues:
                raise VisualCompileError(
                    tuple(
                        CompileIssue(issue.code, issue.path, issue.message)
                        for issue in evidence_issues
                    )
                )
            compiled = CompiledVisualization(
                topic_id=compiled.topic_id,
                compiler_version=compiled.compiler_version,
                render_profile=compiled.render_profile,
                plan=compiled.plan,
                plan_digest=compiled.plan_digest,
                aliases=compiled.aliases,
                evidence=ledger,
            )
        return compiled

    def _validate_input(
        self,
        artifact: TeachingArtifact | None,
        semantics: VisualSemantics,
        contract: VisualContract,
        context: RenderContext,
        topic_id: str,
    ) -> list[CompileIssue]:
        issues: list[CompileIssue] = []
        if context.topic_id != topic_id:
            issues.append(CompileIssue("topic_mismatch", "$.context.topic_id", context.topic_id))
        if context.render_profile.strip() == "":
            issues.append(CompileIssue("invalid_render_profile", "$.context.render_profile", "must not be empty"))
        if artifact is not None:
            try:
                validate_artifact_payload(artifact.to_dict())
            except ArtifactValidationError as error:
                issues.extend(CompileIssue(issue.code, issue.path, issue.message) for issue in error.issues)
            issues.extend(
                CompileIssue(issue.code, issue.path, issue.message)
                for issue in validate_claim_bindings(artifact)
            )
        issues.extend(self._reference_issues(semantics))
        issues.extend(
            CompileIssue(issue.code, f"$.visual_semantics.{issue.code}", issue.detail)
            for issue in validate_contract_semantics(semantics, contract, topic_id=topic_id)
        )
        if semantics.scene_kind not in {"2d", "3d"}:
            issues.append(CompileIssue("scene_scope", "$.visual_semantics.scene_kind", "scene must be 2d or 3d"))
        return issues

    @staticmethod
    def _reference_issues(semantics: VisualSemantics) -> list[CompileIssue]:
        issues: list[CompileIssue] = []
        entity_ids = [entity.id for entity in semantics.entities]
        relation_ids = [relation.id for relation in semantics.relations]
        stage_ids = [stage.id for stage in semantics.stages]
        for kind, values, path in (
            ("entity", entity_ids, "$.visual_semantics.entities"),
            ("relation", relation_ids, "$.visual_semantics.relations"),
            ("stage", stage_ids, "$.visual_semantics.stages"),
        ):
            seen: set[str] = set()
            for index, value in enumerate(values):
                if value in seen:
                    issues.append(CompileIssue("duplicate_id", f"{path}[{index}].id", f"duplicate {kind} id {value!r}"))
                seen.add(value)
        entity_set = set(entity_ids)
        relation_set = set(relation_ids)
        for index, relation in enumerate(semantics.relations):
            for field, value in (("source_ref", relation.source_ref), ("target_ref", relation.target_ref)):
                if value not in entity_set:
                    issues.append(CompileIssue("dangling_reference", f"$.visual_semantics.relations[{index}].{field}", value))
        for index, stage in enumerate(semantics.stages):
            for field, values, known in (
                ("input_entity_refs", stage.input_entity_refs, entity_set),
                ("output_entity_refs", stage.output_entity_refs, entity_set),
                ("relation_refs", stage.relation_refs, relation_set),
            ):
                for ref_index, value in enumerate(values):
                    if value not in known:
                        issues.append(CompileIssue("dangling_reference", f"$.visual_semantics.stages[{index}].{field}[{ref_index}]", value))
        return issues

    def _compile_entity(
        self, entity: VisualEntity, scene: str, context: RenderContext
    ) -> tuple[list[dict[str, Any]], list[str]]:
        operations: list[dict[str, Any]] = []
        aliases: list[str] = []
        prefix = _alias(entity.id)
        role = entity.role if entity.role in {"construction", "result"} else "primary"
        if entity.kind == "point":
            coordinates = _coordinates(entity.value, entity.dimension)
            if scene == "2d":
                operations.append({"op": "point.upsert", "alias": prefix, "coordinates": list(coordinates), "name": entity.label})
            else:
                operations.append({"op": "point3d.upsert", "alias": prefix, "coordinates": list(coordinates), "name": entity.label})
            aliases.append(prefix)
        elif entity.kind == "vector":
            coordinates = _coordinates(entity.value, entity.dimension)
            origin = f"{prefix}__origin"
            end = f"{prefix}__end"
            aliases.extend((prefix, end))
            if scene == "2d":
                operations.extend(
                    [
                        {"op": "point.upsert", "alias": origin, "coordinates": [0.0, 0.0], "name": "O"},
                        {"op": "point.upsert", "alias": end, "coordinates": list(coordinates), "name": entity.label},
                        {"op": "linear.upsert", "alias": prefix, "start": origin, "end": end, "kind": "vector", "role": role, "label": entity.label},
                    ]
                )
            else:
                operations.append(
                    {"op": "linear3d.upsert", "alias": prefix, "start": [0.0, 0.0, 0.0], "end": list(coordinates), "kind": "vector", "role": role, "label": entity.label}
                )
        elif entity.kind in {"matrix", "grid"} and scene == "2d":
            matrix = _matrix2(entity.value)
            if matrix is not None:
                operations.append({"op": "geometry.transformed_grid", "matrix": matrix, "bounds": list(context.bounds), "step": 1.0})
                aliases.append(prefix)
        elif entity.kind in {"basis", "region"} and scene == "2d":
            basis = _vectors2(entity.value)
            if basis:
                operations.append({"op": "geometry.subspace_region", "basis": [list(vector) for vector in basis], "bounds": list(context.bounds), "opacity": 0.2})
                aliases.append(prefix)
        elif entity.kind == "area" and scene == "2d":
            vectors = _vectors2(entity.value)
            if len(vectors) == 2:
                operations.append({"op": "geometry.oriented_area", "alias": prefix, "vectors": [list(vector) for vector in vectors]})
                aliases.append(prefix)
        elif entity.kind == "volume" and scene == "3d":
            vectors = _vectors3(entity.value)
            if len(vectors) == 3:
                operations.append({"op": "geometry.parallelepiped", "alias": prefix, "origin": [0.0, 0.0, 0.0], "vectors": [list(vector) for vector in vectors], "opacity": 0.2})
                aliases.append(prefix)
        return operations, aliases

    def _compile_relation(
        self,
        relation: VisualRelation,
        semantics: VisualSemantics,
        context: RenderContext,
        aliases: Mapping[str, list[str]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        entity_by_id = {entity.id: entity for entity in semantics.entities}
        source = entity_by_id[relation.source_ref]
        target = entity_by_id[relation.target_ref]
        operations: list[dict[str, Any]] = []
        relation_alias = _alias(relation.id)
        if relation.kind == "projects_to" and semantics.scene_kind == "2d":
            source_coordinates = _coordinates(source.value, 2)
            direction_coordinates = _coordinates(target.value, 2)
            foot = next((entity for entity in semantics.entities if entity.role == "foot"), None)
            residual = next((entity for entity in semantics.entities if entity.role == "residual"), None)
            operations.append(
                {
                    "op": "geometry.projection",
                    "vector": list(source_coordinates),
                    "direction": list(direction_coordinates),
                    "result_alias": _alias(target.id),
                    "foot_alias": _alias(foot.id) if foot else f"{relation_alias}__foot",
                    "residual_alias": _alias(residual.id) if residual else f"{relation_alias}__residual",
                }
            )
            return operations, [relation_alias]
        matrix = _matrix2(relation.parameters.get("matrix")) if isinstance(relation.parameters, Mapping) else None
        if relation.kind == "maps_to" and matrix is not None and semantics.scene_kind == "2d":
            operations.append({"op": "linear_algebra.matrix_transform", "matrix": matrix})
            return operations, [relation_alias]
        matrices = relation.parameters.get("matrices") if isinstance(relation.parameters, Mapping) else None
        if relation.kind == "composition_order" and _matrix_sequence(matrices):
            points = [_coordinates(entity_by_id[ref].value, 2) for ref in (relation.source_ref, relation.target_ref)]
            operations.append({"op": "geometry.staged_transform", "matrices": matrices, "points": [list(point) for point in points], "aliases": [f"{relation_alias}__source", f"{relation_alias}__target"]})
            return operations, [relation_alias]
        # Semantic relations without a dedicated primitive remain visible as
        # bounded annotations.  They do not carry executable text or colors.
        position = _annotation_position(len(operations), context.bounds, semantics.scene_kind)
        operations.append(
            {
                "op": "annotation.upsert",
                "alias": relation_alias,
                "text": f"{relation.kind}: {source.label} → {target.label}",
                "position": position,
            }
        )
        return operations, [relation_alias]


def _alias(value: str) -> str:
    result = _SAFE_ALIAS.sub("_", value).strip("_") or "semantic"
    return f"sem__{result}"


def _coordinates(value: object, dimension: int) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != dimension:
        raise VisualCompileError((CompileIssue("invalid_value", "$.visual_semantics", f"expected a {dimension}D coordinate"),))
    coordinates = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in coordinates):
        raise VisualCompileError((CompileIssue("invalid_value", "$.visual_semantics", "coordinates must be finite"),))
    return coordinates


def _matrix2(value: object) -> list[list[float]] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    if any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in value):
        return None
    matrix = [[float(item) for item in row] for row in value]
    return matrix if all(math.isfinite(item) for row in matrix for item in row) else None


def _vectors2(value: object) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    vectors: list[tuple[float, float]] = []
    for item in value:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            vector = (float(item[0]), float(item[1]))
            if all(math.isfinite(number) for number in vector):
                vectors.append(vector)
    return tuple(vectors)


def _vectors3(value: object) -> tuple[tuple[float, float, float], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    vectors: list[tuple[float, float, float]] = []
    for item in value:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            vector = (float(item[0]), float(item[1]), float(item[2]))
            if all(math.isfinite(number) for number in vector):
                vectors.append(vector)
    return tuple(vectors)


def _matrix_sequence(value: object) -> bool:
    return isinstance(value, (list, tuple)) and bool(value) and all(_matrix2(matrix) is not None for matrix in value)


def _annotation_position(index: int, bounds: tuple[float, float, float, float], scene: str) -> list[float]:
    left, right, bottom, top = bounds
    x = left + 0.35 + (index % 3) * 0.8
    y = top - 0.35 - (index // 3) * 0.35
    # annotation.upsert is a 2D protocol primitive even in a 3D plan; the
    # scene host projects this label into its overlay layer.
    return [x, y]


__all__ = [
    "COMPILER_VERSION",
    "CompileIssue",
    "CompiledVisualization",
    "VisualCompileError",
    "VisualSemanticsCompiler",
]
