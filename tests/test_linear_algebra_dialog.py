from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication

from ui.linear_algebra_dialog import LinearAlgebraDialog


def make_linear_algebra_dialog() -> LinearAlgebraDialog:
    _application = QApplication.instance() or QApplication([])
    return LinearAlgebraDialog()


def test_default_tree_has_three_open_chapters_and_closed_sections() -> None:
    dialog = make_linear_algebra_dialog()
    assert dialog.tree.topLevelItemCount() == 3
    for index in range(3):
        chapter = dialog.tree.topLevelItem(index)
        assert chapter.isExpanded()
        assert chapter.childCount() > 0
        assert all(not chapter.child(i).isExpanded() for i in range(chapter.childCount()))


def test_branch_click_does_not_emit_but_topic_leaf_does() -> None:
    dialog = make_linear_algebra_dialog()
    received: list[str] = []
    dialog.requested.connect(received.append)
    chapter = dialog.tree.topLevelItem(0)
    dialog.activate_item(chapter)
    assert received == []
    topic = chapter.child(0).child(0)
    dialog.activate_item(topic)
    assert received == [topic.data(0, Qt.ItemDataRole.UserRole)]


def test_search_and_expansion_controls_are_deterministic() -> None:
    dialog = make_linear_algebra_dialog()
    dialog.search_edit.setText("克拉默")
    assert dialog.tree_model.visible_topic_ids() == ("ch03.cramer.area-ratio",)
    dialog.search_edit.clear()
    dialog.expand_all()
    assert dialog.tree_model.all_branches_expanded()
    dialog.collapse_to_chapters()
    assert dialog.tree_model.all_chapters_collapsed()
    dialog.search_edit.clear()
    assert dialog.tree.topLevelItemCount() == 3
    assert dialog.tree_model.default_expansion_is_restored()


def test_popup_controls_have_accessible_names_and_object_names() -> None:
    dialog = make_linear_algebra_dialog()
    assert dialog.search_edit.objectName() == "linearAlgebraSearch"
    assert dialog.search_edit.placeholderText() == "搜索讲义目录"
    assert dialog.tree.objectName() == "linearAlgebraTree"
    assert dialog.expand_button.objectName() == "linearAlgebraExpandButton"
    assert dialog.collapse_button.objectName() == "linearAlgebraCollapseButton"
    assert dialog.expand_button.toolTip() == "展开全部目录"
    assert dialog.collapse_button.toolTip() == "折叠到章级"


def test_content_is_owned_by_a_widget_resizable_scroll_area() -> None:
    dialog = make_linear_algebra_dialog()
    assert dialog.content_scroll.widget() is dialog.content_view
    assert dialog.content_scroll.widgetResizable()
    assert dialog.content_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_show_limits_dialog_to_eighty_percent_of_available_screen(monkeypatch) -> None:
    dialog = make_linear_algebra_dialog()

    class FakeScreen:
        def availableGeometry(self):
            return QRect(0, 0, 1200, 1000)

    monkeypatch.setattr(dialog, "screen", lambda: FakeScreen())
    dialog.show()
    QApplication.processEvents()
    assert dialog.maximumHeight() == 800
    assert dialog.height() <= 800
    dialog.close()


def test_long_content_scrolls_inside_the_dialog() -> None:
    dialog = make_linear_algebra_dialog()
    topic = dialog.registry.topics[0]
    explanation = dialog.registry.get_explanation(topic.explanation_id)
    dialog.content_view.set_content(explanation)
    dialog.content_view.steps_label.setText("\n".join("这是很长的讲义内容。" * 40 for _ in range(80)))
    dialog.content_scroll.show()
    dialog.resize(480, 600)
    dialog.show()
    QApplication.processEvents()
    assert dialog.content_scroll.widgetResizable()
    assert dialog.content_scroll.verticalScrollBar().maximum() > 0
    dialog.close()


def test_short_content_does_not_force_a_scrollbar() -> None:
    dialog = make_linear_algebra_dialog()
    topic = dialog.registry.topics[0]
    dialog.content_view.set_content(dialog.registry.get_explanation(topic.explanation_id))
    dialog.content_scroll.show()
    dialog.resize(900, 900)
    dialog.show()
    QApplication.processEvents()
    assert dialog.content_scroll.verticalScrollBar().maximum() == 0
    dialog.close()
