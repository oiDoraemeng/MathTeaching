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
    "ch01.vector.magnitude": "sha256:bb4f4238604ac4e65e25de180491d6357e6f99e1b2e50e8278889baea172d9e6",
    "ch01.ops.addition": "sha256:28d36cbf27d448be3b41b99c1849378e1bb7f03acb737f3118b2a9e1b4bb86ae",
    "ch01.ops.subtraction": "sha256:86739d3926804242fe1ae18947e8aed9d5dd3fe9848918cd998f055ce3deddd7",
    "ch01.ops.scalar": "sha256:fda9ff56813c525ddf954c37ac8ed328d2a78423af9040e353a1c1de465cfcb8",
    "ch01.ops.linear-combination": "sha256:423a60449c466f5e1b2dda613d720b0c93d2a231173d73eb31e9902c3fe3cf29",
    "ch01.inner.definitions": "sha256:87727eef228c62cb72f94048a50757360234607f01ffeac3b17df86a349bb9b5",
    "ch01.inner.applications": "sha256:3aa2fe524cec1f43b368869e8cb46e995dd3ddb19333fb885af528089911afaa",
    "ch01.inner.cauchy-schwarz": "sha256:264f34bd521f05f03bb0e268e35158e2895bc33227ce999fdfcd9f3a49daeb9e",
    "ch01.projection.definition": "sha256:66450b1edbf36646762a740be7239a41f6439eb97c2398cae640f8eaa8e10711",
    "ch01.proof.midline": "sha256:ef698dd38942fce8724934c6ab59f110933a256d13d16f4c56c4972526f542a9",
    "ch01.proof.centroid": "sha256:5de6421a77a36b5a797f748c0e6d8b522de19ca6bf4431183b80603e000a3b7c",
    "ch01.proof.parallelogram-diagonals": "sha256:8f1b8650bb4b211abe3036f0b58ef1f5d7b8f9670668602af8eb07a8b83decc3",
    "ch02.batch.inner-products": "sha256:e7dbeb49e88770e1d6a7a9bc32cae6e8984c938cc9e892af6fee405cba3a6c63",
    "ch02.batch.projection": "sha256:3cfa17678f2a1e8b07f6861e9e3d7b9b863da0bacc76151a834d23ac843117e3",
    "ch02.matrix.additive-distributivity": "sha256:c9740c08c8f0dadaddfb757f7b4927d7f33dae4f6c047335b6c17a048f6dee95",
    "ch02.matrix.row-column": "sha256:14bf287a1ad72e10340e2f71e69676f56e697e9c22ba2368c7b25de3a3066b87",
    "ch02.matrix.transformed-grid": "sha256:67c74bebb5afd024f977ff6b907f8838cad32bad2ffcfb061a24016da3829a3c",
    "ch02.matrix.stretch-rotate-scale": "sha256:c8d35032796a651d9a227938a6395b44e49839905150b972d8dff3a9d9e3379d",
    "ch02.matrix.composition": "sha256:efa1dd269ebe968fdc49db7cf500597b29f8b721d476250857f6192f7c620c41",
    "ch02.matrix.basis": "sha256:4825278e2c8287fa5eefcd0f74082f9d6759d7537575f1a1a986b417ff897a20",
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
    "ch03.det.high-dimensional-volume": "sha256:5744129f7bcfd9e0ae494768d9cc7a05943a23e4d4ab6df1e5a93d06de05ff47",
    "ch03.inverse.reverse-order": "sha256:d4ef9954671d74564885686c13a75e019650dd7065951ea654e37be5bcc794b8",
}


@pytest.fixture(scope="module")
def legacy_registry_bundle() -> tuple[object, object]:
    return catalog_registry(), bundled_teaching_store()


def test_all_legacy_topic_ids_and_plan_digests_are_frozen(legacy_registry_bundle) -> None:
    registry, store = legacy_registry_bundle
    legacy_ids = tuple(topic.id for topic in topic_entries() if topic.chapter_number <= 3)

    assert legacy_ids == tuple(LEGACY_PLAN_DIGESTS)
    assert len(legacy_ids) == 35
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
