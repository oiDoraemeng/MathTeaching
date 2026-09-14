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
    "ch01.vector.point-distinction": "sha256:77b53ff6306c6c10b9e0bbd563090f7b8f99409755813392b4b9d926d25876d3",
    "ch01.vector.coordinate-system": "sha256:1331ddb2299591d9cdb1c01c2f9ae24e5130950d066b19930c1fe57889984476",
    "ch01.vector.direction-examples": "sha256:2cdbc6ecdbf5509bc686f5e855b0892009631f03be0b4e13d9520e809aba0e17",
    "ch01.ops.addition": "sha256:28d36cbf27d448be3b41b99c1849378e1bb7f03acb737f3118b2a9e1b4bb86ae",
    "ch01.ops.subtraction": "sha256:86739d3926804242fe1ae18947e8aed9d5dd3fe9848918cd998f055ce3deddd7",
    "ch01.ops.scalar": "sha256:fda9ff56813c525ddf954c37ac8ed328d2a78423af9040e353a1c1de465cfcb8",
    "ch01.ops.linear-combination": "sha256:423a60449c466f5e1b2dda613d720b0c93d2a231173d73eb31e9902c3fe3cf29",
    "ch01.inner.definitions": "sha256:59eeafbf679929d3313676abf48a165bc60bf54ec845a74030e6881e7416087f",
    "ch01.inner.applications": "sha256:3aa2fe524cec1f43b368869e8cb46e995dd3ddb19333fb885af528089911afaa",
    "ch01.inner.cauchy-schwarz": "sha256:264f34bd521f05f03bb0e268e35158e2895bc33227ce999fdfcd9f3a49daeb9e",
    "ch01.projection.definition": "sha256:66450b1edbf36646762a740be7239a41f6439eb97c2398cae640f8eaa8e10711",
    "ch01.projection.properties": "sha256:08d7274f46c8ee0ebeef7ea8f7b111f9b47e2b9b350f4df93ba3cae10dfcff21",
    "ch01.projection.force": "sha256:95037f3eb47fc9014e6816a2d2603e029dbd6fb02579c830e29a69726a32bb42",
    "ch01.proof.midline": "sha256:c4f3fbb033f3234d55203e05a7b48289e0cd2b01d4f3b5430880a9f533af5640",
    "ch01.proof.centroid": "sha256:5de6421a77a36b5a797f748c0e6d8b522de19ca6bf4431183b80603e000a3b7c",
    "ch01.proof.parallelogram-diagonals": "sha256:8f1b8650bb4b211abe3036f0b58ef1f5d7b8f9670668602af8eb07a8b83decc3",
    "ch02.batch.inner-products": "sha256:4e2581e44db8bb10d0dec2592412cc7e004556681833bd38bd71170a55e6b361",
    "ch02.batch.projection": "sha256:2b2db32eabf64b601d8f306beecde78dbce4dd703d31f55d370666bbedaa0009",
    "ch02.matrix.additive-distributivity": "sha256:4c2b51cff78dca33ebd36d565448ea9c0a8a2772c45e632233df8a89dab124e3",
    "ch02.matrix.row-column": "sha256:4a0040884569fb39c30fd5fd0c3e6fe4c4e8bb957023346035c1f7f402bd7843",
    "ch02.matrix.transformed-grid": "sha256:ee06cd31ef21c5b1962fbe61de210438f31b6f4abd7ac2b3c59cfbb0b6c0c9a3",
    "ch02.matrix.stretch-rotate-scale": "sha256:5427c1a1cf66dc76ba1b6b4fb0916748a41a5b6ce4293f6133e3355b117a4272",
    "ch02.matrix.composition": "sha256:0b9cb46b9db85818f268d13115fe7f38ebc58764bbd4f28fd166f9a1f04a3199",
    "ch02.matrix.basis": "sha256:aca7fe950f2be71a0847c51ea577c55febaeb1b7a058553ca17abedbbf22fbbb",
    "ch02.matrix.powers": "sha256:03187262de2817e38036a9393fdecd4a7b284e79425b6c2a69a81747eda19a1f",
    "ch02.subspace.independence": "sha256:b1f8fa3c756f422838cb6e297620863d4fde5807ff8567ef25251eb947d8026f",
    "ch02.subspace.rank": "sha256:09d5e3a361ffda2952b4e23e6c6ea507551d31ece5b4922563d9ba0700807c68",
    "ch02.subspace.null": "sha256:182d4bcaa33c5ab213767beaaa0d26b1ce0045937b582ccf8743bf30bf031fb5",
    "ch02.subspace.column": "sha256:0da4b6aad9abee4404d35828c5d95a9fe42f5c0359f49e577fab677eae28e4dc",
    "ch02.subspace.rank-nullity": "sha256:2a953bb12ec5661096e29c480db7974787aacc4a53829c60e7e865bb3e099f3a",
    "ch02.high-dimensional.analogy": "sha256:924547c443bc5c575239307460fd9bf9926b6d8127ff425bbc1645850fdaae88",
    "ch03.det.oriented-area": "sha256:7c1a0156921aafbf2a7f2e7f8e4a769196f103a826037356eb8574a123c66c45",
    "ch03.det.ad-bc": "sha256:da9a6a5c2740e5b469867237d42e6ba70e2aebbc625c52cca667e56750192623",
    "ch03.det.sign-zero-one": "sha256:2e7b6839ff3f6da268514565b3ec60091511d3fb263311062622d0e019484d54",
    "ch03.det.examples": "sha256:746140e62cc59c2c4bca9eead3e6d80bdf16f2184606cb15fd0e41e4a231d774",
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
    assert len(legacy_ids) == 47
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
