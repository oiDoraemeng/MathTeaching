import numpy as np
import pytest

from linear_algebra.visualizations.families.spectral import SpectralFamilyCompiler, spectral_evidence
from linear_algebra.visualizations.compiler import VisualCompileError
from services.scene_commands import CommandPlan, SceneCommandService


def test_each_real_spectral_root_binds_to_an_eigenspace():
    evidence = spectral_evidence([[2, 0], [0, 3]], 1e-9)
    assert {root.value for root in evidence.roots} == {2, 3}
    assert all(root.eigenspace_id in evidence.eigenspaces for root in evidence.roots)


def test_complex_only_roots_have_no_fake_real_direction():
    evidence = spectral_evidence([[0, -1], [1, 0]], 1e-9)
    assert evidence.roots == ()
    assert evidence.complex_roots


def test_spectrum_compiler_emits_stable_aliases_and_command_gate():
    result = SpectralFamilyCompiler.compile({"matrix": [[2, 0, 0], [0, 3, 0], [0, 0, 4]], "bounds": [-2, 2, -2, 2, -2, 2]})
    assert result["aliases"] == ("spectrum__matrix", "spectrum__roots")
    assert SceneCommandService().validate(CommandPlan(scene="3d", operations=result["operations"])).valid
    assert {operation["op"] for operation in result["operations"]} >= {"geometry.spectrum", "geometry.projection3d"}


def test_spectrum_service_rejects_unbounded_or_nonfinite_trust_boundary():
    operation = {"op": "geometry.spectrum", "matrix": [[2, 0, 0], [0, 3, 0], [0, 0, 4]], "roots": [2], "eigenspaces": {}, "roots_alias": "roots", "bounds": [-1000, 1000, -2, 2, -2, 2], "tolerance": 1e-9}
    assert not SceneCommandService().validate(CommandPlan(scene="3d", operations=(operation,))).valid


def test_spectrum_service_rejects_valid_3d_over_budget_counts():
    operation = {"op": "geometry.spectrum", "matrix": [[2, 0, 0], [0, 3, 0], [0, 0, 4]], "roots": [2, 3, 4], "eigenspaces": {}, "roots_alias": "roots", "bounds": [-2, 2, -2, 2, -2, 2], "entity_count": 33, "stage_count": 7, "sample_count": 1}
    result = SceneCommandService().validate(CommandPlan(scene="3d", operations=(operation,)))
    assert not result.valid and any("budget" in message for message in result.messages)


def test_main_window_3d_dispatcher_records_spectrum_projection_and_orthogonalization():
    from types import SimpleNamespace
    from ui.designer_window import MainWindow

    class Controller:
        def __init__(self):
            self.calls = []
        def add_linear(self, alias, start, end, **kwargs):
            self.calls.append(("direction", alias))
        def add_projection3d(self, alias, vector, foot, residual, **kwargs):
            self.calls.extend((("projection", alias + "__projection"), ("residual", alias + "__residual"), ("right-angle", alias + "__right_angle")))
        def add_orthogonalization_stage(self, alias, residual, normalized, **kwargs):
            self.calls.append(("stage", alias))

    controller = Controller()
    scene = SimpleNamespace(geometry3d_controller=controller, _agent_geometry3d={})
    window = object.__new__(MainWindow)
    window._pane_scene = lambda: scene
    window._apply_scene_command({"op": "geometry.spectrum", "alias": "spectrum", "eigenspaces": {"spectrum__eigenspace_0": ((1.0, 0.0, 0.0),)}, "roots": (2.0,)})
    window._apply_scene_command({"op": "geometry.projection3d", "alias": "projection", "vector": (1.0, 0.0, 0.0), "foot": (0.5, 0.0, 0.0), "residual": (0.5, 0.0, 0.0)})
    window._apply_scene_command({"op": "geometry.orthogonalization", "alias": "orthogonalization", "stages": ({"id": "orthogonalization__stage_0", "residual": (1.0, 0.0, 0.0), "normalized": (1.0, 0.0, 0.0)},), "vectors": ((1.0, 0.0, 0.0),)})
    assert ("direction", "spectrum__eigenspace_0__direction_0") in controller.calls
    projection_aliases = {alias for kind, alias in controller.calls if kind in {"projection", "residual", "right-angle"}}
    assert projection_aliases == {"projection__projection", "projection__residual", "projection__right_angle"}
    stage_aliases = {alias for kind, alias in controller.calls if kind == "stage"}
    assert stage_aliases == {"orthogonalization__stage_0"}
    assert len(stage_aliases) == 1


def test_spectrum_rejects_nonfinite():
    with pytest.raises(VisualCompileError):
        SpectralFamilyCompiler.compile({"matrix": [[float("nan"), 0], [0, 1]]})
