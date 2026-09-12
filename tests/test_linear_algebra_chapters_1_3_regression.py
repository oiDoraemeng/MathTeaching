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
    "ch01.ops.addition": "sha256:9c33ec3a773efac7847c10c1b8111de9bc6128356d8c5310213d1172663b7f50",
    "ch01.ops.subtraction": "sha256:62238fe208ef52738a47f4da271a78606a156cda753434d71263942db4ea191c",
    "ch01.ops.scalar": "sha256:75fe680cfe2f6d6e96e31a4fc8559faf22ddddf5060e80f43f45b3bafaa42cef",
    "ch01.ops.linear-combination": "sha256:8f9bd6a3a4d96905a4f3533aa1353ec2ad29fbc3ff7bb97935b4c5ebb1e6cac8",
    "ch01.ops.velocity": "sha256:e1db799cba0ba5c536b8e98f22c6c7abccc700367a122a485fef9b96d6e2564d",
    "ch01.ops.cross-product": "sha256:142288470a646a9a20874f0f1051cb3a9c822b21d23e040402fc27e0e2e9fa3e",
    "ch01.ops.scalar-triple": "sha256:c0414dd0b839079b99a9f71ca5a2f3fe28ed47a643e84ea4b69f3dfb127049bc",
    "ch01.inner.equivalence": "sha256:ced43992407a03d281cc418cb1d636accb71cd23d118aa9a526893c01651fc95",
    "ch01.inner.definitions": "sha256:49836b2df395d63b2a8a4cc9d553e74a7979bc85e5a47c2efa8a16dc1977dffb",
    "ch01.inner.applications": "sha256:ee3f5c88a5db962205526f0efa8065a67300e222547b0ca2a42e4850c641a221",
    "ch01.inner.cauchy-schwarz": "sha256:8a0cec89864e05d10ec3b2bf7e9a437339b9a431d16aa9b24104d4a25488ca2e",
    "ch01.inner.examples": "sha256:54589cae8aa925f6530d01bccb1c344aa1db0999da378223090a0e4645bbb418",
    "ch01.projection.definition": "sha256:5af33367c30bbfcc669acc1b9735b55849c7a5862de39610f239c2177387e295",
    "ch01.projection.properties": "sha256:2e23a78474f635acb6bf8698e762352e22c80d02c2902f4f4239b9e332643c61",
    "ch01.projection.force": "sha256:f78bfe55018e4737bc9b6981e829485527c61a990b78bdefee43af2e147ce044",
    "ch01.proof.method": "sha256:aa3da7ae3bde932981f63e070d15c7201a74301116bf4229d7837e6414808a07",
    "ch01.proof.midline": "sha256:51d83de76f0e1b347d8c8d63f116ea119a52b39e6f81a458bec2d485fb0817f4",
    "ch01.proof.centroid": "sha256:c6fe05aaf1597648817d256ddf31f2b416e64fe0e2b7df5521e0240d5d8eb880",
    "ch01.proof.parallelogram-diagonals": "sha256:cfa43995db0483591b37e57dc49283fed019bd6adb3a325e08c36daa131eff95",
    "ch01.high-dimensional.analogy": "sha256:219911982690061d76bf69125b0de9e829b54d037f96ad8c123c0a6002429d17",
    "ch02.batch.inner-products": "sha256:869dca859f1570685505939f3ecbec239b9ff312a4bc89d981801bc4608f6c9b",
    "ch02.batch.projection": "sha256:651f6b03a975bbf479bdb92b043799229bbc2c951fc0aef1999e743b46411d20",
    "ch02.matrix.additive-distributivity": "sha256:946c001f369bda2955f3ca9994616c5b93972b9142dce88a26c93faf1daf4ccf",
    "ch02.matrix.row-column": "sha256:a3c2ee35e5eba7a2fe3510c8b9226325d6efbea1fe305ce20b9295689637f584",
    "ch02.matrix.transformed-grid": "sha256:b7fd0ed4641f2685263e51303bf3cf50e28347ea4da06522dd08c25ff89a91f8",
    "ch02.matrix.stretch-rotate-scale": "sha256:45bbb745c6e5e11b01033f85d61dea04ed394107e306a9c01f1024939a772e5a",
    "ch02.matrix.composition": "sha256:b48ff6452845342c9ad5f6286d0d31ab27e2a1175dc667ff8800a2381eb6ece8",
    "ch02.matrix.basis": "sha256:6c1e74b1f1100cd8e40dcaddb2d3441f524f6a0f28c7d6949994cd0054001707",
    "ch02.matrix.powers": "sha256:610a009884caefff3e8993fc228a65c93ee92acf9ad66367fd87fddbc1cf58a3",
    "ch02.subspace.independence": "sha256:0cc8933557df45bf1ca52afb1379682b7b899941e6a5999869bd5e87853c9248",
    "ch02.subspace.rank": "sha256:6b37994f3b13ba7c83169b6344776c032596eca0b2a2db0df25302121e8b2430",
    "ch02.subspace.null": "sha256:62891894f9e01b74c04ff3b740af8b2073c0d6304015c8afdd0886ca13d0cc1a",
    "ch02.subspace.column": "sha256:48c71199f872603b0eccaf50f938e3871bf3f6d24adce7bd13f86bfcf21ee06c",
    "ch02.subspace.rank-nullity": "sha256:cf071cb5bab137e9666915f4678da8eac4e8bf133d39921dd2131f2270f576e0",
    "ch02.high-dimensional.analogy": "sha256:14f2c694bfc046c4c8675e78ada5e5cea656a17675d8cd4cf93449176f9093bb",
    "ch03.det.oriented-area": "sha256:7c1a0156921aafbf2a7f2e7f8e4a769196f103a826037356eb8574a123c66c45",
    "ch03.det.ad-bc": "sha256:8c1dc65f2efde7cad8451a867eb7a81ab7977dda69d683a72ed27dc8ce83f4fc",
    "ch03.det.sign-zero-one": "sha256:2e7b6839ff3f6da268514565b3ec60091511d3fb263311062622d0e019484d54",
    "ch03.det.examples": "sha256:d98d8757759564bbb24d8549217ce1e188c326a0066a1bf82cfdd3fff3924299",
    "ch03.det.row-swap": "sha256:cac64eb0b748e2514d099a7c44f72d6401366ce00c9c5643ada26921304e72d3",
    "ch03.det.scaling": "sha256:48071122621c703f14a27096f32878699e30b9033e8d12e6fe1c2190961685ee",
    "ch03.det.shear": "sha256:f955248683a5bf6c3dab44a0cac8f3f8d35aabc225448afa364ec64313935334",
    "ch03.det.multiplicativity": "sha256:e9720722e8844abce9e399e67c07d40fb632a84bfae44096d792f85d3ec6a303",
    "ch03.cramer.area-ratio": "sha256:7d33ba2c30549b5dd2272692446dba20407ce0f11a4411d32e27321ca59bf110",
    "ch03.inverse.undo": "sha256:28ec0b3a7e10110845066adb6749507713d2a08bbfe036a05fdf8ad9640b6536",
    "ch03.inverse.formula": "sha256:419e4bf15d1e2dba73018b7a1710691f1391f0477c60b2aeba8c35b3bac79bc5",
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
    assert len(legacy_ids) == 54
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
