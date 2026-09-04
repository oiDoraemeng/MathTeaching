"""PyVista 场景的高级光照控制面板。"""

from copy import deepcopy

from PySide6.QtCore import QSignalBlocker, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from rendering.lighting import LightSettings, rotate_light_positions
from rendering.materials import MATERIAL_PRESETS
from ui.tokens import ThemeName, apply_drop_shadow, flatten_theme
from widgets.LightRotationWidget import LightRotationWidget


class LightingDialog(QDialog):
    """环境光、主光、补光和轮廓光的实时编辑器。"""

    settings_changed = Signal(object)
    material_changed = Signal(str)

    def __init__(
        self,
        settings: LightSettings,
        material_name: str = "光泽塑料",
        parent: QWidget | None = None,
        *,
        effective_theme: ThemeName | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("lightingDialog")
        self.setWindowTitle("高级光照")
        self.setMinimumWidth(430)
        self.effective_theme = effective_theme if effective_theme in ("light", "dark") else self._resolve_effective_theme(parent)
        self.set_effective_theme(self.effective_theme)
        self.settings = deepcopy(settings)
        self.material_name = material_name if material_name in MATERIAL_PRESETS else "光泽塑料"
        self._color_buttons: dict[str, QPushButton] = {}
        self._intensity_sliders: dict[str, QSlider] = {}
        self._intensity_value_labels: dict[str, QLabel] = {}
        self._position_spins: dict[str, list[QSpinBox]] = {}
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._emit_change_now)
        self._build_ui()
        self.set_effective_theme(self.effective_theme)

    @staticmethod
    def _resolve_effective_theme(parent: QWidget | None) -> ThemeName:
        window = getattr(parent, "window", None)
        if callable(window):
            window = window()
        resolved = getattr(window, "effective_theme", None)
        return resolved if resolved in ("light", "dark") else "light"

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        self.material_combo = QComboBox()
        self.material_combo.addItems(MATERIAL_PRESETS)
        self.material_combo.setCurrentText(self.material_name)
        self.material_combo.currentTextChanged.connect(self._set_material)
        self.ambient_slider = self._slider(0, 100, round(self.settings.ambient * 100))
        self.ambient_slider.valueChanged.connect(lambda value: self._set_ambient(value / 100))
        ambient_host, self.ambient_value_label = self._slider_row(self.ambient_slider)
        form = QFormLayout()
        form.addRow("曲面材质", self.material_combo)
        form.addRow("曲面环境光", ambient_host)
        layout.addLayout(form)
        self.rotation_widget = LightRotationWidget(self.settings.rotation_angle)
        self.rotation_widget.angle_changed.connect(self._set_rotation)
        layout.addWidget(self.rotation_widget)
        layout.addWidget(self._light_group("主光", "key"))
        layout.addWidget(self._light_group("补光", "fill"))
        layout.addWidget(self._light_group("轮廓光", "rim"))
        reset = QPushButton("恢复默认光照")
        reset.clicked.connect(self._reset_defaults)
        layout.addWidget(reset)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    def set_effective_theme(self, effective_theme: ThemeName) -> None:
        self.effective_theme = effective_theme
        apply_drop_shadow(self, "modal", effective_theme)
        if hasattr(self, "rotation_widget"):
            self.rotation_widget.set_theme(flatten_theme(effective_theme))

    def _light_group(self, label: str, key: str) -> QGroupBox:
        group = QGroupBox(label)
        form = QFormLayout(group)
        light = getattr(self.settings, key)
        intensity = self._slider(0, 200, round(light["intensity"] * 100))
        self._intensity_sliders[key] = intensity
        intensity.valueChanged.connect(lambda value, name=key: self._set_light(name, "intensity", value / 100))
        intensity_host, intensity_value_label = self._slider_row(intensity)
        self._intensity_value_labels[key] = intensity_value_label
        form.addRow("强度", intensity_host)
        direction = QHBoxLayout()
        position_spins: list[QSpinBox] = []
        for index, axis in enumerate(("X", "Y", "Z")):
            spin = QSpinBox()
            spin.setRange(-200, 200)
            spin.setValue(round(light["position"][index] * 100))
            spin.setSuffix(f"  {axis}")
            spin.valueChanged.connect(lambda value, name=key, coordinate=index: self._set_position(name, coordinate, value / 100))
            direction.addWidget(spin)
            position_spins.append(spin)
        self._position_spins[key] = position_spins
        direction_host = QWidget()
        direction_host.setLayout(direction)
        form.addRow("方向", direction_host)
        color = QPushButton()
        color.clicked.connect(lambda _checked=False, name=key: self._choose_color(name))
        self._color_buttons[key] = color
        self._set_color_button(key)
        form.addRow("颜色", color)
        return group

    @staticmethod
    def _slider(minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        return slider

    def _slider_row(self, slider: QSlider) -> tuple[QWidget, QLabel]:
        host = QWidget(self)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        value_label = QLabel(f"{slider.value()}%", host)
        value_label.setMinimumWidth(38)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda value: value_label.setText(f"{value}%"))
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        return host, value_label

    def _set_ambient(self, value: float) -> None:
        self.settings.ambient = value
        self._emit_change()

    def _set_material(self, material_name: str) -> None:
        self.material_name = material_name
        self.material_changed.emit(material_name)

    def _set_rotation(self, angle: float) -> None:
        rotate_light_positions(self.settings, angle)
        self._emit_change_now()

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

    def _set_color_button(self, name: str, source: object | None = None) -> None:
        value = getattr(source or self.settings, name)
        color = QColor(value) if isinstance(value, str) else QColor.fromRgbF(*value["color"])
        light_theme = flatten_theme("light")
        dark_theme = flatten_theme("dark")
        foreground = light_theme["text_on_accent"] if color.lightness() < 128 else dark_theme["text_on_accent"]
        self._color_buttons[name].setText(color.name().upper())
        self._color_buttons[name].setStyleSheet(f"background: {color.name()}; color: {foreground};")

    def _sync_controls_from_settings(self) -> None:
        """Refresh all controls after an external settings replacement."""
        with QSignalBlocker(self.material_combo):
            self.material_combo.setCurrentText(self.material_name)
        with QSignalBlocker(self.ambient_slider):
            self.ambient_slider.setValue(round(self.settings.ambient * 100))
        self.ambient_value_label.setText(f"{self.ambient_slider.value()}%")
        for key, slider in self._intensity_sliders.items():
            with QSignalBlocker(slider):
                slider.setValue(round(getattr(self.settings, key)["intensity"] * 100))
            self._intensity_value_labels[key].setText(f"{slider.value()}%")
            for index, spin in enumerate(self._position_spins[key]):
                with QSignalBlocker(spin):
                    spin.setValue(round(getattr(self.settings, key)["position"][index] * 100))
        with QSignalBlocker(self.rotation_widget):
            self.rotation_widget.set_angle(self.settings.rotation_angle)
        for name in self._color_buttons:
            self._set_color_button(name)

    def _reset_defaults(self) -> None:
        self.settings = LightSettings()
        self.material_name = "光泽塑料"
        self._sync_controls_from_settings()
        self.material_changed.emit(self.material_name)
        self._emit_change_now()

    def _emit_change(self) -> None:
        # 滑块每经过一个像素都会发出信号；合并这些事件以稳定刷新交互渲染器。
        self._update_timer.start(70)

    def _emit_change_now(self) -> None:
        self._update_timer.stop()
        self.settings_changed.emit(self.settings)
