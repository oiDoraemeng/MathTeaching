from services.scene_commands import CommandPlan, SceneCommandService


class PaneHost:
    def __init__(self, modes):
        self.modes = dict(modes)
        self.active = next(iter(self.modes))
        self.calls = {pane: [] for pane in self.modes}

    def for_pane(self, pane_id=None):
        target = pane_id or self.active
        host = PaneHost(self.modes)
        host.active = target
        host.calls = self.calls
        return host

    def activate_for_tool(self):
        return self.active

    @property
    def scene_mode(self):
        return self.modes[self.active]

    def begin_scene_command_transaction(self):
        self.calls[self.active].append("begin")

    def apply_scene_command(self, op):
        self.calls[self.active].append(op)

    def commit_scene_command_transaction(self):
        self.calls[self.active].append("commit")

    def rollback_scene_command_transaction(self):
        self.calls[self.active].append("rollback")


def test_commands_without_pane_id_follow_active_pane_only():
    host = PaneHost({"pane-1": "2d", "pane-2": "2d"})
    host.active = "pane-2"
    result = SceneCommandService(host).execute(CommandPlan(operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},)))
    assert result.valid
    assert any(item.get("alias") == "P" for item in host.calls["pane-2"] if isinstance(item, dict))
    assert host.calls["pane-1"] == []


def test_2d_command_on_3d_pane_returns_unsupported_without_mutation():
    host = PaneHost({"pane-1": "2d", "pane-2": "3d"})
    host.active = "pane-2"
    result = SceneCommandService(host).execute(CommandPlan(scene="2d", operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},)))
    assert not result.valid
    assert "unsupported_mode" in result.messages[0]
    assert host.calls["pane-1"] == [] and host.calls["pane-2"] == []


def test_real_host_proxy_style_mode_guard_runs_before_transaction():
    host = PaneHost({"pane-1": "3d"})
    host.active = "pane-1"
    # This mirrors _SceneCommandHostProxy: scene_mode is read from the pinned
    # pane before begin/apply/commit are invoked.
    result = SceneCommandService(host).execute(
        CommandPlan(scene="2d", operations=({"op": "annotation.upsert", "alias": "a", "text": "x", "position": [0, 0]},))
    )
    assert result.valid is False
    assert result.messages[0].startswith("unsupported_mode:")
    assert host.calls["pane-1"] == []


def test_edit_operations_are_scoped_to_selected_pane():
    host = PaneHost({"pane-1": "2d", "pane-2": "2d"})
    host.active = "pane-2"
    plan = CommandPlan(operations=(
        {"op": "point.upsert", "alias": "P", "coordinates": [0, 0]},
        {"op": "point.upsert", "alias": "Q", "coordinates": [1, 1]},
        {"op": "linear.upsert", "alias": "L", "kind": "segment", "start": "P", "end": "Q"},
        {"op": "annotation.upsert", "alias": "A", "text": "old", "position": [0, 0]},
        {"op": "annotation.formula", "alias": "A", "text": "x²", "position": [0, 0], "latex": "x^2"},
    ))
    assert SceneCommandService(host).execute(plan).valid
    assert host.calls["pane-1"] == []
    edits = [x for x in host.calls["pane-2"] if isinstance(x, dict)]
    assert [x["op"] for x in edits if "op" in x] == ["scene.set_mode", "point.upsert", "point.upsert", "linear.upsert", "annotation.upsert", "annotation.formula"]
