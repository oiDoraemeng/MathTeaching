"""二维无限画布的回归契约。"""

from models.scene_mode import SceneAppearance
from rendering.ticks import ViewportBounds
from rendering.two_d_scene import TwoDGuides, _overscan_bounds


def test_guide_geometry_overscans_viewport_bounds() -> None:
    bounds = ViewportBounds((-10.0, 10.0), (-5.0, 5.0))
    expanded = _overscan_bounds(bounds)
    assert expanded.x_range[0] < bounds.x_range[0]
    assert expanded.x_range[1] > bounds.x_range[1]
    assert expanded.y_range[0] < bounds.y_range[0]
    assert expanded.y_range[1] > bounds.y_range[1]


def test_guides_keep_axis_and_grid_continuous_past_visible_edges() -> None:
    class Plotter:
        def __init__(self):
            self.actors = {}
        def add_mesh(self, mesh, *, name, **_kwargs):
            actor = type("Actor", (), {"visibility": True, "prop": None})()
            self.actors[name] = actor
            return actor
        def add_point_labels(self, *_args, name, **_kwargs):
            actor = type("Actor", (), {"visibility": True, "prop": None})()
            self.actors[name] = actor
            return actor
        def remove_actor(self, name, **_kwargs):
            self.actors.pop(name, None)

    plotter = Plotter()
    guides = TwoDGuides(plotter)
    bounds = ViewportBounds((-2.0, 2.0), (-2.0, 2.0))
    guides.render(bounds, SceneAppearance(show_grid=True, show_ticks=False))
    axis = guides._meshes["axis_X"]
    assert axis.points[0, 0] < bounds.x_range[0]
    assert axis.points[1, 0] > bounds.x_range[1]

