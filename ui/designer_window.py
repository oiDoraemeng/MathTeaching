"""Qt Designer 主窗口表单的行为控制器。"""

from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QTimer, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFileDialog, QComboBox, QFrame, QLabel, QSlider, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from models.parameters import HyperboloidParameters
from models.surface_settings import SurfaceSettings
from rendering.lighting import LightSettings, update_light_rotation
from rendering.scene import build_scene, update_lighting, update_surface_colors, update_surface_geometry
from ui.lighting_dialog import LightingDialog
from rendering.materials import MATERIAL_PRESETS, material_preset


class MainWindow:
    """加载 Designer 表单，并连接到 PyVista 场景。"""

    def __init__(self) -> None:
        self.lighting = LightSettings()
        self.surface = SurfaceSettings()
        self.material_name = "光泽塑料"
        self._lighting_dialog: LightingDialog | None = None
        self._parameter_timer = QTimer()
        self._parameter_timer.setSingleShot(True)
        self._parameter_timer.setInterval(16)
        self._parameter_timer.timeout.connect(self._render_interactive_scene)
        self.window = self._load_designer_form()
        self._configure_viewport()
        self._bind_controls()
        self._apply_style()
        self._render_scene()

    def _load_designer_form(self) -> QWidget:
        form_path = Path(__file__).with_name("main_window.ui")
        form_file = QFile(str(form_path))
        if not form_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Unable to open Designer form: {form_path}")
        try:
            window = QUiLoader().load(form_file)
        finally:
            form_file.close()
        if window is None:
            raise RuntimeError(f"Unable to load Designer form: {form_path}")
        return window

    def _configure_viewport(self) -> None:
        host = self._widget("viewportHost", QWidget)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plotter = QtInteractor(host)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.plotter.interactor)

    def _bind_controls(self) -> None:
        self.sliders = {name: self._widget(f"{name}Slider", QSlider) for name in ("a", "b", "c")}
        self.value_labels = {name: self._widget(f"{name}Value", QLabel) for name in ("a", "b", "c")}
        self.axes_button = self._widget("axesButton")
        self.helpers_button = self._widget("helpersButton")
        # 材质选择下拉框（在 UI 中定义为 materialCombo）
        try:
            self.material_combo = self._widget("materialCombo", QComboBox)
        except RuntimeError:
            self.material_combo = None
        if self.material_combo is not None:
            # 保证下拉项与预设一致
            self.material_combo.clear()
            for name in MATERIAL_PRESETS:
                self.material_combo.addItem(name)
            # 绑定回调以实时切换材质
            self.material_combo.currentTextChanged.connect(self._material_changed)
            self.material_preview = self._widget("materialColorPreview", QFrame)
            self.material_detail = self._widget("materialDetailLabel", QLabel)
        for name, slider in self.sliders.items():
            self.value_labels[name].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            slider.valueChanged.connect(lambda value, key=name: self._parameter_changed(key, value))
            slider.sliderReleased.connect(self._finish_parameter_drag)
            self._parameter_changed(name, slider.value())
        self.axes_button.toggled.connect(self._render_scene)
        self.helpers_button.toggled.connect(self._render_scene)
        self._widget("regenerateButton").clicked.connect(self._render_scene)
        self._widget("lightingButton").clicked.connect(self._show_lighting_dialog)
        self._widget("saveButton").clicked.connect(self._save_screenshot)
        if self.material_combo is not None:
            self._update_material_summary()

    def _widget(self, name: str, widget_type: type | None = None):
        widget = self.window.findChild(widget_type or QWidget, name)
        if widget is None:
            raise RuntimeError(f"Designer form is missing required widget: {name}")
        return widget

    def _parameter_changed(self, name: str, value: int) -> None:
        self.value_labels[name].setText(f"{value / 100:.2f}")
        if self.window.isVisible():
            self._parameter_timer.start()

    def _parameters(self) -> HyperboloidParameters:
        return HyperboloidParameters(**{name: slider.value() / 100.0 for name, slider in self.sliders.items()})

    def _render_interactive_scene(self) -> None:
        update_surface_geometry(self.plotter, self._parameters())

    def _finish_parameter_drag(self) -> None:
        self._parameter_timer.stop()
        self._render_scene()

    def _render_scene(self, interactive: bool = False) -> None:
        camera_position = self._current_camera_position()
        build_scene(
            self.plotter,
            self._parameters(),
            self.axes_button.isChecked(),
            self.helpers_button.isChecked(),
            lighting=self.lighting,
            surface_settings=self.surface,
            material_name=self.material_name,
            camera_position=camera_position,
            interactive=interactive,
        )
        self.plotter.render()

    def _current_camera_position(self) -> list | None:
        """获取当前相机位置、焦点和上方向，首次构建时返回空值。"""
        if "hyperboloid" not in self.plotter.renderer.actors:
            return None
        return [tuple(vector) for vector in self.plotter.camera_position]

    def _material_changed(self, name: str) -> None:
        """应用下拉框选中的材质预设及其内外表面默认颜色。"""
        self.material_name = name
        preset = material_preset(name)
        self.surface.outer_color = preset["outer_color"]
        self.surface.inner_color = preset["inner_color"]
        self.surface.use_preset_colors = True
        self._update_material_summary(preset)
        self._render_scene()

    def _update_material_summary(self, preset: dict | None = None) -> None:
        """更新材质下拉框下方的颜色预览与物质感说明。"""
        preset = preset or material_preset(self.material_name)
        descriptions = {
            "光泽塑料": "高光强、半透明的聚合物表面",
            "透明玻璃": "低漫反射、高透光的玻璃质感",
            "磨砂陶瓷": "柔和反光、不透明的细腻表面",
            "抛光金属": "高镜面反射，明亮的抛光金属高光",
            "半透明玉石": "柔和透光、温润的矿物质感",
        }
        self.material_detail.setText(descriptions.get(self.material_name, "自定义表面材质"))
        self.material_preview.setStyleSheet(
            f"background: {preset['outer_color']}; border: 1px solid rgba(0, 0, 0, 0.14); border-radius: 9px;"
        )

    def _save_screenshot(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self.window, "保存场景", str(Path.home() / "hyperboloid.png"), "PNG Images (*.png)"
        )
        if not filename:
            return
        build_scene(
            self.plotter,
            self._parameters(),
            self.axes_button.isChecked(),
            self.helpers_button.isChecked(),
            high_quality=True,
            lighting=self.lighting,
            surface_settings=self.surface,
            material_name=self.material_name,
            camera_position=self._current_camera_position(),
        )
        try:
            # 高质量场景重建后先提交一帧 VTK 渲染，确保光源和高光进入像素缓冲区。
            self.plotter.render()
            self.plotter.ren_win.Render()
            self.plotter.screenshot(filename, return_img=False)
        finally:
            self._render_scene()

    def _show_lighting_dialog(self) -> None:
        if self._lighting_dialog is None:
            self._lighting_dialog = LightingDialog(self.lighting, self.surface, self.window)
            self._lighting_dialog.setWindowModality(Qt.WindowModality.NonModal)
            self._lighting_dialog.settings_changed.connect(self._update_lighting)
            self._lighting_dialog.surface_settings_changed.connect(self._update_surface_colors)
            self._lighting_dialog.rotation_changed.connect(self._update_light_rotation)
        self._lighting_dialog.show()
        self._lighting_dialog.raise_()
        self._lighting_dialog.activateWindow()

    def _update_lighting(self, settings: LightSettings) -> None:
        self.lighting = settings
        update_lighting(self.plotter, self.lighting)

    def _update_surface_colors(self, settings: SurfaceSettings) -> None:
        self.surface = settings
        update_surface_colors(self.plotter, self.surface)

    def _update_light_rotation(self, angle: float) -> None:
        update_light_rotation(self.plotter, self.lighting, angle)

    def _apply_style(self) -> None:
        self.window.setStyleSheet("""
            #sidebar { background: #ffffff; border-right: 1px solid #dde1e8; }
            QLabel { color: #29313d; font-size: 13px; }
            #titleLabel { font-size: 21px; font-weight: 700; }
            #surfaceLabel { color: #7457af; font-size: 15px; font-weight: 600; }
            #formulaLabel { background: #f7f6fb; border: 1px solid #e6e2f0; padding: 10px; font-size: 14px; }
            #parameterLabel { font-weight: 700; font-size: 14px; }
            #materialLabel { color: #5d4b87; font-size: 13px; font-weight: 700; }
            #materialCombo { min-height: 34px; background: #fbfaff; color: #2e2740; border: 1px solid #cfc5e8; border-radius: 5px; padding: 3px 28px 3px 10px; font-size: 13px; font-weight: 600; }
            #materialCombo:hover { border-color: #9a82d0; background: #f6f2ff; }
            #materialCombo:focus { border: 2px solid #8363c4; }
            #materialCombo::drop-down { border: 0; width: 28px; }
            #materialCombo::down-arrow { width: 8px; height: 8px; }
            #materialPreviewBand { background: #faf8ff; border: 1px solid #e3ddf0; border-radius: 5px; }
            #materialDetailLabel { color: #6f667f; font-size: 11px; }
            #hintLabel { color: #737a87; font-size: 11px; }
            QPushButton { background: #f0ecfb; color: #4d397e; border: 1px solid #d6cdef; border-radius: 5px; padding: 9px; font-weight: 600; }
            QPushButton:hover { background: #e5ddf8; }
            QPushButton:checked { background: #8363c4; color: white; border-color: #8363c4; }
            QSlider::groove:horizontal { height: 5px; background: #e2e5eb; border-radius: 2px; }
            QSlider::handle:horizontal { width: 15px; margin: -5px 0; border-radius: 7px; background: #8264c4; }
            QSlider::sub-page:horizontal { background: #b9a5e3; border-radius: 2px; }
        """)

    def show(self) -> None:
        self.window.show()
