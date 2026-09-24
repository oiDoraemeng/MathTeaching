import copy
import json
from pathlib import Path

import numpy as np
import pytest

from linear_algebra.catalog.manifest import lecture_manifest
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.examples import verify_worked_example
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


TOPICS = tuple("ch07." + name for name in ("eigen.direction", "characteristic-polynomial", "eigenspace", "diagonalization"))
REMOVED = ("ch07.gram-schmidt", "ch07.orthogonal-transform")


def compile_topic(topic, payload=None):
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload if payload is not None else artifact_payload_for(topic)))


@pytest.mark.parametrize("topic", TOPICS)
def test_four_topics_compile_to_disjoint_real_evidence(topic):
    compiled = compile_topic(topic)
    operations = {operation["alias"]: operation for operation in compiled.plan.operations if operation.get("alias")}
    used = set()
    graph = artifact_payload_for(topic)["visual_semantics"]
    for category in ("entities", "relations", "stages"):
        for item in graph[category]:
            aliases = set(compiled.aliases_for(item["id"]))
            assert aliases and not used.intersection(aliases)
            assert all(not operations[alias]["op"].startswith("annotation.") for alias in aliases)
            used.update(aliases)


def test_diagonalization_is_change_basis_then_scale_then_change_back():
    compiled = compile_topic("ch07.diagonalization")
    evidence = compiled.family_evidence
    assert evidence["endpoint_error"] < 1e-9
    assert np.allclose(evidence["diagonal"], [[3, 0], [0, 1]])
    assert np.allclose(evidence["basis"], [[1, 1], [1, -1]])
    assert [stage.id.split(".")[-1] for stage in compiled.storyboard] == ["change_basis", "diagonal_scale", "change_basis_back"]


def numeric_paths(value, prefix=()):
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from numeric_paths(child, (*prefix, index))
    else:
        yield prefix


@pytest.mark.parametrize("topic", TOPICS)
def test_every_entity_and_relation_numeric_leaf_is_checked(topic):
    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    for kind in ("entities", "relations"):
        for index, item in enumerate(original["visual_semantics"][kind]):
            witnesses = {"value": item["value"]} if kind == "entities" else item["parameters"]
            for field, value in witnesses.items():
                for path in numeric_paths(value):
                    payload = copy.deepcopy(original)
                    obj = payload["visual_semantics"][kind][index]
                    container = obj if kind == "entities" else obj["parameters"]
                    if path:
                        target = container[field]
                        for part in path[:-1]:
                            target = target[part]
                        target[path[-1]] += 0.37
                    else:
                        container[field] += 0.37
                    with pytest.raises(ValueError):
                        compile_topic(topic, payload)


@pytest.mark.parametrize("topic", TOPICS)
def test_exact_graph_and_every_stage_member_fail_before_operations(topic, monkeypatch):
    from linear_algebra.visualizations.families import chapter_07

    original = artifact_payload_for(topic)
    compile_topic(topic, original)
    monkeypatch.setattr(chapter_07, "_Scene", lambda *args: pytest.fail("invalid graph reached operations"))
    graph = original["visual_semantics"]
    for category in ("entities", "relations", "stages"):
        for index, item in enumerate(graph[category]):
            payload = copy.deepcopy(original)
            del payload["visual_semantics"][category][index]
            with pytest.raises(ValueError):
                compile_topic(topic, payload)
            fields = ("id", "role", "kind", "label") if category == "entities" else ("id", "kind", "source_ref", "target_ref") if category == "relations" else ("id", "title", "caption", "layout")
            for field in fields:
                payload = copy.deepcopy(original)
                payload["visual_semantics"][category][index][field] += "__tampered"
                with pytest.raises(ValueError):
                    compile_topic(topic, payload)
            if category == "relations":
                for field in item["parameters"]:
                    payload = copy.deepcopy(original)
                    del payload["visual_semantics"][category][index]["parameters"][field]
                    with pytest.raises(ValueError):
                        compile_topic(topic, payload)
            if category == "stages":
                for field in ("input_entity_refs", "output_entity_refs", "relation_refs", "expected_invariants"):
                    for member in range(len(item[field])):
                        for delete in (True, False):
                            payload = copy.deepcopy(original)
                            refs = payload["visual_semantics"][category][index][field]
                            if delete:
                                del refs[member]
                            else:
                                refs[member] += "__tampered"
                            with pytest.raises(ValueError):
                                compile_topic(topic, payload)


def test_lecture_numeric_evidence_is_recomputed():
    direction = compile_topic("ch07.eigen.direction").family_evidence
    assert direction["directions"]["stretch_x"] == {"eigenvalue": 2.0, "output": [2.0, 0.0]}
    assert direction["counterexamples"]["stretch_diagonal"] == {"output": [2.0, 1.0], "direction_changed": True}
    assert direction["directions"]["projection_y"] == {"eigenvalue": 0.0, "output": [0.0, 0.0]}
    assert direction["rotation_real_directions"] == []

    polynomial = compile_topic("ch07.characteristic-polynomial").family_evidence
    assert polynomial["spectra"]["real_spectrum"]["coefficients"] == [1.0, -4.0, 3.0]
    assert polynomial["spectra"]["real_spectrum"]["roots"] == [[1.0, 0.0], [3.0, 0.0]]
    assert polynomial["spectra"]["complex_spectrum"]["roots"] == [[1.0, -1.0], [1.0, 1.0]]
    assert polynomial["complex_real_directions"] == []

    eigenspace = compile_topic("ch07.eigenspace").family_evidence
    assert eigenspace["eigenspaces"] == {"space_3": [[1.0, 1.0]], "space_1": [[1.0, -1.0]], "shear_space": [[1.0, 0.0]]}
    assert eigenspace["determinant"] == pytest.approx(3.0)
    assert eigenspace["trace"] == 4.0


@pytest.mark.parametrize("topic", TOPICS)
def test_all_lecture_worked_examples_verify(topic):
    artifact = TeachingArtifact.from_dict(artifact_payload_for(topic))
    assert artifact.explanation.worked_examples
    assert all(verify_worked_example(example).valid for example in artifact.explanation.worked_examples)


def test_chapter7_tree_merges_711_to_713_and_keeps_requested_titles():
    nodes = {node.id: node for node in lecture_manifest()}
    assert nodes["ch07"].children == ("ch07.s1", "ch07.s2", "ch07.s3", "ch07.s4")
    assert [nodes[section].title for section in nodes["ch07"].children] == [
        "7.1 定义与几何意义", "7.2 特征多项式", "7.3 求特征向量", "7.4 对角化的几何意义",
    ]
    assert [nodes[nodes[section].children[0]].title for section in nodes["ch07"].children] == [
        "特征值与特征向量", "特征多项式", "求特征向量", "对角化的几何意义",
    ]


def test_chapter7_merges_711_to_713_and_uses_the_confirmed_direction_contrast():
    direction = artifact_payload_for("ch07.eigen.direction")["explanation"]
    assert "**（特征值与特征向量）**" in direction["definition"]
    assert "**（特征空间）**" in direction["definition"]
    assert "**定义 7.1" not in direction["definition"]
    assert "**定义 7.2" not in direction["definition"]
    assert "几何直觉（先看图）" in direction["definition"]
    assert "几何直觉总结表" in direction["definition"]
    assert "没有实特征向量" in direction["definition"]
    assert len(direction["worked_examples"]) == 1
    assert len(direction["case_layout"]["cases"]) == 1
    assert direction["case_layout"]["default_pane_count"] == 1
    case = direction["worked_examples"][0]
    assert case["id"] == "example.ch07.eigen.direction.contrast"
    assert r"\boldsymbol u" in case["calculation"][0]
    assert r"\boldsymbol A\boldsymbol u" in case["calculation"][0]
    assert r"\begin{pmatrix}" in direction["definition"]
    assert "| 不变量 |" not in direction["definition"]
    assert "分层例题" not in direction["definition"]
    assert "补充例题" not in direction["definition"]
    assert "自检" not in direction["definition"]
    assert "二次型" not in direction["definition"]
    assert direction["invariants"] == []
    assert all(section["title"] != "不变量" for section in direction["sections"])
    assert direction["case_layout"]["cases"][0]["stage_refs"] == ["stage.ch07.eigen.direction.stretch"]

    polynomial = artifact_payload_for("ch07.characteristic-polynomial")["explanation"]
    assert "$(\\boldsymbol A-\\lambda\\boldsymbol I)\\boldsymbol v=\\boldsymbol 0$" in polynomial["derivation"][0]
    assert len(polynomial["worked_examples"]) == 2

    eigenspace = artifact_payload_for("ch07.eigenspace")["explanation"]
    joined = "\n".join([eigenspace["definition"], *eigenspace["derivation"], *[line for example in eigenspace["worked_examples"] for line in example["calculation"]]])
    assert "特征值的乘积与行列式" in joined
    assert "特征值的和与迹" in joined
    assert "不同特征值对应的特征向量线性无关" in joined
    assert "代数重数与几何重数" in joined
    assert "例 7：不可对角化的矩阵" in {example["title"] for example in eigenspace["worked_examples"]}

    diagonalization = artifact_payload_for("ch07.diagonalization")["explanation"]
    assert diagonalization["case_layout"]["default_pane_count"] == 3
    assert [case["purpose"] for case in diagonalization["case_layout"]["cases"]] == [
        "第一步：换到特征基", "第二步：沿特征方向独立缩放", "第三步：换回标准基",
    ]
    assert "定义与公式" not in joined


def test_removed_75_and_76_have_no_runtime_resources():
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    indexed = {row["topic_id"] for row in json.loads((data / "index.json").read_text(encoding="utf-8"))["topics"]}
    assert set(REMOVED).isdisjoint(indexed)
    for topic in REMOVED:
        assert not (data / "compiled" / f"{topic}.json").exists()
        assert not (data / "drafts" / "ch07" / topic / "r1.json").exists()
        assert not (data / "revieweds" / "ch07" / topic / "r1.json").exists()


def test_registry_and_canonical_publication_match_chapter7_resources():
    from linear_algebra.teaching.compile_resources import compile_reviewed_topic, compiled_resource_store
    from linear_algebra.visualizations import recipes_for_topics

    data = Path("linear_algebra/teaching/data")
    rows = json.loads((data / "index.json").read_text(encoding="utf-8"))["topics"]
    assert len(rows) == len({row["topic_id"] for row in rows}) == 47
    assert sum(row["chapter"] == 7 for row in rows) == 4
    by_id = {row["topic_id"]: row for row in rows}
    recipes = recipes_for_topics()
    for topic in TOPICS:
        assert "draw." + topic in recipes
        assert recipes["draw." + topic].scene == "2d"
        assert json.loads((data / "revieweds" / "ch07" / topic / "r1.json").read_text(encoding="utf-8")) == artifact_payload_for(topic)
        resource = compile_reviewed_topic(topic).to_dict()
        assert resource == compiled_resource_store().get(topic).to_dict()
        for key in ("revision", "artifact_digest", "source_hash", "compiler_version", "render_profile", "plan_digest", "contract_digest", "scene_family"):
            assert resource[key] == by_id[topic][key]


def test_nine_file_release_is_transactional_at_every_replacement(tmp_path, monkeypatch):
    import os
    from linear_algebra.teaching.compile_resources import compile_chapter_07

    index = tmp_path / "index.json"
    index.write_bytes(Path("linear_algebra/teaching/data/index.json").read_bytes())
    payloads = {topic: artifact_payload_for(topic) for topic in TOPICS}
    args = dict(output_root=tmp_path / "compiled", index_path=index, reviewed_root=tmp_path / "reviewed", reviewed_payloads=payloads)
    compile_chapter_07(**args)
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
                compile_chapter_07(**args)
        assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == before
    with pytest.raises(ValueError):
        compile_chapter_07(**dict(args, reviewed_payloads={}))
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == before
