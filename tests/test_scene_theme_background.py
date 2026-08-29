"""场景背景随应用有效主题变化的回归测试。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import ui.designer_window as designer_window

from models.scene_mode import SceneAppearance, SceneMode
from rendering.lighting import LightSettings
from rendering.ticks import ViewportBounds
from ui.designer_window import MainWindow


def test_auto_background_uses_effective_theme() -> None:
    appearance = SceneAppearance()

    assert appearance.background == "auto"
    assert appearance.background_color("light") == "#f4f6f9"
    assert appearance.background_color("dark") == "#1e1f23"


def test_legacy_background_values_remain_explicit() -> None:
    assert SceneAppearance(background="light").background_color("dark") == "#f7f8fb"
    assert SceneAppearance(background="dark").background_color("light") == "#101317"


def test_set_theme_rerenders_only_the_active_auto_background_scene() -> None:
    auto_window = object.__new__(MainWindow)
    auto_window._apply_style = lambda: None
    auto_window._render_scene = MagicMock()
    auto_window.plotter = object()
    auto_window.scene_mode = SceneMode.TWO_D
    auto_window.scene_appearances = {SceneMode.TWO_D: SceneAppearance(background="auto")}

    MainWindow.set_theme(auto_window, "dark", "dark")

    auto_window._render_scene.assert_called_once_with()

    explicit_window = object.__new__(MainWindow)
    explicit_window._apply_style = lambda: None
    explicit_window._render_scene = MagicMock()
    explicit_window.plotter = object()
    explicit_window.scene_mode = SceneMode.TWO_D
    explicit_window.scene_appearances = {SceneMode.TWO_D: SceneAppearance(background="light")}

    MainWindow.set_theme(explicit_window, "dark", "dark")

    explicit_window._render_scene.assert_not_called()


def test_render_2d_scene_passes_effective_theme_to_guides(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CapturingGuides:
        def __init__(self, _plotter: object) -> None:
            pass

        def render(self, _bounds: ViewportBounds, _appearance: SceneAppearance, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(designer_window, "TwoDGuides", CapturingGuides)
    monkeypatch.setattr(designer_window, "configure_2d_camera", lambda _plotter: None)
    monkeypatch.setattr(designer_window, "CurveSceneController", lambda *_args: object())
    monkeypatch.setattr(designer_window, "GeometrySceneController", lambda *_args: object())

    window = object.__new__(MainWindow)
    window.effective_theme = "dark"
    window.scene_appearances = {SceneMode.TWO_D: SceneAppearance()}
    window.plotter = MagicMock()
    window._restore_2d_camera = lambda: None
    window._current_2d_bounds = lambda: ViewportBounds((-4.0, 4.0), (-3.0, 3.0))
    window._curve_sampling_domain = lambda bounds: bounds
    window.curve_layers = []
    window.geometry_points = []
    window.linear_objects = []
    window.annotations = []
    window._render_agent_areas = lambda: None
    window._two_d_panel_layers = lambda: []
    window._sync_panel_layers = lambda _layers: None
    window.algebra_panel = SimpleNamespace(set_status=lambda *_args, **_kwargs: None)

    MainWindow._render_2d_scene(window)

    assert captured["effective_theme"] == "dark"


def test_render_3d_scene_passes_effective_theme_to_builder(monkeypatch) -> None:
    build_scene = MagicMock()

    class FakeAxes:
        def __init__(self, _plotter: object) -> None:
            pass

        def render(self, *_args: object, **_kwargs: object) -> float:
            return 1.0

    class FakeLayerController:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def set_global_intersections_visible(self, _visible: bool) -> None:
            pass

    monkeypatch.setattr(designer_window, "build_scene", build_scene)
    monkeypatch.setattr(designer_window, "configure_3d_camera_interaction", lambda _plotter: None)
    monkeypatch.setattr(designer_window, "ThreeDAxes", FakeAxes)
    monkeypatch.setattr(designer_window, "LayerSceneController", FakeLayerController)

    window = object.__new__(MainWindow)
    window.effective_theme = "dark"
    window.scene_appearances = {SceneMode.THREE_D: SceneAppearance()}
    window.plotter = MagicMock()
    window.plotter.camera.focal_point = (0.0, 0.0, 0.0)
    window.lighting = LightSettings()
    window._three_d_camera_position = None
    window._three_d_spacing = None
    window._current_3d_axis_extent = lambda: 4.0
    window.plot_domain = SimpleNamespace(explicit_resolution=64, implicit_resolution=32)
    window.material_name = "光泽塑料"
    window.layers = []
    window._sync_panel_layers = lambda _layers: None
    window.algebra_panel = SimpleNamespace(set_status=lambda *_args, **_kwargs: None)
    window._render_agent_points3d = lambda: None
    window._refresh_3d_viewport = lambda **_kwargs: None

    MainWindow._render_3d_scene(window)

    assert build_scene.call_args.kwargs["effective_theme"] == "dark"
