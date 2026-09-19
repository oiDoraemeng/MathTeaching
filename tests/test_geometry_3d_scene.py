import math
from types import SimpleNamespace

import pytest

from rendering.geometry_3d_scene import (
    _VECTOR_LINE_WIDTH,
    _VECTOR_TIP_LENGTH_PX,
    _VECTOR_TIP_RADIUS_PX,
    Geometry3DSceneController,
)
from rendering.axis import _AXIS_TIP_LENGTH_RATIO
from rendering.scene import DEFAULT_3D_AXIS_EXTENT


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True
        self.mapper = SimpleNamespace(dataset=None)


class FakePlotter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.actors: dict[str, FakeActor] = {}
        self.meshes: dict[str, object] = {}
        self.mesh_kwargs: dict[str, dict[str, object]] = {}

    def add_mesh(self, mesh, *, name: str, **kwargs):
        self.calls.append(("add_mesh", name))
        actor = FakeActor()
        self.actors[name] = actor
        self.meshes[name] = mesh
        self.mesh_kwargs[name] = kwargs
        return actor

    def remove_actor(self, name: str, **kwargs) -> None:
        self.calls.append(("remove_actor", name))
        self.actors.pop(name, None)
        self.meshes.pop(name, None)

    def render(self) -> None:
        self.calls.append(("render", ""))


class FakeCamera:
    """The subset of the VTK camera API the arrow sizing needs."""

    def __init__(self, *, distance: float = 10.0, view_angle: float = 30.0, parallel: bool = False, parallel_scale: float = 2.0) -> None:
        self.distance = float(distance)
        self.view_angle = float(view_angle)
        self.parallel = bool(parallel)
        self.parallel_scale = float(parallel_scale)

    def GetPosition(self):
        return (0.0, 0.0, self.distance)

    def GetFocalPoint(self):
        return (0.0, 0.0, 0.0)

    def GetViewAngle(self) -> float:
        return self.view_angle

    def GetParallelProjection(self) -> bool:
        return self.parallel

    def GetParallelScale(self) -> float:
        return self.parallel_scale


class SizedPlotter(FakePlotter):
    """A plotter with a measurable viewport and a controllable camera."""

    def __init__(self, *, height: int = 600, camera: FakeCamera | None = None) -> None:
        super().__init__()
        self.renderer = SimpleNamespace(GetSize=lambda: (800, height))
        self.camera = camera or FakeCamera()


def test_controller_tracks_3d_linear_and_solid_actors() -> None:
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("v", (0, 0, 0), (1, 2, 3), kind="vector")
    controller.add_parallelepiped("box", (0, 0, 0), ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    assert "geometry3d:linear:v" in plotter.actors
    assert plotter.meshes["geometry3d:linear:v"].n_points > 2
    assert "geometry3d:solid:box" in plotter.actors
    controller.clear()
    assert plotter.actors == {}


def test_3d_vector_arrow_uses_a_screen_width_shaft_and_cone_head() -> None:
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)

    controller.add_linear("v", (0, 0, 0), (1, 0, 0), kind="vector")

    mesh = plotter.meshes["geometry3d:linear:v"]
    kwargs = plotter.mesh_kwargs["geometry3d:linear:v"]
    assert mesh.n_lines == 1
    assert mesh.n_faces > 0
    assert kwargs["line_width"] == _VECTOR_LINE_WIDTH
    assert kwargs["render_lines_as_tubes"] is False


def test_3d_vector_head_world_size_tracks_the_camera_so_pixels_stay_constant() -> None:
    """头部是实体几何：相机拉远一倍，世界尺寸也要加倍，屏幕上才不变。"""
    camera = FakeCamera(distance=10.0, view_angle=30.0)
    # 高像素视口使计算结果容易精确核对。
    plotter = SizedPlotter(height=2000, camera=camera)
    controller = Geometry3DSceneController(plotter)

    near_length, near_radius = controller._arrow_head((0, 0, 0), (0, 1, 0))
    # 所有向量共用相机焦平面的尺度，可见世界高度 = 2 * 10 * tan(fov/2)。
    expected = _VECTOR_TIP_LENGTH_PX * (2.0 * 10.0 * math.tan(math.radians(15.0)) / 2000)
    assert near_length == pytest.approx(expected, rel=1e-6)
    assert near_radius == pytest.approx(near_length * _VECTOR_TIP_RADIUS_PX / _VECTOR_TIP_LENGTH_PX, rel=1e-6)

    camera.distance = 19.0
    far_length, _ = controller._arrow_head((0, 0, 0), (0, 1, 0))
    assert far_length == pytest.approx(near_length * 1.9, rel=1e-6)

    # 缩小视场角（滚轮缩放的另一条路径）同样被补偿。
    camera.distance = 10.0
    camera.view_angle = 15.0
    zoomed_length, _ = controller._arrow_head((0, 0, 0), (0, 1, 0))
    assert zoomed_length == pytest.approx(_VECTOR_TIP_LENGTH_PX * (2.0 * 10.0 * math.tan(math.radians(7.5)) / 2000), rel=1e-6)
    assert zoomed_length < near_length


def test_3d_vectors_use_one_global_tool_style() -> None:
    camera = FakeCamera(distance=10.0, view_angle=30.0)
    plotter = SizedPlotter(height=1000, camera=camera)
    controller = Geometry3DSceneController(plotter)

    controller.add_linear(
        "lesson-vector",
        (0, 0, 0),
        (0, 1, 0),
        kind="vector",
        line_width=2.4,
    )

    expected_scale = 2.0 * 10.0 * math.tan(math.radians(15.0)) / 1000
    assert controller._arrow_tip_lengths["lesson-vector"] == pytest.approx(_VECTOR_TIP_LENGTH_PX * expected_scale)
    assert plotter.mesh_kwargs["geometry3d:linear:lesson-vector"]["line_width"] == _VECTOR_LINE_WIDTH

    camera.distance = 20.0
    assert controller.refresh_vector_heads() is True
    assert controller._arrow_tip_lengths["lesson-vector"] == pytest.approx(2.0 * _VECTOR_TIP_LENGTH_PX * expected_scale)


def test_3d_vector_head_rebuilds_from_the_live_viewport_after_first_paint() -> None:
    """Lesson vectors created before a Qt viewport is ready do not retain a large fallback head."""
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("lesson-vector", (0, 0, 0), (0, 1, 0), kind="vector")
    assert controller._arrow_tip_lengths["lesson-vector"] == pytest.approx(0.14)

    plotter.renderer = SimpleNamespace(GetSize=lambda: (800, 1000))
    plotter.camera = FakeCamera(distance=10.0, view_angle=30.0)

    assert controller.refresh_vector_heads() is True
    expected_scale = 2.0 * 10.0 * math.tan(math.radians(15.0)) / 1000
    assert controller._arrow_tip_lengths["lesson-vector"] == pytest.approx(_VECTOR_TIP_LENGTH_PX * expected_scale)


def test_3d_vector_head_size_does_not_depend_on_vector_length() -> None:
    camera = FakeCamera(distance=10.0)
    plotter = SizedPlotter(height=600, camera=camera)
    controller = Geometry3DSceneController(plotter)

    short_head = controller._arrow_head((0, 0, 0), (0, 0.2, 0))
    long_head = controller._arrow_head((0, 0, 0), (0, 2.0, 0))

    expected_scale = 2.0 * 10.0 * math.tan(math.radians(15.0)) / 600
    assert short_head[0] == pytest.approx(_VECTOR_TIP_LENGTH_PX * expected_scale)
    assert short_head == pytest.approx(long_head)


def test_3d_vector_heads_are_smaller_than_coordinate_axis_heads() -> None:
    """The default vector head is deliberately more compact than an axis head."""
    camera = FakeCamera(distance=10.0, view_angle=30.0)
    controller = Geometry3DSceneController(SizedPlotter(height=600, camera=camera))
    world_per_pixel = controller._world_per_pixel((0, 0, 0))
    assert world_per_pixel is not None
    axis_head_pixels = DEFAULT_3D_AXIS_EXTENT * 2.0 * _AXIS_TIP_LENGTH_RATIO / world_per_pixel
    assert _VECTOR_TIP_LENGTH_PX == 12.0
    assert _VECTOR_TIP_RADIUS_PX == 3
    assert _VECTOR_TIP_LENGTH_PX < axis_head_pixels


def test_3d_vectors_at_different_depths_keep_the_same_pixel_head_size() -> None:
    """Perspective world sizes differ so their projected heads remain equal."""
    camera = FakeCamera(distance=10.0, view_angle=30.0)
    controller = Geometry3DSceneController(SizedPlotter(height=1000, camera=camera))

    nearer_end = (0, 0, 3)
    farther_end = (0, 0, -3)
    nearer_head = controller._arrow_head((0, 0, 0), nearer_end)
    farther_head = controller._arrow_head((0, 0, 0), farther_end)

    assert nearer_head[0] < farther_head[0]
    assert nearer_head[0] / controller._world_per_pixel(nearer_end) == pytest.approx(_VECTOR_TIP_LENGTH_PX)
    assert farther_head[0] / controller._world_per_pixel(farther_end) == pytest.approx(_VECTOR_TIP_LENGTH_PX)


def test_3d_vector_head_rebuild_keeps_the_storyboard_mask() -> None:
    """缩放重建头部时必须就地换几何，否则被遮罩隐藏的向量会重新出现。"""
    camera = FakeCamera(distance=10.0)
    plotter = SizedPlotter(height=600, camera=camera)
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("v", (0, 0, 0), (0, 0, 1), kind="vector")
    controller.set_visible("v", False)
    actor = plotter.actors["geometry3d:linear:v"]
    original = actor.mapper.dataset

    camera.distance = 20.0
    assert controller.refresh_vector_heads() is True

    assert plotter.actors["geometry3d:linear:v"] is actor
    assert actor.visibility is False
    assert actor.mapper.dataset is not original
    assert plotter.mesh_kwargs["geometry3d:linear:v"]["line_width"] == _VECTOR_LINE_WIDTH
    assert plotter.calls.count(("add_mesh", "geometry3d:linear:v")) == 1
    assert ("remove_actor", "geometry3d:linear:v") not in plotter.calls
    # 没有实质变化时不再重建。
    assert controller.refresh_vector_heads() is False


def test_3d_vector_heads_remeasure_when_the_viewport_resizes() -> None:
    camera = FakeCamera(distance=10.0)
    plotter = SizedPlotter(height=600, camera=camera)
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("v", (0, 0, 0), (0, 10, 0), kind="vector")
    initial_length = controller._arrow_tip_lengths["v"]

    plotter.renderer.GetSize = lambda: (800, 1200)
    assert controller.refresh_vector_heads() is True

    assert controller._arrow_tip_lengths["v"] == pytest.approx(initial_length / 2.0)


def test_remove_alias_clears_nested_linear_algebra_children() -> None:
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("constraint__line", (0, 0, 0), (1, 0, 0), kind="segment")
    controller.add_plane("constraint__plane", (0, 0, 0), (0, 0, 1))

    controller.remove_alias("constraint")

    assert plotter.actors == {}
    assert controller.linears == {}
    assert controller.planes == {}
