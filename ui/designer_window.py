"""用于组合相互独立二维/三维公式场景的主窗口。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QEvent, QFile, QIODevice, QObject, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from MathInputWidget import LatexParseError, LatexParser
from geometry.cas_curve import CurveExpressionError, parse_curve_expression
from geometry.cas_surface import ExpressionError, parse_surface_expression
from geometry.standard_surfaces import BUILTIN_SURFACES, DEFAULT_BUILTIN_ID, create_builtin_layer
from models.curve_layer import CurveLayer, Plot2DDomain
from models.function_catalog import catalog_entries, catalog_entry
from models.scene_mode import SceneAppearance, SceneMode
from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.axis import ThreeDAxes, add_cartesian_axes
from rendering.curve_scene import CurveRenderError, CurveSceneController
from rendering.layer_scene import LayerRenderError, LayerSceneController
from rendering.lighting import LightSettings
from rendering.scene import build_scene, configure_3d_camera_interaction, update_lighting
from rendering.ticks import ViewportBounds, tick_spacing, visible_2d_bounds, visible_3d_axis_extent
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from ui.algebra_panel import AlgebraPanel
from ui.lighting_dialog import LightingDialog
from ui.scene_settings import SceneSettingsPanel


# 辅助线在视口四周额外绘制此比例；小幅平移和缩放仍落在既有区域内，
# 因而无需立刻重建辅助线和曲线采样。
_GUIDE_MARGIN = 0.6


class _ViewportResizeFilter(QObject):
    """在原生 VTK 视口调整尺寸时，让 Qt 覆盖控件保持位于上层。"""

    def __init__(self, callback: Callable[[], None], parent: QObject) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._callback()
        return False


class MainWindow:
    """加载 Designer 窗口骨架，并协调两个相互独立的绘图工作区。"""

    def __init__(self) -> None:
        self.lighting = LightSettings()
        self.material_name = "光泽塑料"
        self._lighting_dialog: LightingDialog | None = None
        self.scene_mode = SceneMode.THREE_D
        self.plot_domain = PlotDomain()
        self.curve_domain = Plot2DDomain()
        self.latex_parser = LatexParser()
        self.layers: list[SurfaceLayer] = [create_builtin_layer(DEFAULT_BUILTIN_ID)]
        self.curve_layers: list[CurveLayer] = []
        self.layer_controller: LayerSceneController | None = None
        self.curve_controller: CurveSceneController | None = None
        self.scene_appearances = {
            SceneMode.THREE_D: SceneAppearance(show_grid=False, show_intersections=False),
            SceneMode.TWO_D: SceneAppearance(show_grid=True, show_intersections=False),
        }
        self._three_d_camera_position: list | None = None
        self._two_d_parallel_scale: float | None = None
        self._two_d_camera_position: list | None = None
        self._two_d_guide_spacing: float | None = None
        self._two_d_guide_bounds: ViewportBounds | None = None
        self._two_d_sample_bounds: ViewportBounds | None = None
        self._two_d_guides: TwoDGuides | None = None
        self._three_d_axes: ThreeDAxes | None = None
        self._three_d_spacing: float | None = None
        self._three_d_extent: float | None = None
        self._last_domain_extent: float | None = None
        self._viewport_refreshing = False
        self._viewport_refresh_pending = False
        self._viewport_refresh_timer: QTimer | None = None
        self._viewport_interaction_observer: int | None = None
        self._intersection_color_revision = 0
        self._scene_settings_closing = False

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
        self.viewport_host = self._widget("viewportHost", QWidget)
        layout = QVBoxLayout(self.viewport_host)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plotter = QtInteractor(self.viewport_host)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.plotter.interactor)

        self.viewport_toolbar = QFrame(self.viewport_host)
        self.viewport_toolbar.setObjectName("viewportToolbar")
        toolbar_layout = QVBoxLayout(self.viewport_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)
        self.scene_settings_button = QToolButton(self.viewport_toolbar)
        self.scene_settings_button.setText("⚙")
        self.scene_settings_button.setToolTip("场景设置")
        self.scene_settings_button.setFixedSize(38, 38)
        self.scene_mode_button = QToolButton(self.viewport_toolbar)
        self.scene_mode_button.setToolTip("切换二维和三维场景")
        self.scene_mode_button.setFixedSize(38, 38)
        toolbar_layout.addWidget(self.scene_settings_button)
        toolbar_layout.addWidget(self.scene_mode_button)
        self.viewport_toolbar.adjustSize()

        self.scene_settings_panel = SceneSettingsPanel(self.viewport_host)
        self.scene_settings_panel.hide()
        self._scene_settings_animation = QPropertyAnimation(self.scene_settings_panel, b"geometry", self.window)
        self._scene_settings_animation.setDuration(180)
        self._scene_settings_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scene_settings_animation.finished.connect(self._finish_scene_settings_animation)
        self._viewport_resize_filter = _ViewportResizeFilter(self._on_viewport_host_changed, self.viewport_host)
        self.viewport_host.installEventFilter(self._viewport_resize_filter)
        self._position_viewport_overlays()
        self.scene_settings_button.clicked.connect(self._toggle_scene_settings)
        self.scene_mode_button.clicked.connect(self._toggle_scene_mode)
        self.scene_settings_panel.background_changed.connect(self._set_scene_background)
        self.scene_settings_panel.axis_color_mode_changed.connect(self._set_axis_color_mode)
        self.scene_settings_panel.grid_changed.connect(self._set_grid_visible)
        self.scene_settings_panel.ticks_changed.connect(self._set_ticks_visible)
        self.scene_settings_panel.tick_spacing_mode_changed.connect(self._set_tick_spacing_mode)
        self.scene_settings_panel.tick_spacing_changed.connect(self._set_tick_spacing)
        self.scene_settings_panel.intersections_changed.connect(self._set_global_intersections_visible)
        self.scene_settings_panel.lighting_requested.connect(self._show_lighting_dialog)
        self._viewport_refresh_timer = QTimer(self.window)
        self._viewport_refresh_timer.setSingleShot(True)
        self._viewport_refresh_timer.setInterval(90)
        self._viewport_refresh_timer.timeout.connect(self._refresh_visible_viewport)
        interactor = getattr(self.plotter, "iren", None)
        if interactor is not None:
            try:
                self._viewport_interaction_observer = interactor.add_observer(
                    "EndInteractionEvent", self._on_viewport_interaction_finished
                )
            except (AttributeError, RuntimeError, TypeError):
                self._viewport_interaction_observer = None
        self._sync_scene_controls()

    def _on_viewport_host_changed(self) -> None:
        self._position_viewport_overlays()
        self._queue_viewport_refresh()

    def _on_viewport_interaction_finished(self, *_args: object) -> None:
        self._queue_viewport_refresh()

    def _queue_viewport_refresh(self) -> None:
        if (
            self._viewport_refreshing
            or self._viewport_refresh_pending
            or self._viewport_refresh_timer is None
        ):
            return
        self._viewport_refresh_pending = True
        self._viewport_refresh_timer.start()

    def _position_viewport_overlays(self) -> None:
        if not hasattr(self, "viewport_toolbar"):
            return
        host = self.viewport_host
        toolbar_width = self.viewport_toolbar.width()
        self.viewport_toolbar.move(max(8, host.width() - toolbar_width - 12), 12)
        self.viewport_toolbar.raise_()
        if (
            self.scene_settings_panel.isVisible()
            and self._scene_settings_animation.state() != QPropertyAnimation.State.Running
        ):
            self.scene_settings_panel.setGeometry(self._scene_settings_target_geometry())
            self.scene_settings_panel.raise_()

    def _scene_settings_target_geometry(self) -> QRect:
        host = self.viewport_host
        width = self.scene_settings_panel.width()
        return QRect(
            max(8, host.width() - self.viewport_toolbar.width() - width - 20),
            12,
            width,
            max(240, host.height() - 24),
        )

    def _bind_algebra_panel(self) -> None:
        panel = self.algebra_panel
        mode = getattr(self, "scene_mode", SceneMode.THREE_D)
        panel.set_scene_mode(mode)
        panel.set_catalog_entries(catalog_entries(mode))
        panel.set_builtin_surfaces((surface.id, surface.name) for surface in BUILTIN_SURFACES)
        panel.add_requested.connect(self._add_formula_for_scene)
        panel.catalog_requested.connect(self._add_catalog_entry)
        panel.builtin_requested.connect(self._add_builtin_surface)
        panel.lighting_requested.connect(self._show_lighting_dialog)
        panel.update_requested.connect(self._update_formula_for_scene)
        panel.delete_requested.connect(self._remove_layer_for_scene)
        panel.visibility_changed.connect(self._set_layer_visibility)
        panel.intersections_visibility_changed.connect(self._set_surface_intersections_visibility)
        panel.intersection_color_changed.connect(self._set_surface_intersection_color)
        panel.color_changed.connect(self._set_layer_color)
        panel.opacity_changed.connect(self._set_surface_opacity)
        panel.line_width_changed.connect(self._set_curve_line_width)
        panel.range_changed.connect(self._set_layer_range)
        # 扩展程序仍可能连接旧信号；界面中已不再提供对应的工具栏操作。
        panel.auto_intersections_changed.connect(self._set_auto_intersections)
        panel.manual_intersection_requested.connect(self._add_manual_intersection)

    def _render_scene(self) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._render_2d_scene()
        else:
            self._render_3d_scene()

    def _render_3d_scene(self) -> None:
        appearance = self.scene_appearances[SceneMode.THREE_D]
        build_scene(
            self.plotter,
            show_axes=False,
            show_helpers=True,
            lighting=self.lighting,
            camera_position=self._three_d_camera_position,
            background_color=appearance.background_color,
            axis_color_mode=appearance.axis_color_mode,
            contrast_axis_color=appearance.contrast_axis_color,
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
            base_surface=False,
        )
        configure_3d_camera_interaction(self.plotter)
        # build_scene 内部会调用 plotter.clear() 清除全部 actor，因此坐标轴需要重新创建。
        self._three_d_axes = ThreeDAxes(self.plotter)
        extent = self._current_3d_axis_extent()
        spacing = self._three_d_axes.render(
            extent,
            axis_color_mode=appearance.axis_color_mode,
            contrast_color=appearance.contrast_axis_color,
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
        )
        self._three_d_spacing = spacing
        self._three_d_extent = extent
        focal = tuple(self.plotter.camera.focal_point)
        self.plot_domain = PlotDomain(
            x_range=(focal[0] - extent, focal[0] + extent),
            y_range=(focal[1] - extent, focal[1] + extent),
            z_range=(focal[2] - extent, focal[2] + extent),
            explicit_resolution=self.plot_domain.explicit_resolution,
            implicit_resolution=self.plot_domain.implicit_resolution,
        )
        self._last_domain_extent = extent
        self.layer_controller = LayerSceneController(
            self.plotter,
            self.plot_domain,
            ambient=self.lighting.ambient,
            material_name=self.material_name,
        )
        self.layer_controller.set_global_intersections_visible(appearance.show_intersections)
        self.curve_controller = None
        available_layers: list[SurfaceLayer] = []
        for layer in self.layers:
            try:
                self.layer_controller.add_layer(layer)
            except (ExpressionError, LayerRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self.layers = available_layers
        self._sync_panel_layers(self.layers)
        self.algebra_panel.set_status("三维场景已准备好")
        self._refresh_3d_viewport(resample=True, render=False)
        self.plotter.render()

    def _render_2d_scene(self) -> None:
        appearance = self.scene_appearances[SceneMode.TWO_D]
        self.plotter.clear()
        self.plotter.set_background(appearance.background_color)
        configure_2d_camera(self.plotter)
        self._restore_2d_camera()
        visible = self._current_2d_bounds()
        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        sampling_domain = self._curve_sampling_domain(sampling_bounds)
        self.curve_domain = sampling_domain
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
        )
        # plotter.clear() 会清除全部 actor，因此二维辅助线池也必须重新建立。
        self._two_d_guides = TwoDGuides(self.plotter)
        self._two_d_guides.render(sampling_bounds, appearance, spacing=spacing)
        self._two_d_guide_spacing = spacing
        self._two_d_guide_bounds = sampling_bounds
        self._two_d_sample_bounds = sampling_bounds
        self.curve_controller = CurveSceneController(self.plotter, sampling_domain)
        self.layer_controller = None
        available_layers: list[CurveLayer] = []
        for layer in self.curve_layers:
            try:
                self.curve_controller.add_layer(layer)
            except (CurveExpressionError, CurveRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self.curve_layers = available_layers
        self._sync_panel_layers(self.curve_layers)
        self.algebra_panel.set_status("二维场景已准备好")
        self.plotter.render()

    def _restore_2d_camera(self) -> None:
        # 2D 场景使用并行投影（parallel projection），这里的 parallel_scale 相当于
        # "视口的世界单位 zoom"：数值越大，视口显示的世界范围越大，图像越小；
        # 数值越小，视口显示的范围越小，图像越放大。
        #
        # 这个值会直接影响 _current_2d_bounds() 中的 visible_2d_bounds() 计算：
        #   half_height = parallel_scale / 2
        #   half_width = half_height * aspect_ratio
        # 因此它决定了当前可见窗口的 x/y 范围，进而影响网格、刻度和采样区域。
        if self._two_d_camera_position is not None:
            self.plotter.camera_position = self._two_d_camera_position
        else:
            self.plotter.camera_position = [
                (0.0, 0.0, 20.0),    # 相机位置
                (0.0, 0.0, 0.0),     # 相机焦点
                (0.0, 1.0, 0.0),     # 相机“向上”的方向
            ]
        if self._two_d_parallel_scale is not None:
            self.plotter.camera.parallel_scale = max(1e-6, self._two_d_parallel_scale)
        else:
            self.plotter.camera.parallel_scale = 6.0
        self.plotter.camera.clipping_range = (0.01, 1000.0)

    def _current_2d_bounds(self) -> ViewportBounds:
        interactor = getattr(self.plotter, "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        focal = tuple(self.plotter.camera.focal_point)
        return visible_2d_bounds(focal, float(self.plotter.camera.parallel_scale), width / height)

    def _curve_sampling_domain(self, bounds: ViewportBounds) -> Plot2DDomain:
        return Plot2DDomain(
            x_range=bounds.x_range,
            y_range=bounds.y_range,
            curve_resolution=self.curve_domain.curve_resolution,
            implicit_resolution=self.curve_domain.implicit_resolution,
        )

    def _refresh_2d_viewport(
        self, *, resample: bool = True, render: bool = True, force: bool = False
    ) -> None:
        visible = self._current_2d_bounds()
        appearance = self.scene_appearances[SceneMode.TWO_D]
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            previous_spacing=None if force else self._two_d_guide_spacing,
        )
        spacing_unchanged = (
            self._two_d_guide_spacing is not None
            and abs(spacing - self._two_d_guide_spacing) <= self._two_d_guide_spacing * 1e-9
        )
        still_covered = (
            self._two_d_guide_bounds is not None
            and self._two_d_guide_bounds.contains(visible)
        )
        if not force and spacing_unchanged and still_covered:
            if render:
                self.plotter.render()
            return

        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        if self._two_d_guides is not None:
            self._two_d_guides.render(sampling_bounds, appearance, spacing=spacing)
        self._two_d_guide_spacing = spacing
        self._two_d_guide_bounds = sampling_bounds
        if resample and self.curve_controller is not None:
            needs_resample = force or self._two_d_sample_bounds is None or (
                not self._two_d_sample_bounds.contains(visible)
            )
            if needs_resample:
                sampling_domain = self._curve_sampling_domain(sampling_bounds)
                try:
                    self.curve_controller.set_domain(sampling_domain)
                except (CurveExpressionError, CurveRenderError) as error:
                    self.algebra_panel.set_status(f"无法重新绘制曲线: {error}", is_error=True)
                else:
                    self.curve_domain = sampling_domain
                    self._two_d_sample_bounds = sampling_bounds
        if render:
            self.plotter.render()

    def _current_3d_axis_extent(self) -> float:
        camera = self.plotter.camera
        distance = float(camera.distance)
        view_angle = float(camera.view_angle)
        interactor = getattr(self.plotter, "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        return visible_3d_axis_extent(distance, view_angle, width / height)

    def _refresh_3d_viewport(
        self, *, resample: bool = True, render: bool = True, force: bool = False
    ) -> None:
        appearance = self.scene_appearances[SceneMode.THREE_D]
        extent = self._current_3d_axis_extent()
        span = 2.0 * extent
        spacing = tick_spacing(
            span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            target_intervals=10,
            previous_spacing=None if force else self._three_d_spacing,
        )
        spacing_unchanged = (
            self._three_d_spacing is not None
            and abs(spacing - self._three_d_spacing) <= self._three_d_spacing * 1e-9
        )
        extent_ratio = (
            extent / self._three_d_extent
            if self._three_d_extent is not None and self._three_d_extent > 0
            else 0.0
        )
        still_covered = 0.7 <= extent_ratio <= 1.3
        need_axes_update = force or not spacing_unchanged or not still_covered

        if need_axes_update:
            padded_extent = extent * 1.3
            if self._three_d_axes is not None:
                spacing = self._three_d_axes.render(
                    padded_extent,
                    axis_color_mode=appearance.axis_color_mode,
                    contrast_color=appearance.contrast_axis_color,
                    show_ticks=appearance.show_ticks,
                    tick_spacing_mode=appearance.tick_spacing_mode,
                    custom_tick_spacing=appearance.tick_spacing,
                    previous_spacing=None if force else self._three_d_spacing,
                )
            self._three_d_spacing = spacing
            self._three_d_extent = extent

        # 曲面在初始定义域上只采样一次，缩放纯粹是相机操作，不重建几何，
        # 以获得类似 GeoGebra 的流畅缩放（不再随视口跳档重采样）。
        if render:
            self.plotter.render()


    def _refresh_visible_viewport(self) -> None:
        self._viewport_refresh_pending = False
        if self._viewport_refreshing or not hasattr(self, "plotter"):
            return
        self._viewport_refreshing = True
        try:
            if self.scene_mode is SceneMode.TWO_D:
                self._refresh_2d_viewport()
            else:
                self._refresh_3d_viewport()
        finally:
            self._viewport_refreshing = False

    def _sync_panel_layers(self, layers: list[SurfaceLayer] | list[CurveLayer]) -> None:
        self.algebra_panel.set_scene_mode(self.scene_mode)
        self.algebra_panel.set_catalog_entries(catalog_entries(self.scene_mode))
        self.algebra_panel.set_layers(layers)
        self._sync_scene_controls()

    def _add_formula_for_scene(self, kind: str, latex: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._add_cas_curve(kind, latex)
        else:
            self._add_cas_surface(kind, latex)

    def _update_formula_for_scene(self, layer_id: str, kind: str, latex: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._update_curve_expression(layer_id, kind, latex)
        else:
            self._update_surface_expression(layer_id, kind, latex)

    def _add_catalog_entry(self, entry_id: str) -> None:
        entry = catalog_entry(entry_id, self.scene_mode)
        if entry is None:
            return
        if entry.mode is SceneMode.THREE_D:
            self._add_builtin_surface(entry.builtin_id or entry.id)
            return
        layer = CurveLayer(
            name=entry.name,
            kind=entry.kind,
            expression=entry.expression,
            latex=entry.latex,
            parameters=dict(entry.parameters),
            builtin_id=entry.id,
            color=entry.color,
        )
        self._add_curve_layer(layer)

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

    def _add_cas_curve(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_curve(latex, kind)
        except (CurveExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        layer = CurveLayer(
            name=f"曲线 {len(self.curve_layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: 1.0 for name in parsed.parameter_names},
        )
        if self._add_curve_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_builtin_surface(self, builtin_id: str) -> None:
        if self.scene_mode is not SceneMode.THREE_D:
            return
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

    def _add_curve_layer(self, layer: CurveLayer) -> bool:
        if self.curve_controller is None:
            return False
        try:
            self.curve_controller.add_layer(layer)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲线: {error}", is_error=True)
            return False
        self.curve_layers.append(layer)
        self.algebra_panel.set_layers(self.curve_layers)
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
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self.plotter.render()

    def _update_curve_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self.curve_controller is None:
            return
        try:
            formula, parsed = self._parse_mathlive_curve(latex, kind)
        except (CurveExpressionError, LatexParseError) as error:
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
            self.curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线: {error}", is_error=True)
            return
        self.curve_layers = [updated if layer.id == layer_id else layer for layer in self.curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self.plotter.render()

    def _parse_mathlive_surface(self, latex: str, kind: str):
        formula = self.latex_parser.parse(latex, kind)
        return formula, parse_surface_expression(formula.canonical_source, formula.kind)

    def _parse_mathlive_curve(self, latex: str, kind: str):
        formula = self.latex_parser.parse_2d(latex, kind)
        return formula, parse_curve_expression(formula.canonical_source, formula.kind)

    def _remove_layer_for_scene(self, layer_id: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._remove_curve(layer_id)
        else:
            self._remove_surface(layer_id)

    def _remove_surface(self, layer_id: str) -> None:
        if self.layer_controller is None:
            return
        self.layer_controller.remove_layer(layer_id)
        self.layers = [layer for layer in self.layers if layer.id != layer_id]
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status("已删除曲面")
        self.plotter.render()

    def _remove_curve(self, layer_id: str) -> None:
        if self.curve_controller is None:
            return
        self.curve_controller.remove_layer(layer_id)
        self.curve_layers = [layer for layer in self.curve_layers if layer.id != layer_id]
        self.algebra_panel.set_layers(self.curve_layers)
        self.algebra_panel.set_status("已删除曲线")
        self.plotter.render()

    def _set_layer_visibility(self, layer_id: str, visible: bool) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._set_curve_visibility(layer_id, visible)
        else:
            self._set_surface_visibility(layer_id, visible)

    def _set_surface_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_visible(layer_id, visible)
        self._replace_layer(layer_id, visible=visible)
        self.plotter.render()

    def _set_curve_visibility(self, layer_id: str, visible: bool) -> None:
        if self.curve_controller is not None:
            self.curve_controller.set_visible(layer_id, visible)
        self._replace_curve_layer(layer_id, visible=visible)
        self.plotter.render()

    def _set_surface_intersections_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_intersections_visible(layer_id, visible)
        self._replace_layer(layer_id, intersections_visible=visible)
        self.plotter.render()

    def _set_surface_intersection_color(self, layer_id: str, color: str) -> None:
        current = self._layer(layer_id)
        if current is None:
            return
        self._intersection_color_revision = (
            max(
                self._intersection_color_revision,
                *(layer.intersection_color_revision for layer in self.layers),
            )
            + 1
        )
        updated = replace(
            current,
            intersection_color=color,
            intersection_color_revision=self._intersection_color_revision,
        )
        if self.layer_controller is not None:
            self.layer_controller.set_intersection_color(
                layer_id, color, updated.intersection_color_revision
            )
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.plotter.render()

    def _set_layer_color(self, layer_id: str, color: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            if self.curve_controller is not None:
                self.curve_controller.set_color(layer_id, color)
            self._replace_curve_layer(layer_id, color=color)
        else:
            if self.layer_controller is not None:
                self.layer_controller.set_color(layer_id, color)
            self._replace_layer(layer_id, color=color)
        self.plotter.render()

    def _set_surface_color(self, layer_id: str, color: str) -> None:
        self._set_layer_color(layer_id, color)

    def _set_surface_opacity(self, layer_id: str, opacity: float) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_opacity(layer_id, opacity)
        self._replace_layer(layer_id, opacity=opacity)
        self.plotter.render()

    def _set_curve_line_width(self, layer_id: str, line_width: float) -> None:
        if self.curve_controller is not None:
            self.curve_controller.set_line_width(layer_id, line_width)
        self._replace_curve_layer(layer_id, line_width=line_width)
        self.plotter.render()

    def _set_layer_range(self, layer_id: str, range_scale: float) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._set_curve_range(layer_id, range_scale)
        else:
            self._set_surface_range(layer_id, range_scale)

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
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 {updated.range_scale:.0%}")
        self.plotter.render()

    def _set_curve_range(self, layer_id: str, range_scale: float) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self.curve_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self.curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线范围: {error}", is_error=True)
            return
        self.curve_layers = [updated if layer.id == layer_id else layer for layer in self.curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 x{updated.range_scale:.1f}")
        self.plotter.render()

    def _set_auto_intersections(self, enabled: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_auto_intersections(enabled)
        self.plotter.render()

    def _add_manual_intersection(self, first_id: str, second_id: str) -> None:
        if self.layer_controller is None:
            return
        self.layer_controller.set_manual_intersection_pair(first_id, second_id, True)
        self.plotter.render()

    def _toggle_scene_mode(self) -> None:
        next_mode = SceneMode.TWO_D if self.scene_mode is SceneMode.THREE_D else SceneMode.THREE_D
        self._set_scene_mode(next_mode)

    def _set_scene_mode(self, mode: SceneMode) -> None:
        if mode is self.scene_mode:
            return
        self._save_current_view_state()
        self.scene_mode = mode
        self._close_scene_settings(immediate=True)
        self._render_scene()

    def _save_current_view_state(self) -> None:
        if not hasattr(self, "plotter"):
            return
        if self.scene_mode is SceneMode.TWO_D:
            self._two_d_parallel_scale = float(self.plotter.camera.parallel_scale)
            self._two_d_camera_position = self._current_camera_position()
        else:
            self._three_d_camera_position = self._current_camera_position()

    def _set_scene_background(self, background: str) -> None:
        self.scene_appearances[self.scene_mode].background = background
        self._save_current_view_state()
        self._render_scene()

    def _set_axis_color_mode(self, axis_color_mode: str) -> None:
        self.scene_appearances[self.scene_mode].axis_color_mode = axis_color_mode
        self._save_current_view_state()
        self._render_scene()

    def _set_grid_visible(self, visible: bool) -> None:
        self.scene_appearances[SceneMode.TWO_D].show_grid = visible
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)

    def _set_ticks_visible(self, visible: bool) -> None:
        appearance = self.scene_appearances[self.scene_mode]
        appearance.show_ticks = visible
        self._save_current_view_state()
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing_mode(self, mode: str) -> None:
        appearance = self.scene_appearances[self.scene_mode]
        appearance.tick_spacing_mode = mode if mode in {"auto", "custom"} else "auto"
        self._save_current_view_state()
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing(self, spacing: float) -> None:
        if spacing <= 0:
            return
        self.scene_appearances[self.scene_mode].tick_spacing = float(spacing)
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_global_intersections_visible(self, visible: bool) -> None:
        self.scene_appearances[SceneMode.THREE_D].show_intersections = visible
        if self.scene_mode is SceneMode.THREE_D and self.layer_controller is not None:
            self.layer_controller.set_global_intersections_visible(visible)
            self.plotter.render()

    def _toggle_scene_settings(self) -> None:
        if self.scene_settings_panel.isVisible():
            self._close_scene_settings()
            return
        self._sync_scene_controls()
        target = self._scene_settings_target_geometry()
        start = QRect(self.viewport_host.width() + 4, target.y(), target.width(), target.height())
        self._scene_settings_closing = False
        self.scene_settings_panel.setGeometry(start)
        self.scene_settings_panel.show()
        self.scene_settings_panel.raise_()
        self._scene_settings_animation.stop()
        self._scene_settings_animation.setStartValue(start)
        self._scene_settings_animation.setEndValue(target)
        self._scene_settings_animation.start()

    def _close_scene_settings(self, immediate: bool = False) -> None:
        if not hasattr(self, "scene_settings_panel") or not self.scene_settings_panel.isVisible():
            return
        if immediate:
            self._scene_settings_animation.stop()
            self.scene_settings_panel.hide()
            return
        current = self.scene_settings_panel.geometry()
        end = QRect(self.viewport_host.width() + 4, current.y(), current.width(), current.height())
        self._scene_settings_closing = True
        self._scene_settings_animation.stop()
        self._scene_settings_animation.setStartValue(current)
        self._scene_settings_animation.setEndValue(end)
        self._scene_settings_animation.start()

    def _finish_scene_settings_animation(self) -> None:
        if self._scene_settings_closing:
            self.scene_settings_panel.hide()
            self._scene_settings_closing = False

    def _sync_scene_controls(self) -> None:
        if not hasattr(self, "scene_mode_button"):
            return
        appearance = self.scene_appearances[self.scene_mode]
        self.scene_mode_button.setText("2D" if self.scene_mode is SceneMode.TWO_D else "3D")
        self.scene_settings_panel.set_mode(self.scene_mode)
        self.scene_settings_panel.set_values(
            background=appearance.background,
            axis_color_mode=appearance.axis_color_mode,
            grid=appearance.show_grid,
            ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            tick_spacing=appearance.tick_spacing,
            intersections=appearance.show_intersections,
        )

    def _show_lighting_dialog(self) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            return
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
        if self.scene_mode is SceneMode.THREE_D:
            if self.layer_controller is not None:
                self.layer_controller.set_ambient(settings.ambient)
            update_lighting(self.plotter, settings)

    def _update_material(self, material_name: str) -> None:
        self.material_name = material_name
        if self.scene_mode is SceneMode.THREE_D and self.layer_controller is not None:
            self.layer_controller.set_material(material_name)
            self.plotter.render()

    def _replace_layer(self, layer_id: str, **changes: object) -> None:
        self.layers = [replace(layer, **changes) if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, self._layer(layer_id))

    def _replace_curve_layer(self, layer_id: str, **changes: object) -> None:
        self.curve_layers = [
            replace(layer, **changes) if layer.id == layer_id else layer for layer in self.curve_layers
        ]
        self.algebra_panel.sync_layer(layer_id, self._curve_layer(layer_id))

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self.layers if layer.id == layer_id), None)

    def _curve_layer(self, layer_id: str) -> CurveLayer | None:
        return next((layer for layer in self.curve_layers if layer.id == layer_id), None)

    def _current_camera_position(self) -> list | None:
        if not getattr(self, "plotter", None):
            return None
        try:
            return [tuple(vector) for vector in self.plotter.camera_position]
        except (AttributeError, TypeError):
            return None

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
            #algebraLayerRow, #catalogEntryRow { background: #f9fafb; border: 1px solid #dfe3e8; border-radius: 6px; }
            #catalogEntryRow:hover { background: #eaf2f7; border-color: #b7ccdc; }
            #catalogCategory { color: #536273; font-size: 12px; font-weight: 700; padding: 8px 2px 2px 2px; }
            #algebraStatus { color: #536273; font-size: 12px; padding-top: 2px; }
            #algebraStatus[isError="true"] { color: #b42318; }
            QScrollArea { border: 0; background: #ffffff; }
            QLabel { color: #263241; font-size: 12px; }
            QLineEdit, QComboBox { min-height: 30px; background: #ffffff; color: #1f2937; border: 1px solid #cbd3dd; border-radius: 4px; padding: 2px 7px; }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #2f7ebd; }
            QPushButton { min-height: 30px; background: #edf3f7; color: #1f547d; border: 1px solid #b9d0e1; border-radius: 4px; padding: 3px 8px; font-weight: 600; }
            QPushButton:hover { background: #dfeef7; }
            QToolButton { min-width: 24px; min-height: 24px; color: #4a5563; border: 1px solid transparent; border-radius: 4px; }
            QToolButton:hover { background: #eef2f5; border-color: #cfd8e1; }
            QCheckBox { color: #405064; spacing: 4px; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #aab5c1; border-radius: 3px; background: #ffffff; }
            QCheckBox::indicator:checked { background: #2777b6; border-color: #2777b6; }
            QSlider::groove:horizontal { height: 4px; background: #d7e0e7; border-radius: 2px; }
            QSlider::handle:horizontal { width: 13px; margin: -5px 0; border-radius: 6px; background: #2f7ebd; }
            #layerSettingsPopup, #functionCatalogPopup, #sceneSettingsPanel { background: #ffffff; border: 1px solid #d0d7df; border-radius: 8px; }
            #settingsPopupTitle { color: #17212e; font-size: 13px; font-weight: 600; }
            #formulaEditorPopup { background: #ffffff; border: 1px solid #d0d7df; border-radius: 8px; }
            #viewportToolbar { background: #ffffff; border: 1px solid #d0d7df; border-radius: 6px; }
            #viewportToolbar QToolButton { font-size: 15px; font-weight: 700; }
            """
        )

    def show(self) -> None:
        self.window.show()
