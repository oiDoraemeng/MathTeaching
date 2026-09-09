"""代数列表、函数目录与按场景模式适配的图层控制。"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QMouseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QTabWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)


class HoverCloseTabBar(QTabBar):
    """Tab bar whose close affordance appears only while hovering a tab."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setUsesScrollButtons(True)
        self.setStyleSheet("QTabBar { qproperty-expanding: false; } QTabBar QToolButton { width: 16px; } QTabBar QScrollBar:horizontal { height: 0px; }")

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
        if button is not None:
            button.setVisible(False)

    def mouseMoveEvent(self, event):
        hovered = self.tabAt(event.position().toPoint())
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
            if button is not None:
                button.setVisible(index == hovered)
        return super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
            if button is not None:
                button.setVisible(False)
        return super().leaveEvent(event)

from MathInputWidget import FormulaEditorPopup, FormulaListWidget, FormulaPreviewWidget
from models.curve_layer import CurveLayer
from models.function_catalog import CatalogEntry
from models.geometry_2d import Annotation2D, GeometryObject, Linear2D, Point2D
from models.scene_mode import SceneMode
from models.surface_layer import SurfaceLayer
from ui.icons import apply_icon, icon_color, retint_icons
from ui.linear_algebra_dialog import LinearAlgebraDialog
from ui.tokens import ThemeName, apply_drop_shadow, apply_rounded_overlay


Layer = SurfaceLayer | CurveLayer | GeometryObject | Annotation2D
_PLACEHOLDERS = {
    SceneMode.THREE_D: {
        "explicit": "z = x^2 - y^2",
        "implicit": "x^2 + y^2 + z^2 = 1",
        "parametric": "(u*cos(v), u*sin(v), v); u=[0,1], v=[-1,1]",
    },
    SceneMode.TWO_D: {
        "explicit": "y = sin(x)",
        "implicit": "x^2 + y^2 = 1",
        "parametric": "(cos(t), sin(t)); t=[0, 2*pi]",
    },
}


class LayerSettingsPopup(QDialog):
    """随曲线或曲面类型切换的单图层显示控制面板。"""

    intersections_changed = Signal(str, bool)
    intersection_color_changed = Signal(str, str)
    color_changed = Signal(str, str)
    opacity_changed = Signal(str, float)
    line_width_changed = Signal(str, float)
    range_changed = Signal(str, float)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layer_id: str | None = None
        self._is_curve = False
        self._color_dialog: QColorDialog | None = None
        self._color_target = "layer"
        self.setObjectName("layerSettingsPopup")
        self.setWindowTitle("函数设置")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        apply_rounded_overlay(self, "lg")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._show_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_animation.setDuration(150)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumWidth(278)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        self.title = QLabel("函数设置", self)
        self.title.setObjectName("settingsPopupTitle")
        layout.addWidget(self.title)

        self.intersections_check = QCheckBox("显示相关交线", self)
        layout.addWidget(self.intersections_check)

        self.color_row, self.color_button = self._color_row("函数颜色", "选择函数颜色")
        layout.addWidget(self.color_row)
        self.intersection_color_row, self.intersection_color_button = self._color_row(
            "交线颜色", "选择交线颜色"
        )
        layout.addWidget(self.intersection_color_row)

        self.opacity_row, self.opacity_slider, self.opacity_value = self._slider_row(
            "透明度", 5, 100
        )
        layout.addWidget(self.opacity_row)
        self.line_width_row, self.line_width_slider, self.line_width_value = self._slider_row(
            "线宽", 10, 80
        )
        layout.addWidget(self.line_width_row)
        self.range_row, self.range_slider, self.range_value = self._slider_row("采样范围", 10, 100)
        layout.addWidget(self.range_row)

        self.delete_button = QPushButton("删除函数", self)
        self.delete_button.setToolTip("删除当前函数")
        layout.addWidget(self.delete_button)

        self.intersections_check.toggled.connect(self._emit_intersections)
        self.color_button.clicked.connect(lambda: self._choose_color("layer"))
        self.intersection_color_button.clicked.connect(lambda: self._choose_color("intersection"))
        self.opacity_slider.valueChanged.connect(self._emit_opacity)
        self.line_width_slider.valueChanged.connect(self._emit_line_width)
        self.range_slider.valueChanged.connect(self._update_range_label)
        self.range_slider.sliderReleased.connect(self._emit_range)
        self.delete_button.clicked.connect(self._request_delete)

    def _color_row(self, label: str, tooltip: str) -> tuple[QWidget, QToolButton]:
        host = QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        text = QLabel(label, host)
        text.setObjectName("sectionHeader")
        row.addWidget(text)
        button = QToolButton(host)
        button.setFixedSize(28, 28)
        button.setToolTip(tooltip)
        row.addWidget(button)
        row.addStretch()
        return host, button

    def _slider_row(self, label: str, minimum: int, maximum: int) -> tuple[QWidget, QSlider, QLabel]:
        host = QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        text = QLabel(label, host)
        text.setObjectName("sectionHeader")
        row.addWidget(text)
        slider = QSlider(Qt.Orientation.Horizontal, host)
        slider.setRange(minimum, maximum)
        value = QLabel(host)
        value.setMinimumWidth(40)
        row.addWidget(slider, 1)
        row.addWidget(value)
        return host, slider, value

    def open_layer(self, layer: Layer, anchor: QPoint | None) -> None:
        self._layer_id = layer.id
        self._is_curve = isinstance(layer, CurveLayer)
        self.title.setText("曲线设置" if self._is_curve else "曲面设置")
        self.intersections_check.setVisible(not self._is_curve)
        self.intersection_color_row.setVisible(not self._is_curve)
        self.opacity_row.setVisible(not self._is_curve)
        self.line_width_row.setVisible(self._is_curve)
        controls = (self.intersections_check, self.opacity_slider, self.line_width_slider, self.range_slider)
        for control in controls:
            control.blockSignals(True)
        try:
            # 曲面范围使用视口的 10% 至 100%；曲线范围使用 1.0 至 5.0 倍的绝对缩放。
            if self._is_curve:
                self.line_width_slider.setValue(round(layer.line_width * 10))
                self.range_slider.setMinimum(10)
                self.range_slider.setMaximum(50)
                self.range_slider.setValue(round(layer.range_scale * 10))
            else:
                self.intersections_check.setChecked(layer.intersections_visible)
                self.opacity_slider.setValue(round(layer.opacity * 100))
                self.range_slider.setMinimum(10)
                self.range_slider.setMaximum(100)
                self.range_slider.setValue(round(layer.range_scale * 100))
        finally:
            for control in controls:
                control.blockSignals(False)
        self.opacity_value.setText(f"{self.opacity_slider.value()}%")
        self.line_width_value.setText(f"{self.line_width_slider.value() / 10:.1f}")
        self._update_range_label(self.range_slider.value())
        self._set_color_button(self.color_button, layer.color)
        if isinstance(layer, SurfaceLayer):
            self._set_color_button(self.intersection_color_button, layer.intersection_color)
        self.setWindowOpacity(0.0)
        self.show()
        self._show_animation.stop()
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(1.0)
        self._show_animation.start()
        if anchor is not None:
            self.move(anchor)

    def _emit_intersections(self, visible: bool) -> None:
        if self._layer_id is not None and not self._is_curve:
            self.intersections_changed.emit(self._layer_id, visible)

    def _choose_color(self, target: str) -> None:
        if self._layer_id is None:
            return
        self._color_target = target
        button = self.intersection_color_button if target == "intersection" else self.color_button
        dialog = QColorDialog(QColor(button.property("layerColor")), self)
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
        if self._color_target == "intersection":
            self._set_color_button(self.intersection_color_button, color_name)
            self.intersection_color_changed.emit(self._layer_id, color_name)
        else:
            self._set_color_button(self.color_button, color_name)
            self.color_changed.emit(self._layer_id, color_name)

    @staticmethod
    def _set_color_button(button: QToolButton, color: str) -> None:
        button.setProperty("layerColor", color)
        button.setStyleSheet(f"background: {color};")

    def _emit_opacity(self, value: int) -> None:
        self.opacity_value.setText(f"{value}%")
        if self._layer_id is not None and not self._is_curve:
            self.opacity_changed.emit(self._layer_id, value / 100.0)

    def _emit_line_width(self, value: int) -> None:
        self.line_width_value.setText(f"{value / 10:.1f}")
        if self._layer_id is not None and self._is_curve:
            self.line_width_changed.emit(self._layer_id, value / 10.0)

    def _update_range_label(self, value: int) -> None:
        if self._is_curve:
            self.range_value.setText(f"x{value / 10:.1f}")
        else:
            self.range_value.setText(f"{value}%")

    def _emit_range(self) -> None:
        if self._layer_id is not None:
            if self._is_curve:
                self.range_changed.emit(self._layer_id, self.range_slider.value() / 10.0)
            else:
                self.range_changed.emit(self._layer_id, self.range_slider.value() / 100.0)

    def _request_delete(self) -> None:
        if self._layer_id is not None:
            layer_id = self._layer_id
            self.hide()
            self.delete_requested.emit(layer_id)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.isVisible()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and watched is not self
            and not self.isAncestorOf(watched)
            and (self._color_dialog is None or not self._color_dialog.isAncestorOf(watched))
        ):
            QTimer.singleShot(0, self.hide)
        return super().eventFilter(watched, event)


class GeometrySettingsPopup(QDialog):
    """为不可编辑的二维几何对象提供最小化的删除操作。"""

    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._object_id: str | None = None
        self.setObjectName("geometrySettingsPopup")
        self.setWindowTitle("几何对象")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        apply_rounded_overlay(self, "lg")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._show_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_animation.setDuration(150)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        self.title = QLabel("几何对象", self)
        self.title.setObjectName("settingsPopupTitle")
        layout.addWidget(self.title)
        self.delete_button = QPushButton("删除对象", self)
        self.delete_button.clicked.connect(self._request_delete)
        layout.addWidget(self.delete_button)

    def open_geometry(self, geometry: GeometryObject | Annotation2D, anchor: QPoint | None) -> None:
        self._object_id = geometry.id
        if isinstance(geometry, Point2D):
            self.title.setText("点设置")
        elif isinstance(geometry, Annotation2D):
            self.title.setText("标注设置")
        else:
            names = {"line": "直线", "segment": "线段", "ray": "射线", "vector": "向量"}
            self.title.setText(f"{names[geometry.kind]}设置")
        self.setWindowOpacity(0.0)
        self.show()
        self._show_animation.stop()
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(1.0)
        self._show_animation.start()
        if anchor is not None:
            self.move(anchor)
        self.raise_()

    def _request_delete(self) -> None:
        if self._object_id is None:
            return
        object_id = self._object_id
        self.hide()
        self.delete_requested.emit(object_id)


class IntersectionPopup(QDialog):
    """仅为 API 兼容而保留的旧版手动交线选择器。"""

    requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("intersectionPopup")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        apply_rounded_overlay(self, "lg")
        layout = QHBoxLayout(self)
        self.first_combo = QComboBox(self)
        self.second_combo = QComboBox(self)
        button = QPushButton("计算", self)
        button.clicked.connect(self._request)
        layout.addWidget(self.first_combo)
        layout.addWidget(self.second_combo)
        layout.addWidget(button)

    def set_layers(self, layers: Iterable[SurfaceLayer]) -> None:
        for combo in (self.first_combo, self.second_combo):
            combo.clear()
            for layer in layers:
                combo.addItem(layer.name, layer.id)

    def open_at(self, anchor: QPoint) -> None:
        self.show()
        self.move(anchor)

    def _request(self) -> None:
        first_id = str(self.first_combo.currentData() or "")
        second_id = str(self.second_combo.currentData() or "")
        if first_id and second_id and first_id != second_id:
            self.requested.emit(first_id, second_id)


class CatalogEntryRow(QFrame):
    """可点击的函数目录行，预览统一由 MathLive 排版。"""

    selected = Signal(str)

    def __init__(self, entry: CatalogEntry, parent: QWidget | None = None, *, initial_theme: ThemeName = "light") -> None:
        super().__init__(parent)
        self.entry_id = entry.id
        self.setObjectName("catalogEntryRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        name = QLabel(entry.name, self)
        name.setMinimumWidth(76)
        self.preview = FormulaPreviewWidget(entry.latex, self, initial_theme=initial_theme)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(name)
        layout.addWidget(self.preview, 1)
        self.preview.edit_requested.connect(lambda: self.selected.emit(self.entry_id))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.entry_id)
            event.accept()
            return
        super().mousePressEvent(event)


class FunctionCatalogPopup(QDialog):
    """显示在左侧函数按钮下方、并按场景筛选的可滚动目录。"""

    requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme: ThemeName = "light"
        self.setObjectName("functionCatalogPopup")
        self.setWindowTitle("函数")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        apply_rounded_overlay(self, "lg")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(440, 420)
        self.resize(460, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget(self.scroll)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def set_entries(self, entries: Iterable[CatalogEntry]) -> None:
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        last_category: str | None = None
        for entry in entries:
            if entry.category != last_category:
                category = QLabel(entry.category, self.content)
                category.setObjectName("catalogCategory")
                self.content_layout.insertWidget(self.content_layout.count() - 1, category)
                last_category = entry.category
            row = CatalogEntryRow(entry, self.content, initial_theme=self._theme)
            row.selected.connect(self._request)
            self.content_layout.insertWidget(self.content_layout.count() - 1, row)

    def open_at(self, anchor: QPoint) -> None:
        self.show()
        self.move(anchor)
        self.raise_()

    def _request(self, entry_id: str) -> None:
        self.hide()
        self.requested.emit(entry_id)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.isVisible()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and watched is not self
            and not self.isAncestorOf(watched)
        ):
            QTimer.singleShot(0, self.hide)
        return super().eventFilter(watched, event)

    def set_theme(self, theme: ThemeName) -> None:
        self._theme = theme
        for preview in self.findChildren(FormulaPreviewWidget):
            preview.set_theme(theme)


class LayerRow(QFrame):
    """包含可见性、MathLive 直接编辑和设置入口的紧凑图层行。"""

    edit_requested = Signal(str, str, str, object)
    settings_requested = Signal(str, object)
    visibility_changed = Signal(str, bool)

    _MINIMUM_ROW_HEIGHT = 48
    _MINIMUM_FORMULA_HEIGHT = 32
    _VERTICAL_MARGINS = 8

    def __init__(self, layer: Layer, parent: QWidget | None = None, *, initial_theme: ThemeName = "light") -> None:
        super().__init__(parent)
        self.layer_id = layer.id
        self.setObjectName("algebraLayerRow")
        self.setFixedHeight(self._MINIMUM_ROW_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        self.visible_button = QToolButton(self)
        self.visible_button.setCheckable(True)
        self.visible_button.setChecked(layer.visible)
        self.visible_button.setFixedSize(28, 28)
        self._set_visibility_icon(layer.visible)
        self.expression_button = FormulaPreviewWidget(layer.latex or layer.expression, self, initial_theme=initial_theme)
        self.expression_button.setObjectName("layerExpressionButton")
        self.expression_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.expression_button.setToolTip(layer.latex or layer.expression)
        self.settings_button = QToolButton(self)
        apply_icon(self.settings_button, "ellipsis", icon_color(), icon_size=16, hit_size=28)
        self.settings_button.setToolTip("函数显示与采样设置")
        layout.addWidget(self.visible_button)
        layout.addWidget(self.expression_button, 1)
        layout.addWidget(self.settings_button)
        self.visible_button.toggled.connect(self._emit_visibility)
        self.expression_button.content_height_changed.connect(self.set_formula_height)
        self.expression_button.edit_requested.connect(
            lambda: self.edit_requested.emit(
                self.layer_id,
                layer.kind,
                layer.latex or layer.expression,
                self.expression_button.mapToGlobal(QPoint(0, 0)),
            )
        )
        self.settings_button.clicked.connect(
            lambda: self.settings_requested.emit(
                self.layer_id,
                self.settings_button.mapToGlobal(QPoint(0, self.settings_button.height() + 4)),
            )
        )

    def sync(self, layer: Layer) -> None:
        self.visible_button.blockSignals(True)
        self.visible_button.setChecked(layer.visible)
        self._set_visibility_icon(layer.visible)
        self.visible_button.blockSignals(False)
        display = layer.latex or layer.expression
        if self.expression_button.get_latex() != display:
            self.expression_button.set_latex(display)
            self.expression_button.setToolTip(display)

    def set_formula_height(self, formula_height: int) -> None:
        formula_height = max(self._MINIMUM_FORMULA_HEIGHT, int(formula_height))
        if self.expression_button.height() != formula_height:
            self.expression_button.setFixedHeight(formula_height)
        row_height = max(self._MINIMUM_ROW_HEIGHT, formula_height + self._VERTICAL_MARGINS)
        if self.height() != row_height:
            self.setFixedHeight(row_height)
            self.updateGeometry()

    def _emit_visibility(self, visible: bool) -> None:
        self._set_visibility_icon(visible)
        self.visibility_changed.emit(self.layer_id, visible)

    def _set_visibility_icon(self, visible: bool) -> None:
        apply_icon(
            self.visible_button,
            "eye" if visible else "eye-off",
            icon_color(),
            icon_size=16,
            hit_size=28,
        )
        self.visible_button.setToolTip("隐藏函数" if visible else "显示函数")


class AlgebraPanel(QFrame):
    tab_closed = Signal(str)
    """由相互独立的二维和三维场景共用的紧凑代数面板。"""

    add_requested = Signal(str, str)
    update_requested = Signal(str, str, str)
    pane_update_requested = Signal(str, str, str, str)
    pane_visibility_requested = Signal(str, int)
    delete_requested = Signal(str)
    visibility_changed = Signal(str, bool)
    intersections_visibility_changed = Signal(str, bool)
    intersection_color_changed = Signal(str, str)
    color_changed = Signal(str, str)
    opacity_changed = Signal(str, float)
    line_width_changed = Signal(str, float)
    range_changed = Signal(str, float)
    catalog_requested = Signal(str)
    # 为插件和旧测试保留该信号；工具栏中已没有对应的可见操作入口。
    builtin_requested = Signal(str)
    lighting_requested = Signal()
    auto_intersections_changed = Signal(bool)
    manual_intersection_requested = Signal(str, str)
    linear_algebra_requested = Signal(str)
    linear_algebra_opened = Signal()
    pane_changed = Signal(str)
    MIN_WIDTH = 260
    DEFAULT_WIDTH = 320
    MAX_WIDTH = 420

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._effective_theme: ThemeName = getattr(parent, "effective_theme", "light")
        self.rows: dict[str, LayerRow] = {}
        self._layers: list[Layer] = []
        self._scene_mode = SceneMode.THREE_D
        self._active_layer_id: str | None = None
        self._inline_active_layer_id: str | None = None
        self._pane_id = "pane-1"
        self._pane_models: dict[str, FormulaListWidget] = {}
        self._pane_manager = None
        self.inline_editor = None
        self.setObjectName("algebraPanel")
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(7)
        toolbar = QHBoxLayout()
        title = QLabel("代数", self)
        title.setObjectName("algebraTitle")
        toolbar.addWidget(title)
        toolbar.addStretch()
        self.new_formula_button = self._icon_button("plus", "新增公式")
        self.function_catalog_button = self._tool_button("函数", "函数目录")
        self.function_catalog_button.setFixedWidth(44)
        self.linear_algebra_button = self._tool_button("线性代数", "线性代数案例")
        self.linear_algebra_button.setFixedWidth(72)
        toolbar.addWidget(self.new_formula_button)
        toolbar.addWidget(self.function_catalog_button)
        toolbar.addWidget(self.linear_algebra_button)
        layout.addLayout(toolbar)

        # 这些对象维持旧版公开 API，同时不重新引入隐藏的工具栏控件。
        self.builtin_button = self.function_catalog_button
        self.builtin_menu = QMenu(self)
        self.lighting_button = QToolButton(self)
        self.lighting_button.setVisible(False)
        self.intersection_button = QToolButton(self)
        self.intersection_button.setVisible(False)
        self.intersection_menu = QMenu(self)
        self.auto_intersections_action = QAction("自动生成交线", self, checkable=True)
        self.auto_intersections_action.setChecked(True)
        self.manual_intersection_action = QAction("手动选择两个曲面", self)
        self.intersection_menu.addAction(self.auto_intersections_action)
        self.intersection_menu.addAction(self.manual_intersection_action)

        self.formula_tabs = QTabWidget(self)
        self.formula_tabs.setObjectName("algebraPaneTabs")
        self.formula_tabs.setDocumentMode(True)
        self.formula_tabs.setTabBar(HoverCloseTabBar(self.formula_tabs))
        self.formula_tabs.setTabsClosable(True)
        self.formula_list = FormulaListWidget(self.formula_tabs, initial_theme=self._effective_theme)
        self._pane_models[self._pane_id] = self.formula_list
        self.formula_tabs.addTab(self.formula_list, "窗格 1")
        self.formula_tabs.currentChanged.connect(self._on_tab_changed)
        self.formula_tabs.tabBarDoubleClicked.connect(self._edit_tab_title)
        self.formula_tabs.tabCloseRequested.connect(self._close_tab)
        self.formula_tabs.tabBar().setMovable(False)
        self.rows_container = self.formula_list
        self.rows_scroll = self.formula_list
        layout.addWidget(self.formula_tabs, 1)
        self.status_label = QLabel("", self)
        self.status_label.setObjectName("algebraStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.formula_popup = FormulaEditorPopup(self, initial_theme=self._effective_theme)
        self.settings_popup = LayerSettingsPopup(self)
        self.geometry_settings_popup = GeometrySettingsPopup(self)
        self.intersection_popup = IntersectionPopup(self)
        self.catalog_popup = FunctionCatalogPopup(self)
        self.linear_algebra_popup = LinearAlgebraDialog(self)
        self.sync_overlay_theme(self._effective_theme)
        self.new_formula_button.clicked.connect(self._open_new_formula)
        self.function_catalog_button.clicked.connect(self._open_catalog)
        self.linear_algebra_button.clicked.connect(self._open_linear_algebra)
        self.lighting_button.clicked.connect(self.lighting_requested)
        self.auto_intersections_action.toggled.connect(self.auto_intersections_changed)
        self.manual_intersection_action.triggered.connect(self._open_manual_intersection_popup)
        self.formula_popup.submitted.connect(self._submit_formula)
        self.formula_popup.dismissed.connect(self._cancel_formula_edit)
        self.settings_popup.intersections_changed.connect(self.intersections_visibility_changed)
        self.settings_popup.intersection_color_changed.connect(self.intersection_color_changed)
        self.settings_popup.color_changed.connect(self.color_changed)
        self.settings_popup.opacity_changed.connect(self.opacity_changed)
        self.settings_popup.line_width_changed.connect(self.line_width_changed)
        self.settings_popup.range_changed.connect(self.range_changed)
        self.settings_popup.delete_requested.connect(self.delete_requested)
        self.geometry_settings_popup.delete_requested.connect(self.delete_requested)
        self.intersection_popup.requested.connect(self.manual_intersection_requested)
        self.catalog_popup.requested.connect(self.catalog_requested)
        self.linear_algebra_popup.requested.connect(self.linear_algebra_requested)
        self.formula_list.edit_requested.connect(self._open_inline_formula_for_layer)
        self.formula_list.formula_submitted.connect(
            lambda layer_id, latex, model=self.formula_list: self._submit_inline_formula_from_model(
                model, layer_id, latex
            )
        )
        self.formula_list.edit_cancelled.connect(self._cancel_inline_formula_edit)
        self.formula_list.visibility_changed.connect(self.visibility_changed)
        self.formula_list.settings_requested.connect(self._open_settings)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

    def sync_overlay_theme(self, theme: ThemeName) -> None:
        self._effective_theme = theme
        for model in self._pane_models.values():
            model.set_theme(theme)
        self.formula_popup.set_theme(theme)
        self.catalog_popup.set_theme(theme)
        for preview in self.findChildren(FormulaPreviewWidget):
            preview.set_theme(theme)
        for popup in (
            self.settings_popup,
            self.geometry_settings_popup,
            self.intersection_popup,
            self.catalog_popup,
            self.formula_popup,
            self.linear_algebra_popup,
        ):
            apply_drop_shadow(popup, "overlay", theme)
            retint_icons(popup, theme)
        # QSS cannot restyle a QIcon, so panel buttons must be repainted too.
        retint_icons(self, theme)

    @staticmethod
    def _tool_button(text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedHeight(32)
        return button

    @staticmethod
    def _icon_button(name: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setToolTip(tooltip)
        apply_icon(button, name, icon_color(), icon_size=16, hit_size=28)
        return button

    def set_scene_mode(self, mode: SceneMode) -> None:
        self._scene_mode = mode
        self.formula_list.cancel_edit()
        self.settings_popup.hide()
        self.geometry_settings_popup.hide()
        self.catalog_popup.hide()

    def set_pane_id(self, pane_id: str, title: str | None = None) -> None:
        """Activate (or create) the algebra tab associated with a scene pane."""
        pane_id = str(pane_id)
        if pane_id not in self._pane_models:
            model = FormulaListWidget(self.formula_tabs, initial_theme=self._effective_theme)
            self._pane_models[pane_id] = model
            self.formula_tabs.addTab(model, title or pane_id)
            self._wire_formula_list(model)
        index = list(self._pane_models).index(pane_id)
        self.formula_tabs.setCurrentIndex(index)
        self._pane_id = pane_id
        self.formula_list = self._pane_models[pane_id]
        self.rows_container = self.formula_list
        self.rows_scroll = self.formula_list
        self.pane_changed.emit(pane_id)

    def set_pane_manager(self, manager) -> None:
        """Bind tab focus and title edits to the scene pane manager."""
        previous = self._pane_manager
        if previous is not None and hasattr(previous, "pane_deleted"):
            try:
                previous.pane_deleted.disconnect(self._on_manager_pane_deleted)
            except (RuntimeError, TypeError):
                pass
        self._pane_manager = manager
        if manager is not None and hasattr(manager, "pane_deleted"):
            manager.pane_deleted.connect(self._on_manager_pane_deleted)
        if manager is not None and hasattr(manager, "workspace_restored"):
            manager.workspace_restored.connect(self.sync_pane_tabs)

    def sync_pane_tabs(self) -> None:
        """Materialize retained tabs without activating their hidden viewports."""
        manager = self._pane_manager
        if manager is None:
            return
        blocked = self.formula_tabs.blockSignals(True)
        try:
            for pane_id in tuple(self._pane_models):
                if pane_id not in manager.panes:
                    self._remove_tab_model(pane_id)
            for pane in manager.panes.values():
                self.set_pane_id(pane.pane_id, pane.name)
                self.formula_tabs.setTabText(list(self._pane_models).index(pane.pane_id), pane.name)
            self.set_pane_id(manager.active_pane_id)
        finally:
            self.formula_tabs.blockSignals(blocked)

    def _on_manager_pane_deleted(self, pane_id: str) -> None:
        """Remove the algebra model whose scene pane was closed elsewhere."""
        pane_id = str(pane_id)
        if pane_id not in self._pane_models or len(self._pane_models) <= 1:
            return
        self._remove_tab_model(pane_id)

    def _remove_tab_model(self, pane_id: str) -> None:
        """Detach one tab/model while keeping the current tab valid."""
        pane_ids = list(self._pane_models)
        if pane_id not in pane_ids or len(pane_ids) <= 1:
            return
        index = pane_ids.index(pane_id)
        was_current = self._pane_id == pane_id
        model = self._pane_models.pop(pane_id)
        self.formula_tabs.blockSignals(True)
        try:
            self.formula_tabs.removeTab(index)
        finally:
            self.formula_tabs.blockSignals(False)
        model.deleteLater()
        self.tab_closed.emit(pane_id)
        if was_current:
            fallback = next(iter(self._pane_models))
            self.set_pane_id(fallback)

    def _close_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._pane_models) or len(self._pane_models) <= 1:
            return
        pane_id = list(self._pane_models)[index]
        if self._pane_manager is not None:
            try:
                self._pane_manager.delete_pane(pane_id)
            except (RuntimeError, ValueError):
                return
            # ScenePaneManager.pane_deleted synchronously removes this tab.
            if pane_id not in self._pane_models:
                return
        self._remove_tab_model(pane_id)

    def _edit_tab_title(self, index: int) -> None:
        if index < 0 or index >= len(self._pane_models):
            return
        pane_id = list(self._pane_models)[index]
        current = self.formula_tabs.tabText(index)
        title, accepted = QInputDialog.getText(self, "重命名窗格", "窗格名称", text=current)
        if not accepted or not title.strip():
            return
        self.formula_tabs.setTabText(index, title.strip())
        if self._pane_manager is not None:
            try:
                self._pane_manager.pane(pane_id).name = title.strip()
            except (AttributeError, KeyError, ValueError):
                pass

    def set_pane_titles(self, titles: dict[str, str]) -> None:
        for pane_id, title in titles.items():
            self.set_pane_id(pane_id, title)
            self.formula_tabs.setTabText(list(self._pane_models).index(pane_id), str(title))
        self.set_pane_id(self._pane_id)

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._pane_models):
            return
        pane_id = list(self._pane_models)[index]
        previous_pane = self._pane_id
        if previous_pane != pane_id:
            previous_model = self._pane_models.get(previous_pane)
            if previous_model is not None and previous_model._active_layer_id is not None:
                previous_model.accept_edit()
            if self._pane_manager is not None:
                try:
                    # Retained panes beyond the current layout are valid tabs.
                    # Reveal the pane before focusing it so the UI and manager
                    # cannot disagree about the active pane.
                    visible_getter = getattr(self._pane_manager, "visible_pane_ids", None)
                    visible = tuple(visible_getter()) if callable(visible_getter) else (pane_id,)
                    if pane_id not in visible:
                        self._pane_manager.reveal_pane(pane_id)
                        self.pane_visibility_requested.emit(pane_id, len(visible))
                    self._pane_manager.focus_pane(pane_id)
                except (AttributeError, KeyError, ValueError):
                    pass
        self._pane_id = pane_id
        self.formula_list = self._pane_models[pane_id]
        self.rows_container = self.formula_list
        self.rows_scroll = self.formula_list
        self.pane_changed.emit(pane_id)

    def _wire_formula_list(self, formula_list: FormulaListWidget) -> None:
        formula_list.edit_requested.connect(self._open_inline_formula_for_layer)
        # Capture the originating model.  WebView callbacks can arrive after
        # the user has switched tabs; routing through ``self.formula_list``
        # would then apply the edit to the newly selected pane.
        formula_list.formula_submitted.connect(
            lambda layer_id, latex, model=formula_list: self._submit_inline_formula_from_model(
                model, layer_id, latex
            )
        )
        formula_list.edit_cancelled.connect(self._cancel_inline_formula_edit)
        formula_list.visibility_changed.connect(self.visibility_changed)
        formula_list.settings_requested.connect(self._open_settings)

    def set_catalog_entries(self, entries: Iterable[CatalogEntry]) -> None:
        self.catalog_popup.set_entries(entries)

    def set_builtin_surfaces(self, surfaces: Iterable[tuple[str, str]]) -> None:
        self.builtin_menu.clear()
        for surface_id, name in surfaces:
            action = self.builtin_menu.addAction(name)
            action.triggered.connect(
                lambda _checked=False, identifier=surface_id: self.builtin_requested.emit(identifier)
            )

    def set_layers(self, layers: Iterable[Layer]) -> None:
        self._layers = list(layers)
        self.rows.clear()
        self.formula_list.set_layers(self._layers)
        self.intersection_popup.set_layers(
            layer for layer in self._layers if isinstance(layer, SurfaceLayer)
        )

    def set_selected_layer(self, layer_id: str | None) -> None:
        """同步画布选中状态到列表高亮。"""
        self.formula_list.set_selected(layer_id)

    def begin_geometry_edit(self, layer_id: str) -> None:
        """从画布双击进入点坐标行内编辑。"""
        layer = self._layer(layer_id)
        if not isinstance(layer, Point2D):
            return
        self.settings_popup.hide()
        self.geometry_settings_popup.hide()
        self.catalog_popup.hide()
        self.formula_popup.dismiss()
        self._active_layer_id = None
        self._inline_active_layer_id = layer_id
        self.formula_list.begin_edit(layer_id)

    def set_status(self, message: str, is_error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setVisible(bool(message))
        self.status_label.setProperty("isError", is_error)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def confirm_formula_saved(self) -> None:
        self._active_layer_id = None
        self.formula_popup.accept_submission()
        if self._inline_active_layer_id is not None:
            self._inline_active_layer_id = None
            self.formula_list.accept_edit()

    def finish_edit(self) -> None:
        self.confirm_formula_saved()

    def _open_new_formula(self) -> None:
        self.settings_popup.hide()
        self.catalog_popup.hide()
        self.formula_list.cancel_edit()
        self._active_layer_id = None
        placeholder = _PLACEHOLDERS[self._scene_mode]["explicit"]
        self.formula_popup.open_formula("", "explicit", placeholder, self._popup_anchor(self.new_formula_button))

    def _open_catalog(self) -> None:
        self.settings_popup.hide()
        self.formula_list.cancel_edit()
        self.catalog_popup.open_at(self._popup_anchor(self.function_catalog_button))

    def _open_linear_algebra(self) -> None:
        self.settings_popup.hide()
        self.catalog_popup.hide()
        self.formula_list.cancel_edit()
        # 先让主窗口进入二维工作区，再打开目录。工具栏本身已经默认完整显示，
        # 这里仅负责打开讲义目录，不负责决定工具栏是否可见。
        self.linear_algebra_opened.emit()
        self.linear_algebra_popup.open_at(self._popup_anchor(self.linear_algebra_button))

    def _open_formula_for_layer(self, layer_id: str, kind: str, latex: str, anchor: QPoint | None) -> None:
        self.settings_popup.hide()
        self.formula_list.cancel_edit()
        self._active_layer_id = layer_id
        placeholder = _PLACEHOLDERS[self._scene_mode].get(kind, _PLACEHOLDERS[self._scene_mode]["explicit"])
        self.formula_popup.open_formula(latex, kind, placeholder, anchor)

    def _open_settings(self, layer_id: str, anchor: QPoint | None) -> None:
        layer = self._layer(layer_id)
        if layer is None:
            return
        self.formula_popup.dismiss()
        self.catalog_popup.hide()
        self.formula_list.cancel_edit()
        if isinstance(layer, (Point2D, Linear2D, Annotation2D)):
            self.settings_popup.hide()
            self.geometry_settings_popup.open_geometry(layer, anchor)
            return
        self.geometry_settings_popup.hide()
        self.settings_popup.open_layer(layer, anchor)

    def _open_manual_intersection_popup(self) -> None:
        if self.auto_intersections_action.isChecked():
            self.auto_intersections_action.setChecked(False)
        self.intersection_popup.open_at(self._popup_anchor(self.function_catalog_button))

    def _submit_formula(self, kind: str, latex: str) -> None:
        if self._active_layer_id is None:
            self.add_requested.emit(kind, latex)
            return
        self.update_requested.emit(self._active_layer_id, kind, latex)

    def _open_inline_formula_for_layer(self, layer_id: str, *_args: object) -> None:
        layer = self._layer(layer_id)
        # 线类几何对象由端点决定，不可行内编辑；点和函数曲线可以。
        if layer is None or isinstance(layer, Linear2D):
            return
        self.settings_popup.hide()
        self.catalog_popup.hide()
        self.formula_popup.dismiss()
        self._active_layer_id = None
        self._inline_active_layer_id = layer_id

    def _submit_inline_formula(self, layer_id: str, latex: str) -> None:
        self._submit_inline_formula_from_model(self.formula_list, layer_id, latex)

    def _submit_inline_formula_from_model(
        self, model: FormulaListWidget, layer_id: str, latex: str
    ) -> None:
        layer = model._layers.get(layer_id)
        if layer is not None and not isinstance(layer, Linear2D) and latex.strip():
            self._inline_active_layer_id = layer_id
            self.update_requested.emit(layer_id, layer.kind, latex)
            self.pane_update_requested.emit(self._pane_id_for_model(model), layer_id, layer.kind, latex)

    def _pane_id_for_model(self, model: FormulaListWidget) -> str:
        return next((pane_id for pane_id, candidate in self._pane_models.items() if candidate is model), self._pane_id)

    def _cancel_formula_edit(self) -> None:
        self._active_layer_id = None

    def _cancel_inline_formula_edit(self, layer_id: str | None = None) -> None:
        if layer_id is None or layer_id == self._inline_active_layer_id:
            self._inline_active_layer_id = None

    def _popup_anchor(self, widget: QWidget) -> QPoint:
        return widget.mapToGlobal(QPoint(0, widget.height() + 4))

    def sync_layer(self, layer_id: str, layer: Layer | None) -> None:
        if layer is None:
            return
        self._layers = [layer if current.id == layer_id else current for current in self._layers]
        self.formula_list.sync_layer(layer_id, layer)
        if self.settings_popup.isVisible() and self.settings_popup._layer_id == layer_id:
            self.settings_popup.open_layer(layer, None)
        if self.geometry_settings_popup.isVisible() and self.geometry_settings_popup._object_id == layer_id:
            self.geometry_settings_popup.open_geometry(layer, None)

    def _layer(self, layer_id: str | None) -> Layer | None:
        if layer_id is None:
            return None
        return next((layer for layer in self._layers if layer.id == layer_id), None)
