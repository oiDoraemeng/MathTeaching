from rendering.geometry_3d_scene import Geometry3DSceneController


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


class FakePlotter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.actors: dict[str, FakeActor] = {}

    def add_mesh(self, mesh, *, name: str, **kwargs):
        self.calls.append(("add_mesh", name))
        actor = FakeActor()
        self.actors[name] = actor
        return actor

    def remove_actor(self, name: str, **kwargs) -> None:
        self.calls.append(("remove_actor", name))
        self.actors.pop(name, None)

    def render(self) -> None:
        self.calls.append(("render", ""))


def test_controller_tracks_3d_linear_and_solid_actors() -> None:
    plotter = FakePlotter()
    controller = Geometry3DSceneController(plotter)
    controller.add_linear("v", (0, 0, 0), (1, 2, 3), kind="vector")
    controller.add_parallelepiped("box", (0, 0, 0), ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    assert "geometry3d:linear:v" in plotter.actors
    assert "geometry3d:solid:box" in plotter.actors
    controller.clear()
    assert plotter.actors == {}

