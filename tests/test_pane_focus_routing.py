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
