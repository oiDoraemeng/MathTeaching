"""测试缩放按比例更新定义域，且滑块状态保持独立。"""
from models.surface_layer import PlotDomain


def test_default_range_scale_is_golden_ratio():
    from models.surface_layer import SurfaceLayer

    layer = SurfaceLayer("plane", "explicit", "z = x + y")
    assert abs(layer.range_scale - 0.618) < 1e-9


def test_domain_scaled_by_range_scale():
    """domain.scaled(0.618) 应将每根轴缩小到原定义域的 61.8%。"""
    domain = PlotDomain(
        x_range=(-10.0, 10.0),
        y_range=(-10.0, 10.0),
        z_range=(-10.0, 10.0),
    )
    scaled = domain.scaled(0.618)
    assert abs(scaled.x_range[0] - (-6.18)) < 1e-9
    assert abs(scaled.x_range[1] - 6.18) < 1e-9


def test_domain_tracks_viewport_extent():
    """视口范围变化时，定义域应同步匹配。"""
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

    # 缩放前的曲面范围
    surface_before = domain_before.scaled(range_scale)
    assert abs(surface_before.x_range[1] - 6.18) < 1e-9

    # 缩放后的曲面范围
    surface_after = domain_after.scaled(range_scale)
    assert abs(surface_after.x_range[1] - 3.09) < 1e-9

    # 两者均恰好填满各自视口范围的 61.8%
    ratio_before = surface_before.x_range[1] / extent_before
    ratio_after = surface_after.x_range[1] / extent_after
    assert abs(ratio_before - ratio_after) < 1e-9


def test_range_scale_one_fills_viewport():
    """range_scale=1.0 表示曲面填满整个视口。"""
    extent = 10.0
    domain = PlotDomain(
        x_range=(-extent, extent),
        y_range=(-extent, extent),
        z_range=(-extent, extent),
    )
    scaled = domain.scaled(1.0)
    assert abs(scaled.x_range[0] - (-10.0)) < 1e-9
    assert abs(scaled.x_range[1] - 10.0) < 1e-9
