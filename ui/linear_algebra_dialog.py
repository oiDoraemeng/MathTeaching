"""Searchable lecture-tree popup for linear algebra topics."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLineEdit, QScrollArea, QToolButton, QTreeWidget, QVBoxLayout, QWidget

from linear_algebra.registry import CurriculumRegistry, catalog_registry
from ui.icons import apply_icon, icon_color
from ui.linear_algebra_content_view import LinearAlgebraContentView
from ui.linear_algebra_tree_model import LinearAlgebraTreeModel
from ui.tokens import apply_rounded_overlay


class LectureSearchEdit(QLineEdit):
    reset_requested = Signal()

    def clear(self) -> None:
        had_text = bool(self.text())
        super().clear()
        if not had_text:
            self.reset_requested.emit()


class LinearAlgebraDialog(QDialog):
    requested = Signal(str)

    def __init__(self, parent: QWidget | None = None, *, registry: CurriculumRegistry | None = None) -> None:
        super().__init__(parent)
        self.registry = registry or catalog_registry()
        self.setObjectName("linearAlgebraDialog")
        self.setWindowTitle("线性代数")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        apply_rounded_overlay(self, "lg")
        self.setMinimumSize(420, 460)
        self.resize(480, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.search_edit = LectureSearchEdit(self)
        self.search_edit.setObjectName("linearAlgebraSearch")
        self.search_edit.setPlaceholderText("搜索讲义目录")
        self.search_edit.setAccessibleName("搜索线性代数讲义目录")
        self.expand_button = QToolButton(self)
        self.expand_button.setObjectName("linearAlgebraExpandButton")
        self.expand_button.setToolTip("展开全部目录")
        self.expand_button.setAccessibleName("展开全部目录")
        apply_icon(self.expand_button, "chevrons-down", icon_color(), icon_size=16, hit_size=32)
        self.collapse_button = QToolButton(self)
        self.collapse_button.setObjectName("linearAlgebraCollapseButton")
        self.collapse_button.setToolTip("折叠到章级")
        self.collapse_button.setAccessibleName("折叠到章级")
        apply_icon(self.collapse_button, "chevrons-up", icon_color(), icon_size=16, hit_size=32)
        controls.addWidget(self.search_edit, 1)
        controls.addWidget(self.expand_button)
        controls.addWidget(self.collapse_button)
        layout.addLayout(controls)

        self.tree = QTreeWidget(self)
        self.tree.setObjectName("linearAlgebraTree")
        self.tree.setAccessibleName("线性代数讲义目录")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setExpandsOnDoubleClick(False)
        layout.addWidget(self.tree, 1)
        self.content_view = LinearAlgebraContentView(self)
        self.content_scroll = QScrollArea(self)
        self.content_scroll.setObjectName("linearAlgebraContentScroll")
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.content_scroll.setWidget(self.content_view)
        self.content_scroll.hide()
        layout.addWidget(self.content_scroll)
        self.tree_model = LinearAlgebraTreeModel(self.tree, self.registry)

        self.search_edit.textChanged.connect(self.tree_model.filter)
        self.search_edit.reset_requested.connect(self.tree_model.restore_default_expansion)
        self.expand_button.clicked.connect(self.expand_all)
        self.collapse_button.clicked.connect(self.collapse_to_chapters)
        self.tree.itemClicked.connect(lambda item, _column: self.activate_item(item))

        self._show_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_animation.setDuration(150)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._outside_click_timer = QTimer(self)
        self._outside_click_timer.setSingleShot(True)
        self._outside_click_timer.timeout.connect(self.hide)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def activate_item(self, item) -> None:
        self._outside_click_timer.stop()
        topic_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not topic_id:
            item.setExpanded(not item.isExpanded())
            return
        # The catalog only selects a topic. The main window publishes its
        # explanation after the corresponding scene has loaded successfully.
        self.content_scroll.hide()
        self.show()
        self.raise_()
        self.requested.emit(str(topic_id))

    def expand_all(self) -> None:
        self.tree_model.expand_all()

    def collapse_to_chapters(self) -> None:
        self.tree_model.collapse_to_chapters()

    def open_at(self, anchor: QPoint) -> None:
        self._outside_click_timer.stop()
        if self.tree_model.needs_filter(self.search_edit.text()):
            self.tree_model.filter(self.search_edit.text())
        was_visible = self.isVisible()
        self.move(anchor)
        self.raise_()
        if was_visible:
            self.activateWindow()
            return
        self.setWindowOpacity(0.0)
        self.show()
        self._show_animation.stop()
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(1.0)
        self._show_animation.start()
        self.search_edit.setFocus()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt 事件名
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            self.setMaximumHeight(int(screen.availableGeometry().height() * 0.8))
        super().showEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.isVisible()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and watched is not self
            and not self.isAncestorOf(watched)
        ):
            self._outside_click_timer.start(0)
        return super().eventFilter(watched, event)
