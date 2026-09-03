from types import SimpleNamespace
from unittest.mock import MagicMock

from linear_algebra.catalog.manifest import topic_entries
from models.scene_mode import SceneMode
from services.scene_commands import CommandPlan
from ui.designer_window import MainWindow


def test_every_topic_is_wrapped_in_one_clear_and_load_plan() -> None:
    for topic in topic_entries():
        plan = MainWindow._linear_algebra_lesson_plan(topic.id)
        assert isinstance(plan, CommandPlan)
        assert plan.operations[0] == {"op": "scene.clear", "scope": "all"}
        assert plan.scene in {"2d", "3d"}
        assert plan.operations[-1]["op"] == "view.fit"


def test_unknown_topic_reports_error_without_executing() -> None:
    statuses: list[tuple[str, bool]] = []
    executed: list[CommandPlan] = []
    window = MainWindow.__new__(MainWindow)
    window.algebra_panel = SimpleNamespace(set_status=lambda text, is_error=False: statuses.append((text, is_error)))
    window.scene_command_service = SimpleNamespace(execute=executed.append)

    window._load_linear_algebra_topic("missing-topic")

    assert executed == []
    assert statuses and statuses[-1][1] is True
    assert "线性代数主题" in statuses[-1][0]


def test_linear_algebra_toolbar_context_tracks_loaded_topic() -> None:
    window = MainWindow.__new__(MainWindow)
    window.scene_mode = SceneMode.TWO_D
    window._linear_algebra_workspace_active = False
    window._active_linear_algebra_topic_id = "ch01.ops.addition"
    assert window._is_linear_algebra_context() is True

    window._active_linear_algebra_topic_id = "ch01.ops.cross-product"
    assert window._is_linear_algebra_context() is False

    window._active_linear_algebra_topic_id = None
    assert window._is_linear_algebra_context() is False

    window._linear_algebra_workspace_active = True
    assert window._is_linear_algebra_context() is True


def test_opening_linear_algebra_enters_2d_workspace_and_reveals_tools() -> None:
    window = MainWindow.__new__(MainWindow)
    window.scene_mode = SceneMode.THREE_D
    window._linear_algebra_workspace_active = False
    window._active_linear_algebra_topic_id = "ch01.ops.cross-product"
    window._set_scene_mode = MagicMock(
        side_effect=lambda mode: setattr(window, "scene_mode", mode)
    )
    window._set_2d_geometry_tool = MagicMock()
    window._sync_scene_controls = MagicMock()
    window._position_viewport_overlays = MagicMock()
    window.linear_algebra_toolbar = MagicMock()
    window.algebra_panel = MagicMock()

    window._enter_linear_algebra_workspace()

    assert window._linear_algebra_workspace_active is True
    assert window._active_linear_algebra_topic_id is None
    window._set_scene_mode.assert_called_once_with(SceneMode.TWO_D)
    window._set_2d_geometry_tool.assert_called_once_with("select")
    window.linear_algebra_toolbar.set_active_tool.assert_called_once_with(
        "select",
        emit_signal=False,
    )
    window._sync_scene_controls.assert_called_once_with()
    window._position_viewport_overlays.assert_called_once_with()
    window.algebra_panel.set_status.assert_called_once_with(
        "线性代数工具栏已显示在画布左上角"
    )


def test_loading_a_2d_topic_activates_the_visible_select_tool() -> None:
    window = MainWindow.__new__(MainWindow)
    window.scene_mode = SceneMode.TWO_D
    window.algebra_panel = SimpleNamespace(set_status=lambda *_args, **_kwargs: None)
    window.scene_command_service = SimpleNamespace(execute=lambda _plan: None)
    window._set_2d_geometry_tool = MagicMock()
    window._sync_scene_controls = MagicMock()
    window.linear_algebra_toolbar = MagicMock()

    window._load_linear_algebra_topic("ch01.ops.addition")

    assert window._active_linear_algebra_topic_id == "ch01.ops.addition"
    window._set_2d_geometry_tool.assert_called_once_with("select")
    window.linear_algebra_toolbar.set_active_tool.assert_called_once_with(
        "select",
        emit_signal=False,
    )
