"""3-D toolbar and algebra-only vector-entry regression tests."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget
from PySide6.QtCore import Qt

from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for
from models.geometry_3d import AlgebraAnnotation3D, AlgebraPlane3D, AlgebraVector3D
from models.scene_mode import SceneMode
from rendering.geometry_3d_scene import Geometry3DSceneController
from ui.algebra_panel import AlgebraPanel
from ui.designer_window import MainWindow, parse_3d_vector_endpoint
from ui.scene_pane_manager import ScenePaneManager
from ui.three_d_tools import ThreeDGeometryToolbar


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_three_d_toolbar_is_vertical_left_middle_and_emits_its_actions() -> None:
    host = QWidget()
    host.resize(500, 400)
    toolbar = ThreeDGeometryToolbar(host)
    host.show()
    toolbar.show()
    toolbar.position_in_host()
    QApplication.processEvents()

    actions: list[str] = []
    toolbar.vector_requested.connect(lambda: actions.append("vector"))
    toolbar.annotation_requested.connect(lambda: actions.append("annotation"))
    toolbar.undo_requested.connect(lambda: actions.append("undo"))
    toolbar.redo_requested.connect(lambda: actions.append("redo"))
    toolbar.set_history_state(can_undo=True, can_redo=True)
    toolbar.vector_button.click()
    toolbar.annotation_button.click()
    toolbar.undo_button.click()
    toolbar.redo_button.click()

    assert toolbar.layout().direction() is QBoxLayout.Direction.TopToBottom
    assert toolbar.x() == 12
    assert toolbar.y() == (host.height() - toolbar.height()) // 2
    assert toolbar.annotation_button.property("_kiro_icon_state")[0] == "type"
    assert actions == ["vector", "annotation", "undo", "redo"]


def test_three_d_vector_is_an_editable_row_in_the_shared_algebra_list() -> None:
    panel = AlgebraPanel()
    row = AlgebraVector3D("manual_vector_1", (1.0, 0.0, 0.0))
    updates: list[tuple[str, str, str]] = []
    panel.three_d_vector_updated.connect(
        lambda pane_id, alias, latex: updates.append((pane_id, alias, latex))
    )

    panel.set_layers([row])
    assert panel.formula_list._layers[row.id] is row
    assert row.latex == r"\vec{v}_{1}=\begin{pmatrix}1\\0\\0\end{pmatrix}"

    panel.formula_list.begin_edit = MagicMock()
    panel.begin_three_d_vector_edit(row.alias)
    panel.formula_list.begin_edit.assert_called_once_with(row.alias)

    vector = r"\vec{v}_{1}=\begin{pmatrix}1\\2\\3\end{pmatrix}"
    panel._submit_inline_formula_from_model(panel.formula_list, row.id, vector)
    assert updates == [("pane-1", row.alias, vector)]


def test_teaching_three_d_vectors_are_rows_in_the_shared_algebra_list() -> None:
    window = _three_d_window()
    scene = window._pane_scene()
    scene._agent_geometry3d = {
        "ch04__entity__input_vector_a": {
            "op": "linear3d.upsert", "alias": "ch04__entity__input_vector_a",
            "start": [0.0, 0.0, 0.0], "end": [2.0, 0.0, 3.0], "kind": "vector",
        },
        "ch04__entity__output_vector_a": {
            "op": "linear3d.upsert", "alias": "ch04__entity__output_vector_a",
            "start": [0.0, 0.0, 0.0], "end": [2.0, 0.0, 0.0], "kind": "vector",
        },
        "ch04__entity__kernel_vector": {
            "op": "linear3d.upsert", "alias": "ch04__entity__kernel_vector",
            "start": [0.0, 0.0, 0.0], "end": [0.0, 0.0, 3.0], "kind": "vector",
        },
    }

    rows = window._three_d_panel_layers()

    assert {row.alias for row in rows if isinstance(row, AlgebraVector3D)} == set(scene._agent_geometry3d)
    assert window._three_d_vector_row("ch04__entity__input_vector_a").latex.startswith(r"x_{1}")
    assert window._three_d_vector_row("ch04__entity__output_vector_a").latex.startswith(r"Ax_{1}")
    assert window._three_d_vector_row("ch04__entity__kernel_vector").latex.startswith("k")


def test_teaching_case_algebra_rows_follow_the_selected_stage() -> None:
    window = _three_d_window()
    topic = "ch04.subspace.col-null"
    compiled = VisualSemanticsCompiler().compile(
        TeachingArtifact.from_dict(artifact_payload_for(topic)),
        contract_for(topic),
        RenderContext.default(topic),
    )
    scene = window._pane_scene()
    scene._agent_geometry3d = {
        str(operation["alias"]): dict(operation)
        for operation in compiled.plan.operations
        if operation.get("alias")
    }
    pane_id = window._pane().pane_id
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {
        pane_id: ("stage.ch04.subspace.col-null.null_space",),
    }
    window._active_linear_algebra_compiled = compiled

    rows = window._three_d_panel_layers()
    row_aliases = {row.alias for row in rows if isinstance(row, (AlgebraPlane3D, AlgebraVector3D))}

    assert row_aliases == {
        "ch04__entity__column_space",
        "ch04__entity__kernel_vector",
    }


def test_dependence_relation_terms_stay_out_of_the_algebra_panel() -> None:
    window = _three_d_window()
    topic = "ch04.dependence.redundancy"
    compiled = VisualSemanticsCompiler().compile(
        TeachingArtifact.from_dict(artifact_payload_for(topic)),
        contract_for(topic),
        RenderContext.default(topic),
    )
    scene = window._pane_scene()
    scene._agent_geometry3d = {
        str(operation["alias"]): dict(operation)
        for operation in compiled.plan.operations
        if operation.get("alias")
    }
    pane_id = window._pane().pane_id
    window._teaching_case_pane_ids = [pane_id]
    window._teaching_case_stage_refs = {
        pane_id: ("stage.ch04.dependence.redundancy.line",),
    }
    window._active_linear_algebra_compiled = compiled

    vector_aliases = {
        row.alias
        for row in window._three_d_panel_layers()
        if isinstance(row, AlgebraVector3D)
    }

    assert vector_aliases == {"ch04__entity__span_line__generator_1"}
    assert not any("__relation__" in alias for alias in vector_aliases)


def test_three_d_command_uses_the_global_tool_style_for_vectors() -> None:
    window = _three_d_window()

    window._command_upsert_linear3d({
        "op": "linear3d.upsert",
        "alias": "lesson-vector",
        "start": [0.0, 0.0, 0.0],
        "end": [1.0, 2.0, 3.0],
        "kind": "vector",
        "line_width": 2.4,
    })

    window._pane_scene().geometry3d_controller.add_linear.assert_called_once_with(
        "lesson-vector",
        (0.0, 0.0, 0.0),
        (1.0, 2.0, 3.0),
        kind="vector",
        color="#2777b6",
        role="primary",
        style="solid",
    )


def test_teaching_points_at_vector_starts_do_not_render_origin_spheres(monkeypatch) -> None:
    window = _three_d_window()
    scene = window._pane_scene()
    scene._agent_geometry3d = {
        "ch04__entity__input_vector_a": {
            "op": "linear3d.upsert", "kind": "vector",
            "start": [0.0, 0.0, 0.0], "end": [2.0, 0.0, 3.0],
        },
    }
    scene._agent_points3d = {
        "ch04__entity__zero": (0.0, 0.0, 0.0),
        "ch04__entity__other": (1.0, 0.0, 0.0),
    }
    renderer = window._pane().renderer_3d
    renderer.remove_actor = MagicMock()
    renderer.add_mesh = MagicMock()
    monkeypatch.setattr("pyvista.Sphere", lambda **kwargs: kwargs)

    window._render_agent_points3d(render=False)

    assert [call.kwargs["name"] for call in renderer.add_mesh.call_args_list] == [
        "agent-point:ch04__entity__other"
    ]


def test_teaching_point_spheres_follow_storyboard_visibility_after_rerender(monkeypatch) -> None:
    window = _three_d_window()
    scene = window._pane_scene()
    renderer = window._pane().renderer_3d
    renderer.remove_actor = MagicMock()
    first_actor = SimpleNamespace(visibility=True)
    second_actor = SimpleNamespace(visibility=True)
    renderer.add_mesh = MagicMock(side_effect=(first_actor, second_actor))
    scene.geometry3d_controller = Geometry3DSceneController(renderer)
    scene._agent_points3d = {"case_result": (2.0, -1.0, 0.0)}
    monkeypatch.setattr("pyvista.Sphere", lambda **kwargs: kwargs)

    window._render_agent_points3d(render=False)
    scene.geometry3d_controller.set_visible("case_result", False)
    window._render_agent_points3d(render=False)

    assert scene.geometry3d_controller.actors["agent-point:case_result"] is second_actor
    assert second_actor.visibility is False


def test_three_d_annotation_is_an_editable_row_in_the_shared_algebra_list() -> None:
    panel = AlgebraPanel()
    row = AlgebraAnnotation3D(
        "manual_annotation_1", (1.0, 2.0, 3.0), "标记", "标记"
    )
    updates: list[tuple[str, str, str]] = []
    panel.annotation_updated.connect(
        lambda pane_id, alias, latex: updates.append((pane_id, alias, latex))
    )

    panel.set_layers([row])
    panel.formula_list.begin_edit = MagicMock()
    panel.begin_annotation_edit(row.alias)
    panel.formula_list.begin_edit.assert_called_once_with(row.alias)

    panel._submit_inline_formula_from_model(panel.formula_list, row.id, r"\text{这里可以输入中文}")
    assert updates == [("pane-1", row.alias, r"\text{这里可以输入中文}")]


def test_teaching_plane_has_a_read_only_algebra_equation_row() -> None:
    row = AlgebraPlane3D(
        "ch04__entity__column_space",
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        label="Col(A)",
    )
    panel = AlgebraPanel()

    panel.set_layers([row])

    assert panel.formula_list._layers[row.id] is row
    assert row.name == "Col(A)"
    assert row.latex == "z=0"
    assert panel.formula_list._serialize_layer(row)["editable"] is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(1, 2, 3)", (1.0, 2.0, 3.0)),
        (r"\vec{v}=\begin{pmatrix}-1.5\\\frac{1}{4}\\2e1\end{pmatrix}", (-1.5, 0.25, 20.0)),
        (r"v=\\left(-1.5, .25, 2e1\\right)", (-1.5, 0.25, 20.0)),
        ("1, 2", None),
        ("(1, nan, 3)", None),
    ],
)
def test_parse_3d_vector_endpoint_accepts_only_three_finite_numbers(text: str, expected: tuple[float, float, float] | None) -> None:
    assert parse_3d_vector_endpoint(text) == expected


def _three_d_window() -> MainWindow:
    window = object.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    pane = window._pane()
    pane.scene_mode = SceneMode.THREE_D
    pane.renderer_3d = SimpleNamespace(
        camera=SimpleNamespace(view_angle=30.0),
        camera_position=[(0.0, 0.0, 8.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        render=MagicMock(),
    )
    scene = window._pane_scene()
    scene.geometry3d_controller = MagicMock()
    window._render_scene = MagicMock()
    window._update_geometry_history_controls = MagicMock()
    window.algebra_panel = MagicMock()
    return window


class _MouseEvent:
    def __init__(self) -> None:
        self.accepted = False

    @staticmethod
    def button():
        return Qt.MouseButton.LeftButton

    @staticmethod
    def position():
        return SimpleNamespace(x=lambda: 30.0, y=lambda: 40.0)

    def accept(self) -> None:
        self.accepted = True


def test_new_algebra_vector_row_creates_and_updates_an_origin_vector_with_history() -> None:
    window = _three_d_window()

    window._create_3d_vector()

    operation = window._pane_scene()._agent_geometry3d["manual_vector_1"]
    assert operation == {
        "op": "linear3d.upsert",
        "alias": "manual_vector_1",
        "start": (0.0, 0.0, 0.0),
        "end": (1.0, 0.0, 0.0),
        "kind": "vector",
        "color": "#2777b6",
        "role": "primary",
    }
    assert window.pane_manager.can_undo
    window.algebra_panel.begin_three_d_vector_edit.assert_called_once_with("manual_vector_1")

    window._update_3d_vector_from_algebra(
        window._pane().pane_id,
        "manual_vector_1",
        r"\vec{v}_{1}=\begin{pmatrix}1\\-2\\3\end{pmatrix}",
    )
    assert window._pane_scene()._agent_geometry3d["manual_vector_1"]["end"] == (1.0, -2.0, 3.0)

    window._undo_2d_geometry()
    assert window._pane_scene()._agent_geometry3d["manual_vector_1"]["end"] == (1.0, 0.0, 0.0)

    window._undo_2d_geometry()
    assert "manual_vector_1" not in window._pane_scene()._agent_geometry3d
    assert window.pane_manager.can_redo

    window._redo_2d_geometry()
    assert window._pane_scene()._agent_geometry3d["manual_vector_1"]["end"] == (1.0, 0.0, 0.0)
    window._redo_2d_geometry()
    assert window._pane_scene()._agent_geometry3d["manual_vector_1"]["end"] == (1.0, -2.0, 3.0)


def test_new_three_d_mark_creates_an_editable_row_and_keeps_plain_text() -> None:
    window = _three_d_window()
    window.effective_theme = "dark"

    assert window._create_3d_annotation((1.0, 2.0, 3.0))

    operation = window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]
    assert operation["position"] == (1.0, 2.0, 3.0)
    assert operation["text"] == ""
    assert operation["latex"] == ""
    assert operation["color"] == "#f3f6fa"
    window.algebra_panel.begin_annotation_edit.assert_called_once_with("manual_annotation_1")

    window._update_annotation_from_algebra(
        window._pane().pane_id,
        "manual_annotation_1",
        r"\text{这里可以输入中文和 English}",
    )
    assert window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]["text"] == "这里可以输入中文和 English"

    window._undo_2d_geometry()
    assert window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]["text"] == ""
    window._undo_2d_geometry()
    assert "annotation:manual_annotation_1" not in window._pane_scene()._agent_geometry3d


def test_three_d_mark_uses_hand_cursor_and_drag_is_undoable() -> None:
    window = _three_d_window()
    assert window._create_3d_annotation((1.0, 2.0, 3.0))
    event = _MouseEvent()
    cursor_calls = []
    window._three_d_annotation_at = lambda _event: "manual_annotation_1"
    window._three_d_annotation_position = lambda _event: (4.0, 5.0, 6.0)
    window._set_3d_annotation_cursor = cursor_calls.append

    assert window._handle_3d_annotation_mouse_move(event) is False
    assert cursor_calls[-1] is Qt.CursorShape.OpenHandCursor
    assert window._handle_3d_annotation_mouse_press(event)
    assert cursor_calls[-1] is Qt.CursorShape.ClosedHandCursor
    assert window._handle_3d_annotation_mouse_move(event)
    assert window._handle_3d_annotation_mouse_release(event)

    operation = window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]
    assert operation["position"] == (4.0, 5.0, 6.0)
    assert window.pane_manager.can_undo
    window._undo_2d_geometry()
    restored = window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]
    assert restored["position"] == (1.0, 2.0, 3.0)


def test_three_d_mark_hover_redraws_an_outline_and_clears_it() -> None:
    window = _three_d_window()
    renderer = window._pane().renderer_3d
    renderer.add_point_labels = MagicMock()
    renderer.remove_actor = MagicMock()
    assert window._create_3d_annotation((1.0, 2.0, 3.0))
    window._update_annotation_from_algebra(
        window._pane().pane_id,
        "manual_annotation_1",
        "标记内容",
    )

    window._set_3d_annotation_hover("manual_annotation_1")
    assert renderer.add_point_labels.call_args.kwargs["shape"] == "rounded_rect"
    assert renderer.add_point_labels.call_args.kwargs["shape_color"] == "#1a73e8"
    assert renderer.add_point_labels.call_args.kwargs["fill_shape"] is False

    window._set_3d_annotation_hover(None)
    assert renderer.add_point_labels.call_args.kwargs["shape"] is None


def test_three_d_mark_supports_visibility_and_deletion() -> None:
    window = _three_d_window()
    assert window._create_3d_annotation((0.0, 0.0, 0.0))

    window._set_layer_visibility("manual_annotation_1", False)
    assert window._pane_scene()._agent_geometry3d["annotation:manual_annotation_1"]["visible"] is False

    window._remove_layer_for_scene("manual_annotation_1")
    assert "annotation:manual_annotation_1" not in window._pane_scene()._agent_geometry3d

    window._undo_2d_geometry()
    assert "annotation:manual_annotation_1" in window._pane_scene()._agent_geometry3d


def test_teaching_plane_equation_row_controls_the_existing_plane_actor() -> None:
    window = _three_d_window()
    alias = "ch04__entity__column_space"
    window._pane_scene()._agent_geometry3d[alias] = {
        "op": "plane3d.upsert",
        "alias": alias,
        "origin": [0.0, 0.0, 0.0],
        "normal": [0.0, 0.0, 1.0],
        "algebra_visible": True,
        "algebra_label": "Col(A)",
    }

    row = window._three_d_plane_row(alias)
    assert row is not None and row.latex == "z=0"
    window._set_layer_visibility(alias, False)

    assert window._pane_scene()._agent_geometry3d[alias]["visible"] is False
    window._pane_scene().geometry3d_controller.set_visible.assert_called_once_with(alias, False)
