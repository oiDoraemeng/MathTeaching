import json
from pathlib import Path

import pytest

from linear_algebra.catalog.chapter_04 import TOPICS
from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
from linear_algebra.teaching.compile_resources import compiled_resource_store
from linear_algebra.teaching.compile_resources import compile_chapter_04
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.chapter_04 import RECIPES
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.chapter_04_semantics import semantic_for
from services.scene_commands import SceneCommandService
from ui.teaching_case_panes import case_plan

def test_chapter_four_has_4_complete_topic_recipes_and_validated_plans():
    assert len(TOPICS) == len(RECIPES) == 4
    for recipe in RECIPES:
        plan = recipe.builder(RenderContext.default(recipe.id))
        assert SceneCommandService().validate(plan).valid
        assert any(operation["op"].startswith(("geometry.", "linear.", "annotation.")) for operation in plan.operations)


def test_chapter_four_builders_use_reviewed_graph_contract_and_source_context():
    reviewed = load_reviewed_artifacts()
    compiler = VisualSemanticsCompiler()
    for topic in TOPICS:
        artifact = TeachingArtifact.from_dict(reviewed[topic.id])
        contract = contract_for(topic.id)
        compiled = compiler.compile(artifact, contract, RenderContext.default(topic.id))
        recipe = next(recipe for recipe in RECIPES if recipe.id == f"draw.{topic.id}")
        plan = recipe.builder(RenderContext.default(recipe.id))
        assert plan.to_dict() == compiled.plan.to_dict()
        actual_ops = {operation["op"] for operation in plan.operations}
        assert actual_ops
        assert artifact.source.source_hash == artifact.generated.source_hash
        assert artifact.source.heading_path


def test_chapter_four_compiled_bundles_and_index_are_linked():
    root = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data"
    store = compiled_resource_store(root / "compiled")
    reviewed = load_reviewed_artifacts()
    resources = [store.get(topic.id) for topic in TOPICS]
    assert len(resources) == 4
    assert {resource.topic_id for resource in resources} == {topic.id for topic in TOPICS}
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    topic_ids = [row["topic_id"] for row in index["topics"]]
    assert len(topic_ids) == len(set(topic_ids))
    assert sum(topic_id.startswith("ch04.") for topic_id in topic_ids) == 4
    rows = {row["topic_id"]: row for row in index["topics"]}
    assert set(topic.id for topic in TOPICS) <= rows.keys()
    for resource in resources:
        artifact = TeachingArtifact.from_dict(reviewed[resource.topic_id])
        row = rows[resource.topic_id]
        assert resource.revision == artifact.revision == row["published_revision"]
        assert resource.source_hash == artifact.source.source_hash == row["source_hash"]
        assert resource.artifact_digest == row["artifact_digest"]
        assert resource.contract_digest == row["contract_digest"]
        assert resource.scene_family == artifact.visual_semantics.scene_family == row["scene_family"]
        assert resource.plan_digest == row["plan_digest"]


def test_chapter_four_topics_have_explicit_distinct_semantic_mappings():
    reviewed = load_reviewed_artifacts()
    plans = {}
    for topic in TOPICS:
        semantic = semantic_for(topic.id)
        artifact = TeachingArtifact.from_dict(reviewed[topic.id])
        contract = contract_for(topic.id)
        assert artifact.visual_semantics.scene_family == semantic.family
        assert contract.required_primitives == (semantic.primitive,)
        assert contract.required_relations == (semantic.relation,)
        compiled = VisualSemanticsCompiler().compile(artifact, contract, RenderContext.default(topic.id))
        plans[topic.id] = tuple(operation["op"] for operation in compiled.plan.operations)
    assert len(plans) == 4
    assert plans["ch04.subspace.col-null"] != plans["ch04.basis.definition"]
    assert plans["ch04.dependence.redundancy"] != plans["ch04.linear-map.definition"]


def test_basis_definition_omits_optional_explanation_tail_sections():
    artifact = TeachingArtifact.from_dict(
        load_reviewed_artifacts()["ch04.basis.definition"]
    )

    assert artifact.explanation.analogy_boundary == ""
    assert artifact.explanation.transfer_note == ""
    assert artifact.explanation.conclusion == ""


def test_dependence_topic_uses_four_progressive_3d_cases_with_consistent_colours():
    topic_id = "ch04.dependence.redundancy"
    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic_id])
    compiled = VisualSemanticsCompiler().compile(artifact, contract_for(topic_id), RenderContext.default(topic_id))

    assert [(section.id, section.title) for section in artifact.explanation.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    assert artifact.explanation.summary == ""
    assert artifact.explanation.derivation == ()
    assert artifact.explanation.conclusion == ""
    assert artifact.explanation.analogy_boundary == ""
    assert artifact.explanation.transfer_note == ""
    assert "定义 4.5" not in artifact.explanation.definition
    assert "**（生成集）**" in artifact.explanation.definition
    assert "**（线性无关）**" in artifact.explanation.definition
    assert "**（线性相关）**" in artifact.explanation.definition
    assert r"\operatorname{Span}\{\boldsymbol u,\boldsymbol v,\boldsymbol w\}" in artifact.explanation.definition
    assert r"c_{1}\boldsymbol v_{1}+...+c_{k}\boldsymbol v_{k}=\boldsymbol 0" in artifact.explanation.definition
    assert "| 3个在$R^{3}$ | 不共面 | 共面 |" in artifact.explanation.definition
    assert "判定方法" not in artifact.explanation.definition
    assert [example.kind for example in artifact.explanation.worked_examples] == [
        "scalar_multiple",
        "linear_combination",
        "linear_combination",
        "linear_combination",
    ]
    assert [example.result for example in artifact.explanation.worked_examples] == [
        (2.0, 0.0, 0.0),
        (2.0, -1.0, 0.0),
        (1.0, 1.0, 1.0),
        (0.0, 0.0, 0.0),
    ]
    assert r"t=2" in artifact.explanation.worked_examples[0].calculation[-1]
    assert r"a=2,b=-1" in artifact.explanation.worked_examples[1].calculation[-1]
    assert all(r"\begin{pmatrix}" in "\n".join(example.calculation) for example in artifact.explanation.worked_examples)
    assert artifact.explanation.case_layout is not None
    assert artifact.explanation.case_layout.default_pane_count == 4
    assert [case.purpose for case in artifact.explanation.case_layout.cases] == [
        "① 一根向量：张成直线",
        "② 两根不共线向量：张成平面",
        "③ 加入平面外方向：张成整个三维空间",
        "④ 加入冗余方向：仍只张成原平面",
    ]
    assert [stage.id for stage in compiled.storyboard] == [
        "stage.ch04.dependence.redundancy.line",
        "stage.ch04.dependence.redundancy.plane",
        "stage.ch04.dependence.redundancy.space",
        "stage.ch04.dependence.redundancy.dependent",
    ]

    operations = {operation["alias"]: operation for operation in compiled.plan.operations if operation.get("alias")}
    groups = (
        ("span_line__generator", (r"\boldsymbol{u}",)),
        ("span_plane__generator", (r"\boldsymbol{u}", r"\boldsymbol{v}")),
        ("independent_set__axis", (r"\boldsymbol{u}", r"\boldsymbol{v}", r"\boldsymbol{w}")),
        ("dependent_set__generator", (r"\boldsymbol{u}", r"\boldsymbol{v}", r"\boldsymbol{w}")),
    )
    rendered_groups = []
    for prefix, symbols in groups:
        vectors = [operations[f"ch04__entity__{prefix}_{index}"] for index in range(1, len(symbols) + 1)]
        assert [vector["algebra_symbol"] for vector in vectors] == list(symbols)
        assert len({vector["color"] for vector in vectors}) == len(vectors)
        assert all("line_width" not in vector for vector in vectors)
        assert all("arrow_tip_length_px" not in vector and "arrow_tip_radius_px" not in vector for vector in vectors)
        assert all(vector["arrow_head_scale"] == pytest.approx(2.0 / 3.0) for vector in vectors)
        assert all(vector["algebra_visible"] is True for vector in vectors)
        rendered_groups.append(vectors)
    assert rendered_groups[0][0]["color"] == rendered_groups[1][0]["color"] == rendered_groups[2][0]["color"] == rendered_groups[3][0]["color"]
    assert rendered_groups[1][1]["color"] == rendered_groups[2][1]["color"] == rendered_groups[3][1]["color"]
    assert rendered_groups[2][2]["color"] == rendered_groups[3][2]["color"]

    relation_terms = [
        operation
        for operation in compiled.plan.operations
        if str(operation.get("alias", "")).startswith("ch04__relation__")
        and "__term_" in str(operation.get("alias", ""))
    ]
    assert relation_terms == []

    line = case_plan(compiled, "stage.ch04.dependence.redundancy.line")
    plane = case_plan(compiled, "stage.ch04.dependence.redundancy.plane")
    independent = case_plan(compiled, "stage.ch04.dependence.redundancy.space")
    dependent = case_plan(compiled, "stage.ch04.dependence.redundancy.dependent")
    assert "ch04__entity__span_line" in {operation.get("alias") for operation in line.operations}
    assert "ch04__entity__span_plane" in {operation.get("alias") for operation in plane.operations}
    assert "ch04__entity__dependent_set" not in {operation.get("alias") for operation in independent.operations}
    assert "ch04__entity__dependent_set" in {operation.get("alias") for operation in dependent.operations}


def test_linear_map_definition_merges_verbatim_lecture_and_uses_two_coloured_case_panes():
    topic_id = "ch04.linear-map.definition"
    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic_id])
    compiled = VisualSemanticsCompiler().compile(
        artifact, contract_for(topic_id), RenderContext.default(topic_id)
    )

    source_bodies = [span.text.split("\n", 2)[2] for span in artifact.source.spans]
    assert artifact.explanation.definition == "\n\n".join(source_bodies)
    assert [span.heading_path[-1] for span in artifact.source.spans] == [
        "4.4.1 线性变换的定义",
        "4.4.2 是 vs 不是线性变换",
    ]
    assert "4.4.3 线性变换的矩阵表示" not in artifact.source.excerpt
    assert [(section.id, section.title) for section in artifact.explanation.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    assert artifact.explanation.summary == ""
    assert artifact.explanation.derivation == ()
    assert artifact.explanation.case_layout is not None
    assert artifact.explanation.case_layout.default_pane_count == 2
    assert [case.purpose for case in artifact.explanation.case_layout.cases] == [
        "拉伸（是）",
        "平移（不是）",
    ]

    stretch = case_plan(compiled, "stage.ch04.linear-map.definition.stretch")
    translation = case_plan(compiled, "stage.ch04.linear-map.definition.translation")
    stretch_grid = next(op for op in stretch.operations if op.get("op") == "geometry.transformed_grid")
    translation_grid = next(op for op in translation.operations if op.get("op") == "geometry.transformed_grid")
    assert stretch_grid["matrix"] == [[2, 0], [0, 1]]
    assert translation_grid["matrix"] == [[1, 0], [0, 1]]
    assert translation_grid["origin"] == [1, 0]
    assert stretch_grid["bounds"] == translation_grid["bounds"]
    assert stretch_grid["show_source_grid"] is translation_grid["show_source_grid"] is False
    translation_vectors = {
        op["alias"]: op
        for op in translation.operations
        if op.get("op") == "linear.upsert"
    }
    assert translation_vectors["ch04__relation__translation_case__direct"]["color"] != (
        translation_vectors["ch04__relation__translation_case__separate"]["color"]
    )
    assert compiled.family_evidence["translation_sum_image"] == [2, 1]
    assert compiled.family_evidence["translation_sum_of_images"] == [3, 1]


def test_chapter_four_index_upsert_preserves_legacy_rows_and_is_idempotent(tmp_path):
    bundled = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "index.json"
    baseline = json.loads(bundled.read_text(encoding="utf-8"))
    legacy_rows = [row for row in baseline["topics"] if not row["topic_id"].startswith("ch04.")]
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"schema_version": 1, "topic_count": len(legacy_rows), "topics": legacy_rows}, sort_keys=True), encoding="utf-8")

    compile_chapter_04(output_root=tmp_path / "compiled", index_path=index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["topic_count"] == len(payload["topics"]) == 57
    assert len({row["topic_id"] for row in payload["topics"]}) == 57
    assert sum(row["topic_id"].startswith("ch04.") for row in payload["topics"]) == 4
    retained = {row["topic_id"]: row for row in payload["topics"] if not row["topic_id"].startswith("ch04.")}
    assert list(retained.values()) == legacy_rows
    first_bytes = index_path.read_bytes()
    compile_chapter_04(output_root=tmp_path / "compiled", index_path=index_path)
    assert index_path.read_bytes() == first_bytes


def test_chapter_four_index_upsert_validates_before_writing_resources(tmp_path):
    index_path = tmp_path / "index.json"
    before = {"schema_version": 999, "topic_count": 0, "topics": []}
    index_path.write_text(json.dumps(before), encoding="utf-8")
    with pytest.raises(ValueError, match="schema-version-1"):
        compile_chapter_04(output_root=tmp_path / "compiled", index_path=index_path)
    assert json.loads(index_path.read_text(encoding="utf-8")) == before
    assert not (tmp_path / "compiled").exists()
