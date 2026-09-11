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
from .palette import role_color
from .limits import validate_budget


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
    storyboard: tuple["CompiledStoryboardStage", ...] = ()

    def aliases_for(self, semantic_id: str) -> tuple[str, ...]:
        for key, values in self.aliases:
            if key == semantic_id:
                return values
        return ()


@dataclass(frozen=True)
class CompiledStoryboardStage:
    id: str
    title: str
    caption: str
    layout: str
    visible_refs: tuple[str, ...]
    visible_aliases: tuple[str, ...]
    anchor: tuple[float, float]


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
        # Family compilers are the semantic source of truth for chapter 4.
        from .families import family_compiler_for
        family_result = None
        if resolved_topic.startswith("ch04."):
            family_result = family_compiler_for(semantics.scene_family).compile(
                topic_id=resolved_topic, semantics=semantics, context=context
            )
        if isinstance(family_result, Mapping):
            operations.extend(list(family_result.get("operations", ())))
            family_aliases = family_result.get("aliases", ())
            if isinstance(family_aliases, Mapping):
                for key, values in family_aliases.items():
                    vals = values if isinstance(values, (list, tuple)) else (values,)
                    aliases.setdefault(str(key), []).extend(str(value) for value in vals)
            else:
                for alias in family_aliases:
                    aliases.setdefault(str(alias), []).append(str(alias))
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

        if not resolved_topic.startswith("ch04."):
            self._emit_declared_capability_evidence(semantics, context, operations, aliases, resolved_topic)

        storyboard, stage_operations, stage_issues = self._compile_storyboard(semantics, context, aliases)
        if stage_issues:
            raise VisualCompileError(tuple(stage_issues))
        operations.extend(stage_operations)

        # Formula annotations are a declared catalog capability rather than
        # executable model output.  Emit them only for topics that explicitly
        # request the capability; this preserves the compact plan shape for
        # topics whose contract does not include a formula label.
        if artifact is not None and _topic_requires_capability(resolved_topic, "annotation_formula"):
            formula = artifact.explanation.formula.strip()
            if formula:
                operations.append(
                    {
                        "op": "annotation.formula",
                        "alias": f"{_alias(resolved_topic)}__formula",
                        "text": formula,
                        "position": [context.bounds[0] + 0.35, context.bounds[3] - 0.35],
                    }
                )
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
            "seed": context.seed,
            "bounds": list(context.bounds),
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
            storyboard=storyboard,
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
                storyboard=compiled.storyboard,
            )
        return compiled

    def _emit_declared_capability_evidence(
        self,
        semantics: VisualSemantics,
        context: RenderContext,
        operations: list[dict[str, Any]],
        aliases: dict[str, list[str]],
        topic_id: str,
    ) -> None:
        """Fill small, typed evidence gaps declared by the catalog.

        A provider is not allowed to emit operations.  Some explanations only
        need to name a relationship (for example, an angle or a triangle) and
        therefore omit a dedicated relation node.  These bounded fallbacks
        derive the missing primitive from the first compatible semantic
        entities, keeping capability coverage explicit without inventing
        arbitrary scene data.
        """

        declared = _topic_capabilities(topic_id)
        operation_names = {str(operation.get("op")) for operation in operations}
        entities = tuple(entity for entity in semantics.entities if entity.kind == "vector")
        vectors2 = tuple(
            _coordinates(entity.value, 2)
            for entity in entities
            if entity.dimension == 2
        )
        if "vector_2d" in declared and "linear.upsert" not in operation_names and semantics.scene_kind == "2d":
            vector = vectors2[0] if vectors2 else None
            if vector is not None:
                operations.extend(
                    [
                        {"op": "point.upsert", "alias": "cap__vector2d_origin", "coordinates": [0.0, 0.0], "name": "O"},
                        {"op": "point.upsert", "alias": "cap__vector2d_end", "coordinates": list(vector), "name": "v"},
                        {"op": "linear.upsert", "alias": "cap__vector2d", "start": "cap__vector2d_origin", "end": "cap__vector2d_end", "kind": "vector", "role": "primary", "color": role_color("vector_a")},
                    ]
                )
        if "polygon_2d" in declared and "geometry.polygon" not in operation_names:
            if len(vectors2) >= 2:
                first, second = vectors2[:2]
                if abs(first[0] * second[1] - first[1] * second[0]) <= 1e-12:
                    second = (-first[1], first[0]) if abs(first[0]) + abs(first[1]) > 1e-12 else (0.0, 1.0)
                vertices = ([0.0, 0.0], list(first), [first[0] + second[0], first[1] + second[1]], list(second))
                operations.append({"op": "geometry.polygon", "alias": "cap__polygon", "vertices": vertices, "color": role_color("area"), "opacity": 0.24, "outline": True})
        if "projection_2d" in declared and "geometry.projection" not in operation_names:
            if len(vectors2) >= 2:
                operations.append({"op": "geometry.projection", "vector": list(vectors2[0]), "direction": list(vectors2[1]), "result_alias": "cap__projection", "foot_alias": "cap__foot", "residual_alias": "cap__residual", "color": role_color("projection")})
        if "transformed_grid" in declared and "geometry.transformed_grid" not in operation_names and semantics.scene_kind == "2d" and "staged_transform" not in declared:
            matrix = next(
                (matrix for entity in semantics.entities if (matrix := _matrix2(entity.value)) is not None),
                None,
            )
            matrix = matrix or [[1.0, 0.0], [0.0, 1.0]]
            operations.append({"op": "geometry.transformed_grid", "matrix": matrix, "bounds": list(context.bounds), "step": 1.0, "color": role_color("transformed_a")})
        if "subspace_region" in declared and "geometry.subspace_region" not in operation_names and semantics.scene_kind == "2d":
            basis = vectors2[:2]
            if len(basis) >= 1:
                operations.append({"op": "geometry.subspace_region", "basis": [list(vector) for vector in basis], "bounds": list(context.bounds), "opacity": 0.2, "color": role_color("area")})
        if "staged_transform" in declared and "geometry.staged_transform" not in operation_names and semantics.scene_kind == "2d" and _topic_has_matrix_relation(semantics):
            matrix = next(
                (matrix for entity in semantics.entities if (matrix := _matrix2(entity.value)) is not None),
                None,
            )
            point_values = [list(_coordinates(entity.value, 2)) for entity in semantics.entities if entity.kind == "vector" and entity.dimension == 2][:2]
            if matrix is not None and point_values:
                operations.append({"op": "geometry.staged_transform", "matrices": [matrix, [[1.0, 0.0], [0.0, 1.0]]], "points": point_values, "aliases": ["cap__stage_source", "cap__stage_target"]})
        if "angle_2d" in declared and "geometry.angle_arc" not in operation_names:
            if len(vectors2) >= 2:
                operations.append({"op": "geometry.angle_arc", "alias": "cap__angle", "vertex": [0.0, 0.0], "first": list(vectors2[0]), "second": list(vectors2[1]), "radius": 0.45, "color": role_color("projection")})
        if "right_angle_2d" in declared and "geometry.right_angle_marker" not in operation_names:
            if len(vectors2) >= 2:
                operations.append({"op": "geometry.right_angle_marker", "alias": "cap__right_angle", "vertex": [0.0, 0.0], "first": list(vectors2[0]), "second": list(vectors2[1]), "size": 0.3, "color": role_color("neutral")})
        if "vector_3d" in declared and semantics.scene_kind == "3d" and "linear3d.upsert" not in operation_names:
            vector3 = next(
                (tuple(float(value) for value in entity.value) for entity in entities if entity.dimension == 3),
                None,
            )
            if vector3 is not None:
                operations.append({"op": "linear3d.upsert", "alias": "cap__vector3d", "start": [0.0, 0.0, 0.0], "end": list(vector3), "kind": "vector", "role": "primary", "color": role_color("vector_a")})

    @staticmethod
    def _compile_storyboard(
        semantics: VisualSemantics,
        context: RenderContext,
        aliases: Mapping[str, list[str]],
    ) -> tuple[tuple[CompiledStoryboardStage, ...], list[dict[str, Any]], list[CompileIssue]]:
        stages = semantics.stages
        compiled: list[CompiledStoryboardStage] = []
        operations: list[dict[str, Any]] = []
        issues: list[CompileIssue] = []
        for index, stage in enumerate(stages):
            anchor = _stage_anchor(stage.layout, index, len(stages), context.bounds)
            if anchor is None:
                issues.append(CompileIssue("layout_overflow", f"$.visual_semantics.stages[{index}]", stage.id))
                continue
            visible_refs = tuple(dict.fromkeys((*stage.input_entity_refs, *stage.output_entity_refs, *stage.relation_refs)))
            visible_aliases_list = []
            for ref in visible_refs:
                for alias in aliases.get(ref, ()):
                    visible_aliases_list.append(alias)
                    if alias.endswith("__end"):
                        visible_aliases_list.append(f"{alias[:-5]}__origin")
            title_alias = f"{_alias(stage.id)}__title"
            show_case_stage_title = not (
                stage.id.startswith("stage.magnitude.")
                or stage.id.startswith("stage.point-distinction.")
                or stage.id.startswith("stage.coordinate-system.")
                or stage.id.startswith("stage.direction-examples.")
                or stage.id.startswith("stage.subtraction.")
                or stage.id.startswith("stage.scalar.")
                or stage.id.startswith("stage.linear-combination.")
                or stage.id.startswith("stage.velocity.")
                or stage.id.startswith("stage.cross-product.")
                or stage.id.startswith("stage.scalar-triple.")
                or stage.id.startswith("stage.claim.ch01.ops.addition.")
                or stage.id.startswith("stage.case.")
            )
            if show_case_stage_title:
                visible_aliases_list.append(title_alias)
            operations.extend(_stage_geometry_operations(semantics, stage, index, aliases, context))
            visible_aliases_list.extend(_stage_specific_aliases(semantics, index))
            visible_aliases = tuple(dict.fromkeys(visible_aliases_list))
            compiled.append(
                CompiledStoryboardStage(
                    id=stage.id,
                    title=_stage_title(semantics, stage.title, index),
                    caption=_stage_caption(semantics, stage.caption, index),
                    layout=stage.layout,
                    visible_refs=visible_refs,
                    visible_aliases=visible_aliases,
                    anchor=anchor,
                )
            )
            if semantics.scene_kind == "2d" and show_case_stage_title:
                operations.append(
                    {
                        "op": "annotation.upsert",
                        "alias": title_alias,
                        "text": _stage_title(semantics, stage.title, index),
                        "position": list(anchor),
                    }
                )
        return tuple(compiled), operations, issues

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
        if semantics.scene_family:
            from .families import family_compiler_for
            try:
                family_compiler_for(semantics.scene_family)
            except VisualCompileError as error:
                issues.extend(error.issues)
        for error in validate_budget(
            context.render_profile,
            scene=semantics.scene_kind,
            entity_count=len(semantics.entities),
            stage_count=len(semantics.stages),
            sample_count=len(semantics.entities) + len(semantics.relations),
            bounds=context.bounds,
        ):
            issues.append(CompileIssue("render_budget", "$.context", error))
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
                is_magnitude_topic = context.topic_id == "ch01.vector.magnitude"
                is_point_distinction_topic = context.topic_id == "ch01.vector.point-distinction"
                is_zero_vector = not any(abs(value) > 1e-12 for value in coordinates)
                operations.extend(
                    [
                        {
                            "op": "point.upsert",
                            "alias": origin,
                            "coordinates": [0.0, 0.0],
                            "name": (
                                ""
                                if is_magnitude_topic and is_zero_vector
                                else "O"
                                if not is_point_distinction_topic or entity.id == "vector_v"
                                else ""
                            ),
                        },
                        {
                            "op": "point.upsert",
                            "alias": end,
                            "coordinates": list(coordinates),
                            # The vector label is placed once on the segment;
                            # repeating it at the endpoint makes the magnitude
                            # example look cluttered.  A zero vector has no
                            # segment, so retain its point label instead.
                            "name": (
                                ""
                                if is_point_distinction_topic
                                else entity.label
                                if (is_zero_vector or not is_magnitude_topic)
                                else ""
                            ),
                        },
                        {
                            "op": "linear.upsert",
                            "alias": prefix,
                            "start": origin,
                            "end": end,
                            "kind": "vector",
                            "role": role,
                            "color": role_color(entity.role),
                            "label": (
                                ""
                                if (is_magnitude_topic and is_zero_vector)
                                else entity.label
                            ),
                        },
                    ]
                )
            else:
                operations.append(
                    {"op": "linear3d.upsert", "alias": prefix, "start": [0.0, 0.0, 0.0], "end": list(coordinates), "kind": "vector", "role": role, "color": role_color(entity.role), "label": entity.label}
                )
        elif entity.kind in {"matrix", "grid"} and scene == "2d":
            matrix = _matrix2(entity.value)
            if matrix is not None:
                operations.append({"op": "geometry.transformed_grid", "alias": prefix, "matrix": matrix, "bounds": list(context.bounds), "step": 1.0, "color": role_color(entity.role)})
                aliases.append(prefix)
        elif entity.kind in {"basis", "region"} and scene == "2d":
            basis = _vectors2(entity.value)
            if basis:
                operations.append({"op": "geometry.subspace_region", "alias": prefix, "basis": [list(vector) for vector in basis], "bounds": list(context.bounds), "opacity": 0.2, "color": role_color(entity.role)})
                aliases.append(prefix)
        elif entity.kind == "area" and scene == "2d":
            vectors = _vectors2(entity.value)
            if len(vectors) == 2:
                operations.append({"op": "geometry.oriented_area", "alias": prefix, "vectors": [list(vector) for vector in vectors], "color": role_color(entity.role)})
                aliases.append(prefix)
        elif entity.kind == "volume" and scene == "3d":
            vectors = _vectors3(entity.value)
            if len(vectors) == 3:
                volume_payload = {
                    "alias": prefix,
                    "origin": [0.0, 0.0, 0.0],
                    "vectors": [list(vector) for vector in vectors],
                    "color": role_color(entity.role),
                }
                # A volume carries both the signed-measure primitive and the
                # filled parallelepiped primitive when the topic declares the
                # latter capability.  Both are derived from the same typed
                # semantic value and remain renderer-free at this boundary.
                operations.append({"op": "geometry.oriented_volume", **volume_payload})
                if _topic_requires_capability(context.topic_id, "parallelepiped_3d"):
                    operations.append({"op": "geometry.parallelepiped", **volume_payload, "opacity": 0.24})
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
        if relation.kind == "sum" and relation.id.startswith("rel.addition."):
            # Vector-addition cases already render their input and result
            # vectors.  A generic source-to-target annotation is misleading
            # because the target is the second addend, not the sum vector.
            return operations, [relation_alias]
        if relation.id.startswith("rel.magnitude."):
            # The magnitude case is self-contained in the vector and point
            # labels.  Do not expose the compiler's internal relation kind or
            # its source/target labels in the student-facing 2D plot.
            return operations, [relation_alias]
        if relation.id.startswith("rel.point-distinction."):
            # The first pane needs only the position label.  In the second
            # pane, retain the standard-basis decomposition as a native 2D
            # text label: this renderer cannot interpret KaTeX source, so a
            # Unicode subscript label is the stable student-facing form.
            if relation.id == "rel.point-distinction.basis":
                operations.append(
                    {
                        "op": "annotation.upsert",
                        "alias": relation_alias,
                        "text": "v = 3e₁ + 4e₂",
                        # Keep the formula away from the origin-to-(3,4)
                        # arrow, which occupies the first quadrant.
                        "position": [context.bounds[0] + 0.35, context.bounds[2] + 0.55],
                    }
                )
            return operations, [relation_alias]
        if relation.id.startswith("rel.direction-examples."):
            # Direction panes use only the student-facing vector labels.  Do
            # not surface the semantic comparison edge as raw implementation
            # text such as "compare: v→v".
            return operations, [relation_alias]
        if relation.id.startswith("rel.subtraction.") and semantics.scene_kind == "2d":
            # A difference vector joins the two endpoints.  Semantic vectors
            # are normally drawn from the origin, so this explicit relation
            # operation preserves the lecture's endpoint geometry.
            operations.append(
                {
                    "op": "linear.upsert",
                    "alias": relation_alias,
                    "start": f"{_alias(source.id)}__end",
                    "end": f"{_alias(target.id)}__end",
                    "kind": "vector",
                    "role": "result",
                    "color": role_color("result"),
                    "label": "a-b",
                }
            )
            return operations, [relation_alias]
        if relation.id.startswith("rel.scalar."):
            # The two scalar-multiple vectors are the student-facing evidence;
            # the relation itself carries no additional annotation.
            return operations, [relation_alias]
        if relation.id.startswith(("rel.linear-combination.", "rel.velocity.", "rel.cross-product.", "rel.scalar-triple.")):
            # The formula and typed entities are the student-facing evidence;
            # these bookkeeping edges do not need a raw relation annotation.
            return operations, [relation_alias]
        if relation.id.startswith("rel.case.") and relation.kind != "projects_to":
            # Case panes already display their source/result vectors.  A
            # compiler-internal relation label would repeat the case title and
            # expose implementation vocabulary such as “compare”.
            return operations, [relation_alias]
        if relation.kind == "projects_to" and semantics.scene_kind == "2d":
            source_coordinates = _coordinates(source.value, 2)
            direction_coordinates = _coordinates(target.value, 2)
            foot = next((entity for entity in semantics.entities if entity.role == "foot"), None)
            residual = next((entity for entity in semantics.entities if entity.role == "residual"), None)
            operations.append(
                {
                    "op": "geometry.projection",
                    "alias": relation_alias,
                    "vector": list(source_coordinates),
                    "direction": list(direction_coordinates),
                    "result_alias": _alias(target.id),
                    "foot_alias": _alias(foot.id) if foot else f"{relation_alias}__foot",
                    "residual_alias": _alias(residual.id) if residual else f"{relation_alias}__residual",
                    "color": role_color("projection"),
                }
            )
            return operations, [relation_alias]
        matrix = _matrix2(relation.parameters.get("matrix")) if isinstance(relation.parameters, Mapping) else None
        if relation.kind == "maps_to" and matrix is not None and semantics.scene_kind == "2d":
            operations.append(
                {
                    "op": "linear_algebra.matrix_transform",
                    "alias": relation_alias,
                    "matrix": matrix,
                }
            )
            return operations, [relation_alias]
        if relation.kind == "batch_maps_to" and matrix is not None and semantics.scene_kind == "2d":
            operations.append({"op": "geometry.transformed_grid", "alias": relation_alias, "matrix": matrix, "bounds": list(context.bounds), "step": 1.0, "color": role_color("transformed_a")})
            return operations, [relation_alias]
        matrices = relation.parameters.get("matrices") if isinstance(relation.parameters, Mapping) else None
        # A semantic relation parameter is intentionally bounded to one scalar,
        # vector, or matrix.  Accept a single ``matrix`` as the compact
        # one-stage form and normalize it for the staged-transform primitive.
        if not _matrix_sequence(matrices) and isinstance(relation.parameters, Mapping):
            single_matrix = relation.parameters.get("matrix")
            if _matrix2(single_matrix) is not None:
                matrices = [single_matrix]
        if relation.kind == "composition_order" and _matrix_sequence(matrices):
            points = [_coordinates(entity_by_id[ref].value, 2) for ref in (relation.source_ref, relation.target_ref)]
            operations.append({"op": "geometry.staged_transform", "matrices": matrices, "points": [list(point) for point in points], "aliases": [f"{relation_alias}__source", f"{relation_alias}__target"]})
            return operations, [relation_alias]
        if relation.kind == "orientation" and semantics.scene_kind == "2d":
            first = _coordinates(source.value, 2)
            second = _coordinates(target.value, 2)
            operations.append({"op": "geometry.angle_arc", "alias": relation_alias, "vertex": [0.0, 0.0], "first": list(first), "second": list(second), "radius": 0.45, "color": role_color("projection")})
            return operations, [relation_alias]
        if relation.kind == "orthogonal_to" and semantics.scene_kind == "2d":
            first = _coordinates(source.value, 2)
            second = _coordinates(target.value, 2)
            operations.append({"op": "geometry.right_angle_marker", "alias": relation_alias, "vertex": [0.0, 0.0], "first": list(first), "second": list(second), "size": 0.3, "color": role_color("neutral")})
            return operations, [relation_alias]
        if relation.kind == "spans" and semantics.scene_kind == "2d":
            vertices = relation.parameters.get("vertices") if isinstance(relation.parameters, Mapping) else None
            if isinstance(vertices, (list, tuple)) and len(vertices) >= 3:
                points = _vectors2(vertices)
                if len(points) >= 3:
                    operations.append(
                        {
                            "op": "geometry.polygon",
                            "alias": relation_alias,
                            "vertices": [list(point) for point in points],
                            "color": role_color("area"),
                            "opacity": 0.24,
                            "outline": True,
                        }
                    )
                    return operations, [relation_alias]
        # Semantic relations without a dedicated primitive remain visible as
        # bounded 2D annotations.  3D storyboard metadata carries the label,
        # because the current command protocol has no 3D annotation primitive.
        position = _annotation_position(len(operations), context.bounds, semantics.scene_kind)
        if semantics.scene_kind == "3d":
            return operations, [relation_alias]
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


def _stage_title(semantics: VisualSemantics, title: str, index: int) -> str:
    """Turn generator-only stage labels into student-facing geometry names."""
    if title not in {"观察对象", "代数验证"}:
        return title
    relation_kinds = {relation.kind for relation in semantics.relations}
    if "sum" in relation_kinds and len(semantics.stages) >= 2:
        return ("三角形法则", "平行四边形法则")[min(index, 1)]
    if "composition_order" in relation_kinds:
        return ("先做右侧变换", "再做左侧变换")[min(index, 1)]
    if "projects_to" in relation_kinds:
        return ("投影分量", "残差分量")[min(index, 1)]
    if "maps_to" in relation_kinds:
        return ("观察输入网格", "观察输出网格")[min(index, 1)]
    if "spans" in relation_kinds:
        return ("生成的张成区域", "张成区域的边界")[min(index, 1)]
    if "orientation" in relation_kinds:
        return ("第一个向量", "第二个向量")[min(index, 1)]
    if "orthogonal_to" in relation_kinds:
        return ("基准向量", "垂直向量")[min(index, 1)]
    return f"几何意义 {index + 1}"


def _stage_caption(semantics: VisualSemantics, caption: str, index: int) -> str:
    if caption.strip() and caption not in {"先读对象、角色和输入输出。", "按公式计算并检查几何关系。"}:
        return caption
    if any(relation.kind == "sum" for relation in semantics.relations):
        return ("把第二个向量平移到第一个向量的终点，和向量是三角形的第三边。", "以两个向量为邻边作平行四边形，对角线就是和向量。")[min(index, 1)]
    if any(relation.kind == "composition_order" for relation in semantics.relations):
        return ("先观察右侧变换如何移动向量。", "再观察左侧变换如何作用在中间结果上。")[min(index, 1)]
    if any(relation.kind == "projects_to" for relation in semantics.relations):
        return ("沿着方向线读出投影分量。", "看垂直方向上剩下的残差。")[min(index, 1)]
    if any(relation.kind == "maps_to" for relation in semantics.relations):
        return ("先看输入网格，再看它被矩阵拉伸、旋转或剪切后的形状。", "对比同一网格在变换后的方向和面积变化。")[min(index, 1)]
    return caption


def _stage_specific_aliases(semantics: VisualSemantics, index: int) -> tuple[str, ...]:
    """Return aliases for stage-only construction geometry."""
    relation_kinds = {relation.kind for relation in semantics.relations}
    if "sum" in relation_kinds:
        stage_id = str(getattr(semantics.stages[index], "id", "")) if index < len(semantics.stages) else ""
        if "components" in stage_id:
            return ()
        if "geometry" in stage_id:
            return (
                "sem__addition_geometry__translated_b",
                "sem__addition_geometry__triangle",
                "sem__addition_geometry__parallelogram",
            )
        if "velocity" in stage_id:
            return ()
        if "triangle" in stage_id:
            return ("sem__addition_triangle",)
        if "parallelogram" in stage_id:
            return ("sem__addition_parallelogram",)
        return ("sem__addition_triangle",) if index == 0 else ("sem__addition_parallelogram",)
    if "composition_order" in relation_kinds:
        stage_alias = f"sem__stage_order__{index + 1}"
        return (stage_alias,)
    if "projects_to" in relation_kinds:
        stage_alias = f"sem__projection__{index + 1}"
        return (stage_alias,)
    if "maps_to" in relation_kinds:
        return (f"sem__mapping_grid__{index + 1}",)
    if "spans" in relation_kinds:
        return (f"sem__span__{index + 1}",)
    if "orientation" in relation_kinds:
        return (f"sem__orientation__{index + 1}",)
    if "orthogonal_to" in relation_kinds:
        return (f"sem__orthogonal__{index + 1}",)
    return ()


def _stage_geometry_operations(
    semantics: VisualSemantics,
    stage: Any,
    index: int,
    aliases: Mapping[str, list[str]],
    context: RenderContext,
) -> list[dict[str, Any]]:
    """Compile visible construction geometry for vector-addition examples."""
    if semantics.scene_kind != "2d":
        return []
    entity_by_id = {entity.id: entity for entity in semantics.entities}
    relation_kinds = {relation.kind for relation in semantics.relations}
    vectors = [entity_by_id[ref] for ref in stage.input_entity_refs if ref in entity_by_id and entity_by_id[ref].kind == "vector"]
    if "sum" in relation_kinds:
        if len(vectors) < 2:
            return []
        a = _coordinates(vectors[0].value, 2)
        b = _coordinates(vectors[1].value, 2)
        stage_id = str(getattr(stage, "id", ""))
        if "components" in stage_id:
            return []
        if "geometry" in stage_id:
            endpoint = (a[0] + b[0], a[1] + b[1])
            return [
                {
                    "op": "linear.upsert",
                    "alias": "sem__addition_geometry__translated_b",
                    "start": f"{_alias(vectors[0].id)}__end",
                    "end": f"{_alias(stage.output_entity_refs[0])}__end",
                    "kind": "vector",
                    "role": "construction",
                    "color": role_color("vector_b"),
                    "label": "b",
                },
                {
                    "op": "geometry.polygon",
                    "alias": "sem__addition_geometry__triangle",
                    "vertices": [[0.0, 0.0], list(a), list(endpoint)],
                    "color": role_color("vector_b"),
                    "opacity": 0.10,
                    "outline": True,
                },
                {
                    "op": "geometry.polygon",
                    "alias": "sem__addition_geometry__parallelogram",
                    "vertices": [[0.0, 0.0], list(a), list(endpoint), list(b)],
                    "color": role_color("construction"),
                    "opacity": 0.08,
                    "outline": True,
                },
            ]
        if "velocity" in stage_id:
            return []
        if "triangle" in stage_id or ("parallelogram" not in stage_id and index == 0):
            return [{"op": "geometry.polygon", "alias": "sem__addition_triangle", "vertices": [[0.0, 0.0], list(a), [a[0] + b[0], a[1] + b[1]]], "color": role_color("construction"), "opacity": 0.14, "outline": True}]
        return [{"op": "geometry.polygon", "alias": "sem__addition_parallelogram", "vertices": [[0.0, 0.0], list(a), [a[0] + b[0], a[1] + b[1]], list(b)], "color": role_color("construction"), "opacity": 0.14, "outline": True}]
    if "composition_order" in relation_kinds:
        relation = next(
            (
                item
                for item in semantics.relations
                if item.kind == "composition_order"
                and (not stage.relation_refs or item.id in stage.relation_refs)
            ),
            None,
        )
        if relation is None or not isinstance(relation.parameters, Mapping):
            return []
        matrices = relation.parameters.get("matrices")
        if not _matrix_sequence(matrices):
            single_matrix = relation.parameters.get("matrix")
            if _matrix2(single_matrix) is not None:
                matrices = [single_matrix]
        if not _matrix_sequence(matrices):
            return []
        stage_alias = f"sem__stage_order__{index + 1}"
        point_entities: list[VisualEntity] = []
        for entity_id in (relation.source_ref, relation.target_ref):
            entity = entity_by_id.get(entity_id)
            if entity is not None and entity.kind == "vector" and entity not in point_entities:
                point_entities.append(entity)
        if not point_entities:
            point_entities = vectors[:2]
        if not point_entities:
            return []
        point_values = [list(_coordinates(entity.value, 2)) for entity in point_entities]
        point_aliases = [
            f"{stage_alias}__{'source' if item_index == 0 else 'target'}"
            for item_index in range(len(point_values))
        ]
        return [
            {
                "op": "geometry.staged_transform",
                "alias": stage_alias,
                "matrices": list(matrices)[: min(index + 1, len(matrices))],
                "points": point_values,
                "aliases": point_aliases,
            }
        ]
    if "projects_to" in relation_kinds:
        relation = next((item for item in semantics.relations if item.kind == "projects_to"), None)
        if relation is None:
            return []
        source = entity_by_id.get(relation.source_ref)
        direction = entity_by_id.get(relation.target_ref)
        if source is None or direction is None or source.kind != "vector" or direction.kind != "vector":
            return []
        stage_alias = f"sem__projection__{index + 1}"
        return [{
            "op": "geometry.projection",
            "alias": stage_alias,
            "vector": list(_coordinates(source.value, 2)),
            "direction": list(_coordinates(direction.value, 2)),
            "result_alias": stage_alias,
            "foot_alias": f"{stage_alias}__foot",
            "residual_alias": f"{stage_alias}__residual",
            "color": role_color("projection"),
        }]
    if "maps_to" in relation_kinds:
        matrix = next(
            (_matrix2(relation.parameters.get("matrix")) for relation in semantics.relations if relation.kind == "maps_to" and isinstance(relation.parameters, Mapping) and _matrix2(relation.parameters.get("matrix")) is not None),
            None,
        )
        if matrix is None:
            return []
        stage_alias = f"sem__mapping_grid__{index + 1}"
        return [{"op": "geometry.transformed_grid", "alias": stage_alias, "matrix": matrix, "bounds": list(context.bounds), "step": 1.0, "color": role_color("transformed_a")}]
    if "spans" in relation_kinds:
        relation = next((item for item in semantics.relations if item.kind == "spans"), None)
        if relation is None or not isinstance(relation.parameters, Mapping):
            return []
        vertices = relation.parameters.get("vertices")
        if not isinstance(vertices, (list, tuple)) or len(vertices) < 3:
            return []
        points = _vectors2(vertices)
        if len(points) < 3:
            return []
        return [{"op": "geometry.polygon", "alias": f"sem__span__{index + 1}", "vertices": [list(point) for point in points], "color": role_color("area"), "opacity": 0.24, "outline": True}]
    if "orientation" in relation_kinds:
        relation = next((item for item in semantics.relations if item.kind == "orientation"), None)
        if relation is None:
            return []
        first = _coordinates(entity_by_id[relation.source_ref].value, 2)
        second = _coordinates(entity_by_id[relation.target_ref].value, 2)
        return [{"op": "geometry.angle_arc", "alias": f"sem__orientation__{index + 1}", "vertex": [0.0, 0.0], "first": list(first), "second": list(second), "radius": 0.45, "color": role_color("projection")}]
    if "orthogonal_to" in relation_kinds:
        relation = next((item for item in semantics.relations if item.kind == "orthogonal_to"), None)
        if relation is None:
            return []
        first = _coordinates(entity_by_id[relation.source_ref].value, 2)
        second = _coordinates(entity_by_id[relation.target_ref].value, 2)
        return [{"op": "geometry.right_angle_marker", "alias": f"sem__orthogonal__{index + 1}", "vertex": [0.0, 0.0], "first": list(first), "second": list(second), "size": 0.3, "color": role_color("neutral")}]
    return []


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


def _topic_requires_capability(topic_id: str, capability: str) -> bool:
    """Read a catalog declaration without coupling the compiler to a registry."""

    from linear_algebra.catalog.manifest import topic_entries

    return any(
        topic.id == topic_id and capability in topic.required_capabilities
        for topic in topic_entries()
    )


def _topic_capabilities(topic_id: str) -> frozenset[str]:
    from linear_algebra.catalog.manifest import topic_entries

    for topic in topic_entries():
        if topic.id == topic_id:
            return frozenset(topic.required_capabilities)
    return frozenset()


def _topic_has_matrix_relation(semantics: VisualSemantics) -> bool:
    return any(
        relation.kind in {"maps_to", "batch_maps_to"}
        and isinstance(relation.parameters, Mapping)
        and _matrix2(relation.parameters.get("matrix")) is not None
        for relation in semantics.relations
    )


def _annotation_position(index: int, bounds: tuple[float, float, float, float], scene: str) -> list[float]:
    left, right, bottom, top = bounds
    x = left + 0.35 + (index % 3) * 0.8
    y = top - 0.35 - (index // 3) * 0.35
    # annotation.upsert is a 2D protocol primitive even in a 3D plan; the
    # scene host projects this label into its overlay layer.
    return [x, y]


def _stage_anchor(
    layout: str, index: int, count: int, bounds: tuple[float, float, float, float]
) -> tuple[float, float] | None:
    left, right, bottom, top = bounds
    width = right - left
    height = top - bottom
    if layout == "side_by_side":
        x = left + width * ((index + 0.5) / max(count, 1))
        y = top - min(0.35, height * 0.1)
    elif layout == "overlay":
        x = left + width * 0.5
        y = top - min(0.35, height * 0.1)
    else:  # sequence
        x = left + min(0.35, width * 0.1)
        y = top - min(0.35, height * 0.1) - index * max(0.45, height * 0.08)
    if not (left <= x <= right and bottom <= y <= top):
        return None
    return (round(x, 8), round(y, 8))


def storyboard_visibility(compiled: CompiledVisualization, stage_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return aliases controlled by a storyboard and those shown for one stage."""
    stage = next((item for item in compiled.storyboard if item.id == stage_id), None)
    if stage is None:
        raise ValueError(f"unknown storyboard stage: {stage_id}")
    all_aliases = tuple(
        dict.fromkeys(alias for item in compiled.storyboard for alias in item.visible_aliases)
    )
    return all_aliases, stage.visible_aliases


__all__ = [
    "COMPILER_VERSION",
    "CompileIssue",
    "CompiledVisualization",
    "CompiledStoryboardStage",
    "VisualCompileError",
    "VisualSemanticsCompiler",
    "storyboard_visibility",
]
