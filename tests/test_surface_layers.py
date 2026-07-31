"""Tests for independent layer display state."""

import unittest

from models.surface_layer import SurfaceLayer


class SurfaceLayerTests(unittest.TestCase):
    def test_serialization_preserves_surface_and_intersection_display_controls(self) -> None:
        layer = SurfaceLayer(
            name="sphere",
            kind="implicit",
            expression="x^2 + y^2 + z^2 = r^2",
            parameters={"r": 1.0},
            visible=False,
            intersections_visible=False,
            color="#d1664a",
            opacity=0.42,
            range_scale=2.5,
        )

        restored = SurfaceLayer.from_dict(layer.to_dict())

        self.assertEqual(restored.to_dict(), layer.to_dict())
        self.assertEqual(restored.color, "#d1664a")
        self.assertEqual(restored.opacity, 0.42)
        self.assertEqual(restored.range_scale, 2.5)


if __name__ == "__main__":
    unittest.main()
