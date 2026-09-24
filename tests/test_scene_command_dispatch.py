from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from MathInputWidget import LatexParser

from models.curve_layer import Plot2DDomain
from rendering.curve_scene import CurveSceneController
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.chapter_04_semantics import TOPIC_SEMANTICS
from linear_algebra.registry import catalog_registry, runtime_teaching_store
from services.scene_commands import CommandError, CommandPlan, SceneCommandService
from ui.designer_window import MainWindow
from ui.scene_pane_manager import ScenePaneManager
from ui.teaching_case_panes import case_plan

from ui.designer_window import _SceneCommandBridge, _SceneCommandHostProxy


class _RecordingHost:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None, QThread]] = []

    def begin_scene_command_transaction(self) -> None:
        self.calls.append(("begin", None, QThread.currentThread()))

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self.calls.append(("apply", operation, QThread.currentThread()))

    def commit_scene_command_transaction(self) -> None:
        self.calls.append(("commit", None, QThread.currentThread()))

    def rollback_scene_command_transaction(self) -> None:
        self.calls.append(("rollback", None, QThread.currentThread()))


class _FailingHost(_RecordingHost):
    def apply_scene_command(self, operation: dict[str, object]) -> None:
        super().apply_scene_command(operation)
        raise RuntimeError("scene mutation failed")


class _DispatchWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, proxy: _SceneCommandHostProxy) -> None:
        super().__init__()
        self.proxy = proxy

    @Slot()
    def run(self) -> None:
        try:
            self.proxy.begin_scene_command_transaction()
            self.proxy.apply_scene_command({"op": "point.upsert", "id": "P"})
            self.proxy.commit_scene_command_transaction()
        except Exception as error:  # pragma: no cover - assertion reports this
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


def test_scene_command_host_proxy_dispatches_scene_mutations_to_gui_thread() -> None:
    app = QApplication.instance() or QApplication([])
    host = _RecordingHost()
    bridge = _SceneCommandBridge(host)
    proxy = _SceneCommandHostProxy(bridge)
    worker_thread = QThread()
    worker = _DispatchWorker(proxy)
    worker.moveToThread(worker_thread)
    errors: list[str] = []
    worker_thread.started.connect(worker.run)
    worker.failed.connect(errors.append)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(app.quit)
    worker_thread.start()
    QTimer.singleShot(5000, app.quit)
    app.exec()
    worker_thread.wait(1000)

    assert not errors
    assert [(name, value) for name, value, _ in host.calls] == [
        ("begin", None),
        ("apply", {"op": "point.upsert", "id": "P"}),
        ("commit", None),
    ]
    assert all(thread == bridge.thread() for _, _, thread in host.calls)


def test_scene_command_host_proxy_rethrows_gui_thread_errors() -> None:
    app = QApplication.instance() or QApplication([])
    bridge = _SceneCommandBridge(_FailingHost())
    proxy = _SceneCommandHostProxy(bridge)
    worker_thread = QThread()
    worker = _DispatchWorker(proxy)
    worker.moveToThread(worker_thread)
    errors: list[str] = []
    worker_thread.started.connect(worker.run)
    worker.failed.connect(errors.append)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(app.quit)
    worker_thread.start()
    QTimer.singleShot(5000, app.quit)
    app.exec()
    worker_thread.wait(1000)

    assert errors == ["scene mutation failed"]


def _pane_window() -> MainWindow:
    """Exercise real scene mutation helpers with independent renderer doubles."""
    app = QApplication.instance() or QApplication([])
    window = object.__new__(MainWindow)
    window._test_app = app
    window.pane_manager = ScenePaneManager()
    window.pane_manager.set_layout(2)
    window.latex_parser = LatexParser()
    window.algebra_panel = MagicMock()
    window._sync_panel_layers = MagicMock()
    window._refresh_2d_viewport = MagicMock()
    window._render_scene = MagicMock()
    for pane_id in window.pane_manager.visible_pane_ids():
        pane = window.pane_manager.pane(pane_id)
        renderer = MagicMock()
        renderer.camera = SimpleNamespace(
            focal_point=(0.0, 0.0, 0.0), position=(0.0, 0.0, 20.0), parallel_scale=6.0
        )
        renderer.camera_position = [(0.0, 0.0, 20.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        pane.renderer_2d = pane.renderer_3d = renderer
        scene = window._pane_scene(pane_id)
        scene.geometry_controller = GeometrySceneController(renderer, ViewportBounds((-6, 6), (-6, 6)))
        scene.curve_controller = CurveSceneController(renderer, Plot2DDomain())
    return window


def test_empty_teaching_algebra_area_is_hidden_and_restored_when_content_exists() -> None:
    window = object.__new__(MainWindow)
    window.algebra_panel = MagicMock()
    window.algebra_resize_handle = MagicMock()
    window.pane_manager = SimpleNamespace(active_pane_id="case-1")
    window._teaching_case_pane_ids = ["case-1"]
    window.algebra_panel._layers = []
    window.algebra_panel.matrix_transform_editor.side_effect = [None, object(), None]

    window._sync_teaching_algebra_panel_visibility()
    window._sync_teaching_algebra_panel_visibility()
    window.pane_manager.active_pane_id = "user-1"
    window._sync_teaching_algebra_panel_visibility()

    assert [call.args[0] for call in window.algebra_panel.setVisible.call_args_list] == [False, True, True]
    assert [call.args[0] for call in window.algebra_resize_handle.setVisible.call_args_list] == [False, True, True]


def test_teaching_algebra_area_stays_visible_while_case_materializes() -> None:
    window = object.__new__(MainWindow)
    window.algebra_panel = MagicMock()
    window.algebra_resize_handle = MagicMock()
    window.pane_manager = SimpleNamespace(active_pane_id="case-1")
    window._teaching_case_pane_ids = ["case-1"]
    window._teaching_case_materializing = True
    window.algebra_panel._layers = []

    window._sync_teaching_algebra_panel_visibility()

    window.algebra_panel.setVisible.assert_called_once_with(True)
    window.algebra_resize_handle.setVisible.assert_called_once_with(True)


def test_teaching_algebra_area_stays_visible_when_switching_scene_mode() -> None:
    """A loaded lecture keeps its explanation panel across 2-D/3-D changes."""
    window = object.__new__(MainWindow)
    window.algebra_panel = MagicMock()
    window.algebra_resize_handle = MagicMock()
    window.pane_manager = SimpleNamespace(active_pane_id="case-1")
    window._teaching_case_pane_ids = ["case-1"]
    window._active_linear_algebra_topic_id = "ch04.subspace.col-null"
    window._active_linear_algebra_explanation_case = object()
    window.algebra_panel._layers = []
    window.algebra_panel.matrix_transform_editor.return_value = None

    # Mode changes can leave the current case without ordinary scene layers;
    # the active teaching topic is still the algebra panel's content.
    window._sync_teaching_algebra_panel_visibility()

    window.algebra_panel.setVisible.assert_called_once_with(True)
    window.algebra_resize_handle.setVisible.assert_called_once_with(True)


def _drawing_plan() -> CommandPlan:
    return CommandPlan(operations=(
        {"op": "point.upsert", "alias": "A", "coordinates": [1, 2]},
        {"op": "point.upsert", "alias": "B", "coordinates": [4, 6]},
        {"op": "linear.upsert", "alias": "AB", "kind": "segment", "start": "A", "end": "B"},
        {"op": "curve.create", "alias": "f", "kind": "explicit", "expression": "y=x^2"},
        {"op": "annotation.upsert", "alias": "label", "text": "A to B", "position": [2, 3]},
        {"op": "view.fit", "padding": 1.2},
    ))


def test_formula_annotation_uses_text_as_default_latex_source() -> None:
    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    result = service.execute(
        CommandPlan(
            scene="2d",
            operations=(
                {
                    "op": "annotation.formula",
                    "alias": "pythagoras",
                    "text": r"c^2=a^2+b^2",
                    "position": [1.0, 2.0],
                },
            ),
        ),
        pane_id=target,
    )

    annotation = window._pane_scene(target).annotations[0]
    assert result.valid
    assert annotation.text == r"c^2=a^2+b^2"
    assert annotation.latex == r"c^2=a^2+b^2"


def test_formula_annotation_prefers_explicit_latex_source() -> None:
    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    result = service.execute(
        CommandPlan(
            scene="2d",
            operations=(
                {
                    "op": "annotation.formula",
                    "alias": "density",
                    "text": "density",
                    "latex": r"\rho=\frac{m}{V}",
                    "position": [0.0, 0.0],
                },
            ),
        ),
        pane_id=target,
    )

    annotation = window._pane_scene(target).annotations[0]
    assert result.valid
    assert annotation.text == "density"
    assert annotation.latex == r"\rho=\frac{m}{V}"


def test_three_d_formula_annotation_sends_mathtext_to_vtk_labels() -> None:
    from models.scene_mode import SceneMode

    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    scene = window._pane_scene(target)
    scene.scene_mode = SceneMode.THREE_D
    scene.geometry3d_controller = SimpleNamespace(actors={})
    renderer = window._pane_renderer(target)
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    result = service.execute(
        CommandPlan(
            scene="3d",
            operations=(
                {
                    "op": "annotation.formula",
                    "alias": "pressure",
                    "text": r"p=\rho gh",
                    "position": [0.0, 0.0, 1.0],
                },
            ),
        ),
        pane_id=target,
    )

    assert result.valid
    assert renderer.add_point_labels.call_args.args[1] == [r"$p=\rho gh$"]
    assert scene.geometry3d_controller.actors["geometry3d:annotation:pressure"] is renderer.add_point_labels.return_value


def test_matrix_case_plan_replays_all_primitives_without_rolling_back() -> None:
    """A real chapter-2 case must leave its transformed grid and vectors visible.

    This covers the deferred path used when a case-pane interactor becomes
    available.  In particular it catches model fields accepted by commands but
    missing from ``Linear2D``: such a mismatch raises midway through the plan
    and the transaction deliberately restores an empty pane.
    """
    compiled = catalog_registry().resolve_bundle(
        "ch02.matrix.transformed-grid",
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    pane_id = window.pane_manager.visible_pane_ids()[0]
    plan = None
    for stage in compiled.storyboard:
        candidate = case_plan(compiled, stage.id)
        if any(operation.get("op") == "geometry.transformed_grid" for operation in candidate.operations):
            plan = candidate
            break
    assert plan is not None

    result = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window))).execute(
        plan, pane_id=pane_id
    )

    scene = window._pane_scene(pane_id)
    assert result.valid
    assert scene.geometry_points
    assert scene.linear_objects
    assert {item.label_side for item in scene.linear_objects} <= {"above", "below"}
    grid_aliases = {
        str(operation["alias"])
        for operation in plan.operations
        if operation.get("op") == "geometry.transformed_grid"
    }
    assert grid_aliases & set(scene._agent_teaching_2d)
    assert window._pane_renderer(pane_id).add_mesh.call_count > 0


def test_transformed_grid_case_uses_one_toolbar_matrix_row_in_algebra_panel() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch02.matrix.transformed-grid",
        artifact_store=runtime_teaching_store(),
    ).compiled
    stage = compiled.storyboard[1]
    window = _pane_window()
    pane_id = window.pane_manager.visible_pane_ids()[0]
    plan = case_plan(compiled, stage.id)
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    assert service.execute(plan, pane_id=pane_id).valid

    matrix_model = MagicMock()
    window.algebra_panel.add_matrix_transform_tab.return_value = matrix_model
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = stage.id
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {pane_id: (stage.id,)}
    window.pane_manager.focus_pane(pane_id)

    window._apply_linear_algebra_storyboard_visibility()

    matrix_model.set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}2&0\\0&1\end{pmatrix}"
    )
    window.algebra_panel.add_matrix_transform_tab.assert_called_once_with(
        pane_id,
        window.pane_manager.pane(pane_id).name,
        editable=False,
        activate=False,
    )
    assert any(
        getattr(annotation, "agent_alias", None) == "sem__mv_grid_stretch__label"
        for annotation in window._pane_scene(pane_id).annotations
    )
    algebra_aliases = {
        getattr(layer, "agent_alias", None)
        for layer in window.algebra_panel.set_layers.call_args.args[0]
    }
    assert "sem__mv_grid_stretch__label" not in algebra_aliases


@pytest.mark.parametrize(
    "topic_id, stage_index, expected_latex, expected_extent, label_alias",
    [
        (
            "ch02.matrix.additive-distributivity",
            0,
            r"A=\begin{pmatrix}3&0\\0&3\end{pmatrix}",
            3,
            None,
        ),
        (
            "ch02.matrix.composition",
            0,
            r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}",
            3,
            None,
        ),
        (
            "ch02.matrix.composition",
            1,
            r"A=\begin{pmatrix}0&-2\\1&0\end{pmatrix}",
            3,
            None,
        ),
        (
            "ch02.matrix.composition",
            2,
            r"A=\begin{pmatrix}0&-1\\2&0\end{pmatrix}",
            3,
            None,
        ),
        (
            "ch02.matrix.powers",
            0,
            r"A=\begin{pmatrix}1&2\\3&4\end{pmatrix}",
            1,
            "sem__grid_a__label",
        ),
        (
            "ch02.matrix.powers",
            1,
            r"A=\begin{pmatrix}7&10\\15&22\end{pmatrix}",
            1,
            "sem__grid_a2__label",
        ),
    ],
)
def test_other_chapter_two_matrix_cases_use_one_toolbar_matrix_row(
    topic_id: str,
    stage_index: int,
    expected_latex: str,
    expected_extent: int,
    label_alias: str | None,
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled
    stage = compiled.storyboard[stage_index]
    window = _pane_window()
    pane_id = window.pane_manager.visible_pane_ids()[0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    assert service.execute(case_plan(compiled, stage.id), pane_id=pane_id).valid

    matrix_model = MagicMock()
    window.algebra_panel.add_matrix_transform_tab.return_value = matrix_model
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = stage.id
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {pane_id: (stage.id,)}
    window.pane_manager.focus_pane(pane_id)

    window._apply_linear_algebra_storyboard_visibility()

    matrix_model.set_matrix_transform_value.assert_called_once_with(expected_latex)
    matrix_model.set_matrix_transform_grid_range.assert_called_once_with(expected_extent)
    window.algebra_panel.add_matrix_transform_tab.assert_called_once_with(
        pane_id,
        window.pane_manager.pane(pane_id).name,
        editable=False,
        activate=False,
    )
    if label_alias is not None:
        assert any(
            getattr(annotation, "agent_alias", None) == label_alias
            for annotation in window._pane_scene(pane_id).annotations
        )
        algebra_aliases = {
            getattr(layer, "agent_alias", None)
            for layer in window.algebra_panel.set_layers.call_args.args[0]
        }
        assert label_alias not in algebra_aliases


@pytest.mark.parametrize(
    "topic_id, expected_latex",
    (
        (
            "ch06.basis-change.coordinates",
            r"A=\begin{pmatrix}1&-1\\1&1\end{pmatrix}",
        ),
        (
            "ch06.similarity-transform",
            r"A=\begin{pmatrix}1&-1\\1&1\end{pmatrix}",
        ),
    ),
)
def test_chapter_six_matrix_toolbar_starts_at_default_grid_range_five(
    topic_id: str,
    expected_latex: str,
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled
    stage = compiled.storyboard[0]
    plan = case_plan(compiled, stage.id)
    grid = next(
        operation
        for operation in plan.operations
        if operation.get("op") == "geometry.transformed_grid"
    )
    window = _pane_window()
    pane_id = window.pane_manager.visible_pane_ids()[0]
    window._pane_scene(pane_id)._agent_teaching_2d[str(grid["alias"])] = dict(grid)
    window._active_linear_algebra_compiled = compiled
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {pane_id: (stage.id,)}
    matrix_model = MagicMock()
    window.algebra_panel.add_matrix_transform_tab.return_value = matrix_model

    window._sync_teaching_matrix_grid(
        pane_id,
        SimpleNamespace(visible_aliases=(str(grid["alias"]),)),
    )

    matrix_model.set_matrix_transform_value.assert_called_once_with(expected_latex)
    matrix_model.set_matrix_transform_grid_range.assert_called_once_with(5)


def test_basis_case_syncs_each_visible_grid_matrix_to_its_algebra_tab() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch04.basis.definition",
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    for pane_id in (first, second):
        result = service.execute(compiled.plan, pane_id=pane_id)
        assert result.valid

    models = {first: MagicMock(), second: MagicMock()}
    window.algebra_panel.add_matrix_transform_tab.side_effect = (
        lambda pane_id, *_args, **_kwargs: models[pane_id]
    )
    standard = "stage.ch04.basis.definition.standard"
    oblique = "stage.ch04.basis.definition.oblique"
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = standard
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {first: (standard,), second: (oblique,)}
    window.pane_manager.focus_pane(first)

    window._apply_linear_algebra_storyboard_visibility()

    models[first].set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}"
    )
    models[second].set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}1&1\\1&-1\end{pmatrix}"
    )
    models[first].set_matrix_transform_grid_range.assert_called_once_with(5)
    models[second].set_matrix_transform_grid_range.assert_called_once_with(5)
    assert all(
        call.kwargs == {"editable": False, "activate": False}
        for call in window.algebra_panel.add_matrix_transform_tab.call_args_list
    )
    first_linears = {
        linear.agent_alias: linear
        for linear in window._pane_scene(first).linear_objects
    }
    second_linears = {
        linear.agent_alias: linear
        for linear in window._pane_scene(second).linear_objects
    }
    assert first_linears["ch04__entity__standard_basis__generator_1"].visible
    assert not first_linears["ch04__entity__oblique_basis__generator_1"].visible
    assert second_linears["ch04__entity__oblique_basis__generator_1"].visible
    assert not second_linears["ch04__entity__standard_basis__generator_1"].visible

    panel_aliases = {
        layer.agent_alias
        for layer in window.algebra_panel.set_layers.call_args.args[0]
        if getattr(layer, "agent_alias", None)
    }
    assert "ch04__entity__standard_basis__generator_1" in panel_aliases
    assert "ch04__entity__oblique_basis__generator_1" not in panel_aliases

    window._clear_linear_algebra_tool_overlays = MagicMock()
    window._apply_matrix_transform_from_tab(
        first,
        r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}",
        8,
    )

    standard_grid = window._pane_scene(first)._agent_teaching_2d[
        "ch04__relation__standard_readout__grid"
    ]
    assert standard_grid["bounds"] == [-8.0, 8.0, -8.0, 8.0]
    assert window._pane_scene(first)._matrix_transform_grid_range == 8
    window._clear_linear_algebra_tool_overlays.assert_not_called()


def test_linear_map_matrix_sync_skips_affine_translation() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch04.linear-map.definition",
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    window.scene_command_service = service
    stages = tuple(compiled.storyboard[:2])
    for pane_id, stage in zip((first, second), stages):
        result = service.execute(case_plan(compiled, stage.id), pane_id=pane_id)
        assert result.valid

    models = {first: MagicMock(), second: MagicMock()}
    window.algebra_panel.add_matrix_transform_tab.side_effect = (
        lambda pane_id, *_args, **_kwargs: models[pane_id]
    )
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = stages[0].id
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: (stages[0].id,),
        second: (stages[1].id,),
    }
    window.pane_manager.focus_pane(first)

    window._apply_linear_algebra_storyboard_visibility()

    models[first].set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}2&0\\0&1\end{pmatrix}"
    )
    models[first].set_matrix_transform_grid_range.assert_called_once_with(3)
    models[second].set_matrix_transform_value.assert_not_called()
    models[second].set_matrix_transform_grid_range.assert_not_called()
    assert window.algebra_panel.add_matrix_transform_tab.call_count == 1
    translation_grid = window._pane_scene(second)._agent_teaching_2d[
        "ch04__relation__translation_case__grid"
    ]
    assert translation_grid["origin"] == [1, 0]


@pytest.mark.parametrize(
    "topic_id, expected_matrices, expected_latex",
    (
        (
            "ch03.det.basic-properties",
            (
                [[2.0, 1.0], [1.0, 2.0]],
                [[1.0, 2.0], [2.0, 1.0]],
            ),
            (
                r"A=\begin{pmatrix}2&1\\1&2\end{pmatrix}",
                r"A=\begin{pmatrix}1&2\\2&1\end{pmatrix}",
            ),
        ),
        (
            "ch03.det.multiplicativity",
            (
                [[1.0, 0.0], [0.0, 1.0]],
                [[1.0, 0.0], [0.0, 3.0]],
            ),
            (
                r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}",
                r"A=\begin{pmatrix}1&0\\0&3\end{pmatrix}",
            ),
        ),
        (
            "ch03.det.transpose",
            (
                [[2.0, 2.0], [1.0, 3.0]],
                [[2.0, 1.0], [2.0, 3.0]],
            ),
            (
                r"A=\begin{pmatrix}2&2\\1&3\end{pmatrix}",
                r"A=\begin{pmatrix}2&1\\2&3\end{pmatrix}",
            ),
        ),
    ),
)
def test_fixed_determinant_cases_sync_matrices_without_an_active_global_stage(
    topic_id: str,
    expected_matrices: tuple[list[list[float]], list[list[float]]],
    expected_latex: tuple[str, str],
) -> None:
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    stages = tuple(compiled.storyboard[:2])
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    window.scene_command_service = service
    window._render_2d_scene = MagicMock()
    window._sync_pane_state = MagicMock()
    for pane_id, stage in zip((first, second), stages):
        result = service.execute(case_plan(compiled, stage.id), pane_id=pane_id)
        assert result.valid

    models = {first: MagicMock(), second: MagicMock()}
    window.algebra_panel.add_matrix_transform_tab.side_effect = (
        lambda pane_id, *_args, **_kwargs: models[pane_id]
    )
    window.algebra_panel.matrix_transform_editor.side_effect = (
        lambda pane_id: models[pane_id]
    )
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = None
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: (stages[0].id,),
        second: (stages[1].id,),
    }

    window._apply_linear_algebra_storyboard_visibility()

    models[first].set_matrix_transform_value.assert_called_once_with(
        expected_latex[0], ""
    )
    models[second].set_matrix_transform_value.assert_called_once_with(
        expected_latex[1], ""
    )
    models[first].set_matrix_transform_grid_range.assert_called_once_with(5)
    models[second].set_matrix_transform_grid_range.assert_called_once_with(5)
    assert all(
        call.kwargs == {"editable": False, "activate": False}
        for call in window.algebra_panel.add_matrix_transform_tab.call_args_list
    )
    first_grid = window._pane_scene(first)._agent_teaching_2d["la_tool_transform_grid"]
    second_grid = window._pane_scene(second)._agent_teaching_2d["la_tool_transform_grid"]
    assert first_grid["matrix"] == expected_matrices[0]
    assert second_grid["matrix"] == expected_matrices[1]
    assert first_grid["bounds"] == second_grid["bounds"] == [-5.0, 5.0, -5.0, 5.0]

    window._apply_matrix_transform_from_tab(
        first,
        expected_latex[0],
        8,
    )

    resized = window._pane_scene(first)._agent_teaching_2d["la_tool_transform_grid"]
    assert resized["bounds"] == [-8.0, 8.0, -8.0, 8.0]


def test_determinant_matrix_sync_does_not_reenter_during_2d_rebuild() -> None:
    """The toolbar grid setup must not recurse through scene visibility sync."""
    compiled = catalog_registry().resolve_bundle(
        "ch03.det.basic-properties",
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    window.scene_command_service = service
    for pane_id, stage in zip((first, second), compiled.storyboard[:2]):
        assert service.execute(case_plan(compiled, stage.id), pane_id=pane_id).valid

    models = {first: MagicMock(), second: MagicMock()}
    window.algebra_panel.add_matrix_transform_tab.side_effect = (
        lambda pane_id, *_args, **_kwargs: models[pane_id]
    )
    window.algebra_panel.matrix_transform_editor.side_effect = (
        lambda pane_id: models[pane_id]
    )
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_topic_id = "ch03.det.basic-properties"
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: (compiled.storyboard[0].id,),
        second: (compiled.storyboard[1].id,),
    }

    # The real 2-D rebuild invokes visibility sync at its tail.  Reproduce that
    # callback without creating another native render window in this test.
    window._render_2d_scene = lambda: window._apply_linear_algebra_storyboard_visibility()

    window._apply_linear_algebra_storyboard_visibility()

    assert window._pane_scene(first)._agent_teaching_2d["la_tool_transform_grid"]["matrix"] == [
        [2.0, 1.0],
        [1.0, 2.0],
    ]
    assert window._pane_scene(second)._agent_teaching_2d["la_tool_transform_grid"]["matrix"] == [
        [1.0, 2.0],
        [2.0, 1.0],
    ]


def test_chapter_two_basis_uses_actual_a_and_b_matrices_in_algebra_tabs() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch02.matrix.basis",
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    stages = tuple(compiled.storyboard)
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    for pane_id, stage in zip((first, second), stages):
        result = service.execute(case_plan(compiled, stage.id), pane_id=pane_id)
        assert result.valid

    models = {first: MagicMock(), second: MagicMock()}
    window.algebra_panel.add_matrix_transform_tab.side_effect = (
        lambda pane_id, *_args, **_kwargs: models[pane_id]
    )
    window._active_linear_algebra_compiled = compiled
    window._active_linear_algebra_stage_id = stages[0].id
    window._teaching_case_pane_ids = [first, second]
    window._teaching_case_stage_refs = {
        first: (stages[0].id,),
        second: (stages[1].id,),
    }

    window._apply_linear_algebra_storyboard_visibility()

    models[first].set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}0&-1\\1&0\end{pmatrix}"
    )
    models[second].set_matrix_transform_value.assert_called_once_with(
        r"A=\begin{pmatrix}-1&-2\\1&1\end{pmatrix}"
    )
    models[first].set_matrix_transform_grid_range.assert_called_once_with(5)
    models[second].set_matrix_transform_grid_range.assert_called_once_with(5)
    assert all(
        call.kwargs == {"editable": False, "activate": False}
        for call in window.algebra_panel.add_matrix_transform_tab.call_args_list
    )
    expected_labels = {
        first: "sem__mv_basis_grid_a__label",
        second: "sem__mv_basis_grid_b__label",
    }
    for pane_id, label_alias in expected_labels.items():
        assert any(
            getattr(annotation, "agent_alias", None) == label_alias
            for annotation in window._pane_scene(pane_id).annotations
        )
        with window._using_pane(pane_id):
            algebra_aliases = {
                getattr(layer, "agent_alias", None)
                for layer in window._two_d_panel_layers()
            }
        assert label_alias not in algebra_aliases
    assert not any(
        operation.get("op") == "linear_algebra.coordinate_transform"
        for operation in compiled.plan.operations
    )


def test_transformed_grid_origin_reaches_real_host_mesh():
    import numpy as np
    window=_pane_window()
    target=window.pane_manager.visible_pane_ids()[0]
    renderer=window._pane_renderer(target)
    service=SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    service.execute(CommandPlan(scene="2d",operations=({"op":"geometry.transformed_grid","alias":"lane","matrix":[[2,0],[0,1]],"bounds":[-1,1,-1,1],"origin":[8,4]},)),pane_id=target)
    meshes={call.kwargs.get("name"):call.args[0] for call in renderer.add_mesh.call_args_list}
    assert np.allclose(meshes["geometry:teaching:grid:lane:original"].center,[8,4,0])
    assert np.allclose(meshes["geometry:teaching:grid:lane:transformed"].center,[8,4,0])


def test_coordinate_transform_replaces_pane_coordinate_system_without_teaching_grid():
    window = _pane_window()
    window._render_2d_scene = MagicMock()
    target = window.pane_manager.visible_pane_ids()[0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    result = service.execute(
        CommandPlan(
            scene="2d",
            operations=(
                {
                    "op": "linear_algebra.coordinate_transform",
                    "alias": "basis-change",
                    "matrix": [[1.0, 1.0], [1.0, 2.0]],
                    "show_original": False,
                    "show_transformed": True,
                },
            ),
        ),
        pane_id=target,
    )

    scene = window._pane_scene(target)
    assert result.valid
    assert scene._two_d_coordinate_transform == ((1.0, 1.0), (1.0, 2.0))
    assert scene._two_d_show_original_coordinate_system is False
    assert scene._two_d_show_transformed_coordinate_system is True
    assert scene.pane.scene_2d["coordinate_transform"] == [[1.0, 1.0], [1.0, 2.0]]
    assert not scene._agent_teaching_2d
    window._render_2d_scene.assert_called_once()


@pytest.mark.parametrize("explicit", [False, True])
def test_scene_commands_mutate_only_the_resolved_pane(explicit: bool) -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    target = second if explicit else first
    untouched = first if explicit else second
    renderer = window._pane_renderer(untouched)
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    service.execute(_drawing_plan(), pane_id=target if explicit else None)

    scene = window._pane_scene(target)
    assert len(scene.geometry_points) == 2
    assert len(scene.linear_objects) == len(scene.curve_layers) == len(scene.annotations) == 1
    assert window._pane_renderer(target).camera.focal_point == (2.5, 4.0, 0.0)
    assert window._pane_scene(untouched).geometry_points == []
    assert window._pane_scene(untouched).linear_objects == []
    assert window._pane_scene(untouched).curve_layers == []
    assert window._pane_scene(untouched).annotations == []
    assert window._pane_renderer(untouched).camera.parallel_scale == 6.0
    assert renderer.mock_calls == []
    assert window.pane_manager.active_pane_id == target
    assert len(window.pane_manager.pane(target).scene_2d["geometry"]) == 4
    assert not hasattr(window, "plotter")
    assert not hasattr(window, "geometry_controller")


def test_scene_service_keeps_target_when_focus_changes_during_execution() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    original_apply = window.apply_scene_command

    def apply_and_change_focus(operation, pane_id=None):
        original_apply(operation, pane_id)
        window.pane_manager.focus_pane(second)

    window.apply_scene_command = apply_and_change_focus
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    service.execute(_drawing_plan())

    assert window.pane_manager.active_pane_id == second
    assert len(window._pane_scene(first).geometry_points) == 2
    assert window._pane_scene(second).geometry_points == []
    assert window._pane_renderer(second).mock_calls == []


def test_direct_scene_command_accepts_an_explicit_pane() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    window.apply_scene_command({"op": "point.upsert", "alias": "A", "coordinates": [1, 2]}, second)
    assert len(window._pane_scene(second).geometry_points) == 1
    assert window._pane_scene(first).geometry_points == []
    assert window.pane_manager.active_pane_id == first


def test_constraint_compiler_output_replays_in_a_2d_pane() -> None:
    from linear_algebra.visualizations.families.constraints import ConstraintFamilyCompiler

    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    operation = ConstraintFamilyCompiler.compile({"matrix": [[1, 0], [2, 0]], "rhs": [1, 2]})["operations"][0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    validation = service.execute(CommandPlan(scene="2d", operations=(operation,)), pane_id=target)

    assert validation.valid
    scene = window._pane_scene(target)
    assert any(item.agent_alias == "constraint__line" for item in scene.linear_objects)
    assert {item.agent_alias for item in scene.geometry_points} >= {"constraint__line__start", "constraint__line__end"}


def test_constraint_compiler_output_replays_in_a_3d_pane() -> None:
    from linear_algebra.visualizations.families.constraints import ConstraintFamilyCompiler
    from models.scene_mode import SceneMode
    from rendering.geometry_3d_scene import Geometry3DSceneController

    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    scene = window._pane_scene(target)
    scene.scene_mode = SceneMode.THREE_D
    scene.geometry3d_controller = Geometry3DSceneController(window._pane_renderer(target))
    operation = ConstraintFamilyCompiler.compile({
        "matrix": [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
        "rhs": [1, 0, 0],
    })["operations"][0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    validation = service.execute(CommandPlan(scene="3d", operations=(operation,)), pane_id=target)

    assert validation.valid
    assert "geometry3d:plane:constraint__plane" in scene.geometry3d_controller.actors


@pytest.mark.parametrize("pane_id", ["deleted-pane", ""])
def test_missing_command_pane_fails_before_any_mutation(pane_id: str) -> None:
    window = _pane_window()
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    with pytest.raises(CommandError, match="窗格不存在|pane_id"):
        service.execute(_drawing_plan(), pane_id=pane_id)
    assert all(window._pane_scene(key).geometry_points == [] for key in window.pane_manager.panes)


def test_missing_manager_and_renderer_have_explicit_errors() -> None:
    window = object.__new__(MainWindow)
    with pytest.raises(CommandError, match="窗格管理器"):
        window.apply_scene_command({"op": "view.fit"})
    window.pane_manager = ScenePaneManager()
    with pytest.raises(CommandError, match="渲染器尚未初始化"):
        window.apply_scene_command({"op": "view.fit"})


def test_failure_rolls_back_only_the_target_pane_after_focus_changes() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    original_apply = window.apply_scene_command

    def fail_curve(operation, pane_id=None):
        if operation["op"] == "curve.create":
            window.pane_manager.focus_pane(second)
            raise RuntimeError("curve failed")
        original_apply(operation, pane_id)

    window.apply_scene_command = fail_curve
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    with pytest.raises(RuntimeError, match="curve failed"):
        service.execute(_drawing_plan())
    assert window._pane_scene(first).geometry_points == []
    assert window._pane_scene(second).geometry_points == []
    assert window._pane_renderer(second).mock_calls == []
    assert window._transaction_pane_id is None


def test_explicit_command_cannot_escape_an_open_transaction_pane() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    window.begin_scene_command_transaction(first)
    try:
        with pytest.raises(CommandError, match="事务的目标窗格"):
            window.apply_scene_command({"op": "point.upsert", "alias": "A", "coordinates": [1, 2]}, second)
        assert window._pane_scene(second).geometry_points == []
    finally:
        window.rollback_scene_command_transaction(first)


def test_3d_mode_and_camera_commands_leave_other_pane_unchanged() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    window.apply_scene_command({"op": "scene.set_mode", "mode": "3d"}, second)
    window.apply_scene_command({"op": "view.fit"}, second)
    assert window.pane_manager.pane(first).scene_mode == "2d"
    assert window.pane_manager.pane(second).scene_mode == "3d"
    window._pane_renderer(second).reset_camera.assert_called_once()
    assert window._pane_renderer(first).mock_calls == []
    assert window.pane_manager.active_pane_id == first


def test_deleted_transaction_pane_does_not_block_surviving_pane_commands() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    deleted_scene = window._pane_scene(first)
    operation = {"op": "point.upsert", "alias": "A", "coordinates": [1, 2]}
    window.begin_scene_command_transaction(first)
    window.apply_scene_command(operation, first)
    window.pane_manager.delete_pane(first)

    with pytest.raises(CommandError, match="窗格不存在"):
        window.apply_scene_command(operation, first)
    with pytest.raises(CommandError, match="窗格不存在"):
        window.rollback_scene_command_transaction(first)

    assert window._transaction_pane_id is None
    assert window._transaction_scene is None
    assert deleted_scene._scene_command_snapshot is None
    assert deleted_scene._scene_command_active is False
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    service.execute(_drawing_plan(), pane_id=second)
    assert len(window._pane_scene(second).geometry_points) == 2


@pytest.mark.parametrize("topic", sorted(TOPIC_SEMANTICS))
def test_chapter_four_real_host_executes_geometry_and_rolls_back(topic):
    from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from rendering.geometry_3d_scene import Geometry3DSceneController
    from models.scene_mode import SceneMode
    window=_pane_window()
    target,untouched=window.pane_manager.visible_pane_ids()
    plan=VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(artifact_payload_for(topic))).plan
    scene=window._pane_scene(target)
    if plan.scene=="3d":
        scene.scene_mode=SceneMode.THREE_D
        scene.geometry3d_controller=Geometry3DSceneController(window._pane_renderer(target))
    service=SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    service.execute(plan,pane_id=target)
    assert window._pane_scene(untouched).geometry_points==[]
    with window._using_pane(target):
        before=window._capture_scene_command_state()
    failure={"op":"geometry.intersection","alias":"invalid","first":"missing","second":"also_missing"} if plan.scene=="3d" else {"op":"linear.upsert","alias":"invalid","start":"missing","end":"also_missing","kind":"segment"}
    with pytest.raises(CommandError):
        service.execute(CommandPlan(scene=plan.scene,operations=(*plan.operations,failure)),pane_id=target)
    with window._using_pane(target):
        after=window._capture_scene_command_state()
    assert before==after


@pytest.mark.parametrize(
    "topic_id",
    (
        "ch05.affine.solution-set",
        "ch05.consistency.geometry",
        "ch05.gaussian-elimination",
        "ch05.homogeneous.solution-space",
        "ch05.least-squares.projection",
    ),
)
def test_chapter_five_real_host_replays_affine_and_tableau_plans(topic_id: str) -> None:
    """Chapter 5 mixes affine_solution/tableau ops with ordinary 2-D actors.

    A missing host branch used to raise mid-plan, so the atomic load rolled
    back: the pane kept the previous chapter's actors and the explanation
    reverted to that chapter.  Replaying the compiled plan through the real
    host must therefore succeed and register every chapter-5 geometry alias.
    """
    compiled = catalog_registry().resolve_bundle(
        topic_id,
        artifact_store=runtime_teaching_store(),
    ).compiled
    window = _pane_window()
    target = window.pane_manager.visible_pane_ids()[0]
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))

    result = service.execute(compiled.plan, pane_id=target)

    assert result.valid
    scene = window._pane_scene(target)
    special_aliases = {
        str(operation["alias"])
        for operation in compiled.plan.operations
        if operation.get("op")
        in {
            "geometry.affine_solution",
            "geometry.matrix_tableau",
            "geometry.elimination_tableau",
        }
        and operation.get("alias")
    }
    assert special_aliases <= set(scene._agent_teaching_2d)


def test_service_cleans_up_when_pane_is_deleted_during_execution() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    original_apply = window.apply_scene_command

    def delete_after_first_operation(operation, pane_id=None):
        original_apply(operation, pane_id)
        if first in window.pane_manager.panes:
            window.pane_manager.delete_pane(first)

    window.apply_scene_command = delete_after_first_operation
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    with pytest.raises(CommandError, match="窗格不存在"):
        service.execute(_drawing_plan(), pane_id=first)

    window.apply_scene_command = original_apply
    service.execute(_drawing_plan(), pane_id=second)
    assert len(window._pane_scene(second).geometry_points) == 2


def test_wrong_rollback_pane_preserves_original_transaction_for_valid_rollback() -> None:
    window = _pane_window()
    first, second = window.pane_manager.visible_pane_ids()
    scene = window._pane_scene(first)
    window.begin_scene_command_transaction(first)
    snapshot = scene._scene_command_snapshot
    window.apply_scene_command({"op": "point.upsert", "alias": "A", "coordinates": [1, 2]}, first)

    with pytest.raises(CommandError, match="事务的目标窗格"):
        window.rollback_scene_command_transaction(second)

    assert window._transaction_pane_id == first
    assert window._transaction_scene is scene
    assert scene._scene_command_snapshot is snapshot
    assert scene._scene_command_active is True
    assert len(scene.geometry_points) == 1
    window.rollback_scene_command_transaction(first)
    assert scene.geometry_points == []
    assert scene._scene_command_snapshot is None
    assert scene._scene_command_active is False
    assert window._transaction_pane_id is None
    assert window._transaction_scene is None
