from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QTreeWidget

from linear_algebra.registry import catalog_registry
from ui.linear_algebra_tree_model import LinearAlgebraTreeModel


def test_tree_model_preserves_all_topics_in_source_order() -> None:
    _application = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    model = LinearAlgebraTreeModel(tree, catalog_registry())
    assert tree.topLevelItemCount() == 8
    assert model.visible_topic_ids() == tuple(topic.id for topic in catalog_registry().topics)
    assert model.default_expansion_is_restored()
    assert all(
        not tree.topLevelItem(index).child(child_index).isExpanded()
        for index in range(tree.topLevelItemCount())
        for child_index in range(tree.topLevelItem(index).childCount())
    )


def test_search_index_does_not_compile_every_topic_bundle() -> None:
    _application = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    registry = catalog_registry()

    with patch.object(type(registry), "resolve_bundle", side_effect=AssertionError("unexpected compile")):
        model = LinearAlgebraTreeModel(tree, registry)

    assert model.visible_topic_ids() == tuple(topic.id for topic in registry.topics)


def test_search_keeps_cramer_ancestors_and_hides_unrelated_topics() -> None:
    _application = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    model = LinearAlgebraTreeModel(tree, catalog_registry())
    model.filter("克拉默")
    assert tree.topLevelItemCount() == 1
    assert "第3章" in tree.topLevelItem(0).text(0)
    assert model.visible_topic_ids() == ("ch03.cramer.area-ratio",)
    assert tree.topLevelItem(0).child(0).isExpanded()
