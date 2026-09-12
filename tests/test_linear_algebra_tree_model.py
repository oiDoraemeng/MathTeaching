from PySide6.QtWidgets import QApplication, QTreeWidget

from linear_algebra.registry import catalog_registry
from ui.linear_algebra_tree_model import LinearAlgebraTreeModel


def test_tree_model_preserves_all_topics_in_source_order() -> None:
    _application = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    model = LinearAlgebraTreeModel(tree, catalog_registry())
    assert tree.topLevelItemCount() == 8
    assert model.visible_topic_ids() == tuple(topic.id for topic in catalog_registry().topics)


def test_search_keeps_cramer_ancestors_and_hides_unrelated_topics() -> None:
    _application = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    model = LinearAlgebraTreeModel(tree, catalog_registry())
    model.filter("克拉默")
    assert tree.topLevelItemCount() == 1
    assert "第3章" in tree.topLevelItem(0).text(0)
    assert model.visible_topic_ids() == ("ch03.cramer.area-ratio",)
    assert tree.topLevelItem(0).child(0).isExpanded()
