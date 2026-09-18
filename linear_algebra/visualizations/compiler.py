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
# Section 1.5 (geometry proofs) draws a constructed figure rather than a pair
# of free vectors.  Its entity graph declares the two lecture inputs ``a`` and
# ``b``; the figure below derives every midpoint, third side and diagonal from
# those values so the picture and the worked numbers cannot drift apart.
_PROOF_TOPICS = frozenset(
    {
        "ch01.proof.midline",
        "ch01.proof.centroid",
        "ch01.proof.parallelogram-diagonals",
    }
)
# 采用“数学案例流程”并排展示的小节：多个案例窗格必须共用一个固定视角，
# 否则“全部显示”时各窗格按自身对象缩放，会出现一大一小。
_MATRIX_VECTOR_CASE_TOPICS = frozenset(
    {
        "ch02.matrix.row-column",
        "ch02.matrix.transformed-grid",
        "ch02.matrix.stretch-rotate-scale",
        # 2.7 矩阵与基用两组基各占一个窗格，展示同一个旋转在换基后的矩阵。
        "ch02.matrix.basis",
    }
)
# 2.9 的两个小节（线性无关与线性相关、秩）也是按步骤的数学案例，但窗格的主角是
# 「变换后的网格」而不是若干向量：取景若沿用向量的端点，原点会落到窗格角上、
# 被压成的那条线会贴着边缘。它们改为以默认视野为基准共用同一相机，网格仍用大
# 取样范围由视口裁切。
_SUBSPACE_CASE_TOPICS = frozenset(
    {
        "ch02.subspace.independence",
        "ch02.subspace.rank",
    }
)
_FLOW_VIEW_TOPICS = frozenset(
    {
        "ch01.ops.addition",
        "ch01.ops.subtraction",
        "ch01.ops.scalar",
        "ch01.ops.linear-combination",
        "ch01.inner.definitions",
        # 2.2 批量内积沿用 1.3.1 的窗格词汇（u、V 的一列、投影与夹角），
        # 多个案例窗格必须共用同一视角。
        "ch02.batch.inner-products",
        # 3.1 的案例是两步流程：单位正方形一格、两个像与 ad - bc 的外接矩形
        # 构造一格，两格必须共用一个固定视角。
        "ch03.det.oriented-area",
        *_MATRIX_VECTOR_CASE_TOPICS,
    }
)
# 2.5 的矩阵案例用软件已有的矩阵变换功能画网格：取样范围取得比窗格视野大得多，
# 于是变形网格铺满整个窗格、由视口负责裁切（与工具箱“矩阵变换”取当前视口范围
# 一样），而不是在原来坐标系里悬浮一小块网格。案例窗格取景时会把网格演员排除
# 在外，所以取样范围不会把相机拉远。
_MATRIX_VECTOR_GRID_BOUNDS: tuple[float, float, float, float] = (-12.0, 12.0, -12.0, 12.0)
# 3.1 案例把外接矩形的面积标注写在矩形上边之外，取景与标注位置共用这个边距。
_DET_BOX_LABEL_MARGIN = 0.45
# 2.7 的第二个案例把 B 的列写成新基坐标。坐标系命令把 source
# coordinates 映射到显示世界；案例中的 Bv1/Bv2 因而要先换回实际位置，
# 否则它们会被误画在 (-3,2)、(-5,3) 的标准坐标位置。
_CH02_BASIS_MATRIX: tuple[tuple[float, float], tuple[float, float]] = (
    (1.0, 1.0),
    (1.0, 2.0),
)


def _case_grid_bounds(topic_id: str, fallback: tuple[float, ...]) -> tuple[float, ...]:
    """Return the grid sampling rectangle used by one topic's case pane."""

    if topic_id not in _MATRIX_VECTOR_CASE_TOPICS and topic_id not in _SUBSPACE_CASE_TOPICS:
        return fallback
    return _MATRIX_VECTOR_GRID_BOUNDS
# 流程里向量用小写标注；向量的终点是“点”，用大写标注以区别。a+b 的终点是
# 平行四边形与原点相对的顶点，记为 C（不是 A+B）；单一字母标签直接大写，
# 带系数或正负号的标签不再造点。数乘的两步各自落在一个点上：a 的终点是 A，
# 缩放后的 2a 终点是 B。2.5 的案例按同一规则给每个向量的终点一个不同的
# 大写标签（行/列、原像/像用不同字母），点与向量不会重名。
_FLOW_POINT_LABELS = {
    "ch01.ops.addition": {"flow_a": "A", "flow_b": "B", "flow_sum": "C"},
    "ch01.ops.scalar": {"a": "A", "two_a": "B"},
    "ch02.matrix.row-column": {
        "mv_x": "X", "mv_r1": "R1", "mv_r2": "R2",
        "mv_c1": "C1", "mv_c2": "C2", "mv_s1": "S1", "mv_s2": "S2", "mv_sum": "Y",
    },
    "ch02.matrix.transformed-grid": {
        "mv_e1": "E1", "mv_e2": "E2",
        "mv_stretch_e1": "G1", "mv_stretch_e2": "G2",
        "mv_rotate_e1": "H1", "mv_rotate_e2": "H2",
        "mv_ae1": "F1", "mv_ae2": "F2",
    },
    "ch02.matrix.stretch-rotate-scale": {
        "mv_e1": "E1", "mv_e2": "E2",
        "mv_stretch_e1": "F1", "mv_stretch_e2": "F2",
        "mv_rotate_e1": "G1", "mv_rotate_e2": "G2",
        "mv_combo_e1": "H1", "mv_combo_e2": "H2",
    },
    # 2.7 的两个窗格各用一组字母：标准基下旋转的两列记 F1、F2，新基与其像记
    # V1、V2、G1、G2，同一个窗格里的点不会重名。
    "ch02.matrix.basis": {
        "mv_basis_ae1": "F1", "mv_basis_ae2": "F2",
        "mv_basis_v1": "V1", "mv_basis_v2": "V2",
        "mv_basis_bv1": "G1", "mv_basis_bv2": "G2",
    },
}


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
    family_evidence: object | None = None
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
        family_evidence = None
        chapter4_owned = resolved_topic.startswith("ch04.")
        chapter5_owned = resolved_topic.startswith("ch05.")
        chapter6_owned = resolved_topic.startswith("ch06.")
        chapter7_owned = resolved_topic.startswith("ch07.")
        chapter8_owned = resolved_topic.startswith("ch08.")
        if chapter4_owned or chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned:
            family_result = family_compiler_for(semantics.scene_family).compile(
                topic_id=resolved_topic, semantics=semantics, context=context
            )
            if not isinstance(family_result, Mapping):
                raise VisualCompileError((CompileIssue("invalid_family_result", "$.visual_semantics.scene_family", "chapter 4 family compiler must return operations, aliases, and evidence"),))
        if isinstance(family_result, Mapping):
            operations.extend(list(family_result.get("operations", ())))
            family_evidence = family_result.get("evidence")
            family_aliases = family_result.get("aliases", ())
            if isinstance(family_aliases, Mapping):
                for key, values in family_aliases.items():
                    vals = values if isinstance(values, (list, tuple)) else (values,)
                    aliases.setdefault(str(key), []).extend(str(value) for value in vals)
            else:
                for alias in family_aliases:
                    aliases.setdefault(str(alias), []).append(str(alias))
        if chapter4_owned or chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned:
            operation_aliases = {
                str(operation.get("alias")): str(operation.get("op", ""))
                for operation in operations
                if isinstance(operation, Mapping) and isinstance(operation.get("alias"), str)
            }
            required_semantic_ids = {
                *(entity.id for entity in semantics.entities),
                *(relation.id for relation in semantics.relations),
            }
            if chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned:
                required_semantic_ids.update(stage.id for stage in semantics.stages)
            alias_issues: list[CompileIssue] = []
            alias_owners: dict[str, str] = {}
            for semantic_id in sorted(required_semantic_ids):
                bound = aliases.get(semantic_id, ())
                if not bound:
                    alias_issues.append(CompileIssue("missing_family_alias", f"$.aliases.{semantic_id}", "family emitted no evidence alias"))
                    continue
                for alias in bound:
                    if (chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned) and alias in alias_owners and alias_owners[alias] != semantic_id:
                        alias_issues.append(CompileIssue('shared_family_alias', f'$.aliases.{semantic_id}', alias))
                    alias_owners[alias] = semantic_id
                    operation_name = operation_aliases.get(alias, "")
                    if not operation_name or operation_name.startswith("annotation."):
                        alias_issues.append(CompileIssue("annotation_only_evidence", f"$.aliases.{semantic_id}", alias))
            invariant_evidence = family_evidence.get("invariants") if isinstance(family_evidence, Mapping) else None
            if not isinstance(invariant_evidence, Mapping) or any(invariant_evidence.get(name) is not True for name in contract.required_invariants):
                alias_issues.append(CompileIssue("missing_computed_invariant", "$.family_evidence.invariants", "family did not prove every required invariant"))
            if alias_issues:
                raise VisualCompileError(tuple(alias_issues))
        if resolved_topic in _PROOF_TOPICS:
            proof_operations, proof_aliases = _compile_proof_figure(resolved_topic, semantics, context)
            operations.extend(proof_operations)
            for key, values in proof_aliases.items():
                aliases.setdefault(key, []).extend(values)
        elif not chapter4_owned and not chapter5_owned and not chapter6_owned and not chapter7_owned and not chapter8_owned:
            # 投影箭头跟随来源向量配色的修正只服务内积小节（1.3.1 / 2.2）；其余小节保持
            # 原有配色，避免非预期地改动既有 plan digest。
            projection_roles = (
                _projection_source_roles(semantics)
                if context.topic_id in _INNER_PRODUCT_TOPICS
                else {}
            )
            for entity in semantics.entities:
                entity_operations, entity_aliases = self._compile_entity(
                    entity,
                    semantics.scene_kind,
                    context,
                    color_role=projection_roles.get(entity.id),
                )
                operations.extend(entity_operations)
                aliases.setdefault(entity.id, []).extend(entity_aliases)

            for relation in semantics.relations:
                relation_operations, relation_aliases = self._compile_relation(
                    relation, semantics, context, aliases
                )
                operations.extend(relation_operations)
                aliases.setdefault(relation.id, []).extend(relation_aliases)

            _emit_matrix_vector_transform(resolved_topic, semantics, context, operations, aliases)

        if not resolved_topic.startswith(("ch04.", "ch05.", "ch06.", "ch07.", "ch08.")):
            self._emit_declared_capability_evidence(semantics, context, operations, aliases, resolved_topic)

        # 动态向量加法关系要先算出别名，才能跟随它所属关系的阶段可见性：
        # 只画 a、b 的第一步窗格不应执行和向量与平行四边形的联动操作。
        # 与声明能力证据一致，第 4–8 章由族编译器负责，不注入该二维联动。
        addition_operation = (
            None
            if (chapter4_owned or chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned)
            else _vector_addition_operation(semantics, aliases)
        )
        if addition_operation is not None:
            addition_alias = str(addition_operation["alias"])
            for relation in semantics.relations:
                if relation.kind == "sum" and _alias(relation.id) in addition_alias:
                    aliases.setdefault(relation.id, []).append(addition_alias)
                    break

        storyboard, stage_operations, stage_issues = self._compile_storyboard(
            semantics, context, aliases, emit_generic_geometry=not (chapter4_owned or chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned)
        )
        if stage_issues:
            raise VisualCompileError(tuple(stage_issues))
        operations.extend(stage_operations)
        if addition_operation is not None:
            operations.append(addition_operation)
        if chapter4_owned or chapter5_owned or chapter6_owned or chapter7_owned or chapter8_owned:
            operation_names = {str(operation.get("op")) for operation in operations}
            missing_operations = set(contract.expected_operations) - operation_names
            if missing_operations:
                raise VisualCompileError(tuple(CompileIssue("missing_expected_operation", "$.operations", name) for name in sorted(missing_operations)))

        # Formula annotations are a declared catalog capability rather than
        # executable model output.  Emit them only for topics that explicitly
        # request the capability; this preserves the compact plan shape for
        # topics whose contract does not include a formula label.
        # Section 1.5 figures already carry a student-readable formula label
        # bound to the drawn construction, so they must not also receive the
        # generic raw-source annotation at a fixed off-figure position.
        if (
            artifact is not None
            and resolved_topic not in _PROOF_TOPICS
            and _topic_requires_capability(resolved_topic, "annotation_formula")
        ):
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
        view_fit: dict[str, Any] = {
            "op": "view.fit",
            "padding": 1.45 if resolved_topic in _PROOF_TOPICS else 1.15,
        }
        if resolved_topic in _FLOW_VIEW_TOPICS:
            # 流程主题的多个案例窗格必须共享同一视角：若各自按本窗格对象
            # 自适应缩放，“全部显示”时会出现一大一小。这里给出覆盖所有
            # 向量终点（含原点）的固定边界，让每个窗格使用同一相机；网格
            # 由视口裁切，因此不参与取景。
            try:
                endpoints = [
                    _coordinates(entity.value, 2)
                    for entity in semantics.entities
                    if entity.kind == "vector" and entity.dimension == 2
                ]
            except (TypeError, ValueError):
                endpoints = []
            if resolved_topic in _INNER_PRODUCT_TOPICS:
                # a·b 用 OA 的延长线段表示，可能长过所有向量；取景必须把它
                # 算进去，否则延长段会被窗格裁掉。
                extension = _inner_product_extension_endpoint(semantics)
                if extension is not None:
                    endpoints.append(extension)
            if resolved_topic == "ch03.det.oriented-area":
                # 3.1 的案例把两列放进外接矩形，并在矩形上方标出矩形面积；
                # 取景必须覆盖矩形对角与标注位置，否则“全部显示”时会被裁掉。
                endpoints.extend(_det_geometry_view_endpoints(semantics))
            if endpoints:
                xs = [0.0, *(point[0] for point in endpoints)]
                ys = [0.0, *(point[1] for point in endpoints)]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                # 共线向量（例如数乘的 a 与 2a）只占一条轴，退化边界会被
                # 渲染层忽略；补出最小跨度，保证所有窗格仍共用一个视角。
                if max_x <= min_x:
                    min_x, max_x = min_x - 0.5, max_x + 0.5
                if max_y <= min_y:
                    min_y, max_y = min_y - 0.5, max_y + 0.5
                view_fit["bounds"] = [min_x, max_x, min_y, max_y]
        elif resolved_topic in _SUBSPACE_CASE_TOPICS:
            # 2.9 的案例主角是「变换后的网格」：以默认视野为基准（原点保持在
            # 窗格中部，网格由视口裁切），只在案例向量超出视野时才把端点并进来
            # —— 例如讲义表格里两列共线的矩阵 $\begin{pmatrix}1&2\\2&4\end{pmatrix}$
            # 的列 (2, 4)。这样“全部显示”时每个窗格仍然共用同一张图。
            try:
                endpoints = [
                    _coordinates(entity.value, 2)
                    for entity in semantics.entities
                    if entity.kind == "vector" and entity.dimension == 2
                ]
            except (TypeError, ValueError):
                endpoints = []
            xs = [float(context.bounds[0]), float(context.bounds[1]), *(point[0] for point in endpoints)]
            ys = [float(context.bounds[2]), float(context.bounds[3]), *(point[1] for point in endpoints)]
            view_fit["bounds"] = [min(xs), max(xs), min(ys), max(ys)]
        operations.append(view_fit)
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
            family_evidence=family_evidence,
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
                family_evidence=compiled.family_evidence,
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
                # 投影是辅助构造，按讲义习惯默认画成虚线。
                operations.append({"op": "geometry.projection", "vector": list(vectors2[0]), "direction": list(vectors2[1]), "result_alias": "cap__projection", "foot_alias": "cap__foot", "residual_alias": "cap__residual", "style": "dashed", "color": role_color("projection")})
        if "transformed_grid" in declared and topic_id != "ch02.matrix.basis" and "geometry.transformed_grid" not in operation_names and semantics.scene_kind == "2d" and "staged_transform" not in declared:
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
        *,
        emit_generic_geometry: bool = True,
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
            # Chapter-owned stages have executable frame-specific witnesses.
            # Include them in visibility instead of losing their alias mapping.
            visible_aliases_list.extend(aliases.get(stage.id, ()))
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
                or stage.id.startswith("stage.flow.")
                or stage.id.startswith("stage.case.")
            )
            if show_case_stage_title:
                visible_aliases_list.append(title_alias)
            if emit_generic_geometry:
                operations.extend(_stage_geometry_operations(semantics, stage, index, aliases, context))
                visible_aliases_list.extend(_stage_specific_aliases(semantics, stage, index))
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
        self,
        entity: VisualEntity,
        scene: str,
        context: RenderContext,
        color_role: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        operations: list[dict[str, Any]] = []
        aliases: list[str] = []
        prefix = _alias(entity.id)
        role = entity.role if entity.role in {"construction", "result"} else "primary"
        # 投影箭头跟随它所属向量的颜色（见 _projection_source_roles）。
        entity_color = role_color(color_role or entity.role)
        if entity.kind == "point":
            coordinates = _coordinates(entity.value, entity.dimension)
            if scene == "2d":
                operations.append({"op": "point.upsert", "alias": prefix, "coordinates": list(coordinates), "name": entity.label})
            else:
                operations.append({"op": "point3d.upsert", "alias": prefix, "coordinates": list(coordinates), "name": entity.label})
            aliases.append(prefix)
        elif entity.kind == "vector":
            coordinates = _coordinates(entity.value, entity.dimension)
            if context.topic_id == "ch02.matrix.basis" and entity.id in {
                "mv_basis_bv1", "mv_basis_bv2"
            }:
                # These two values are the columns of B in the alternate
                # basis.  Render their physical images in the world selected
                # by S=[v1 v2], while preserving the semantic values for the
                # explanation and evidence layers.
                coordinates = (
                    _CH02_BASIS_MATRIX[0][0] * coordinates[0]
                    + _CH02_BASIS_MATRIX[0][1] * coordinates[1],
                    _CH02_BASIS_MATRIX[1][0] * coordinates[0]
                    + _CH02_BASIS_MATRIX[1][1] * coordinates[1],
                )
            origin = f"{prefix}__origin"
            end = f"{prefix}__end"
            aliases.extend((prefix, end))
            if scene == "2d":
                is_magnitude_topic = context.topic_id == "ch01.vector.magnitude"
                # 2.9 的案例向量标签本身就是 v1、a1 这类多字符标签，按流程主题的
                # 规则不再在终点重复一个同名点标；2.9 的取景另有 _SUBSPACE_CASE_TOPICS
                # 的分支，所以这里单独把它们并入“标签去重”的判断。
                is_flow_topic = (
                    context.topic_id in _FLOW_VIEW_TOPICS
                    or context.topic_id in _SUBSPACE_CASE_TOPICS
                )
                is_zero_vector = not any(abs(value) > 1e-12 for value in coordinates)
                # The vector label is placed once on the segment; repeating it
                # at the endpoint makes the magnitude example look cluttered.
                # A zero vector has no segment, so retain its point label.
                end_name = entity.label if (is_zero_vector or not is_magnitude_topic) else ""
                # 流程里向量用小写 a、b 标注；向量终点是一个“点”，改用大写
                # A、B、C 与向量区分，避免点与向量看起来完全一样。
                if is_flow_topic:
                    explicit = _FLOW_POINT_LABELS.get(context.topic_id, {})
                    if entity.id in explicit:
                        end_name = explicit[entity.id]
                    else:
                        end_name = (
                            entity.label.upper()
                            if len(entity.label) == 1 and entity.label.isalpha()
                            else ""
                        )
                linear_op = {
                    "op": "linear.upsert",
                    "alias": prefix,
                    "start": origin,
                    "end": end,
                    "kind": "vector",
                    "role": role,
                    "color": entity_color,
                    "label": (
                        ""
                        if (is_magnitude_topic and is_zero_vector)
                        else entity.label
                    ),
                }
                # 内积小节把向量名标在线上方，好给线下的模长标注留出位置。
                # 其余小节沿用几何模型默认的 "below"，不写入计划以避免历史摘要漂移。
                if context.topic_id in _INNER_PRODUCT_TOPICS:
                    linear_op["label_side"] = "above"
                operations.extend(
                    [
                        {
                            "op": "point.upsert",
                            "alias": origin,
                            "coordinates": [0.0, 0.0],
                            "name": "" if is_magnitude_topic and is_zero_vector else "O",
                        },
                        {
                            "op": "point.upsert",
                            "alias": end,
                            "coordinates": list(coordinates),
                            "name": end_name,
                        },
                        linear_op,
                    ]
                )
            else:
                operations.append(
                    {"op": "linear3d.upsert", "alias": prefix, "start": [0.0, 0.0, 0.0], "end": list(coordinates), "kind": "vector", "role": role, "color": role_color(entity.role), "label": entity.label}
                )
        elif entity.kind in {"matrix", "grid"} and scene == "2d":
            matrix = _matrix2(entity.value)
            if matrix is not None:
                if context.topic_id != "ch02.matrix.basis":
                    grid_bounds = _case_grid_bounds(context.topic_id, context.bounds)
                    operations.append({"op": "geometry.transformed_grid", "alias": prefix, "matrix": matrix, "bounds": list(grid_bounds), "step": 1.0, "color": role_color(entity.role)})
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
        if (
            relation.kind == "decomposes_into"
            and context.topic_id == "ch03.det.oriented-area"
            and semantics.scene_kind == "2d"
        ):
            # 3.1 的案例用外接矩形说明 |det| = ad - bc：两条辅助线把矩形切成
            # 平行四边形加四个直角三角形，图形与标注都由两列算出，不再人工给值。
            box_operations, box_aliases = _determinant_box_construction(relation, semantics)
            return box_operations, [_alias(relation.id), *box_aliases]
        if relation.kind == "projects_to" and semantics.scene_kind == "2d":
            source_coordinates = _coordinates(source.value, 2)
            direction_coordinates = _coordinates(target.value, 2)
            foot = _pick_role_entity(semantics.entities, "foot", target.id)
            residual = _pick_role_entity(semantics.entities, "residual", target.id)
            # 投影与垂足连线属于辅助构造，按讲义约定一律画成虚线。
            # VisualRelation.style 的默认值 "solid" 无法与「未指定」区分，故此处不读取。
            projection: dict[str, Any] = {
                "op": "geometry.projection",
                "alias": relation_alias,
                "vector": list(source_coordinates),
                "direction": list(direction_coordinates),
                "result_alias": _alias(target.id),
                "foot_alias": _alias(foot.id) if foot else f"{relation_alias}__foot",
                "residual_alias": _alias(residual.id) if residual else f"{relation_alias}__residual",
                "style": "dashed",
                # 投影线跟随被投影向量的颜色：2.2 的两列本就不同色，学生正在
                # 看的那一列与它的投影必须同色，否则两条投影线共用一个通用色。
                # 该配色修正仅用于内积小节，其余小节保留原通用投影色以免计划摘要漂移。
                "color": (
                    role_color(source.role)
                    if context.topic_id in _INNER_PRODUCT_TOPICS
                    else role_color("projection")
                ),
            }
            operations.append(projection)
            aliases = [relation_alias]
            if context.topic_id in _INNER_PRODUCT_TOPICS:
                projection_entity = _pick_role_entity(semantics.entities, "projection", target.id)
                annotations, length_aliases = _inner_product_length_annotations(
                    context,
                    relation_alias,
                    f"{_alias(target.id)}__origin",
                    direction_coordinates,
                    source_coordinates,
                    target.label,
                    source.label,
                    projection_entity.label if projection_entity is not None else "p",
                    direction_color=role_color(target.role),
                    source_color=role_color(source.role),
                )
                operations.extend(annotations)
                aliases.extend(length_aliases)
            return operations, aliases
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


def _compile_proof_figure(
    topic_id: str, semantics: VisualSemantics, context: RenderContext
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Build the constructed figure for one section 1.5 geometry proof.

    The semantic graph supplies the two lecture inputs ``a`` and ``b``; every
    other point, side, median and diagonal is derived from them, so a change to
    the worked numbers moves the drawing with it.  Declared entity and relation
    IDs are bound to concrete figure aliases so the claim evidence ledger keeps
    its one-to-one witness.
    """

    def declared(role: str, fallback: tuple[float, float]) -> tuple[VisualEntity | None, tuple[float, float]]:
        for entity in semantics.entities:
            if entity.role == role and entity.kind == "vector" and entity.dimension == 2:
                return entity, _coordinates(entity.value, 2)
        return None, fallback

    entity_a, side_a = declared("vector_a", (3.0, 0.6))
    entity_b, side_b = declared("vector_b", (1.0, 2.6))
    operations = _proof_figure_operations(topic_id, side_a, side_b)
    aliases: dict[str, list[str]] = {}
    if entity_a is not None:
        aliases[entity_a.id] = ["proof__side_a"]
    if entity_b is not None:
        aliases[entity_b.id] = ["proof__side_b"]
    for relation in semantics.relations:
        aliases[relation.id] = ["proof__region"]
    if topic_id == "ch01.proof.midline":
        # 用户确认：中位线定理只画一张完整构造图（一个窗格），三角形、两腰、
        # 两个中点、中位线、第三边与结论标注一次画全，不再按步骤拆成多张。
        aliases[f"stage.case.{topic_id}.1"] = [
            "proof__region",
            "proof__point_A", "proof__point_B", "proof__point_C",
            "proof__point_D", "proof__point_E",
            "proof__side_a", "proof__side_b",
            "proof__side_bc", "proof__midline", "proof__note_midline",
        ]
    return operations, aliases


def _proof_figure_operations(
    topic_id: str, side_a: tuple[float, float], side_b: tuple[float, float]
) -> list[dict[str, Any]]:
    """Emit the validated operations for one 1.5 construction figure."""

    origin = (0.0, 0.0)
    vertex_b = (float(side_a[0]), float(side_a[1]))
    vertex_c = (float(side_b[0]), float(side_b[1]))
    point_ops: list[dict[str, Any]] = []
    segment_ops: list[dict[str, Any]] = []
    note_ops: list[dict[str, Any]] = []

    def add_point(alias: str, coordinates: tuple[float, float], name: str) -> None:
        point_ops.append(
            {
                "op": "point.upsert",
                "alias": alias,
                "coordinates": [round(float(coordinates[0]), 6), round(float(coordinates[1]), 6)],
                "name": name,
            }
        )

    def add_segment(
        alias: str,
        start: str,
        end: str,
        *,
        color: str,
        role: str = "primary",
        style: str = "solid",
        kind: str = "segment",
    ) -> None:
        segment_ops.append(
            {
                "op": "linear.upsert",
                "alias": alias,
                "start": start,
                "end": end,
                "kind": kind,
                "role": role,
                "color": color,
                "style": style,
            }
        )

    def add_note(alias: str, text: str, position: tuple[float, float]) -> None:
        note_ops.append(
            {
                "op": "annotation.upsert",
                "alias": alias,
                "text": text,
                "position": [round(float(position[0]), 6), round(float(position[1]), 6)],
            }
        )

    def midpoint(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
        return ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)

    def between(first: tuple[float, float], second: tuple[float, float], ratio: float) -> tuple[float, float]:
        return (first[0] + (second[0] - first[0]) * ratio, first[1] + (second[1] - first[1]) * ratio)

    def outward_label(
        first: tuple[float, float],
        second: tuple[float, float],
        away: tuple[float, float],
        distance: float = 0.30,
    ) -> tuple[float, float]:
        """Return a midpoint label pushed to the side facing away from ``away``."""

        mid = midpoint(first, second)
        normal = (second[1] - first[1], first[0] - second[0])
        length = math.hypot(normal[0], normal[1]) or 1.0
        unit = (normal[0] / length, normal[1] / length)
        if unit[0] * (away[0] - mid[0]) + unit[1] * (away[1] - mid[1]) > 0:
            unit = (-unit[0], -unit[1])
        return (mid[0] + unit[0] * distance, mid[1] + unit[1] * distance)

    if topic_id == "ch01.proof.midline":
        midpoint_d = midpoint(origin, vertex_b)
        midpoint_e = midpoint(origin, vertex_c)
        add_point("proof__point_A", origin, "A")
        add_point("proof__point_B", vertex_b, "B")
        add_point("proof__point_C", vertex_c, "C")
        add_point("proof__point_D", midpoint_d, "D")
        add_point("proof__point_E", midpoint_e, "E")
        # 用户确认：这一小节全部按向量画（$\overrightarrow{AB}=\boldsymbol a$ 等），
        # 不画成普通线段；图中也不再重复显示结论公式 DE = ½ BC。
        add_segment("proof__side_a", "proof__point_A", "proof__point_B", color=role_color("vector_a"), kind="vector")
        add_segment("proof__side_b", "proof__point_A", "proof__point_C", color=role_color("vector_b"), kind="vector")
        add_segment("proof__side_bc", "proof__point_B", "proof__point_C", color=role_color("vector_a"), kind="vector")
        add_segment("proof__midline", "proof__point_D", "proof__point_E", color=role_color("transformed_b"), kind="vector")
        centre = ((origin[0] + vertex_b[0] + vertex_c[0]) / 3.0, (origin[1] + vertex_b[1] + vertex_c[1]) / 3.0)
        add_note(
            "proof__note_midline",
            "DE // BC",
            outward_label(midpoint_d, midpoint_e, centre, 0.42),
        )
        formula = ""
        vertices = [origin, vertex_b, vertex_c]
    elif topic_id == "ch01.proof.centroid":
        midpoint_bc = midpoint(vertex_b, vertex_c)
        midpoint_ca = midpoint(vertex_c, origin)
        midpoint_ab = midpoint(origin, vertex_b)
        centre = (
            (origin[0] + vertex_b[0] + vertex_c[0]) / 3.0,
            (origin[1] + vertex_b[1] + vertex_c[1]) / 3.0,
        )
        add_point("proof__point_A", origin, "A")
        add_point("proof__point_B", vertex_b, "B")
        add_point("proof__point_C", vertex_c, "C")
        add_point("proof__point_D", midpoint_bc, "D")
        add_point("proof__point_E", midpoint_ca, "E")
        add_point("proof__point_F", midpoint_ab, "F")
        add_point("proof__point_G", centre, "G")
        add_segment("proof__side_a", "proof__point_A", "proof__point_B", color=role_color("construction"), role="construction")
        add_segment("proof__side_b", "proof__point_B", "proof__point_C", color=role_color("construction"), role="construction")
        add_segment("proof__side_c", "proof__point_C", "proof__point_A", color=role_color("construction"), role="construction")
        add_segment("proof__median_a", "proof__point_A", "proof__point_D", color=role_color("projection"), style="dashed")
        add_segment("proof__median_b", "proof__point_B", "proof__point_E", color=role_color("projection"), style="dashed")
        add_segment("proof__median_c", "proof__point_C", "proof__point_F", color=role_color("projection"), style="dashed")
        add_note(
            "proof__note_centroid",
            "AG : GD = 2 : 1",
            outward_label(origin, midpoint_bc, centre, 0.36),
        )
        formula = "AG = (a + b) / 3"
        vertices = [origin, vertex_b, vertex_c]
    elif topic_id == "ch01.proof.parallelogram-diagonals":
        vertex_d = vertex_b
        vertex_c_para = (vertex_b[0] + vertex_c[0], vertex_b[1] + vertex_c[1])
        centre = midpoint(origin, vertex_c_para)
        add_point("proof__point_A", origin, "A")
        add_point("proof__point_B", vertex_d, "B")
        add_point("proof__point_C", vertex_c_para, "C")
        add_point("proof__point_D", vertex_c, "D")
        add_point("proof__point_M", centre, "M")
        add_segment("proof__side_a", "proof__point_A", "proof__point_B", color=role_color("vector_a"))
        add_segment("proof__side_b", "proof__point_A", "proof__point_D", color=role_color("vector_b"))
        add_segment("proof__side_bc", "proof__point_B", "proof__point_C", color=role_color("construction"), role="construction")
        add_segment("proof__side_dc", "proof__point_D", "proof__point_C", color=role_color("construction"), role="construction")
        add_segment("proof__diagonal_ac", "proof__point_A", "proof__point_C", color=role_color("transformed_a"), style="dashed")
        add_segment("proof__diagonal_bd", "proof__point_B", "proof__point_D", color=role_color("transformed_b"), style="dashed")
        formula = "M(AC) = M(BD) = (a + b) / 2"
        vertices = [origin, vertex_d, vertex_c_para, vertex_c]
    else:
        raise ValueError(f"unsupported geometry-proof topic: {topic_id}")

    x_values = [float(operation["coordinates"][0]) for operation in point_ops]
    y_values = [float(operation["coordinates"][1]) for operation in point_ops]
    left, right = min(x_values), max(x_values)
    bottom, top = min(y_values), max(y_values)
    margin_y = max((top - bottom) * 0.08, 0.10)
    # A long student-readable label is centred under the construction so the
    # fitted pane never clips it against a figure edge.
    formula_position = ((left + right) / 2.0, bottom - margin_y)

    operations: list[dict[str, Any]] = [
        {
            "op": "geometry.polygon",
            "alias": "proof__region",
            "vertices": [[round(float(point[0]), 6), round(float(point[1]), 6)] for point in vertices],
            "color": role_color("area"),
            "opacity": 0.12,
            "outline": True,
        }
    ]
    operations.extend(point_ops)
    operations.extend(segment_ops)
    operations.extend(note_ops)
    if formula:
        operations.append(
            {
                "op": "annotation.formula",
                "alias": "proof__formula",
                "text": formula,
                "position": [round(float(formula_position[0]), 6), round(float(formula_position[1]), 6)],
            }
        )
    return operations


def _alias(value: str) -> str:
    result = _SAFE_ALIAS.sub("_", value).strip("_") or "semantic"
    return f"sem__{result}"


def _pick_role_entity(entities, role: str, anchor: str):
    """Return the ``role`` entity belonging to the same group as ``anchor``.

    A topic may declare the same role for several cases (e.g. two projections),
    so a bare ``next(role == ...)`` lookup would bind every relation to the first
    case's entity. Prefer the entity sharing ``anchor``'s ``case<n>_`` prefix and
    only fall back to positional selection when the choice is unambiguous.
    """
    candidates = [entity for entity in entities if entity.role == role]
    if len(candidates) <= 1:
        return candidates[0] if candidates else None
    prefix = anchor.rsplit("_", 1)[0]
    for entity in candidates:
        if entity.id.rsplit("_", 1)[0] == prefix:
            return entity
    return candidates[0]


def _projection_source_roles(semantics: VisualSemantics) -> dict[str, str]:
    """Map every ``projection`` entity to the role of the vector it comes from.

    A projection arrow pictures one component of the vector being projected, so
    the two are drawn in the same color.  Without this mapping the arrow keeps the
    generic ``projection`` swatch and stops matching its own vector — most
    visibly in 2.2, where the two matrix columns already carry distinct colors.
    """
    entities = {entity.id: entity for entity in semantics.entities}
    color_roles: dict[str, str] = {}
    for relation in semantics.relations:
        if relation.kind != "projects_to":
            continue
        source = entities.get(relation.source_ref)
        target = entities.get(relation.target_ref)
        if source is None or target is None:
            continue
        projection = _pick_role_entity(semantics.entities, "projection", target.id)
        if projection is not None:
            color_roles[projection.id] = source.role
    return color_roles


# 1.3.1「内积的两种定义」与 2.2「行向量与矩阵乘法（批量内积）」都把投影读作内积
# 本身：``a·b = |a|·|p|``。这两个小节在画投影的窗格上标出三段学生可见的长度，并把
# 向量名移到线上方，给线下方留出模长标注的位置。
_INNER_PRODUCT_TOPICS = frozenset({"ch01.inner.definitions", "ch02.batch.inner-products"})


def _format_radical_length(squared: float) -> str | None:
    """Return an exact ``n``/``√n`` text for a squared length, else ``None``.

    Lecture labels prefer the exact surd (``√5``) to a rounded decimal, but only
    when the squared length is a small integer whose root is an integer or a
    squarefree surd.
    """
    rounded = int(round(squared))
    if rounded <= 0 or abs(squared - rounded) > 1e-9:
        return None
    root = math.isqrt(rounded)
    return str(root) if root * root == rounded else f"√{rounded}"


def _magnitude_text(value: float) -> str:
    """Format a length label, preferring the exact surd over a decimal.

    Lecture labels keep the exact radical (``√5``); the rounded ``≈`` form is
    only a fallback for lengths that have no small-integer surd.
    """
    exact = _format_radical_length(value * value)
    if exact:
        return f"= {exact}"
    approximate = f"{value:.3f}".rstrip("0").rstrip(".")
    return f"≈ {approximate}"


def _projection_ratio(dot: float, length_a: float) -> tuple[int, str] | None:
    """Return the exact ratio ``(|a·b|, √m)`` for ``|p| = |a·b| / |a|`` when it exists.

    ``|a|`` is a small-integer surd and ``a·b`` is an integer, so ``|p|`` can be
    written exactly as ``n/√m``; any other case falls back to a decimal.
    """
    denominator = _format_radical_length(length_a * length_a)
    if (
        denominator is not None
        and denominator.startswith("√")
        and abs(dot) > 1e-9
        and abs(dot - round(dot)) <= 1e-9
    ):
        return abs(int(round(dot))), denominator
    return None


def _projection_magnitude_text(dot: float, length_a: float) -> str:
    """``|p| = |a·b| / |a|``: keep the exact ratio ``n/√m`` when one exists."""
    ratio = _projection_ratio(dot, length_a)
    if ratio is not None:
        numerator, denominator = ratio
        return f"= {numerator}/{denominator}"
    return _magnitude_text(abs(dot) / length_a)


def _projection_magnitude_latex(dot: float, length_a: float, label: str) -> str | None:
    """Stacked-fraction LaTeX for ``|p|`` when the exact ratio exists.

    ``denominator`` is the display surd ``√m``; emit proper LaTeX so the label
    renderer can stack it as a fraction over the radical.
    """
    ratio = _projection_ratio(dot, length_a)
    if ratio is None:
        return None
    numerator, denominator = ratio
    radicand = denominator[1:]
    return rf"|{label}| = \frac{{{numerator}}}{{\sqrt{{{radicand}}}}}"


def _inner_product_extension_endpoint(semantics: VisualSemantics) -> tuple[float, float] | None:
    """Return the tip of the ``OA`` extension whose length equals ``a·b``.

    The projection pane draws ``a·b`` as a segment from the origin along ``a``;
    its tip can sit beyond every vector endpoint, so view fitting has to know
    about it explicitly.
    """
    entities = {entity.id: entity for entity in semantics.entities}
    for relation in semantics.relations:
        if relation.kind != "projects_to":
            continue
        target = entities.get(relation.target_ref)
        source = entities.get(relation.source_ref)
        if target is None or source is None:
            continue
        try:
            ax, ay = _coordinates(target.value, 2)
            bx, by = _coordinates(source.value, 2)
        except (TypeError, ValueError):
            continue
        length_a = math.hypot(ax, ay)
        if length_a == 0.0:
            continue
        dot = ax * bx + ay * by
        return (ax / length_a * dot, ay / length_a * dot)
    return None


def _inner_product_length_annotations(
    context: RenderContext,
    relation_alias: str,
    origin_alias: str,
    direction: tuple[float, float],
    source: tuple[float, float],
    target_label: str,
    source_label: str,
    projection_label: str,
    *,
    direction_color: str | None = None,
    source_color: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Annotate ``|a|``, ``|p|`` and the ``OA`` extension carrying ``a·b``.

    ``direction`` is the vector the projection lands on (``a``) and ``source`` is
    the vector being projected (``b``), so ``p = (a·b / a·a)·a`` and the
    projection length satisfies ``a·b = |a|·|p|``.  Both lengths hang just below
    the primitive they measure, and ``a·b`` is drawn as a segment from the origin
    along ``a`` whose length is exactly ``|a·b|``.
    """
    ax, ay = direction
    dot = ax * source[0] + ay * source[1]
    length_a = math.hypot(ax, ay)
    if length_a == 0.0:
        return [], []
    unit_x, unit_y = ax / length_a, ay / length_a
    scale = dot / (length_a * length_a)
    px, py = ax * scale, ay * scale
    bounds = context.bounds
    span = max(
        abs(float(bounds[1]) - float(bounds[0])),
        abs(float(bounds[3]) - float(bounds[2])),
    )
    offset = span * 0.045
    # 两条法线里取指向下方的一条，把模长标注压在对应线段的下方。
    down_x, down_y = unit_y, -unit_x
    if down_y > 0.0 or (down_y == 0.0 and down_x < 0.0):
        down_x, down_y = -down_x, -down_y
    product = (
        str(int(round(dot)))
        if abs(dot - round(dot)) <= 1e-9
        else f"{dot:.3f}".rstrip("0").rstrip(".")
    )
    # 「|a|」跟着方向向量、「|p|」与「a·b」跟着被投影向量：同一案例的线与标注
    # 统一取所属向量的颜色，学生不必靠文字就能把线段和向量对上。
    direction_color = direction_color or role_color("direction")
    source_color = source_color or role_color("projection")
    product_end = f"{relation_alias}__product_end"
    # a·b 的延长段落在 a 的正中间偏外的位置，标注取延长段中点。
    reach_x, reach_y = unit_x * (length_a + dot) / 2.0, unit_y * (length_a + dot) / 2.0
    annotations = [
        {
            "op": "annotation.upsert",
            "alias": f"{relation_alias}__length_a",
            "text": f"|{target_label}| {_magnitude_text(length_a)}",
            "position": [
                round(ax * 0.72 + down_x * offset, 6),
                round(ay * 0.72 + down_y * offset, 6),
            ],
            "color": direction_color,
        },
        {
            "op": "annotation.upsert",
            "alias": f"{relation_alias}__length_p",
            "text": f"|{projection_label}| {_projection_magnitude_text(dot, length_a)}",
            "latex": _projection_magnitude_latex(dot, length_a, projection_label),
            "position": [
                round(px * 0.42 + down_x * offset, 6),
                round(py * 0.42 + down_y * offset, 6),
            ],
            "color": source_color,
        },
        {
            "op": "point.upsert",
            "alias": product_end,
            "coordinates": [round(unit_x * dot, 6), round(unit_y * dot, 6)],
            "name": "",
        },
        {
            "op": "linear.upsert",
            "alias": f"{relation_alias}__length",
            "start": origin_alias,
            "end": product_end,
            "kind": "segment",
            "role": "construction",
            "style": "dashed",
            "color": source_color,
            "label_side": "below",
        },
        {
            "op": "annotation.upsert",
            "alias": f"{relation_alias}__length_product",
            "text": f"{target_label}·{source_label} = {product}",
            "position": [
                round(reach_x + down_x * offset, 6),
                round(reach_y + down_y * offset, 6),
            ],
            "color": source_color,
        },
    ]
    return annotations, [annotation["alias"] for annotation in annotations]


def _vector_addition_operation(
    semantics: VisualSemantics,
    aliases: Mapping[str, list[str] | tuple[str, ...]],
) -> dict[str, Any] | None:
    """Describe an explicit 2-D semantic sum as a live scene relation.

    The compiled drawing still contains the ordinary point/linear operations;
    this small metadata operation lets the Qt host keep the derived endpoint,
    translated copy, and construction polygon synchronized after a drag.
    """
    if semantics.scene_kind != "2d":
        return None
    vectors = [entity for entity in semantics.entities if entity.kind == "vector" and entity.dimension == 2]
    for relation in semantics.relations:
        if relation.kind != "sum":
            continue
        source = next((entity for entity in vectors if entity.id == relation.source_ref), None)
        target = next((entity for entity in vectors if entity.id == relation.target_ref), None)
        if source is None or target is None:
            continue
        def close(left: object, right: object) -> bool:
            try:
                return all(abs(float(a) - float(b)) <= 1e-9 for a, b in zip(left, right, strict=True))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return False
        source_value = tuple(float(value) for value in source.value)
        target_value = tuple(float(value) for value in target.value)
        result = next(
            (
                entity for entity in vectors
                if entity.id not in {source.id, target.id}
                and close(entity.value, (source_value[0] + target_value[0], source_value[1] + target_value[1]))
            ),
            None,
        )
        if result is None:
            # Some family semantics use ``target`` for the result and carry
            # the second addend as a numeric relation parameter.
            result = target
            other = next(
                (
                    entity for entity in vectors
                    if entity.id != source.id
                    and close(entity.value, relation.parameters.get("other_vector"))
                ),
                None,
            ) if isinstance(relation.parameters, Mapping) else None
            if other is None:
                continue
            first, second = source, other
        else:
            first, second = source, target
        first_aliases = tuple(aliases.get(first.id, ()))
        second_aliases = tuple(aliases.get(second.id, ()))
        result_aliases = tuple(aliases.get(result.id, ()))
        first_vector = first_aliases[0] if first_aliases else _alias(first.id)
        second_vector = second_aliases[0] if second_aliases else _alias(second.id)
        result_vector = result_aliases[0] if result_aliases else _alias(result.id)
        polygon_aliases = ["sem__addition_parallelogram"]
        if str(relation.id).endswith("addition.flow"):
            polygon_aliases.append("cap__polygon")
        return {
            "op": "geometry.vector_addition",
            "alias": f"dynamic__{_alias(relation.id)}",
            "vector_a": first_vector,
            "vector_b": second_vector,
            "result_vector": result_vector,
            "result_start": f"{result_vector}__origin",
            "result_end": f"{result_vector}__end",
            "polygon_aliases": polygon_aliases,
        }
    return None


def _det_box_columns(
    relation: VisualRelation, semantics: VisualSemantics
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the two columns ``(v1, v2)`` of the 3.1 outer-rectangle case."""

    entity_by_id = {entity.id: entity for entity in semantics.entities}
    return (
        _coordinates(entity_by_id[relation.source_ref].value, 2),
        _coordinates(entity_by_id[relation.target_ref].value, 2),
    )


def _det_geometry_view_endpoints(semantics: VisualSemantics) -> list[tuple[float, float]]:
    """Return the 3.1 case points a shared case-pane view must contain."""

    relation = next(
        (item for item in semantics.relations if item.kind == "decomposes_into"),
        None,
    )
    if relation is None:
        return []
    try:
        first, second = _det_box_columns(relation, semantics)
    except (KeyError, TypeError, ValueError):
        return []
    if min(first[0], first[1], second[0], second[1]) <= 0.0:
        return []
    return [(first[0] + second[0], first[1] + second[1] + _DET_BOX_LABEL_MARGIN)]


def _det_number(value: float) -> str:
    """Render one scene label number with characters the label font can draw."""

    return f"{float(value):g}"


def _determinant_box_construction(
    relation: VisualRelation, semantics: VisualSemantics
) -> tuple[list[dict[str, Any]], list[str]]:
    """外接矩形 + 两条辅助线：让 ``ad - bc`` 在图上直接读出来。

    把两列 ``v1=(a,c)``、``v2=(b,d)`` 放进以原点与 ``v1+v2`` 为对角的外接矩形
    ``(a+b) x (c+d)``；从矩形右下角连到 ``v1``、从矩形左上角连到 ``v2`` 的两条
    辅助线把矩形切成平行四边形加四个直角三角形。四个三角形都是「底 x 高 / 2」：
    两个底 ``a+b``、高 ``c``，两个底 ``c+d``、高 ``b``，于是

    ``S = (a+b)(c+d) - c(a+b) - b(c+d) = ad - bc``。

    辅助构造统一用 construction 表示色画成虚线，并与它自己的面积标注同色；图内
    标注只写可渲染字符，公式与推导留在讲解面板。
    """

    (a, c), (b, d) = _det_box_columns(relation, semantics)
    if min(a, b, c, d) <= 0.0:
        raise VisualCompileError(
            (
                CompileIssue(
                    "det_geometry_box_requires_positive_columns",
                    f"$.relations.{relation.id}",
                    "外接矩形构造要求 v1、v2 的分量均为正数",
                ),
            )
        )
    width, height = a + b, c + d
    prefix = _alias(relation.id)
    dashed = role_color("construction")
    operations: list[dict[str, Any]] = []

    def _point(suffix: str, coordinates: tuple[float, float]) -> str:
        alias = f"{prefix}__{suffix}"
        operations.append(
            {
                "op": "point.upsert",
                "alias": alias,
                "coordinates": [coordinates[0], coordinates[1]],
                "name": "",
            }
        )
        return alias

    def _edge(suffix: str, start: str, end: str) -> None:
        operations.append(
            {
                "op": "linear.upsert",
                "alias": f"{prefix}__{suffix}",
                "start": start,
                "end": end,
                "kind": "segment",
                "role": "construction",
                "color": dashed,
                "style": "dashed",
            }
        )

    def _label(suffix: str, text: str, position: tuple[float, float], color: str) -> None:
        operations.append(
            {
                "op": "annotation.upsert",
                "alias": f"{prefix}__{suffix}",
                "text": text,
                "position": [position[0], position[1]],
                "color": color,
            }
        )

    origin = f"{_alias(relation.source_ref)}__origin"
    first_end = f"{_alias(relation.source_ref)}__end"
    second_end = f"{_alias(relation.target_ref)}__end"
    bottom_right = _point("bottom-right", (width, 0.0))
    top_right = _point("top-right", (width, height))
    top_left = _point("top-left", (0.0, height))
    _edge("box-bottom", origin, bottom_right)
    _edge("box-right", bottom_right, top_right)
    _edge("box-top", top_right, top_left)
    _edge("box-left", top_left, origin)
    _edge("cut-first", bottom_right, first_end)
    _edge("cut-second", top_left, second_end)
    _label(
        "box-area",
        f"(a+b)(c+d)={_det_number(width * height)}",
        (width / 2.0, height + _DET_BOX_LABEL_MARGIN),
        dashed,
    )
    _label("corner-first-bottom", f"-{_det_number(width * c / 2.0)}", ((width + a) / 3.0, c / 3.0), dashed)
    _label(
        "corner-first-top",
        f"-{_det_number(b * height / 2.0)}",
        ((2.0 * width + a) / 3.0, (height + c) / 3.0),
        dashed,
    )
    _label("corner-second-bottom", f"-{_det_number(b * height / 2.0)}", (b / 3.0, (height + d) / 3.0), dashed)
    _label(
        "corner-second-top",
        f"-{_det_number(width * c / 2.0)}",
        ((width + b) / 3.0, (2.0 * height + d) / 3.0),
        dashed,
    )
    _label(
        "area-total",
        f"ad-bc={_det_number(a * d - b * c)}",
        (width / 2.0, height / 2.0),
        role_color("area"),
    )
    aliases = [
        str(operation["alias"])
        for operation in operations
        if isinstance(operation.get("alias"), str)
    ]
    return operations, aliases


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


def _stage_relation(semantics: VisualSemantics, stage: Any, kind: str):
    """Return the relation of ``kind`` that ``stage`` actually references.

    Per-pane construction geometry (orientation arcs, right-angle markers) used
    to look up ``next(relation.kind == kind)``, so every pane of a topic with
    several relations of that kind drew the *first* case's marker and the panes
    looked identical.  Selecting the referenced relation keeps each pane on its
    own case.  A stage that predates stage-scoped references still draws the
    marker when the topic declares exactly one relation of that kind.
    """
    refs = tuple(getattr(stage, "relation_refs", ()) or ())
    relations = [relation for relation in semantics.relations if relation.kind == kind]
    if refs:
        return next((relation for relation in relations if relation.id in refs), None)
    return relations[0] if len(relations) == 1 else None


def _stage_specific_aliases(semantics: VisualSemantics, stage: Any, index: int) -> tuple[str, ...]:
    """Return aliases for stage-only construction geometry."""
    relation_kinds = {relation.kind for relation in semantics.relations}
    if "sum" in relation_kinds:
        stage_id = str(getattr(stage, "id", ""))
        # 第一步只给出 a、b 两个向量，没有额外构造几何。
        if "components" in stage_id or "objects" in stage_id:
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
    # 投影只由 projects_to 关系本身落笔画：引用该关系的窗格才会显示投影。
    # 这里不再按窗格额外补一条 sem__projection__N，否则未引用投影的窗格
    # （例如「第一步：几何定义」）也会出现投影，并与关系笔画叠成两条。
    if "maps_to" in relation_kinds:
        return (f"sem__mapping_grid__{index + 1}",)
    if "spans" in relation_kinds:
        return (f"sem__span__{index + 1}",)
    # 夹角弧与直角标记只属于引用对应关系的窗格，否则每个窗格都会补出同一条弧。
    if "orientation" in relation_kinds:
        return (
            (f"sem__orientation__{index + 1}",)
            if _stage_relation(semantics, stage, "orientation") is not None
            else ()
        )
    if "orthogonal_to" in relation_kinds:
        return (
            (f"sem__orthogonal__{index + 1}",)
            if _stage_relation(semantics, stage, "orthogonal_to") is not None
            else ()
        )
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
        if "components" in stage_id or "objects" in stage_id:
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
    if "maps_to" in relation_kinds:
        matrix = next(
            (_matrix2(relation.parameters.get("matrix")) for relation in semantics.relations if relation.kind == "maps_to" and isinstance(relation.parameters, Mapping) and _matrix2(relation.parameters.get("matrix")) is not None),
            None,
        )
        if matrix is None:
            return []
        # A stage that already draws a grid or matrix entity owns its grid
        # geometry.  Adding the automatic transformed grid on top would stack
        # two grids in the same pane (the "floating duplicate grid" the
        # walkthrough reported) and would show the transformed grid even in the
        # stage that is supposed to display the *standard* grid.
        stage_refs = tuple(getattr(stage, "input_entity_refs", ()) or ()) + tuple(
            getattr(stage, "output_entity_refs", ()) or ()
        )
        if any(
            entity_by_id[ref].kind in {"grid", "matrix"}
            for ref in stage_refs
            if ref in entity_by_id
        ):
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
        relation = _stage_relation(semantics, stage, "orientation")
        if relation is None:
            return []
        first = _coordinates(entity_by_id[relation.source_ref].value, 2)
        second = _coordinates(entity_by_id[relation.target_ref].value, 2)
        return [{"op": "geometry.angle_arc", "alias": f"sem__orientation__{index + 1}", "vertex": [0.0, 0.0], "first": list(first), "second": list(second), "radius": 0.45, "color": role_color("projection")}]
    if "orthogonal_to" in relation_kinds:
        relation = _stage_relation(semantics, stage, "orthogonal_to")
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


def _matrix_label(name: str, matrix: list[list[float]]) -> str:
    """Return the scene-friendly matrix label used by the transform tool."""

    return (
        f"{name}=["
        f"[{matrix[0][0]:g},{matrix[0][1]:g}],[{matrix[1][0]:g},{matrix[1][1]:g}]"
        "]"
    )


def _stage_content_corner(
    semantics: VisualSemantics, entity_id: str
) -> tuple[float, float] | None:
    """Return the top-left corner of the drawn objects of one case step."""

    stage = next(
        (
            item
            for item in semantics.stages
            if entity_id in (*item.input_entity_refs, *item.output_entity_refs)
        ),
        None,
    )
    if stage is None:
        return None
    refs = {*stage.input_entity_refs, *stage.output_entity_refs}
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for entity in semantics.entities:
        if entity.id in refs and entity.kind == "vector" and entity.dimension == 2:
            try:
                points.append(_coordinates(entity.value, 2))
            except (TypeError, ValueError):
                continue
    if len(points) == 1:
        return None
    return (
        round(min(point[0] for point in points) - 0.4, 6),
        round(max(point[1] for point in points) + 0.45, 6),
    )


def _emit_matrix_vector_transform(
    topic_id: str,
    semantics: VisualSemantics,
    context: RenderContext,
    operations: list[dict[str, Any]],
    aliases: dict[str, list[str]],
) -> None:
    """Draw a 2.5 matrix case with the software's existing matrix-transform feature.

    工具箱里的“矩阵变换”由三部分组成：网格、若干样本点在变换后的位置，以及
    矩阵标注。这里对案例里每一个矩阵对象生成同一组操作，并把别名挂在同一个
    实体上，于是只有引用它的那一步窗格会显示这一组图形。样本点取标准基
    $(1,0)$、$(0,1)$：它们在新位置上的点正是讲义说的两列；网格的取样范围取
    得比窗格大得多，由视口裁切，因此它是这个窗格自己的那套（变形）坐标系，
    而不是叠在原坐标系里的一小块。
    """

    if topic_id not in _MATRIX_VECTOR_CASE_TOPICS:
        return
    entity_by_id = {entity.id: entity for entity in semantics.entities}
    for entity in semantics.entities:
        if entity.kind not in {"matrix", "grid"}:
            continue
        matrix = _matrix2(entity.value)
        if matrix is None:
            continue
        prefix = _alias(entity.id)
        staged_alias = f"{prefix}__staged"
        label_alias = f"{prefix}__label"
        if topic_id == "ch02.matrix.basis":
            # 2.7 的第二窗格不是独立生成一层 teaching grid，而是复用工具箱的
            # “矩阵变换”坐标系：S 的两列就是新基 v1、v2。第一窗格不设置
            # 变换，保留软件默认的标准基坐标系。
            if entity.id == "mv_basis_grid_b":
                if "mv_basis_v1" in entity_by_id and "mv_basis_v2" in entity_by_id:
                    coordinate_alias = prefix
                    operations.append(
                        {
                            "op": "linear_algebra.coordinate_transform",
                            "alias": coordinate_alias,
                            "matrix": [list(row) for row in _CH02_BASIS_MATRIX],
                            "show_original": False,
                            "show_transformed": True,
                        }
                    )
            aliases.setdefault(entity.id, []).append(label_alias)
            if matrix == [[1.0, 0.0], [0.0, 1.0]]:
                continue
            position = _stage_content_corner(semantics, entity.id)
            if position is not None:
                operations.append(
                    {
                        "op": "annotation.upsert",
                        "alias": label_alias,
                        "text": _matrix_label(str(entity.label), matrix),
                        "position": [position[0], position[1]],
                    }
                )
            continue
        aliases.setdefault(entity.id, []).extend((staged_alias, label_alias))
        operations.append(
            {
                "op": "geometry.staged_transform",
                "alias": staged_alias,
                "matrices": [matrix],
                "points": [[1.0, 0.0], [0.0, 1.0]],
                "aliases": [f"{staged_alias}__end1", f"{staged_alias}__end2"],
                "color": role_color(entity.role),
            }
        )
        if matrix == [[1.0, 0.0], [0.0, 1.0]]:
            # 未变换的参考网格没有矩阵可标注（它与标准基相同）。
            continue
        position = _stage_content_corner(semantics, entity.id)
        if position is None:
            continue
        operations.append(
            {
                "op": "annotation.upsert",
                "alias": label_alias,
                "text": _matrix_label(str(entity.label), matrix),
                "position": [position[0], position[1]],
            }
        )


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
    """Return aliases controlled by a storyboard and those shown for one stage.

    Every alias bound to a semantic object of a storyboard topic (entity,
    relation or chapter-owned stage) is stage-scoped: a pane must only show the
    ones it references.  Deriving the controlled set solely from the union of
    ``visible_aliases`` let aliases that *no* stage references (for example the
    projection foot kept out of the first step) fall outside the mask, so the
    runtime showed them in every pane and the panes became identical.
    """
    stage = next((item for item in compiled.storyboard if item.id == stage_id), None)
    if stage is None:
        raise ValueError(f"unknown storyboard stage: {stage_id}")
    controlled: list[str] = []
    for item in compiled.storyboard:
        controlled.extend(item.visible_aliases)
    for _semantic_id, values in getattr(compiled, "aliases", ()) or ():
        controlled.extend(str(value) for value in values)
    # A vector entity binds its ``__end`` alias but not the co-located
    # ``__origin`` point; the storyboard adds that origin only where the end is
    # visible.  Mirror the rule so the shared origin is masked like its vector.
    for alias in tuple(controlled):
        if alias.endswith("__end"):
            controlled.append(f"{alias[:-5]}__origin")
    return tuple(dict.fromkeys(controlled)), stage.visible_aliases


__all__ = [
    "COMPILER_VERSION",
    "CompileIssue",
    "CompiledVisualization",
    "CompiledStoryboardStage",
    "VisualCompileError",
    "VisualSemanticsCompiler",
    "storyboard_visibility",
]
