"""感知相机视图的刻度间距与可见范围测试。"""

import unittest

from rendering.ticks import (
    ViewportBounds,
    automatic_tick_spacing,
    format_tick,
    stable_tick_spacing,
    tick_spacing,
    tick_values,
    visible_2d_bounds,
    visible_3d_axis_extent,
)


class TickCalculationTests(unittest.TestCase):
    def test_automatic_spacing_follows_the_1_2_5_sequence(self) -> None:
        self.assertEqual(automatic_tick_spacing(20.0), 1.0)
        self.assertEqual(automatic_tick_spacing(10.0), 0.5)
        self.assertEqual(automatic_tick_spacing(40.0), 2.0)

    def test_custom_spacing_is_fixed(self) -> None:
        self.assertEqual(tick_spacing(200.0, "custom", 0.5), 0.5)
        self.assertEqual(tick_spacing(10.0, "auto", target_intervals=10), 1.0)
        self.assertEqual(tick_values((-1.1, 1.1), 0.5), (-1.0, -0.5, 0.0, 0.5, 1.0))

    def test_visible_bounds_and_labels_are_stable(self) -> None:
        bounds = visible_2d_bounds((2.0, -1.0, 0.0), 10.0, 2.0)
        self.assertEqual(bounds, ViewportBounds((-18.0, 22.0), (-11.0, 9.0)))
        self.assertEqual(format_tick(0.5, 0.5), "0.5")
        self.assertEqual(format_tick(1_000_000.0, 1.0), "1.000e+6")

    def test_contains_detects_enclosed_and_escaped_regions(self) -> None:
        outer = ViewportBounds((-10.0, 10.0), (-10.0, 10.0))
        self.assertTrue(outer.contains(ViewportBounds((-3.0, 3.0), (-3.0, 3.0))))
        self.assertFalse(outer.contains(ViewportBounds((-3.0, 12.0), (-3.0, 3.0))))

    def test_3d_extent_grows_with_camera_distance(self) -> None:
        near = visible_3d_axis_extent(10.0, 30.0, 1.0)
        far = visible_3d_axis_extent(20.0, 30.0, 1.0)
        self.assertGreater(far, near)


class StableSpacingTests(unittest.TestCase):
    def test_first_call_falls_back_to_automatic(self) -> None:
        self.assertEqual(stable_tick_spacing(20.0, None), automatic_tick_spacing(20.0))

    def test_small_zoom_keeps_previous_spacing(self) -> None:
        # 20 -> 18 keeps ~18 intervals at spacing 1.0, still inside the band.
        self.assertEqual(stable_tick_spacing(18.0, 1.0), 1.0)
        # 适度放大到 12 个区间仍沿用当前间距，因此不需要重标刻度。
        self.assertEqual(stable_tick_spacing(12.0, 1.0), 1.0)

    def test_too_dense_span_switches_to_finer_spacing(self) -> None:
        # 当前滞后下限为 4 个区间；跨度小于该范围时才切换为更细的间距。
        result = stable_tick_spacing(3.0, 1.0)
        self.assertLess(result, 1.0)

    def test_too_sparse_span_switches_to_coarser_spacing(self) -> None:
        # 缩小到出现约 40 个区间时，应切换为更粗的间距。
        result = stable_tick_spacing(40.0, 1.0)
        self.assertGreater(result, 1.0)

    def test_tick_spacing_threads_previous_value(self) -> None:
        self.assertEqual(
            tick_spacing(18.0, "auto", previous_spacing=1.0), 2.0
        )
        self.assertEqual(
            tick_spacing(18.0, "custom", 0.25, previous_spacing=1.0), 0.25
        )


if __name__ == "__main__":
    unittest.main()
