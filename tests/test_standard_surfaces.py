"""Tests for the built-in quadric surface catalog."""

import unittest

from geometry.standard_surfaces import BUILTIN_SURFACE_IDS, DEFAULT_BUILTIN_ID, create_builtin_layer


class BuiltinSurfaceTests(unittest.TestCase):
    def test_catalog_contains_the_requested_standard_quadrics(self) -> None:
        expected = {
            "sphere",
            "ellipsoid",
            "one_sheet_hyperboloid",
            "two_sheet_hyperboloid",
            "elliptic_paraboloid",
            "hyperbolic_paraboloid",
            "elliptic_cone",
            "elliptic_cylinder",
        }

        self.assertTrue(expected.issubset(BUILTIN_SURFACE_IDS))

    def test_default_builtin_is_an_independently_visible_layer(self) -> None:
        layer = create_builtin_layer(DEFAULT_BUILTIN_ID)

        self.assertEqual(layer.builtin_id, DEFAULT_BUILTIN_ID)
        self.assertTrue(layer.visible)
        self.assertTrue(layer.intersections_visible)


if __name__ == "__main__":
    unittest.main()
