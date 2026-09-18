"""三维场景的浮动工具栏。"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QFrame, QToolButton, QWidget

from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import ThemeName, apply_drop_shadow, apply_rounded_overlay


class ThreeDGeometryToolbar(QFrame):
    """只承载当前三维场景可用操作的垂直工具栏。

    向量不是画布绘制工具：点击后由主窗口把焦点交给代数面板中的
    坐标输入框。因此这里仅发出请求信号，不保存任何鼠标交互状态。
    """

    vector_requested = Signal()
    annotation_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget, theme: ThemeName = "light") -> None:
        super().__init__(parent)
        self._theme: ThemeName = theme
        self.setObjectName("threeDGeometryToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        apply_drop_shadow(self, "overlay", theme)
        apply_rounded_overlay(self, "md", theme)

        layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self._layout = layout
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.vector_button = self._button("vector", "添加向量", "threeDVectorToolButton", checkable=True)
        self.annotation_button = self._button("type", "标记", "threeDAnnotationToolButton", checkable=True)
        self.undo_button = self._button("undo-2", "撤销", "threeDUndoToolButton")
        self.redo_button = self._button("redo-2", "恢复", "threeDRedoToolButton")
        layout.addWidget(self.vector_button)
        layout.addWidget(self.annotation_button)
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)

        self.vector_button.clicked.connect(self.vector_requested)
        self.annotation_button.clicked.connect(self.annotation_requested)
        self.undo_button.clicked.connect(self.undo_requested)
        self.redo_button.clicked.connect(self.redo_requested)
        self.adjustSize()
        self.set_history_state(can_undo=False, can_redo=False)

    def set_vector_active(self, active: bool) -> None:
        """Reflect whether the algebra-panel coordinate field is awaiting input."""
        self.vector_button.setChecked(active)

    def set_annotation_active(self, active: bool) -> None:
        """Reflect whether the next 3-D viewport click will place a mark."""
        self.annotation_button.setChecked(active)

    def set_history_state(self, *, can_undo: bool, can_redo: bool) -> None:
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def set_theme(self, theme: ThemeName) -> None:
        self._theme = theme
        apply_drop_shadow(self, "overlay", theme)
        retint_icons(self, theme)

    def position_in_host(self, host_rect: QRect | None = None) -> None:
        """Place this toolbar at the left centre of the viewport host.

        The toolbar is anchored to the whole viewport, so switching the focused
        scene pane never moves it.
        """
        host = self.parentWidget()
        if host is None:
            return
        self.adjustSize()
        target = host_rect if host_rect is not None else host.rect()
        self.move(
            target.x() + 12,
            target.y() + max(8, (target.height() - self.height()) // 2),
        )

    def _button(
        self, icon_name: str, tooltip: str, object_name: str, *, checkable: bool = False
    ) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setCheckable(checkable)
        apply_icon(button, icon_name, icon_color(self._theme), icon_size=16, hit_size=36)
        return button
