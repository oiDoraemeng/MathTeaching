"""Search index coverage for structured teaching artifacts."""

from PySide6.QtWidgets import QApplication, QTreeWidget

from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.teaching_fixtures import projection_artifact_payload
from ui.linear_algebra_tree_model import LinearAlgebraTreeModel

def test_principal_axis_search_keeps_only_exact_topic_ancestors() -> None:
    app = QApplication.instance() or QApplication([])
    tree = QTreeWidget(); model = LinearAlgebraTreeModel(tree, catalog_registry())
    model.filter("主轴定理")
    assert model.visible_topic_ids() == ("ch08.principal-axis",)
    assert tree.topLevelItemCount() == 1 and tree.topLevelItem(0).childCount() == 1
    assert tree.topLevelItem(0).isExpanded() and tree.topLevelItem(0).child(0).isExpanded()

def test_gaussian_elimination_search_keeps_only_exact_topic_ancestors() -> None:
    app = QApplication.instance() or QApplication([])
    tree = QTreeWidget(); model = LinearAlgebraTreeModel(tree, catalog_registry())
    model.filter("高斯消元")
    assert model.visible_topic_ids() == ("ch05.gaussian-elimination",)
    assert tree.topLevelItemCount() == 1 and tree.topLevelItem(0).childCount() == 1
    assert tree.topLevelItem(0).isExpanded() and tree.topLevelItem(0).child(0).isExpanded()


def test_tree_search_includes_terms_only_present_in_derivation(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    artifact = projection_artifact_payload(with_residual=True)
    artifact["explanation"]["derivation"] = ["正交投影系数由内积商给出。"]  # type: ignore[index]
    store = TeachingArtifactStore(tmp_path)
    store.save_published(TeachingArtifact.from_dict(artifact))
    monkeypatch.setenv("MATH3D_TEACHING_ARTIFACT_ROOT", str(tmp_path))
    model = LinearAlgebraTreeModel(QTreeWidget(), catalog_registry())

    model.filter("内积商")

    assert model.visible_topic_ids() == ("ch01.projection.definition",)
