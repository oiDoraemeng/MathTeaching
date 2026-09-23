import copy
import json
from pathlib import Path

import numpy as np
import pytest

from linear_algebra.catalog.chapter_08 import TOPICS as CATALOG_TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


TOPICS = (
    "ch08.quadratic.matrix-form",
    "ch08.quadratic.level-sets",
    "ch08.principal-axis",
    "ch08.definiteness",
)
REMOVED = ("ch08.completing-square", "ch08.congruence-inertia")


def compile_topic(topic: str, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload or artifact_payload_for(topic)))


@pytest.mark.parametrize("topic", TOPICS)
def test_four_retained_topics_compile_with_disjoint_semantic_evidence(topic):
    compiled = compile_topic(topic)
    assert compiled.plan.operations
    operations = {operation["alias"]: operation for operation in compiled.plan.operations if operation.get("alias")}
    used: set[str] = set()
    payload = artifact_payload_for(topic)
    for category in ("entities", "relations", "stages"):
        for item in payload["visual_semantics"][category]:
            bound = set(compiled.aliases_for(item["id"]))
            assert bound and not used.intersection(bound)
            assert all(not operations[alias]["op"].startswith("annotation.") for alias in bound)
            used.update(bound)


def test_principal_axis_is_the_lecture_three_stage_diagonalization():
    compiled = compile_topic("ch08.principal-axis")
    evidence = compiled.family_evidence
    assert evidence["cross_term_after"] < 1e-9
    assert compiled.evidence.cross_term_after_rotation < 1e-9
    assert evidence["endpoint_error"] < 1e-9
    assert [stage.id for stage in compiled.storyboard] == [
        "stage.ch08.principal-axis.original",
        "stage.ch08.principal-axis.axes",
        "stage.ch08.principal-axis.standard",
    ]


@pytest.mark.parametrize("topic", TOPICS)
def test_every_graph_member_rejects_mutation(topic):
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    for category in ("entities", "relations", "stages"):
        for index, item in enumerate(original["visual_semantics"][category]):
            altered = copy.deepcopy(original)
            del altered["visual_semantics"][category][index]
            with pytest.raises(ValueError):
                compile_topic(topic, altered)
            fields = (
                ("id", "role", "kind", "label") if category == "entities"
                else ("id", "kind", "source_ref", "target_ref") if category == "relations"
                else ("id", "title", "caption", "layout")
            )
            for field in fields:
                altered = copy.deepcopy(original)
                altered["visual_semantics"][category][index][field] += "__bad"
                with pytest.raises(ValueError):
                    compile_topic(topic, altered)


def numeric_paths(value, prefix=()):
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from numeric_paths(item, (*prefix, index))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield prefix


@pytest.mark.parametrize("topic", TOPICS)
def test_every_numeric_leaf_and_parameter_is_required(topic):
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    for category in ("entities", "relations"):
        for index, record in enumerate(original["visual_semantics"][category]):
            values = {"value": record["value"]} if category == "entities" else record["parameters"]
            for field, value in values.items():
                altered = copy.deepcopy(original)
                container = altered["visual_semantics"][category][index]
                if category == "relations":
                    container = container["parameters"]
                del container[field]
                with pytest.raises(ValueError):
                    compile_topic(topic, altered)
                for path in numeric_paths(value):
                    altered = copy.deepcopy(original)
                    container = altered["visual_semantics"][category][index]
                    if category == "relations":
                        container = container["parameters"]
                    destination = container[field]
                    for part in path[:-1]:
                        destination = destination[part]
                    if path:
                        destination[path[-1]] += 0.37
                    else:
                        container[field] += 0.37
                    with pytest.raises(ValueError):
                        compile_topic(topic, altered)


@pytest.mark.parametrize("topic", TOPICS)
def test_stage_references_and_invariants_are_strict(topic):
    original = artifact_payload_for(topic)
    for stage_index, stage in enumerate(original["visual_semantics"]["stages"]):
        for field in ("input_entity_refs", "output_entity_refs", "relation_refs", "expected_invariants"):
            assert stage[field]
            for position in range(len(stage[field])):
                altered = copy.deepcopy(original)
                altered["visual_semantics"]["stages"][stage_index][field][position] += "__bad"
                with pytest.raises(ValueError):
                    compile_topic(topic, altered)


@pytest.mark.parametrize("topic", TOPICS)
def test_actual_mainwindow_executes_replays_and_rolls_back(topic):
    from tests.test_scene_command_dispatch import _pane_window
    from ui.designer_window import _SceneCommandBridge, _SceneCommandHostProxy
    from services.scene_commands import CommandError, CommandPlan, SceneCommandService, replay_extended_plan

    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    proxy = _SceneCommandHostProxy(_SceneCommandBridge(window), target)
    plan = compile_topic(topic).plan
    assert SceneCommandService(proxy).execute(plan, pane_id=target).valid
    invalid = {"op": "linear.upsert", "alias": "broken", "start": "missing", "end": "missing2", "kind": "segment"}
    bad = CommandPlan(scene="2d", operations=(*plan.operations, invalid))
    with window._using_pane(target):
        before = window._capture_scene_command_state()
    with pytest.raises(CommandError):
        SceneCommandService(proxy).execute(bad, pane_id=target)
    with window._using_pane(target):
        assert window._capture_scene_command_state() == before
    assert replay_extended_plan(plan, proxy).valid


def test_catalog_merges_8_3_and_uses_requested_titles():
    assert [topic.id for topic in CATALOG_TOPICS] == list(TOPICS)
    assert [topic.section_id for topic in CATALOG_TOPICS] == ["ch08.s1", "ch08.s2", "ch08.s3", "ch08.s4"]
    assert [topic.title for topic in CATALOG_TOPICS] == ["二次型", "二次型的几何意义", "主轴定理", "定性：正定、负定、不定"]
    assert [topic.source_path[-1].split(" ", 1)[0] for topic in CATALOG_TOPICS] == ["8.1", "8.2", "8.3", "8.4"]


def test_full_lecture_content_and_confirmed_case_layouts_are_present():
    matrix_form = artifact_payload_for("ch08.quadratic.matrix-form")["explanation"]
    assert [section["title"] for section in matrix_form["sections"]] == ["定义", "数学案例"]
    assert len(matrix_form["worked_examples"]) == 3
    assert matrix_form["case_layout"]["default_pane_count"] == 1
    assert len(matrix_form["case_layout"]["cases"]) == 3
    assert "交叉项系数" in matrix_form["definition"]
    assert "\\begin{pmatrix}" in matrix_form["definition"]

    level_sets = artifact_payload_for("ch08.quadratic.level-sets")["explanation"]
    assert len(level_sets["worked_examples"]) == 2
    assert "纠缠在一起" in level_sets["definition"]
    assert {case["purpose"] for case in level_sets["case_layout"]["cases"]} == {
        "无交叉项：椭圆与坐标轴对齐", "有交叉项：椭圆主轴倾斜"
    }

    principal = artifact_payload_for("ch08.principal-axis")["explanation"]
    assert [section["title"] for section in principal["sections"]] == ["定义", "推导", "数学案例"]
    assert principal["case_layout"]["default_pane_count"] == 3
    assert len(principal["case_layout"]["cases"]) == 3
    calculation = principal["worked_examples"][0]["calculation"][0]
    assert "第五步：写出标准形" in calculation
    assert "\\sqrt{\\frac18}" in calculation
    assert "特征值与二次型的关系" in calculation

    definiteness = artifact_payload_for("ch08.definiteness")["explanation"]
    assert [section["title"] for section in definiteness["sections"]] == ["定义", "推导", "数学案例"]
    assert len(definiteness["worked_examples"]) == 6
    assert len(definiteness["case_layout"]["cases"]) == 4
    assert "Sylvester 准则" in definiteness["definition"]
    assert "惯性定理" in definiteness["definition"]
    assert "Cholesky 分解" in definiteness["derivation"][0]


def test_scene_contracts_match_the_confirmed_visual_cases():
    matrix_plan = compile_topic("ch08.quadratic.matrix-form")
    matrix_ops = {operation["alias"]: operation for operation in matrix_plan.plan.operations if operation.get("alias")}
    first_matrix_stage = matrix_plan.storyboard[0]
    assert any(matrix_ops[alias]["op"] == "point.upsert" for alias in first_matrix_stage.visible_aliases)
    assert any(matrix_ops[alias]["op"] == "linear.upsert" for alias in first_matrix_stage.visible_aliases)

    level_plan = compile_topic("ch08.quadratic.level-sets")
    level_ops = {operation["alias"]: operation for operation in level_plan.plan.operations if operation.get("alias")}
    assert [level_ops[stage.visible_aliases[0]]["matrix"] for stage in level_plan.storyboard] == [
        [[3.0, 0.0], [0.0, 1.0]], [[2.0, 1.0], [1.0, 2.0]]
    ]

    definite_plan = compile_topic("ch08.definiteness")
    definite_ops = {operation["alias"]: operation for operation in definite_plan.plan.operations if operation.get("alias")}
    negative = definite_ops[definite_plan.storyboard[1].visible_aliases[0]]
    assert negative["classification"] == "negative_definite"
    assert negative["contour_vertices"] == []
    semidefinite_aliases = definite_plan.storyboard[3].visible_aliases
    assert any(definite_ops[alias]["op"] == "linear.upsert" for alias in semidefinite_aliases)


def test_removed_sections_have_no_runtime_or_resource_registration():
    registered = {topic.id for topic in CATALOG_TOPICS}
    data = Path("linear_algebra/teaching/data")
    for topic in REMOVED:
        assert topic not in registered
        assert not (data / "compiled" / f"{topic}.json").exists()
        assert not (data / "revieweds" / "ch08" / topic / "r1.json").exists()
        assert not (data / "drafts" / "ch08" / topic / "r1.json").exists()


def test_canonical_resources_and_index_match_the_four_retained_topics():
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic, compiled_resource_store
    from linear_algebra.visualizations import recipes_for_topics

    data = Path("linear_algebra/teaching/data")
    rows = json.loads((data / "index.json").read_text(encoding="utf-8"))["topics"]
    assert len(rows) == len({row["topic_id"] for row in rows}) == 47
    assert sum(row["chapter"] == 8 for row in rows) == 4
    by_id = {row["topic_id"]: row for row in rows}
    recipes = recipes_for_topics()
    for topic in TOPICS:
        assert f"draw.{topic}" in recipes
        assert artifact_payload_for(topic) == json.loads((data / "revieweds" / "ch08" / topic / "r1.json").read_text(encoding="utf-8"))
        fresh = compile_reviewed_topic(topic).to_dict()
        assert fresh == compiled_resource_store().get(topic).to_dict()
        for field in ("source_hash", "artifact_digest", "contract_digest", "plan_digest", "compiler_version", "render_profile", "scene_family", "revision"):
            assert fresh[field] == by_id[topic][field]


def test_release_nine_files_rolls_back_at_each_replace_and_rejects_empty_bundle(tmp_path, monkeypatch):
    import os
    from linear_algebra.teaching.compile_resources import compile_chapter_08

    index = tmp_path / "index.json"
    index.write_bytes(Path("linear_algebra/teaching/data/index.json").read_bytes())
    args = {
        "output_root": tmp_path / "compiled",
        "reviewed_root": tmp_path / "reviewed",
        "index_path": index,
        "reviewed_payloads": {topic: artifact_payload_for(topic) for topic in TOPICS},
    }
    compile_chapter_08(**args)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*.json")}
    assert len(before) == 9
    original = os.replace
    for fail_at in range(1, 10):
        calls = 0

        def fail(source, destination):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise OSError("injected replacement failure")
            return original(source, destination)

        with monkeypatch.context() as patcher:
            patcher.setattr(os, "replace", fail)
            with pytest.raises(OSError):
                compile_chapter_08(**args)
        assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == before
    with pytest.raises(ValueError):
        compile_chapter_08(**{**args, "reviewed_payloads": {}})


def test_quadratic_contours_do_not_bridge_hyperbola_gaps():
    from linear_algebra.visualizations.families.quadratic import QuadraticFamilyCompiler

    operation = QuadraticFamilyCompiler.compile({"matrix": [[1.0, 0.0], [0.0, -1.0]], "sample_count": 4096})["operations"][0]
    for point in operation["contour_vertices"]:
        vector = np.asarray(point)
        assert vector @ np.diag([1.0, -1.0]) @ vector == pytest.approx(1.0, abs=1e-9)
    for first, second in operation["contour_segments"]:
        assert operation["contour_vertices"][first][0] * operation["contour_vertices"][second][0] > 0


@pytest.mark.parametrize("topic", TOPICS)
def test_all_worked_examples_are_recomputable(topic):
    from linear_algebra.teaching.examples import verify_worked_example

    artifact = TeachingArtifact.from_dict(artifact_payload_for(topic))
    assert artifact.explanation.worked_examples
    assert all(example.kind == "determinant" and verify_worked_example(example).valid for example in artifact.explanation.worked_examples)
