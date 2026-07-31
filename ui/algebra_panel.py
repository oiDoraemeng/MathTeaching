"""Fixed left-side algebra panel for editable surface layers."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

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


class LayerRow(QFrame):
    """One editable algebra layer with independent visibility controls."""

    update_requested = Signal(str, str, str)
    delete_requested = Signal(str)
    visibility_changed = Signal(str, bool)
    intersections_visibility_changed = Signal(str, bool)
    color_changed = Signal(str, str)
    opacity_changed = Signal(str, float)
    range_changed = Signal(str, float)

    def __init__(self, layer: SurfaceLayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layer_id = layer.id
        self.setObjectName("algebraLayerRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(123)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(5)
        self.visible_check = QCheckBox("显示")
        self.visible_check.setChecked(layer.visible)
        self.visible_check.setToolTip("显示或隐藏此曲面")
        self.intersections_check = QCheckBox("交线")
        self.intersections_check.setChecked(layer.intersections_visible)
        self.intersections_check.setToolTip("显示或隐藏与此曲面相关的交线")
        self.kind_combo = QComboBox()
        for label, value in _SURFACE_KINDS:
            self.kind_combo.addItem(label, value)
        self.kind_combo.setCurrentIndex(max(0, self.kind_combo.findData(layer.kind)))
        self.kind_combo.setToolTip("曲面表达形式")
        self.color_button = QToolButton()
        self.color_button.setObjectName("layerColorButton")
        self.color_button.setFixedSize(24, 24)
        self.color_button.setToolTip("选择曲面颜色")
        self._set_color_button(layer.color)
        self.delete_button = QToolButton()
        self.delete_button.setText("X")
        self.delete_button.setToolTip("删除曲面")
        header.addWidget(self.visible_check)
        header.addWidget(self.intersections_check)
        header.addWidget(self.kind_combo, 1)
        header.addWidget(self.color_button)
        header.addWidget(self.delete_button)
        layout.addLayout(header)

        editor = QHBoxLayout()
        editor.setSpacing(5)
        self.expression_edit = QLineEdit(layer.expression)
        self.expression_edit.setPlaceholderText(_PLACEHOLDERS.get(layer.kind, "输入曲面方程"))
        self.expression_edit.setClearButtonEnabled(True)
        self.update_button = QPushButton("更新")
        self.update_button.setMinimumWidth(52)
        editor.addWidget(self.expression_edit, 1)
        editor.addWidget(self.update_button)
        layout.addLayout(editor)

        opacity = QHBoxLayout()
        opacity.setSpacing(6)
        opacity.addWidget(QLabel("透明度"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(round(layer.opacity * 100))
        self.opacity_value = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_value.setMinimumWidth(32)
        opacity.addWidget(self.opacity_slider, 1)
        opacity.addWidget(self.opacity_value)
        layout.addLayout(opacity)

        surface_range = QHBoxLayout()
        surface_range.setSpacing(6)
        surface_range.addWidget(QLabel("范围"))
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setRange(10, 50)
        self.range_slider.setValue(round(layer.range_scale * 10))
        self.range_slider.setToolTip("调整此曲面的采样范围")
        self.range_value = QLabel()
        self.range_value.setMinimumWidth(40)
        self._update_range_label(self.range_slider.value())
        surface_range.addWidget(self.range_slider, 1)
        surface_range.addWidget(self.range_value)
        layout.addLayout(surface_range)

        self.visible_check.toggled.connect(lambda visible: self.visibility_changed.emit(self.layer_id, visible))
        self.intersections_check.toggled.connect(
            lambda visible: self.intersections_visibility_changed.emit(self.layer_id, visible)
        )
        self.expression_edit.returnPressed.connect(self._emit_update)
        self.update_button.clicked.connect(self._emit_update)
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.layer_id))
        self.color_button.clicked.connect(self._choose_color)
        self.opacity_slider.valueChanged.connect(self._emit_opacity)
        self.range_slider.valueChanged.connect(self._update_range_label)
        self.range_slider.sliderReleased.connect(self._emit_range)

    def _emit_update(self) -> None:
        expression = self.expression_edit.text().strip()
        if expression:
            self.update_requested.emit(self.layer_id, str(self.kind_combo.currentData()), expression)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.color_button.property("layerColor")), self, "选择曲面颜色")
        if color.isValid():
            color_name = color.name()
            self._set_color_button(color_name)
            self.color_changed.emit(self.layer_id, color_name)

    def _set_color_button(self, color: str) -> None:
        self.color_button.setProperty("layerColor", color)
        self.color_button.setStyleSheet(f"background: {color}; border: 1px solid #687385; border-radius: 3px;")

    def _emit_opacity(self, value: int) -> None:
        opacity = value / 100.0
        self.opacity_value.setText(f"{value}%")
        self.opacity_changed.emit(self.layer_id, opacity)

    def _update_range_label(self, value: int) -> None:
        self.range_value.setText(f"x{value / 10:.1f}")

    def _emit_range(self) -> None:
        self.range_changed.emit(self.layer_id, self.range_slider.value() / 10.0)


class AlgebraPanel(QFrame):
    """A stable, scan-friendly control surface inspired by an algebra view."""

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
        self.setObjectName("algebraPanel")
        self.setMinimumWidth(350)
        self.setMaximumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(9)

        title = QLabel("代数图层")
        title.setObjectName("algebraTitle")
        layout.addWidget(title)
        subtitle = QLabel("在同一视图中编辑、显示与比较多个曲面")
        subtitle.setObjectName("algebraSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        add_line = QHBoxLayout()
        add_line.setSpacing(6)
        self.kind_combo = QComboBox()
        for label, value in _SURFACE_KINDS:
            self.kind_combo.addItem(label, value)
        self.kind_combo.currentIndexChanged.connect(self._update_placeholder)
        self.expression_edit = QLineEdit()
        self.expression_edit.setClearButtonEnabled(True)
        self._update_placeholder()
        self.add_button = QPushButton("添加")
        self.add_button.setToolTip("添加新的代数曲面")
        add_line.addWidget(self.kind_combo)
        add_line.addWidget(self.expression_edit, 1)
        add_line.addWidget(self.add_button)
        layout.addLayout(add_line)
        self.expression_edit.returnPressed.connect(self._request_add)
        self.add_button.clicked.connect(self._request_add)

        tools_line = QHBoxLayout()
        tools_line.setSpacing(6)
        self.builtin_button = QPushButton("添加内置二次曲面")
        self.builtin_menu = QMenu(self)
        self.builtin_button.setMenu(self.builtin_menu)
        self.lighting_button = QPushButton("高级光照")
        self.lighting_button.setToolTip("调整环境光、三点光源和光照方位")
        self.lighting_button.clicked.connect(self.lighting_requested)
        tools_line.addWidget(self.builtin_button, 1)
        tools_line.addWidget(self.lighting_button)
        layout.addLayout(tools_line)

        self.auto_intersections_check = QCheckBox("自动生成可见曲面的交线")
        self.auto_intersections_check.setChecked(True)
        self.auto_intersections_check.setToolTip("关闭后选择一对曲面再计算交线")
        layout.addWidget(self.auto_intersections_check)
        self.auto_intersections_check.toggled.connect(self._set_manual_controls_enabled)
        self.auto_intersections_check.toggled.connect(self.auto_intersections_changed)

        manual_line = QHBoxLayout()
        manual_line.setSpacing(5)
        self.first_layer_combo = QComboBox()
        self.second_layer_combo = QComboBox()
        self.manual_intersection_button = QPushButton("计算交线")
        self.manual_intersection_button.setToolTip("计算所选两个曲面的交线")
        manual_line.addWidget(self.first_layer_combo, 1)
        manual_line.addWidget(self.second_layer_combo, 1)
        manual_line.addWidget(self.manual_intersection_button)
        layout.addLayout(manual_line)
        self.manual_intersection_button.clicked.connect(self._request_manual_intersection)
        self._set_manual_controls_enabled(True)

        self.rows_container = QWidget()
        self.rows_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding)
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(7)
        self.rows_layout.addStretch()
        self.rows_scroll = QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rows_scroll.setWidget(self.rows_container)
        self.rows_scroll.setMinimumHeight(280)
        layout.addWidget(self.rows_scroll, 1)

        self.status_label = QLabel("添加曲面以开始观察相交关系")
        self.status_label.setObjectName("algebraStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def set_builtin_surfaces(self, surfaces: Iterable[tuple[str, str]]) -> None:
        self.builtin_menu.clear()
        for surface_id, name in surfaces:
            action = self.builtin_menu.addAction(name)
            action.triggered.connect(lambda _checked=False, identifier=surface_id: self.builtin_requested.emit(identifier))

    def set_layers(self, layers: Iterable[SurfaceLayer]) -> None:
        self._layers = list(layers)
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.rows.clear()
        for layer in self._layers:
            row = LayerRow(layer, self.rows_container)
            row.update_requested.connect(self.update_requested)
            row.delete_requested.connect(self.delete_requested)
            row.visibility_changed.connect(self.visibility_changed)
            row.intersections_visibility_changed.connect(self.intersections_visibility_changed)
            row.color_changed.connect(self.color_changed)
            row.opacity_changed.connect(self.opacity_changed)
            row.range_changed.connect(self.range_changed)
            self.rows[layer.id] = row
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self._refresh_manual_pair_choices()

    def set_status(self, message: str, is_error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setProperty("isError", is_error)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _request_add(self) -> None:
        expression = self.expression_edit.text().strip()
        if expression:
            self.add_requested.emit(str(self.kind_combo.currentData()), expression)

    def _request_manual_intersection(self) -> None:
        first_id = str(self.first_layer_combo.currentData() or "")
        second_id = str(self.second_layer_combo.currentData() or "")
        if first_id and second_id and first_id != second_id:
            self.manual_intersection_requested.emit(first_id, second_id)

    def _refresh_manual_pair_choices(self) -> None:
        current_first = self.first_layer_combo.currentData()
        current_second = self.second_layer_combo.currentData()
        for combo, current in ((self.first_layer_combo, current_first), (self.second_layer_combo, current_second)):
            combo.blockSignals(True)
            combo.clear()
            for layer in self._layers:
                combo.addItem(layer.name, layer.id)
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)
        if len(self._layers) > 1 and self.second_layer_combo.currentIndex() == self.first_layer_combo.currentIndex():
            self.second_layer_combo.setCurrentIndex(1)

    def _set_manual_controls_enabled(self, automatic: bool) -> None:
        enabled = not automatic
        self.first_layer_combo.setEnabled(enabled)
        self.second_layer_combo.setEnabled(enabled)
        self.manual_intersection_button.setEnabled(enabled)

    def _update_placeholder(self) -> None:
        self.expression_edit.setPlaceholderText(_PLACEHOLDERS[str(self.kind_combo.currentData())])
