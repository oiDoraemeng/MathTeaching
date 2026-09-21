"""Frozen regressions for the published Chapter 1--3 curriculum.

Chapter 4--8 is an additive extension.  These values intentionally live in
the test rather than being read from the published index: changing a legacy
builder and regenerating its snapshot must not silently move this baseline.
"""

from __future__ import annotations

import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.registry import bundled_teaching_store, catalog_registry
from services.scene_commands import CommandPlan, SceneCommandService
from ui.designer_window import MainWindow


LEGACY_PLAN_DIGESTS = {
    "ch01.vector.magnitude": "sha256:e14f4d44c1783c8c721b68ad78305a98ad6552ca5b979e4fd99d6654c5ec9295",
    "ch01.ops.addition": "sha256:28d36cbf27d448be3b41b99c1849378e1bb7f03acb737f3118b2a9e1b4bb86ae",
    "ch01.ops.subtraction": "sha256:86739d3926804242fe1ae18947e8aed9d5dd3fe9848918cd998f055ce3deddd7",
    "ch01.ops.scalar": "sha256:fda9ff56813c525ddf954c37ac8ed328d2a78423af9040e353a1c1de465cfcb8",
    "ch01.ops.linear-combination": "sha256:423a60449c466f5e1b2dda613d720b0c93d2a231173d73eb31e9902c3fe3cf29",
    "ch01.inner.definitions": "sha256:87727eef228c62cb72f94048a50757360234607f01ffeac3b17df86a349bb9b5",
    "ch01.inner.cauchy-schwarz": "sha256:032d7e836cc4cb664a89a089514f814e29b402082b033e3412f1f91da29c1868",
    "ch01.projection.definition": "sha256:66450b1edbf36646762a740be7239a41f6439eb97c2398cae640f8eaa8e10711",
    "ch01.proof.midline": "sha256:ef698dd38942fce8724934c6ab59f110933a256d13d16f4c56c4972526f542a9",
    # r20：两道证明题改为「命题/公式/向量证明」三分节（无案例、无几何意义），
    # 图全部按向量画；重心图 E、F 按讲义标注为 AB、AC 边中点。
    "ch01.proof.centroid": "sha256:e957d4ef26dc4b21b0a6cfa67b582451e14fd9eb0636d3e4bfcfae683978c3d6",
    "ch01.proof.parallelogram-diagonals": "sha256:00379edf33edb0d6841a24f76402def6790797c9114e26cbae04c523cda45397",
    "ch02.batch.inner-products": "sha256:e7dbeb49e88770e1d6a7a9bc32cae6e8984c938cc9e892af6fee405cba3a6c63",
    # r20：2.3 完整保留讲义定义，单一案例在一个窗格中同时投影三个向量。
    "ch02.batch.projection": "sha256:c9267766e9de66b5ef542c09732dd8827470cc7e367610d2649e9d2fd27aeb57",
    "ch02.matrix.additive-distributivity": "sha256:c9740c08c8f0dadaddfb757f7b4927d7f33dae4f6c047335b6c17a048f6dee95",
    "ch02.matrix.transformed-grid": "sha256:8d958082161d4ba266b55e6e587e6116f9fb3e99d781d914cb4ff9ba0fdf4599",
    "ch02.matrix.composition": "sha256:efa1dd269ebe968fdc49db7cf500597b29f8b721d476250857f6192f7c620c41",
    "ch02.matrix.basis": "sha256:739f6934b0fabaf3644295c38db462cc06e95051ff83d5814117023f26cf81ad",
    "ch02.matrix.powers": "sha256:c78385e0ff98a993de305952ae0ce9ee1be509b3a5a08aa256f0b659a23d34fe",
    # 2.9 只发布讲义 2.9.1「线性无关与线性相关」与 2.9.2「秩」：原零空间、列空间与
    # 与后续章节的关系三节已从目录与数据中移除，冻结的 digest 相应更新。
    "ch02.subspace.independence": "sha256:3e35510a4e2bba9f30db1dfc577c4ea8f95e4cbfe35e942d178678e0ad4a5f1f",
    "ch02.subspace.rank": "sha256:ee0eab65aa4ba075d4e123888ee24f963e2da9ea1cb7256217eb553f1a9c3e65",
    # 3.1 的四个小节已合并为单一小节「行列式的几何定义」：案例改为两步流程
    # （单位正方形 / 两个像 + 外接矩形与切角辅助线），冻结的 digest 相应更新。
    "ch03.det.oriented-area": "sha256:a568f67cf2e15697170e5715c452d1bad983c413b25dc59b120d6cd0581da75e",
    "ch03.det.row-swap": "sha256:cac64eb0b748e2514d099a7c44f72d6401366ce00c9c5643ada26921304e72d3",
    "ch03.det.scaling": "sha256:48071122621c703f14a27096f32878699e30b9033e8d12e6fe1c2190961685ee",
    "ch03.det.shear": "sha256:f955248683a5bf6c3dab44a0cac8f3f8d35aabc225448afa364ec64313935334",
    "ch03.det.multiplicativity": "sha256:e9720722e8844abce9e399e67c07d40fb632a84bfae44096d792f85d3ec6a303",
    "ch03.cramer.area-ratio": "sha256:7d33ba2c30549b5dd2272692446dba20407ce0f11a4411d32e27321ca59bf110",
    "ch03.inverse.undo": "sha256:28ec0b3a7e10110845066adb6749507713d2a08bbfe036a05fdf8ad9640b6536",
    "ch03.inverse.formula": "sha256:387c2362561c51b96abc02abb29e8714b00ac5eb646f004bbed09c499bcc361d",
    "ch03.inverse.examples": "sha256:890dcdedc976c2b2c23de474dc5fc1bc5917809751e315cbe36f78036cf0ce79",
    "ch03.det.zero.equivalence": "sha256:e84a87ae9410886a7af8145c2cf5f0f6189cc0458c122d472b17fd9a782178e7",
}


@pytest.fixture(scope="module")
def legacy_registry_bundle() -> tuple[object, object]:
    return catalog_registry(), bundled_teaching_store()


def test_all_legacy_topic_ids_and_plan_digests_are_frozen(legacy_registry_bundle) -> None:
    registry, store = legacy_registry_bundle
    legacy_ids = tuple(topic.id for topic in topic_entries() if topic.chapter_number <= 3)

    assert legacy_ids == tuple(LEGACY_PLAN_DIGESTS)
    assert len(legacy_ids) == 30
    for topic_id, expected_digest in LEGACY_PLAN_DIGESTS.items():
        bundle = registry.resolve_bundle(topic_id, artifact_store=store)
        assert bundle.compiled.plan_digest == expected_digest
        assert bundle.snapshot.plan_digest == expected_digest


@pytest.mark.parametrize("topic_id", tuple(LEGACY_PLAN_DIGESTS))
def test_every_legacy_topic_keeps_atomic_clear_load_behavior(topic_id: str) -> None:
    plan = MainWindow._linear_algebra_lesson_plan(topic_id)

    assert isinstance(plan, CommandPlan)
    assert plan.operations[0] == {"op": "scene.clear", "scope": "all"}
    assert plan.operations[-1]["op"] == "view.fit"
    assert SceneCommandService().validate(plan).valid


def test_published_source_anchors_match_the_catalog(legacy_registry_bundle) -> None:
    """目录显示名不得通过改写 ``source_path`` 实现。

    ``source_path`` 同时是已发布 artifact 的来源锚点：``commit_curriculum_bundle``
    会逐字比对，一旦漂移，该主题在运行时会被 ``bundle_mismatch`` 拒绝。3.1 合并
    时曾把显示名写进 source_path，目录显示名应改用 ``LessonEntry.display_title``
    覆盖，而 ``source_path`` 必须与已发布资源保持一致。
    """
    _registry, store = legacy_registry_bundle
    for topic in topic_entries():
        if topic.chapter_number > 3:
            continue
        stored = store.published(topic.id)
        assert stored is not None, f"{topic.id} has no published artifact"
        assert tuple(stored.artifact.source.source_path) == tuple(topic.source_path), topic.id


def test_vector_magnitude_preserves_the_complete_lecture_and_existing_case(
    legacy_registry_bundle,
) -> None:
    _registry, store = legacy_registry_bundle
    artifact = store.published("ch01.vector.magnitude").artifact
    explanation = artifact.explanation

    assert explanation.summary == (
        "我们从一个最简单的物理场景出发：\n"
        "从宿舍到食堂，\"向北走300米，再向东走400米\"。\n"
        "这和\"向东走400米，再向北走300米\"的目标位置完全相同。\n"
        "这两个\"走法\"有方向（北偏东）和长度（500米）。\n"
        "它们描述的是同一个位移。\n"
        "把这个直觉翻译成数学语言："
    )
    assert [section.title for section in explanation.sections] == ["定义", "数学案例"]
    assert "**（向量）** 在平面直角坐标系中" in explanation.definition
    assert "记法：向量一般用粗体小写字母表示" in explanation.definition
    assert "关键约定：在线性代数中，所有向量默认从原点出发" in explanation.definition
    assert "**（零向量）** 长度为零的向量称为零向量" in explanation.definition
    assert "**（向量的模）** 向量 $\\boldsymbol v = (x, y)$ 的长度称为模" in explanation.definition
    assert "$$|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}$$" in explanation.definition
    assert "例如，$(3, 4)$ 的模为 $\\sqrt{9 + 16} = 5$。" in explanation.definition
    assert not any(marker in explanation.definition for marker in ("定义 1.1", "定义 1.2", "定义 1.3"))
    assert explanation.derivation == ()
    assert explanation.geometric_meaning == ""
    assert explanation.conclusion == ""

    assert len(explanation.worked_examples) == 1
    example = explanation.worked_examples[0]
    assert example.id == "example.magnitude.nonzero"
    assert example.given == ((3, 4), (3, 4))
    assert example.result == 25
    assert [entity.id for entity in artifact.visual_semantics.entities] == ["v", "v_length"]
    assert [stage.id for stage in artifact.visual_semantics.stages] == ["stage.magnitude.nonzero"]


def test_cauchy_schwarz_keeps_the_complete_lecture_proof_and_two_cases(
    legacy_registry_bundle,
) -> None:
    registry, store = legacy_registry_bundle
    topic_id = "ch01.inner.cauchy-schwarz"
    artifact = store.published(topic_id).artifact
    explanation = artifact.explanation

    assert registry.get_topic(topic_id).title == "柯西—施瓦茨不等式"
    assert [section.title for section in explanation.sections] == [
        "定义",
        "Cauchy-Schwarz 不等式的证明（2D情形）",
        "数学案例",
    ]
    assert explanation.formula == ""
    assert "定理 1.5（Cauchy-Schwarz 不等式）" in explanation.definition
    assert r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq" in explanation.definition
    assert "投影的长度”不可能超过“原向量的长度”" in explanation.definition
    assert "Cauchy-Schwarz 不等式的 n 维推广证明" in explanation.derivation[1]
    assert r"判别式 $\Delta\leq0$" in explanation.derivation[4]
    assert "(a_{1}b_{2}-a_{2}b_{1})^{2}" in explanation.derivation[-2]
    assert all(r"\n" not in item for item in explanation.derivation)
    assert [example.title for example in explanation.worked_examples] == [
        "案例一：严格不等式",
        "案例二：等号成立",
    ]
    strict, equality = explanation.worked_examples
    assert strict.given == ((1, 0), (3, 4))
    assert strict.result == 3.0
    assert any(r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert=3<5" in line for line in strict.calculation)
    assert equality.given == ((1, 0), (5, 0))
    assert equality.result == 5.0
    assert explanation.case_layout is not None
    assert explanation.case_layout.default_pane_count == 1
    assert [case.purpose for case in explanation.case_layout.cases] == [
        "案例一：严格不等式",
        "案例二：等号成立",
    ]

    strict_projection = next(
        relation
        for relation in artifact.visual_semantics.relations
        if relation.id == "rel.cauchy-schwarz.strict.projection"
    )
    assert strict_projection.source_ref == "strict_b"
    assert strict_projection.target_ref == "strict_a"
    assert not any(
        relation.id == "rel.cauchy-schwarz.strict.orthogonal"
        for relation in artifact.visual_semantics.relations
    )
    assert "strict_H" not in {entity.id for entity in artifact.visual_semantics.entities}

    compiled = registry.resolve_bundle(topic_id, artifact_store=store).compiled
    assert compiled.plan.operations[-1] == {
        "op": "view.fit",
        "padding": 1.15,
        "bounds": [0.0, 5.0, 0.0, 4.0],
    }
    orange = "#F08A24"
    colors = {
        str(operation.get("alias")): operation.get("color")
        for operation in compiled.plan.operations
        if operation.get("op") in {"linear.upsert", "geometry.projection"}
    }
    assert colors["sem__strict_b"] == orange
    assert colors["sem__strict_p"] == orange
    assert colors["sem__strict_r"] == orange
    assert colors["sem__rel.cauchy-schwarz.strict.projection"] == orange
    assert not any(
        operation.get("op") == "geometry.right_angle_marker"
        for operation in compiled.plan.operations
    )
    assert not any(
        operation.get("op") == "annotation.upsert"
        and str(operation.get("text", "")).startswith("案例")
        for operation in compiled.plan.operations
    )
