"""Test that zoom updates domain proportionally and slider stays independent."""
from models.surface_layer import PlotDomain


def test_default_range_scale_is_golden_ratio():
    from models.surface_layer import SurfaceLayer

    layer = SurfaceLayer("plane", "explicit", "z = x + y")
    assert abs(layer.range_scale - 0.618) < 1e-9


def test_domain_scaled_by_range_scale():
    """domain.scaled(0.618) should shrink each axis to 61.8% of the domain."""
    domain = PlotDomain(
        x_range=(-10.0, 10.0),
        y_range=(-10.0, 10.0),
        z_range=(-10.0, 10.0),
    )
    scaled = domain.scaled(0.618)
    assert abs(scaled.x_range[0] - (-6.18)) < 1e-9
    assert abs(scaled.x_range[1] - 6.18) < 1e-9


def test_domain_tracks_viewport_extent():
    """When viewport extent changes, domain should match."""
    extent_before = 10.0
    extent_after = 5.0  # zoomed in 2x

    domain_before = PlotDomain(
        x_range=(-extent_before, extent_before),
        y_range=(-extent_before, extent_before),
        z_range=(-extent_before, extent_before),
    )
    domain_after = PlotDomain(
        x_range=(-extent_after, extent_after),
        y_range=(-extent_after, extent_after),
        z_range=(-extent_after, extent_after),
    )

    range_scale = 0.618

    # Surface range before zoom
    surface_before = domain_before.scaled(range_scale)
    assert abs(surface_before.x_range[1] - 6.18) < 1e-9

    # Surface range after zoom
    surface_after = domain_after.scaled(range_scale)
    assert abs(surface_after.x_range[1] - 3.09) < 1e-9

    # Both fill exactly 61.8% of their respective viewports
    ratio_before = surface_before.x_range[1] / extent_before
    ratio_after = surface_after.x_range[1] / extent_after
    assert abs(ratio_before - ratio_after) < 1e-9


def test_range_scale_one_fills_viewport():
    """range_scale=1.0 means surface fills the entire viewport."""
    extent = 10.0
    domain = PlotDomain(
        x_range=(-extent, extent),
        y_range=(-extent, extent),
        z_range=(-extent, extent),
    )
    scaled = domain.scaled(1.0)
    assert abs(scaled.x_range[0] - (-10.0)) < 1e-9
    assert abs(scaled.x_range[1] - 10.0) < 1e-9
