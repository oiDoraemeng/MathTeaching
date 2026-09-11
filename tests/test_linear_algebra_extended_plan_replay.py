import pytest

from linear_algebra.visualizations.capability_map import all_primitive_specs
from services.scene_commands import CommandPlan, SceneCommandService, replay_registry


def test_every_extended_command_op_has_validator_and_replay_adapter():
    service = SceneCommandService()
    for spec in all_primitive_specs():
        for op in spec.command_ops:
            assert op in service.allowed_operations
            assert replay_registry.has(op)


class RecordingHost:
    mode = "2d"
    def __init__(self): self.committed_operations = []; self.pending = []
    def begin_scene_command_transaction(self): self.pending = []
    def apply_scene_command(self, operation):
        self.pending.append(operation)
        if operation.get("op") == "geometry.quadratic_level_set": raise RuntimeError("invalid render")
    def commit_scene_command_transaction(self): self.committed_operations.extend(self.pending); self.pending = []
    def rollback_scene_command_transaction(self): self.pending = []


def test_invalid_operation_rolls_back_entire_extended_plan():
    host = RecordingHost()
    plan = CommandPlan(scene="2d", operations=(
        {"op": "point.upsert", "alias": "A", "coordinates": [0, 0]},
        {"op": "geometry.quadratic_level_set", "alias": "q", "matrix": [[1, 0], [0, 1]], "eigenvalues": [1, 1], "principal_axes": [[1, 0], [0, 1]], "signature": [2, 0, 0], "classification": "positive_definite", "aliases": ["q__original", "q__principal", "q__standard"], "bounds": [-2, 2, -2, 2], "sample_count": 16, "tolerance": 1e-9, "contour_vertices": [[1, 0]], "contour_segments": []},
    ))
    with pytest.raises(RuntimeError): SceneCommandService(host).execute(plan)
    assert host.committed_operations == []


@pytest.mark.parametrize("operation", [
    {"op": "point.upsert", "alias": "A", "coordinates": [float("nan"), 0]},
    {"op": "geometry.quadratic_level_set", "matrix": [[1, 0], [0, 1]], "bounds": [-2, 2, -2, 2], "unknown": True},
    {"op": "geometry.quadratic_level_set", "matrix": [[1, 2], [0, 1]], "bounds": [-2, 2, -2, 2]},
])
def test_extended_boundary_rejects_nonfinite_unknown_or_dimension_mismatch(operation):
    result = SceneCommandService().validate(CommandPlan(scene="2d", operations=(operation,)))
    assert not result.valid


def test_replay_extended_plan_uses_registered_adapters():
    from services.scene_commands import replay_extended_plan
    host = RecordingHost()
    validation = replay_extended_plan(CommandPlan(scene="2d", operations=({"op": "point.upsert", "alias": "A", "coordinates": [0, 0]},)), host)
    assert validation.valid
    assert host.committed_operations[0]["op"] == "scene.set_mode"
