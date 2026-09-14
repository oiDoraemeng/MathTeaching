from rendering.geometry_3d_scene import Geometry3DSceneController


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


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
    assert kwargs["line_width"] == 2.0
    assert kwargs["render_lines_as_tubes"] is False


def test_remove_alias_clears_nested_linear_algebra_children() -> None:
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("constraint__line", (0, 0, 0), (1, 0, 0), kind="segment")
    controller.add_plane("constraint__plane", (0, 0, 0), (0, 0, 1))

    controller.remove_alias("constraint")

    assert plotter.actors == {}
    assert controller.linears == {}
    assert controller.planes == {}
