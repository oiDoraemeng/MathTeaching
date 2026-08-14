"""Floating scene appearance controls for the viewport."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QPushButton,
    QVBoxLayout,
)

from models.scene_mode import SceneMode


class SceneSettingsPanel(QFrame):
    background_changed = Signal(str)
    axis_color_mode_changed = Signal(str)
    grid_changed = Signal(bool)
    ticks_changed = Signal(bool)
    tick_spacing_mode_changed = Signal(str)
    tick_spacing_changed = Signal(float)
    intersections_changed = Signal(bool)
    lighting_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sceneSettingsPanel")
        self.setFixedWidth(264)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.form = QFormLayout()
        self.background_combo = QComboBox(self)
        self.background_combo.addItem("白色背景", "light")
        self.background_combo.addItem("黑色背景", "dark")
        self.axis_combo = QComboBox(self)
        self.axis_combo.addItem("自动对比", "contrast")
        self.axis_combo.addItem("彩色轴", "color")
        self.grid_check = QCheckBox("显示网格", self)
        self.ticks_check = QCheckBox("显示刻度", self)
        self.tick_spacing_combo = QComboBox(self)
        self.tick_spacing_combo.addItem("自动", "auto")
        self.tick_spacing_combo.addItem("自定义", "custom")
        self.tick_spacing_input = QDoubleSpinBox(self)
        self.tick_spacing_input.setDecimals(6)
        self.tick_spacing_input.setRange(0.000001, 1_000_000_000.0)
        self.tick_spacing_input.setSingleStep(0.5)
        self.tick_spacing_input.setValue(1.0)
        self.tick_spacing_input.setSuffix(" 单位")
        self.intersections_check = QCheckBox("显示全局交线", self)
        self.form.addRow("背景", self.background_combo)
        self.form.addRow("坐标轴", self.axis_combo)
        self.form.addRow(self.grid_check)
        self.form.addRow(self.ticks_check)
        self.form.addRow("刻度间距", self.tick_spacing_combo)
        self.form.addRow("自定义间距", self.tick_spacing_input)
        self.form.addRow(self.intersections_check)
        layout.addLayout(self.form)
        self.lighting_button = QPushButton("灯光与材质", self)
        self.lighting_button.clicked.connect(self.lighting_requested)
        layout.addWidget(self.lighting_button)
        layout.addStretch()
        self.background_combo.currentIndexChanged.connect(self._emit_background)
        self.axis_combo.currentIndexChanged.connect(self._emit_axis)
        self.grid_check.toggled.connect(self.grid_changed)
        self.ticks_check.toggled.connect(self.ticks_changed)
        self.tick_spacing_combo.currentIndexChanged.connect(self._emit_tick_spacing_mode)
        self.tick_spacing_input.valueChanged.connect(self.tick_spacing_changed)
        self.intersections_check.toggled.connect(self.intersections_changed)
        self._mode = SceneMode.THREE_D
        self.set_mode(self._mode)

    def set_mode(self, mode: SceneMode) -> None:
        self._mode = mode
        is_2d = mode is SceneMode.TWO_D
        self.grid_check.setVisible(is_2d)
        self.intersections_check.setVisible(not is_2d)
        self.lighting_button.setVisible(not is_2d)
        self._sync_spacing_input_visibility()

    def set_values(
        self,
        *,
        background: str,
        axis_color_mode: str,
        grid: bool,
        ticks: bool = True,
        tick_spacing_mode: str = "auto",
        tick_spacing: float = 1.0,
        intersections: bool = False,
    ) -> None:
        for widget, value in (
            (self.background_combo, background),
            (self.axis_combo, axis_color_mode),
        ):
            widget.blockSignals(True)
            widget.setCurrentIndex(max(0, widget.findData(value)))
            widget.blockSignals(False)
        for widget, value in (
            (self.grid_check, grid),
            (self.ticks_check, ticks),
            (self.intersections_check, intersections),
        ):
            widget.blockSignals(True)
            widget.setChecked(value)
            widget.blockSignals(False)
        self.tick_spacing_combo.blockSignals(True)
        self.tick_spacing_combo.setCurrentIndex(max(0, self.tick_spacing_combo.findData(tick_spacing_mode)))
        self.tick_spacing_combo.blockSignals(False)
        self.tick_spacing_input.blockSignals(True)
        self.tick_spacing_input.setValue(max(self.tick_spacing_input.minimum(), tick_spacing))
        self.tick_spacing_input.blockSignals(False)
        self._sync_spacing_input_visibility()

    def open_at(self, anchor: QPoint) -> None:
        self.adjustSize()
        self.move(anchor)
        self.show()
        self.raise_()

    def _emit_background(self, index: int) -> None:
        value = self.background_combo.itemData(index)
        if value:
            self.background_changed.emit(str(value))

    def _emit_axis(self, index: int) -> None:
        value = self.axis_combo.itemData(index)
        if value:
            self.axis_color_mode_changed.emit(str(value))

    def _emit_tick_spacing_mode(self, index: int) -> None:
        value = self.tick_spacing_combo.itemData(index)
        self._sync_spacing_input_visibility()
        if value:
            self.tick_spacing_mode_changed.emit(str(value))

    def _sync_spacing_input_visibility(self) -> None:
        is_custom = self.tick_spacing_combo.currentData() == "custom"
        self.tick_spacing_input.setVisible(is_custom)
        set_row_visible = getattr(self.form, "setRowVisible", None)
        if set_row_visible is not None:
            set_row_visible(self.tick_spacing_input, is_custom)
