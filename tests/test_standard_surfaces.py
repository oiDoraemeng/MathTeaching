"""内置二次曲面目录的测试。"""

import unittest

from geometry.standard_surfaces import (
    BUILTIN_SURFACES,
    BUILTIN_SURFACE_IDS,
    DEFAULT_BUILTIN_ID,
    create_builtin_layer,
)


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
        self.assertEqual(layer.latex, r"x^{2} + y^{2} - z^{2}=-1")
        self.assertFalse({"a", "b", "c"}.intersection(layer.latex))
        self.assertTrue(layer.visible)
        self.assertTrue(layer.intersections_visible)

    def test_builtin_examples_start_with_integer_parameter_values(self) -> None:
        self.assertTrue(
            all(float(value).is_integer() for surface in BUILTIN_SURFACES for value in surface.parameters.values())
        )


if __name__ == "__main__":
    unittest.main()
