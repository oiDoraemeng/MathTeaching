"""Regression tests for surface-pair intersection curves."""

import unittest

from geometry.cas_surface import build_surface_mesh, parse_surface_expression
from geometry.intersection import intersect_surface_meshes
from models.surface_layer import PlotDomain


class IntersectionTests(unittest.TestCase):
    def test_sphere_and_plane_produce_a_visible_intersection_curve(self) -> None:
        domain = PlotDomain(explicit_resolution=24, implicit_resolution=24)
        sphere = build_surface_mesh(
            parse_surface_expression("x^2 + y^2 + z^2 = 1", "implicit"),
            {},
            domain,
        )
        plane = build_surface_mesh(parse_surface_expression("z = 0", "explicit"), {}, domain)

        curve = intersect_surface_meshes(sphere, plane)

        self.assertGreater(curve.n_points, 8)
        self.assertGreater(curve.n_cells, 1)
        self.assertLess(float(abs(curve.points[:, 2]).max()), 0.08)


if __name__ == "__main__":
    unittest.main()
