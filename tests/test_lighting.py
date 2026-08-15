"""可复用三点光源设置更新的测试。"""

import unittest

from rendering.lighting import LightSettings, rotate_light_positions


class LightingTests(unittest.TestCase):
    def test_rotating_the_rig_updates_all_lights_relative_to_the_key_light(self) -> None:
        settings = LightSettings()
        original_height = settings.key["position"][2]

        rotate_light_positions(settings, 90)

        self.assertEqual(settings.rotation_angle, 90)
        self.assertAlmostEqual(settings.key["position"][1], 0.0, places=6)
        self.assertGreater(settings.key["position"][0], 0.0)
        self.assertEqual(settings.key["position"][2], original_height)


if __name__ == "__main__":
    unittest.main()
