"""PyVista 场景的高级光照控制面板。"""

from copy import deepcopy

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from rendering.lighting import LightSettings


class LightingDialog(QDialog):
    """环境光、主光、补光和轮廓光的实时编辑器。"""

    settings_changed = Signal(object)

    def __init__(self, settings: LightSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("高级光照")
        self.setMinimumWidth(430)
        self.settings = deepcopy(settings)
        self._color_buttons: dict[str, QPushButton] = {}
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._emit_change_now)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        ambient = self._slider(0, 100, round(self.settings.ambient * 100))
        ambient.valueChanged.connect(lambda value: self._set_ambient(value / 100))
        form = QFormLayout()
        form.addRow("曲面环境光", ambient)
        layout.addLayout(form)
        layout.addWidget(self._surface_color_group())
        layout.addWidget(self._light_group("主光", "key"))
        layout.addWidget(self._light_group("补光", "fill"))
        layout.addWidget(self._light_group("轮廓光", "rim"))
        reset = QPushButton("恢复默认光照")
        reset.clicked.connect(self._reset_defaults)
        layout.addWidget(reset)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    def _light_group(self, label: str, key: str) -> QGroupBox:
        group = QGroupBox(label)
        form = QFormLayout(group)
        light = getattr(self.settings, key)
        intensity = self._slider(0, 200, round(light["intensity"] * 100))
        intensity.valueChanged.connect(lambda value, name=key: self._set_light(name, "intensity", value / 100))
        form.addRow("强度", intensity)
        direction = QHBoxLayout()
        for index, axis in enumerate(("X", "Y", "Z")):
            spin = QSpinBox()
            spin.setRange(-200, 200)
            spin.setValue(round(light["position"][index] * 100))
            spin.setSuffix(f"  {axis}")
            spin.valueChanged.connect(lambda value, name=key, coordinate=index: self._set_position(name, coordinate, value / 100))
            direction.addWidget(spin)
        direction_host = QWidget()
        direction_host.setLayout(direction)
        form.addRow("方向", direction_host)
        color = QPushButton()
        color.clicked.connect(lambda _checked=False, name=key: self._choose_color(name))
        self._color_buttons[key] = color
        self._set_color_button(key)
        form.addRow("颜色", color)
        return group

    def _surface_color_group(self) -> QGroupBox:
        group = QGroupBox("曲面双面颜色")
        form = QFormLayout(group)
        for label, name in (("凸面（外部）", "outer_color"), ("凹面（内部）", "inner_color")):
            button = QPushButton()
            button.clicked.connect(lambda _checked=False, key=name: self._choose_surface_color(key))
            self._color_buttons[name] = button
            self._set_color_button(name)
            form.addRow(label, button)
        return group

    @staticmethod
    def _slider(minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        return slider

    def _set_ambient(self, value: float) -> None:
        self.settings.ambient = value
        self._emit_change()

    def _set_light(self, name: str, field: str, value: float) -> None:
        getattr(self.settings, name)[field] = value
        self._emit_change()

    def _set_position(self, name: str, index: int, value: float) -> None:
        position = list(getattr(self.settings, name)["position"])
        position[index] = value
        getattr(self.settings, name)["position"] = tuple(position)
        self._emit_change()

    def _choose_color(self, name: str) -> None:
        color = QColor.fromRgbF(*getattr(self.settings, name)["color"])
        selected = QColorDialog.getColor(color, self, "选择光源颜色")
        if selected.isValid():
            getattr(self.settings, name)["color"] = selected.getRgbF()[:3]
            self._set_color_button(name)
            self._emit_change_now()

    def _choose_surface_color(self, name: str) -> None:
        selected = QColorDialog.getColor(QColor(getattr(self.settings, name)), self, "选择曲面颜色")
        if selected.isValid():
            setattr(self.settings, name, selected.name())
            self._set_color_button(name)
            self._emit_change_now()

    def _set_color_button(self, name: str) -> None:
        value = getattr(self.settings, name)
        color = QColor(value) if isinstance(value, str) else QColor.fromRgbF(*value["color"])
        self._color_buttons[name].setText(color.name().upper())
        self._color_buttons[name].setStyleSheet(f"background: {color.name()}; color: {'#ffffff' if color.lightness() < 128 else '#17202a'};")

    def _reset_defaults(self) -> None:
        self.settings = LightSettings()
        self.close()
        self._emit_change_now()

    def _emit_change(self) -> None:
        # 滑块每经过一个像素都会发出信号；合并这些事件以稳定刷新交互渲染器。
        self._update_timer.start(70)

    def _emit_change_now(self) -> None:
        self._update_timer.stop()
        self.settings_changed.emit(self.settings)
