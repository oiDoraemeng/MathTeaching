"""Main window composition for the CAS surface explorer."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from MathInputWidget import LatexParseError, LatexParser
from geometry.cas_surface import ExpressionError, parse_surface_expression
from geometry.standard_surfaces import BUILTIN_SURFACES, DEFAULT_BUILTIN_ID, create_builtin_layer
from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.layer_scene import LayerRenderError, LayerSceneController
from rendering.lighting import LightSettings
from rendering.scene import build_scene, update_lighting
from ui.algebra_panel import AlgebraPanel
from ui.lighting_dialog import LightingDialog


class MainWindow:
    """Load the Designer shell and add the GeoGebra-like algebra workflow."""

    def __init__(self) -> None:
        self.lighting = LightSettings()
        self.material_name = "光泽塑料"
        self._lighting_dialog: LightingDialog | None = None
        self.plot_domain = PlotDomain()
        self.latex_parser = LatexParser()
        self.layers: list[SurfaceLayer] = [create_builtin_layer(DEFAULT_BUILTIN_ID)]
        self.layer_controller: LayerSceneController | None = None

        self.window = self._load_designer_form()
        self._install_algebra_panel()
        self._configure_viewport()
        self._bind_algebra_panel()
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

    def _install_algebra_panel(self) -> None:
        root_layout = self.window.findChild(QHBoxLayout, "rootLayout")
        if root_layout is None:
            raise RuntimeError("Designer form must use a horizontal root layout")

        legacy_sidebar = self.window.findChild(QWidget, "sidebar")
        if legacy_sidebar is not None:
            root_layout.removeWidget(legacy_sidebar)
            legacy_sidebar.deleteLater()

        self.algebra_panel = AlgebraPanel(self.window)
        root_layout.insertWidget(0, self.algebra_panel)

    def _configure_viewport(self) -> None:
        host = self._widget("viewportHost", QWidget)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plotter = QtInteractor(host)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.plotter.interactor)

    def _bind_algebra_panel(self) -> None:
        panel = self.algebra_panel
        panel.set_builtin_surfaces((surface.id, surface.name) for surface in BUILTIN_SURFACES)
        panel.add_requested.connect(self._add_cas_surface)
        panel.builtin_requested.connect(self._add_builtin_surface)
        panel.lighting_requested.connect(self._show_lighting_dialog)
        panel.update_requested.connect(self._update_surface_expression)
        panel.delete_requested.connect(self._remove_surface)
        panel.visibility_changed.connect(self._set_surface_visibility)
        panel.intersections_visibility_changed.connect(self._set_surface_intersections_visibility)
        panel.color_changed.connect(self._set_surface_color)
        panel.opacity_changed.connect(self._set_surface_opacity)
        panel.range_changed.connect(self._set_surface_range)
        panel.auto_intersections_changed.connect(self._set_auto_intersections)
        panel.manual_intersection_requested.connect(self._add_manual_intersection)

    def _render_scene(self) -> None:
        camera_position = self._current_camera_position()
        build_scene(
            self.plotter,
            show_axes=True,
            show_helpers=True,
            lighting=self.lighting,
            camera_position=camera_position,
            base_surface=False,
        )
        self.layer_controller = LayerSceneController(
            self.plotter,
            self.plot_domain,
            ambient=self.lighting.ambient,
            material_name=self.material_name,
        )
        available_layers: list[SurfaceLayer] = []
        for layer in self.layers:
            try:
                self.layer_controller.add_layer(layer)
            except (ExpressionError, LayerRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self.layers = available_layers
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status("已准备好")
        self.plotter.render()

    def _add_cas_surface(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return

        layer = SurfaceLayer(
            name=f"曲面 {len(self.layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: 1.0 for name in parsed.parameter_names},
        )
        if self._add_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_builtin_surface(self, builtin_id: str) -> None:
        self._add_layer(create_builtin_layer(builtin_id))

    def _add_layer(self, layer: SurfaceLayer) -> bool:
        if self.layer_controller is None:
            return False
        try:
            self.layer_controller.add_layer(layer)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲面: {error}", is_error=True)
            return False
        self.layers.append(layer)
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status(f"已添加 {layer.name}")
        self.plotter.render()
        return True

    def _update_surface_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._layer(layer_id)
        if current is None or self.layer_controller is None:
            return
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return

        updated = replace(
            current,
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: current.parameters.get(name, 1.0) for name in parsed.parameter_names},
            builtin_id=None,
        )
        try:
            self.layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面: {error}", is_error=True)
            return
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self.plotter.render()

    def _parse_mathlive_surface(self, latex: str, kind: str):
        """Normalize MathLive LaTeX before passing its safe text form to CAS."""
        formula = self.latex_parser.parse(latex, kind)
        return formula, parse_surface_expression(formula.canonical_source, formula.kind)

    def _remove_surface(self, layer_id: str) -> None:
        if self.layer_controller is None:
            return
        self.layer_controller.remove_layer(layer_id)
        self.layers = [layer for layer in self.layers if layer.id != layer_id]
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status("已删除曲面")
        self.plotter.render()

    def _set_surface_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_visible(layer_id, visible)
        self._replace_layer(layer_id, visible=visible)
        self.plotter.render()

    def _set_surface_intersections_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_intersections_visible(layer_id, visible)
        self._replace_layer(layer_id, intersections_visible=visible)
        self.plotter.render()

    def _set_surface_color(self, layer_id: str, color: str) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_color(layer_id, color)
        self._replace_layer(layer_id, color=color)
        self.plotter.render()

    def _set_surface_opacity(self, layer_id: str, opacity: float) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_opacity(layer_id, opacity)
        self._replace_layer(layer_id, opacity=opacity)
        self.plotter.render()

    def _set_surface_range(self, layer_id: str, range_scale: float) -> None:
        current = self._layer(layer_id)
        if current is None or self.layer_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self.layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面范围: {error}", is_error=True)
            return
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 x{updated.range_scale:.1f}")
        self.plotter.reset_camera()
        self.plotter.render()

    def _set_auto_intersections(self, enabled: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_auto_intersections(enabled)
        self.algebra_panel.set_status("交线自动计算已开启" if enabled else "请选择两个曲面计算交线")
        self.plotter.render()

    def _show_lighting_dialog(self) -> None:
        if self._lighting_dialog is None:
            self._lighting_dialog = LightingDialog(self.lighting, self.material_name, self.window)
            self._lighting_dialog.setWindowModality(Qt.WindowModality.NonModal)
            self._lighting_dialog.settings_changed.connect(self._update_lighting)
            self._lighting_dialog.material_changed.connect(self._update_material)
            self._lighting_dialog.finished.connect(self._clear_lighting_dialog)
        self._lighting_dialog.show()
        self._lighting_dialog.raise_()
        self._lighting_dialog.activateWindow()

    def _clear_lighting_dialog(self, _result: int) -> None:
        self._lighting_dialog = None

    def _update_lighting(self, settings: LightSettings) -> None:
        self.lighting = settings
        if self.layer_controller is not None:
            self.layer_controller.set_ambient(settings.ambient)
        update_lighting(self.plotter, settings)

    def _update_material(self, material_name: str) -> None:
        self.material_name = material_name
        if self.layer_controller is not None:
            self.layer_controller.set_material(material_name)
        self.plotter.render()

    def _add_manual_intersection(self, first_id: str, second_id: str) -> None:
        if self.layer_controller is None:
            return
        try:
            self.layer_controller.set_manual_intersection_pair(first_id, second_id, True)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法计算交线: {error}", is_error=True)
            return
        self.algebra_panel.set_status("已计算所选曲面的交线")
        self.plotter.render()

    def _replace_layer(self, layer_id: str, **changes: object) -> None:
        self.layers = [replace(layer, **changes) if layer.id == layer_id else layer for layer in self.layers]

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self.layers if layer.id == layer_id), None)

    def _current_camera_position(self) -> list | None:
        if not getattr(self, "plotter", None) or not self.plotter.renderer.actors:
            return None
        return [tuple(vector) for vector in self.plotter.camera_position]

    def _widget(self, name: str, widget_type: type[QWidget]) -> QWidget:
        widget = self.window.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Designer form is missing required widget: {name}")
        return widget

    def _apply_style(self) -> None:
        self.window.setStyleSheet(
            """
            QMainWindow { background: #f7f8fa; }
            #viewportHost { background: #f7f8fa; }
            #algebraPanel { background: #ffffff; border-right: 1px solid #d9dde3; }
            #algebraTitle { color: #17212e; font-size: 20px; font-weight: 700; }
            #algebraSubtitle { color: #667085; font-size: 12px; }
            #algebraLayerRow { background: #f9fafb; border: 1px solid #dfe3e8; border-radius: 6px; }
            #algebraStatus { color: #536273; font-size: 12px; padding-top: 2px; }
            #algebraStatus[isError="true"] { color: #b42318; }
            QScrollArea { border: 0; background: #ffffff; }
            QLabel { color: #263241; font-size: 12px; }
            QLineEdit, QComboBox { min-height: 30px; background: #ffffff; color: #1f2937; border: 1px solid #cbd3dd; border-radius: 4px; padding: 2px 7px; }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #2f7ebd; }
            QPushButton { min-height: 30px; background: #edf3f7; color: #1f547d; border: 1px solid #b9d0e1; border-radius: 4px; padding: 3px 8px; font-weight: 600; }
            QPushButton:hover { background: #dfeef7; }
            QPushButton:disabled { color: #9aa5b1; background: #f5f6f8; border-color: #e0e4e8; }
            QToolButton { min-width: 24px; min-height: 24px; color: #4a5563; border: 1px solid transparent; border-radius: 4px; }
            QToolButton:hover { background: #eef2f5; border-color: #cfd8e1; }
            QCheckBox { color: #405064; spacing: 4px; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #aab5c1; border-radius: 3px; background: #ffffff; }
            QCheckBox::indicator:checked { background: #2777b6; border-color: #2777b6; }
            QSlider::groove:horizontal { height: 4px; background: #d7e0e7; border-radius: 2px; }
            QSlider::handle:horizontal { width: 13px; margin: -5px 0; border-radius: 6px; background: #2f7ebd; }
            """
        )

    def show(self) -> None:
        self.window.show()
