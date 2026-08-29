"""独立场景状态、设置与函数目录数据的单元测试。"""

import unittest
from dataclasses import replace

from models.function_catalog import catalog_entries
from models.scene_mode import SceneAppearance, SceneMode
from models.surface_layer import SurfaceLayer


class SceneModeTests(unittest.TestCase):
    def test_appearance_defaults_match_the_two_viewport_requirements(self) -> None:
        appearance = SceneAppearance()

        self.assertEqual(appearance.background, "auto")
        self.assertEqual(appearance.background_color(), "#f4f6f9")
        self.assertEqual(appearance.contrast_axis_color(), "#17212e")
        self.assertFalse(appearance.show_intersections)
        self.assertTrue(appearance.show_ticks)
        self.assertEqual(appearance.tick_spacing_mode, "auto")
        self.assertEqual(appearance.tick_spacing, 1.0)

    def test_auto_background_uses_effective_theme(self) -> None:
        appearance = SceneAppearance()

        self.assertEqual(appearance.background_color("light"), "#f4f6f9")
        self.assertEqual(appearance.background_color("dark"), "#1e1f23")

    def test_legacy_background_values_remain_explicit(self) -> None:
        self.assertEqual(SceneAppearance(background="light").background_color("dark"), "#f7f8fb")
        self.assertEqual(SceneAppearance(background="dark").background_color("light"), "#101317")

    def test_unknown_background_values_normalize_to_auto(self) -> None:
        self.assertEqual(SceneAppearance(background="legacy").background, "auto")

    def test_catalog_is_filtered_by_scene_and_has_expected_categories(self) -> None:
        two_d = catalog_entries(SceneMode.TWO_D)
        three_d = catalog_entries(SceneMode.THREE_D)

        self.assertEqual({entry.category for entry in two_d}, {"基本初等函数", "代数函数", "圆锥曲线"})
        self.assertEqual({entry.category for entry in three_d}, {"圆锥曲面"})
        self.assertEqual(len(three_d), 11)
        self.assertTrue(all(entry.mode is SceneMode.TWO_D for entry in two_d))

    def test_surface_lists_can_be_kept_independently_for_each_scene(self) -> None:
        three_d_layers = [SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1")]
        two_d_layers: list[object] = []

        two_d_layers.append(object())
        three_d_layers[0] = replace(three_d_layers[0], color="#d64545")

        self.assertEqual(len(two_d_layers), 1)
        self.assertEqual(three_d_layers[0].color, "#d64545")


if __name__ == "__main__":
    unittest.main()
