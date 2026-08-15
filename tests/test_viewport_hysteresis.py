"""二维视口刷新中类 GeoGebra 跳过与滞后策略的测试。"""

import unittest

from models.scene_mode import SceneAppearance, SceneMode
from rendering.ticks import ViewportBounds, tick_spacing
from ui.designer_window import MainWindow


class FakePlotter:
    def __init__(self) -> None:
        self.render_count = 0

    def render(self) -> None:
        self.render_count += 1


class SpyGuides:
    """无需 PyVista 即可记录 render() 调用次数的测试替身。"""

    def __init__(self) -> None:
        self.render_count = 0
        self.last_spacing: float | None = None

    def render(self, bounds, appearance, *, spacing=None, **_kw) -> float:
        self.render_count += 1
        if spacing is None:
            spacing = tick_spacing(bounds.y_span, appearance.tick_spacing_mode, appearance.tick_spacing)
        self.last_spacing = spacing
        return spacing


def _make_window(visible: ViewportBounds) -> MainWindow:
    window = object.__new__(MainWindow)
    window.plotter = FakePlotter()
    window.scene_appearances = {SceneMode.TWO_D: SceneAppearance()}
    window.curve_controller = None
    window.curve_domain = None
    window._two_d_guide_spacing = None
    window._two_d_guide_bounds = None
    window._two_d_sample_bounds = None
    window._two_d_guides = SpyGuides()
    window._current_2d_bounds = lambda: visible  # type: ignore[method-assign]
    return window


class ViewportHysteresisTests(unittest.TestCase):
    def test_small_zoom_skips_guide_rebuild(self) -> None:
        visible = ViewportBounds((-10.0, 10.0), (-10.0, 10.0))
        window = _make_window(visible)
        window._refresh_2d_viewport()
        self.assertEqual(window._two_d_guides.render_count, 1)

        # 轻微放大时保留原间距，且仍处于已绘制网格范围内。
        window._current_2d_bounds = lambda: ViewportBounds(  # type: ignore[method-assign]
            (-9.0, 9.0), (-9.0, 9.0)
        )
        window._refresh_2d_viewport()
        self.assertEqual(window._two_d_guides.render_count, 1)  # no rebuild

    def test_panning_out_of_drawn_region_rebuilds(self) -> None:
        visible = ViewportBounds((-10.0, 10.0), (-10.0, 10.0))
        window = _make_window(visible)
        window._refresh_2d_viewport()

        # 平移到足够远，使视口离开带额外边距的网格区域。
        window._current_2d_bounds = lambda: ViewportBounds(  # type: ignore[method-assign]
            (40.0, 60.0), (-10.0, 10.0)
        )
        window._refresh_2d_viewport()
        self.assertEqual(window._two_d_guides.render_count, 2)  # rebuilt

    def test_zooming_until_too_sparse_rebuilds_with_new_spacing(self) -> None:
        visible = ViewportBounds((-10.0, 10.0), (-10.0, 10.0))
        window = _make_window(visible)
        window._refresh_2d_viewport()
        first_spacing = window._two_d_guide_spacing

        # 大幅缩小：跨度为 200 时，1.0 的刻度会变得过于稀疏。
        window._current_2d_bounds = lambda: ViewportBounds(  # type: ignore[method-assign]
            (-100.0, 100.0), (-100.0, 100.0)
        )
        window._refresh_2d_viewport()
        self.assertEqual(window._two_d_guides.render_count, 2)
        self.assertGreater(window._two_d_guide_spacing, first_spacing)

    def test_force_always_rebuilds(self) -> None:
        visible = ViewportBounds((-10.0, 10.0), (-10.0, 10.0))
        window = _make_window(visible)
        window._refresh_2d_viewport()

        # 即使视口相同，设置发生变化也必须强制重建。
        window._refresh_2d_viewport(resample=False, force=True)
        self.assertEqual(window._two_d_guides.render_count, 2)


if __name__ == "__main__":
    unittest.main()
