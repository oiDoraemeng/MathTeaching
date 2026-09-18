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

def test_chapter_four_has_14_complete_topic_recipes_and_validated_plans():
    assert len(TOPICS) == len(RECIPES) == 14
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
    assert len(resources) == 14
    assert {resource.topic_id for resource in resources} == {topic.id for topic in TOPICS}
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    topic_ids = [row["topic_id"] for row in index["topics"]]
    assert len(topic_ids) == len(set(topic_ids))
    assert sum(topic_id.startswith("ch04.") for topic_id in topic_ids) == 14
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
    assert len(set(plans.values())) >= 8
    assert plans["ch04.space.closure"] != plans["ch04.basis.definition"]
    assert plans["ch04.dependence.redundancy"] != plans["ch04.linear-map.compare"]


def test_chapter_four_index_upsert_preserves_legacy_rows_and_is_idempotent(tmp_path):
    bundled = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "index.json"
    baseline = json.loads(bundled.read_text(encoding="utf-8"))
    legacy_rows = [row for row in baseline["topics"] if not row["topic_id"].startswith("ch04.")]
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"schema_version": 1, "topic_count": len(legacy_rows), "topics": legacy_rows}, sort_keys=True), encoding="utf-8")

    compile_chapter_04(output_root=tmp_path / "compiled", index_path=index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["topic_count"] == len(payload["topics"]) == 72
    assert len({row["topic_id"] for row in payload["topics"]}) == 72
    assert sum(row["topic_id"].startswith("ch04.") for row in payload["topics"]) == 14
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
