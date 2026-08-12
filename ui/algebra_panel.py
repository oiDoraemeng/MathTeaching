"""Compact algebra-layer list and non-modal per-surface controls."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from MathInputWidget import FormulaEditorPopup
from models.surface_layer import SurfaceLayer


_SURFACE_KINDS = (
    ("显式", "explicit"),
    ("隐式", "implicit"),
    ("参数", "parametric"),
)
_PLACEHOLDERS = {
    "explicit": "z = x^2 - y^2",
    "implicit": "x^2 + y^2 + z^2 = 1",
    "parametric": "(u*cos(v), u*sin(v), v); u=[0,1], v=[-1,1]",
}


class LayerSettingsPopup(QDialog):
    """Non-modal display controls for one layer."""

    kind_selected = Signal(str, str)
    intersections_changed = Signal(str, bool)
    color_changed = Signal(str, str)
    opacity_changed = Signal(str, float)
    range_changed = Signal(str, float)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layer_id: str | None = None
        self._color_dialog: QColorDialog | None = None
        self.setObjectName("layerSettingsPopup")
        self.setWindowTitle("曲面设置")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(QLabel("曲面设置"))
        header.addStretch()
        close_button = QToolButton(self)
        close_button.setText("x")
        close_button.setToolTip("关闭设置")
        close_button.clicked.connect(self.hide)
        header.addWidget(close_button)
        layout.addLayout(header)

        form_row = QHBoxLayout()
        form_row.addWidget(QLabel("形式"))
        self.kind_combo = QComboBox(self)
        for label, value in _SURFACE_KINDS:
            self.kind_combo.addItem(label, value)
        form_row.addWidget(self.kind_combo, 1)
        self.kind_combo.setToolTip("下次编辑公式时采用此表达形式")
        layout.addLayout(form_row)

        self.intersections_check = QCheckBox("显示交线", self)
        layout.addWidget(self.intersections_check)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("颜色"))
        self.color_button = QToolButton(self)
        self.color_button.setFixedSize(36, 26)
        self.color_button.setToolTip("选择曲面颜色")
        color_row.addWidget(self.color_button)
        color_row.addStretch()
        layout.addLayout(color_row)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("透明度"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.opacity_slider.setRange(5, 100)
        self.opacity_value = QLabel(self)
        self.opacity_value.setMinimumWidth(34)
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_value)
        layout.addLayout(opacity_row)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("范围"))
        self.range_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.range_slider.setRange(10, 50)
        self.range_value = QLabel(self)
        self.range_value.setMinimumWidth(38)
        range_row.addWidget(self.range_slider, 1)
        range_row.addWidget(self.range_value)
        layout.addLayout(range_row)

        self.delete_button = QPushButton("删除函数", self)
        self.delete_button.setToolTip("删除此曲面及其交线")
        layout.addWidget(self.delete_button)

        self.kind_combo.currentIndexChanged.connect(self._emit_kind)
        self.intersections_check.toggled.connect(self._emit_intersections)
        self.color_button.clicked.connect(self._choose_color)
        self.opacity_slider.valueChanged.connect(self._emit_opacity)
        self.range_slider.valueChanged.connect(self._update_range_label)
        self.range_slider.sliderReleased.connect(self._emit_range)
        self.delete_button.clicked.connect(self._request_delete)

    def open_layer(self, layer: SurfaceLayer, anchor: QPoint | None, kind: str | None = None) -> None:
        """Populate controls for a layer and show near its settings button."""
        self._layer_id = layer.id
        self.kind_combo.blockSignals(True)
        self.intersections_check.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.range_slider.blockSignals(True)
        try:
            index = self.kind_combo.findData(kind or layer.kind)
            self.kind_combo.setCurrentIndex(index if index >= 0 else 1)
            self.intersections_check.setChecked(layer.intersections_visible)
            self.opacity_slider.setValue(round(layer.opacity * 100))
            self.range_slider.setValue(round(layer.range_scale * 10))
        finally:
            self.kind_combo.blockSignals(False)
            self.intersections_check.blockSignals(False)
            self.opacity_slider.blockSignals(False)
            self.range_slider.blockSignals(False)
        self.opacity_value.setText(f"{self.opacity_slider.value()}%")
        self._update_range_label(self.range_slider.value())
        self._set_color_button(layer.color)
        self.show()
        if anchor is not None:
            self.move(anchor)

    def _emit_kind(self) -> None:
        if self._layer_id is not None:
            self.kind_selected.emit(self._layer_id, str(self.kind_combo.currentData()))

    def _emit_intersections(self, visible: bool) -> None:
        if self._layer_id is not None:
            self.intersections_changed.emit(self._layer_id, visible)

    def _choose_color(self) -> None:
        if self._layer_id is None:
            return
        dialog = QColorDialog(QColor(self.color_button.property("layerColor")), self)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.colorSelected.connect(self._emit_color)
        dialog.finished.connect(dialog.deleteLater)
        self._color_dialog = dialog
        dialog.show()

    def _emit_color(self, color: QColor) -> None:
        if self._layer_id is None or not color.isValid():
            return
        color_name = color.name()
        self._set_color_button(color_name)
        self.color_changed.emit(self._layer_id, color_name)

    def _set_color_button(self, color: str) -> None:
        self.color_button.setProperty("layerColor", color)
        self.color_button.setStyleSheet(
            f"background: {color}; border: 1px solid #687385; border-radius: 3px;"
        )

    def _emit_opacity(self, value: int) -> None:
        self.opacity_value.setText(f"{value}%")
        if self._layer_id is not None:
            self.opacity_changed.emit(self._layer_id, value / 100.0)

    def _update_range_label(self, value: int) -> None:
        self.range_value.setText(f"x{value / 10:.1f}")

    def _emit_range(self) -> None:
        if self._layer_id is not None:
            self.range_changed.emit(self._layer_id, self.range_slider.value() / 10.0)

    def _request_delete(self) -> None:
        if self._layer_id is not None:
            layer_id = self._layer_id
            self.hide()
            self.delete_requested.emit(layer_id)


class IntersectionPopup(QDialog):
    """Non-modal manual pair selector used when automatic intersections are off."""

    requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("手动计算交线")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.first_combo = QComboBox(self)
        self.second_combo = QComboBox(self)
        button = QPushButton("计算", self)
        button.clicked.connect(self._request)
        layout.addWidget(self.first_combo)
        layout.addWidget(self.second_combo)
        layout.addWidget(button)

    def set_layers(self, layers: Iterable[SurfaceLayer]) -> None:
        current_first = self.first_combo.currentData()
        current_second = self.second_combo.currentData()
        for combo, current in ((self.first_combo, current_first), (self.second_combo, current_second)):
            combo.blockSignals(True)
            combo.clear()
            for layer in layers:
                combo.addItem(layer.name, layer.id)
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
        if self.second_combo.count() > 1 and self.second_combo.currentIndex() == self.first_combo.currentIndex():
            self.second_combo.setCurrentIndex(1)

    def open_at(self, anchor: QPoint) -> None:
        self.show()
        self.move(anchor)

    def _request(self) -> None:
        first_id = str(self.first_combo.currentData() or "")
        second_id = str(self.second_combo.currentData() or "")
        if first_id and second_id and first_id != second_id:
            self.requested.emit(first_id, second_id)


class LayerRow(QFrame):
    """One fixed-height row: visibility, formula and per-layer settings."""

    edit_requested = Signal(str, str, str, object)
    settings_requested = Signal(str, object)
    visibility_changed = Signal(str, bool)

    def __init__(self, layer: SurfaceLayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layer_id = layer.id
        self.setObjectName("algebraLayerRow")
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self.visible_button = QToolButton(self)
        self.visible_button.setCheckable(True)
        self.visible_button.setChecked(layer.visible)
        self.visible_button.setFixedSize(28, 28)
        self._set_visibility_icon(layer.visible)
        self.expression_button = QPushButton(layer.latex or layer.expression, self)
        self.expression_button.setObjectName("layerExpressionButton")
        self.expression_button.setFlat(True)
        self.expression_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.expression_button.setToolTip(layer.latex or layer.expression)
        self.settings_button = QToolButton(self)
        self.settings_button.setText("⚙")
        self.settings_button.setFixedSize(28, 28)
        self.settings_button.setToolTip("此函数的显示、交线和范围设置")
        layout.addWidget(self.visible_button)
        layout.addWidget(self.expression_button, 1)
        layout.addWidget(self.settings_button)

        self.visible_button.toggled.connect(self._emit_visibility)
        self.expression_button.clicked.connect(
            lambda: self.edit_requested.emit(
                self.layer_id,
                layer.kind,
                layer.latex or layer.expression,
                self.expression_button.mapToGlobal(QPoint(0, self.expression_button.height() + 4)),
            )
        )
        self.settings_button.clicked.connect(
            lambda: self.settings_requested.emit(
                self.layer_id,
                self.settings_button.mapToGlobal(QPoint(0, self.settings_button.height() + 4)),
            )
        )

    def _emit_visibility(self, visible: bool) -> None:
        self._set_visibility_icon(visible)
        self.visibility_changed.emit(self.layer_id, visible)

    def _set_visibility_icon(self, visible: bool) -> None:
        self.visible_button.setText("●" if visible else "○")
        self.visible_button.setToolTip("隐藏此曲面" if visible else "显示此曲面")


class AlgebraPanel(QFrame):
    """Compact Chinese algebra list with floating formula and settings editors."""

    add_requested = Signal(str, str)
    update_requested = Signal(str, str, str)
    delete_requested = Signal(str)
    visibility_changed = Signal(str, bool)
    intersections_visibility_changed = Signal(str, bool)
    color_changed = Signal(str, str)
    opacity_changed = Signal(str, float)
    range_changed = Signal(str, float)
    builtin_requested = Signal(str)
    lighting_requested = Signal()
    auto_intersections_changed = Signal(bool)
    manual_intersection_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rows: dict[str, LayerRow] = {}
        self._layers: list[SurfaceLayer] = []
        self._active_layer_id: str | None = None
        self._draft_kinds: dict[str, str] = {}
        self.setObjectName("algebraPanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(7)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        title = QLabel("代数")
        title.setObjectName("algebraTitle")
        toolbar.addWidget(title)
        toolbar.addStretch()
        self.new_formula_button = self._tool_button("＋", "新建函数")
        self.builtin_button = self._tool_button("二次", "添加内置二次曲面")
        self.intersection_button = self._tool_button("交线", "交线计算方式")
        self.lighting_button = self._tool_button("⚙", "高级光照和材质")
        toolbar.addWidget(self.new_formula_button)
        toolbar.addWidget(self.builtin_button)
        toolbar.addWidget(self.intersection_button)
        toolbar.addWidget(self.lighting_button)
        layout.addLayout(toolbar)

        self.builtin_menu = QMenu(self)
        self.builtin_button.setMenu(self.builtin_menu)
        self.intersection_menu = QMenu(self)
        self.auto_intersections_action = QAction("自动生成交线", self, checkable=True)
        self.auto_intersections_action.setChecked(True)
        self.manual_intersection_action = QAction("手动选择两个曲面", self)
        self.intersection_menu.addAction(self.auto_intersections_action)
        self.intersection_menu.addSeparator()
        self.intersection_menu.addAction(self.manual_intersection_action)
        self.intersection_button.setMenu(self.intersection_menu)

        self.rows_container = QWidget(self)
        self.rows_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        self.rows_layout.addStretch()
        self.rows_scroll = QScrollArea(self)
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rows_scroll.setWidget(self.rows_container)
        layout.addWidget(self.rows_scroll, 1)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("algebraStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.formula_popup = FormulaEditorPopup(self)
        self.settings_popup = LayerSettingsPopup(self)
        self.intersection_popup = IntersectionPopup(self)
        self.new_formula_button.clicked.connect(self._open_new_formula)
        self.lighting_button.clicked.connect(self.lighting_requested)
        self.auto_intersections_action.toggled.connect(self.auto_intersections_changed)
        self.manual_intersection_action.triggered.connect(self._open_manual_intersection_popup)
        self.formula_popup.submitted.connect(self._submit_formula)
        self.formula_popup.dismissed.connect(self._cancel_formula_edit)
        self.formula_popup.kindChanged.connect(self._update_formula_placeholder)
        self.settings_popup.kind_selected.connect(self._set_draft_kind)
        self.settings_popup.intersections_changed.connect(self.intersections_visibility_changed)
        self.settings_popup.color_changed.connect(self.color_changed)
        self.settings_popup.opacity_changed.connect(self.opacity_changed)
        self.settings_popup.range_changed.connect(self.range_changed)
        self.settings_popup.delete_requested.connect(self.delete_requested)
        self.intersection_popup.requested.connect(self.manual_intersection_requested)

    @staticmethod
    def _tool_button(text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedHeight(28)
        return button

    def set_builtin_surfaces(self, surfaces: Iterable[tuple[str, str]]) -> None:
        """Load the compact built-in surface menu."""
        self.builtin_menu.clear()
        for surface_id, name in surfaces:
            action = self.builtin_menu.addAction(name)
            action.triggered.connect(
                lambda _checked=False, identifier=surface_id: self.builtin_requested.emit(identifier)
            )

    def set_layers(self, layers: Iterable[SurfaceLayer]) -> None:
        """Refresh only the compact layer rows and active popup choices."""
        self._layers = list(layers)
        self._draft_kinds = {
            layer_id: kind
            for layer_id, kind in self._draft_kinds.items()
            if any(layer.id == layer_id for layer in self._layers)
        }
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.rows.clear()
        for layer in self._layers:
            row = LayerRow(layer, self.rows_container)
            row.edit_requested.connect(self._open_formula_for_layer)
            row.settings_requested.connect(self._open_settings)
            row.visibility_changed.connect(self.visibility_changed)
            self.rows[layer.id] = row
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self.intersection_popup.set_layers(self._layers)

    def set_status(self, message: str, is_error: bool = False) -> None:
        """Show concise feedback without taking space while no message is needed."""
        self.status_label.setText(message)
        self.status_label.setVisible(bool(message))
        self.status_label.setProperty("isError", is_error)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def confirm_formula_saved(self) -> None:
        """Close the editor only after the host has parsed and rendered its submission."""
        if self._active_layer_id is not None:
            self._draft_kinds.pop(self._active_layer_id, None)
        self._active_layer_id = None
        self.formula_popup.accept_submission()

    def finish_edit(self) -> None:
        """Compatibility alias for successful updates from the main window."""
        self.confirm_formula_saved()

    def _open_new_formula(self) -> None:
        self.settings_popup.hide()
        self._active_layer_id = None
        self.formula_popup.open_formula("", "explicit", _PLACEHOLDERS["explicit"], self._popup_anchor(self.new_formula_button))

    def _open_formula_for_layer(self, layer_id: str, kind: str, latex: str, anchor: QPoint) -> None:
        self.settings_popup.hide()
        self._active_layer_id = layer_id
        selected_kind = self._draft_kinds.get(layer_id, kind)
        self.formula_popup.open_formula(latex, selected_kind, _PLACEHOLDERS[selected_kind], anchor)

    def _open_settings(self, layer_id: str, anchor: QPoint) -> None:
        layer = self._layer(layer_id)
        if layer is None:
            return
        self.formula_popup.dismiss()
        self.settings_popup.open_layer(layer, anchor, self._draft_kinds.get(layer_id))

    def _open_manual_intersection_popup(self) -> None:
        if self.auto_intersections_action.isChecked():
            self.auto_intersections_action.setChecked(False)
        self.intersection_popup.open_at(self._popup_anchor(self.intersection_button))

    def _submit_formula(self, kind: str, latex: str) -> None:
        """Emit only on Enter; live MathLive input never changes a rendered mesh."""
        if self._active_layer_id is None:
            self.add_requested.emit(kind, latex)
            return
        self.update_requested.emit(self._active_layer_id, kind, latex)

    def _cancel_formula_edit(self) -> None:
        self._active_layer_id = None

    def _set_draft_kind(self, layer_id: str, kind: str) -> None:
        self._draft_kinds[layer_id] = kind

    def _update_formula_placeholder(self, kind: str) -> None:
        self.formula_popup.editor.set_placeholder(_PLACEHOLDERS[kind])

    def _popup_anchor(self, widget: QWidget) -> QPoint:
        return widget.mapToGlobal(QPoint(0, widget.height() + 4))

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self._layers if layer.id == layer_id), None)
