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
        self.assertEqual(
            stable_tick_spacing(20.0, None, target_intervals=20),
            automatic_tick_spacing(20.0, target_intervals=20),
        )

    def test_small_zoom_keeps_previous_spacing(self) -> None:
        # 跨度 14 时 1.0 的间距为 14 个区间，仍在滞后区间内，因此复用旧间距。
        self.assertEqual(stable_tick_spacing(14.0, 1.0), 1.0)
        # 适度放大到 6 个区间仍沿用当前间距，因此不需要重标刻度。
        self.assertEqual(stable_tick_spacing(6.0, 1.0), 1.0)

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

    def test_recomputed_spacing_lands_inside_the_hysteresis_band(self) -> None:
        """越界后重算的间距必须立刻落回滞后区间，否则每帧都会重算。"""
        span = 20.0
        for _ in range(60):
            spacing = stable_tick_spacing(span, None)
            self.assertLessEqual(5, span / spacing)
            self.assertLessEqual(span / spacing, 16)
            span /= 1.1

    def test_zoom_never_skips_a_rung_of_the_1_2_5_ladder(self) -> None:
        """放大时间距只能沿 1-2-5 阶梯逐级下降，例如不能从 1 直接跳到 0.2。"""
        ladder = [2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]
        span, spacing = 20.0, None
        seen: list[float] = []
        for _ in range(40):
            spacing = stable_tick_spacing(span, spacing)
            if not seen or spacing != seen[-1]:
                seen.append(spacing)
            span /= 1.15
        for previous, current in zip(seen, seen[1:]):
            self.assertEqual(ladder.index(current), ladder.index(previous) + 1)

    def test_zoom_out_retraces_the_same_spacings_as_zoom_in(self) -> None:
        """放大与缩小必须走同一条阶梯，不能出现 1 -> 0.2 但 0.2 -> 0.5 -> 1。"""
        span, spacing = 20.0, None
        zoom_in: list[float] = []
        for _ in range(30):
            spacing = stable_tick_spacing(span, spacing)
            zoom_in.append(spacing)
            span /= 1.15
        zoom_out: list[float] = []
        for _ in range(30):
            span *= 1.15
            spacing = stable_tick_spacing(span, spacing)
            zoom_out.append(spacing)
        self.assertEqual(sorted(set(zoom_out)), sorted(set(zoom_in)))


if __name__ == "__main__":
    unittest.main()
