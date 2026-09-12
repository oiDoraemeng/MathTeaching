from dataclasses import replace

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtWidgets import QApplication, QToolButton, QWidget

from ui.linear_algebra_dialog import LinearAlgebraDialog
from linear_algebra.teaching.model import TeachingArtifact
from tests.teaching_fixtures import composition_artifact_payload


def make_linear_algebra_dialog() -> LinearAlgebraDialog:
    _application = QApplication.instance() or QApplication([])
    return LinearAlgebraDialog()


def test_default_tree_has_three_open_chapters_and_closed_sections() -> None:
    dialog = make_linear_algebra_dialog()
    assert dialog.tree.topLevelItemCount() == 8
    for index in range(3):
        chapter = dialog.tree.topLevelItem(index)
        assert chapter.isExpanded()
        assert chapter.childCount() > 0
        assert all(chapter.child(i).isExpanded() for i in range(chapter.childCount()))


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


def test_activating_topic_keeps_catalog_visible_without_inline_explanation() -> None:
    dialog = make_linear_algebra_dialog()
    dialog.open_at(QRect(20, 20, 1, 1).topLeft())
    topic = dialog.tree.topLevelItem(0).child(0).child(0)

    dialog.activate_item(topic)
    QApplication.processEvents()

    assert dialog.isVisible()
    assert not dialog.content_scroll.isVisible()
    dialog.close()


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
    assert dialog.tree.topLevelItemCount() == 8
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


def test_structured_teaching_artifact_renders_math_layers() -> None:
    dialog = make_linear_algebra_dialog()
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    dialog.content_view.set_content(artifact.explanation)

    assert dialog.content_view.definition_label.isHidden() is False
    assert "先计算 Bx" in dialog.content_view.derivation_label.text()
    assert dialog.content_view.examples_label.isHidden() is True
    assert dialog.content_view.analogy_boundary_label.isHidden() is True
    assert dialog.content_view.read_guide_label.isHidden() is True
    dialog.close()


def test_structured_teaching_artifact_shows_analogy_boundary_when_present() -> None:
    dialog = make_linear_algebra_dialog()
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    structured = replace(
        artifact.explanation,
        analogy_boundary="二维图像只保留可见几何直觉，高维情形不再依赖同一幅图。",
        read_guide=("先看输入，再看中间结果，最后核对终点。",),
    )

    dialog.content_view.set_content(replace(artifact, explanation=structured).explanation)

    assert dialog.content_view.analogy_boundary_label.isHidden() is False
    assert dialog.content_view.read_guide_label.isHidden() is False
    dialog.close()


def test_external_click_closes_popup_but_reactivation_cancels_pending_close() -> None:
    host = QWidget()
    outside_button = QToolButton(host)
    dialog = make_linear_algebra_dialog()
    anchor = QRect(20, 20, 1, 1).topLeft()
    dialog.open_at(anchor)
    dialog.eventFilter(outside_button, QEvent(QEvent.Type.MouseButtonPress))
    dialog.open_at(anchor)
    QApplication.processEvents()
    assert dialog.isVisible()

    dialog.eventFilter(outside_button, QEvent(QEvent.Type.MouseButtonPress))
    QApplication.processEvents()
    assert not dialog.isVisible()


def test_reopening_popup_does_not_duplicate_chapters_or_reset_expansion() -> None:
    dialog = make_linear_algebra_dialog()
    anchor = QRect(20, 20, 1, 1).topLeft()
    dialog.open_at(anchor)
    chapter = dialog.tree.topLevelItem(1)
    section = chapter.child(0)
    section_id = next(
        node.children[0]
        for node in dialog.registry.nodes
        if node.id == "ch02"
    )
    section.setExpanded(True)
    assert dialog.tree.topLevelItemCount() == 8

    dialog.hide()
    dialog.open_at(anchor)
    QApplication.processEvents()

    chapter_two = dialog.tree_model.item_for("ch02")
    assert chapter_two is not None
    assert dialog.tree.topLevelItemCount() == 8
    assert sum(
        dialog.tree.topLevelItem(index) is chapter_two
        for index in range(dialog.tree.topLevelItemCount())
    ) == 1
    restored_section = dialog.tree_model.item_for(section_id)
    assert restored_section is not None and restored_section.isExpanded()
    assert dialog.tree.viewport().isEnabled()
    dialog.close()


def test_topic_click_keeps_popup_open_when_scene_mode_is_synchronized() -> None:
    dialog = make_linear_algebra_dialog()
    dialog.open_at(QRect(20, 20, 1, 1).topLeft())
    dialog.requested.connect(lambda _topic_id: None)
    topic = dialog.tree.topLevelItem(0).child(0).child(0)

    dialog.activate_item(topic)
    QApplication.processEvents()

    assert dialog.isVisible()
    assert not dialog.content_scroll.isVisible()
    dialog.close()
