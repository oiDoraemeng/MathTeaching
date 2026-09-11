import pytest

from linear_algebra.visualizations.capability_map import all_primitive_specs
from services.scene_commands import CommandPlan, SceneCommandService


def test_every_extended_command_op_has_validator_and_replay_adapter():
    service = SceneCommandService()
    for spec in all_primitive_specs():
        for op in spec.command_ops:
            assert op in service.allowed_operations
            assert op in service.allowed_operations


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
