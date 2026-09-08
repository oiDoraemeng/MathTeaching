"""Focus routing and renderer recovery, with real Qt widgets and no GPU."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import shiboken6
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from services.scene_commands import CommandPlan, SceneCommandService
from ui.designer_window import MainWindow, _GeometryInputFilter, _SceneCommandBridge, _SceneCommandHostProxy
from ui.scene_pane_manager import ScenePaneManager
from ui.scene_pane_widget import ScenePaneWidget


class Renderer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.interactor = self
        self.render_window = object()
        self.render_count = 0

    def render(self):
        self.render_count += 1


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def container(qapp):
    widget = ScenePaneWidget(ScenePaneManager(), interactor_factory=Renderer)
    widget.set_layout(3)
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.mark.parametrize("event_type", [QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn])
def test_mouse_and_keyboard_focus_highlight_exactly_one_pane(container, event_type):
    target = container.manager.visible_pane_ids()[1]
    container.eventFilter(container.interactor(target), QEvent(event_type))
    assert container.manager.active_pane_id == target
    assert [key for key, renderer in container.interactors.items() if renderer.property("activePane")] == [target]


def test_initial_highlight_and_stylesheet_selector_match(container):
    assert all(renderer.objectName() == "scenePane" for renderer in container.interactors.values())
    assert sum(bool(renderer.property("activePane")) for renderer in container.interactors.values()) == 1
    qss = (Path(__file__).parents[1] / "ui/styles/base.qss.in").read_text(encoding="utf-8")
    assert '#scenePane[activePane="true"]' in qss
    assert 'border: 2px solid $accent_default' in qss


def test_input_filter_activates_receiver_before_tool_mutates(container):
    target = container.manager.visible_pane_ids()[1]
    observed = []
    owner = SimpleNamespace(scene_pane_widget=container, pane_manager=container.manager,
                            _handle_geometry_mouse_press=lambda event: observed.append(container.manager.active_pane_id) or True)
    receiver = container.interactor(target)
    event_filter = _GeometryInputFilter(owner, receiver)
    event = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(4, 4), QPointF(4, 4),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert event_filter.eventFilter(receiver, event)
    assert observed == [target]


@pytest.mark.parametrize("activate", [True, False])
def test_explicit_command_activation_and_pinned_agent_policy(qapp, activate):
    window = MainWindow.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    first, second = window.pane_manager.set_layout(2)
    observed = []
    window.begin_scene_command_transaction = lambda pane_id: observed.append(("begin", pane_id, window.pane_manager.active_pane_id))
    window.apply_scene_command = lambda operation, pane_id: observed.append(("apply", pane_id, window.pane_manager.active_pane_id))
    window.commit_scene_command_transaction = lambda pane_id: None
    window.rollback_scene_command_transaction = lambda pane_id: None
    service = SceneCommandService(_SceneCommandHostProxy(_SceneCommandBridge(window)))
    service.execute(CommandPlan(operations=({"op": "view.fit"},)), pane_id=second, activate_pane=activate)
    expected_focus = second if activate else first
    assert observed and all(pane == second and focus == expected_focus for _, pane, focus in observed)


def test_restore_redraws_every_visible_pane_without_changing_focus(container, monkeypatch):
    window = MainWindow.__new__(MainWindow)
    window.window = QWidget()
    window.pane_manager = container.manager
    window.scene_pane_widget = container
    ids = container.manager.visible_pane_ids()
    container.manager.focus_pane(ids[1])
    rendered = []
    window._render_scene = lambda: rendered.append(window._pane().pane_id)
    window._apply_linear_algebra_storyboard_visibility = lambda: None
    monkeypatch.setattr("ui.designer_window.QTimer.singleShot", lambda *args: None)
    refresh = Mock(wraps=container.refresh_visible_panes)
    monkeypatch.setattr(container, "refresh_visible_panes", refresh)
    window._restore_render_surfaces()
    assert refresh.called
    assert rendered == list(ids)
    assert container.manager.active_pane_id == ids[1]
    window.window.close()


@pytest.mark.parametrize("invalidity", ["deleted", "missing_window"])
def test_invalid_renderer_recreated_from_retained_state(container, invalidity):
    pane_id = container.manager.visible_pane_ids()[1]
    state = container.manager.pane(pane_id)
    state.scene_2d["objects"] = ["retained"]
    old = container.interactor(pane_id)
    if invalidity == "deleted":
        shiboken6.delete(old)
    else:
        old.render_window = None
    restored = []
    container._on_interactor_created = lambda key, renderer: restored.append((key, container.manager.pane(key).scene_2d.copy()))
    container.refresh_visible_panes()
    assert container.interactor(pane_id) is not old
    assert state.renderer_2d is container.interactor(pane_id)
    assert restored == [(pane_id, {"objects": ["retained"]})]
    assert container.interactor(pane_id).objectName() == "scenePane"


def test_recovery_retries_are_bounded_and_back_off_without_duplicates(container):
    target = container.manager.visible_pane_ids()[1]
    container.interactor(target).render_window = None
    attempts = []

    def broken_factory(parent):
        attempts.append(True)
        raise RuntimeError("context unavailable")

    container._factory = broken_factory
    container.refresh_visible_panes()
    intervals = []
    for _ in range(4):
        timer = container._retry_timers[target]
        intervals.append(timer.interval())
        assert timer.isActive()
        timer.stop()
        timer.timeout.emit()
    assert intervals == [50, 100, 200, 400]
    assert len(attempts) == 5
    assert target not in container._retry_timers
    assert container.manager.pane(target).renderer_2d is None
    container._factory = Renderer
    container.refresh_visible_panes()
    assert container.interactor(target) is not None
    assert target not in container._retry_attempts


def test_refresh_renders_healthy_panes_and_hidden_surface_is_reused(container):
    previous = container.interactors
    target = next(iter(previous.values()))
    target.hide()
    counts = {key: renderer.render_count for key, renderer in previous.items()}
    container.refresh_visible_panes()
    assert container.interactors == previous
    assert not target.isHidden()
    assert all(renderer.render_count > counts[key] for key, renderer in previous.items())
