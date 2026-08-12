"""Tests for independent layer display state."""

import unittest

from models.surface_layer import SurfaceLayer


class SurfaceLayerTests(unittest.TestCase):
    def test_existing_fourth_positional_argument_remains_the_parameter_mapping(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=r^2", {"r": 2.0})

        self.assertEqual(layer.parameters, {"r": 2.0})
        self.assertIsNone(layer.latex)

    def test_serialization_preserves_surface_and_intersection_display_controls(self) -> None:
        layer = SurfaceLayer(
            name="sphere",
            kind="implicit",
            expression="x^2 + y^2 + z^2 = r^2",
            latex=r"x^2+y^2+z^2=r^2",
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
        self.assertEqual(restored.latex, r"x^2+y^2+z^2=r^2")


if __name__ == "__main__":
    unittest.main()
