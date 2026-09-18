from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QBoxLayout, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from linear_algebra.teaching.load_states import LoadPhase
from models.scene_mode import SceneAppearance, SceneMode
from services.scene_commands import CommandPlan
from ui.designer_window import MainWindow
from ui.icons import LUCIDE_SVG, retint_icons
from ui.scene_pane_manager import ScenePaneManager
from ui.three_d_tools import ThreeDGeometryToolbar
from ui.two_d_tools import TwoDGeometryToolbar


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_layout_icons_are_bundled() -> None:
    assert all(f"layout-{count}" in LUCIDE_SVG for count in range(1, 5))


def test_layout_button_sync_uses_visible_pane_count(qapp: QApplication) -> None:
    host = QWidget()
    buttons = {count: QToolButton(host) for count in range(1, 5)}
    for button in buttons.values():
        button.setCheckable(True)
    manager = type("Manager", (), {"visible_pane_ids": lambda self: ("p1", "p2", "p3")})()
    window = MainWindow.__new__(MainWindow)
    window.layout_buttons = buttons
    window.pane_manager = manager
    MainWindow._sync_layout_buttons(window)
    assert buttons[3].isChecked()
    assert not buttons[1].isChecked()
    host.deleteLater()


def test_layout_icons_retint_with_theme(qapp: QApplication) -> None:
    host = QWidget()
    button = QToolButton(host)
    from ui.icons import apply_icon, icon_color
    apply_icon(button, "layout-1", icon_color("light"))
    assert retint_icons(host, "dark") == 1
    host.deleteLater()


def test_main_window_installs_four_layout_buttons_and_routes_click(qapp: QApplication) -> None:
    host = QWidget()
    window = MainWindow.__new__(MainWindow)
    window.viewport_toolbar = host
    window.effective_theme = "light"
    calls = []
    window.pane_manager = type("Manager", (), {"visible_pane_ids": lambda self: ("p1",), "set_layout": lambda self, n: calls.append(n)})()
    layout = QVBoxLayout(host)
    MainWindow._install_layout_buttons(window, layout)
    assert [b.accessibleName() for b in window.layout_buttons.values()] == ["单窗格布局", "双窗格布局", "三窗格布局", "四窗格布局"]
    assert all(b.toolTip() for b in window.layout_buttons.values())
    window.layout_buttons[4].click()
    assert calls == [4]
    host.deleteLater()


def test_layout_checked_selector_is_in_stylesheet() -> None:
    from ui.tokens import build_qss
    assert "#viewportToolbar QToolButton:checked" in build_qss("light")


def test_loading_new_chapters_preserves_the_mode_specific_toolbar_contract(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lecture loading may replace teaching content, never canvas chrome."""

    class FakeInteractor:
        def __init__(self, parent: QWidget) -> None:
            self.interactor = QWidget(parent)
            self.iren = None

        def setFocusPolicy(self, policy) -> None:
            self.interactor.setFocusPolicy(policy)

    plans = {
        "ch04.space.closure": CommandPlan(scene="2d", operations=({"op": "view.fit"},)),
        "ch08.principal-axis": CommandPlan(scene="3d", operations=({"op": "view.fit"},)),
    }
    opened: list[tuple[str, str]] = []

    class FakeTransaction:
        phase = LoadPhase.STAGED
        diagnostic = None

        def __init__(self, topic_id: str, plan: CommandPlan) -> None:
            self.explanation = SimpleNamespace(topic_id=topic_id)
            self.plan = plan
            self.pane_id = None

        def commit_host(self, _execute, **_kwargs) -> None:
            self.phase = LoadPhase.COMMITTED

        def reject(self, *_args, **_kwargs) -> None:
            self.phase = LoadPhase.REJECTED

    class FakeRegistry:
        def resolve_bundle(self, topic_id: str, **_kwargs):
            chapter_number = int(topic_id[2:4])
            topic = SimpleNamespace(
                id=topic_id,
                title=topic_id,
                source_path=(f"第 {chapter_number} 章", "绘图主题"),
                chapter_number=chapter_number,
            )
            compiled = SimpleNamespace(topic_id=topic_id, plan=plans[topic_id], storyboard=())
            return SimpleNamespace(
                topic=topic,
                compiled=compiled,
                source_diagnostic=None,
            )

        def commit_curriculum_bundle(self, bundle, **_kwargs):
            return FakeTransaction(bundle.topic.id, bundle.compiled.plan)

    monkeypatch.setattr("ui.designer_window.QtInteractor", FakeInteractor)
    monkeypatch.setattr("ui.designer_window.catalog_registry", lambda: FakeRegistry())
    monkeypatch.setattr("ui.designer_window.runtime_teaching_store", lambda: object())

    shell = QWidget()
    viewport_host = QWidget(shell)
    viewport_host.setObjectName("viewportHost")
    QHBoxLayout(shell).addWidget(viewport_host)
    window = object.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window.window = shell
    window.effective_theme = "light"
    window._active_linear_algebra_topic_id = None
    window._active_linear_algebra_compiled = None
    window._active_linear_algebra_stage_id = None
    window._hidden_linear_algebra_aliases = set()
    window._teaching_case_pane_ids = ["teaching-pane"]
    window._teaching_case_stage_refs = {}
    window._pane_scene().scene_mode = SceneMode.THREE_D
    window._pane_scene().scene_appearances = {
        SceneMode.TWO_D: SceneAppearance(),
        SceneMode.THREE_D: SceneAppearance(),
    }
    window._update_geometry_history_controls = MagicMock()
    window.scene_command_service = SimpleNamespace(execute=lambda _plan, **_kwargs: None)
    window._scene_snapshot_from_current_state = lambda: {}
    window.teaching_fingerprints = lambda: ("scene-before", "explanation-before")
    window._open_teaching_case_panes = (
        lambda explanation, compiled: opened.append((explanation.topic_id, compiled.topic_id))
    )
    def finalize(topic, bundle, *_args) -> None:
        window._active_linear_algebra_topic_id = topic.id
        window._active_linear_algebra_compiled = bundle.compiled

    window._finalize_linear_algebra_topic_load = finalize
    window._set_2d_geometry_tool = MagicMock()
    statuses: list[tuple[str, bool]] = []
    window.algebra_panel = SimpleNamespace(
        set_status=lambda text, is_error=False: statuses.append((text, is_error)),
        set_scene_mode=lambda _mode: None,
    )
    # This test isolates the toolbar contract; the 2-D mode transition itself
    # is covered by the linear-algebra loading test.
    window._set_scene_mode = MagicMock()

    MainWindow._configure_viewport(window)
    shell.resize(1000, 700)
    shell.show()
    qapp.processEvents()
    window._position_viewport_overlays()

    two_d_toolbar = window.two_d_geometry_toolbar
    three_d_toolbar = window.three_d_geometry_toolbar
    assert len(viewport_host.findChildren(TwoDGeometryToolbar)) == 1
    assert len(viewport_host.findChildren(ThreeDGeometryToolbar)) == 1
    assert not two_d_toolbar.isVisible()
    assert three_d_toolbar.isVisible()

    def toolbar_contract(toolbar: QWidget) -> tuple[object, ...]:
        actions = tuple(
            (id(button), button.objectName(), button.toolTip(), button.shortcut().toString())
            for button in toolbar.findChildren(QToolButton)
        )
        shortcuts = tuple(
            (id(shortcut), shortcut.key().toString(), shortcut.context())
            for shortcut in (
                window._undo_2d_shortcut,
                window._redo_2d_shortcut,
                window._copy_2d_shortcut,
                window._paste_2d_shortcut,
            )
        )
        return (
            id(toolbar),
            toolbar.objectName(),
            toolbar.pos(),
            toolbar.layout().direction(),
            actions,
            shortcuts,
        )

    two_d_baseline = toolbar_contract(two_d_toolbar)
    three_d_baseline = toolbar_contract(three_d_toolbar)
    assert two_d_baseline[2] == two_d_toolbar.pos()
    assert three_d_baseline[2] == three_d_toolbar.pos()
    assert two_d_toolbar.x() == three_d_toolbar.x() == 12
    assert two_d_baseline[3] == QBoxLayout.Direction.TopToBottom
    assert three_d_baseline[3] == QBoxLayout.Direction.TopToBottom

    window._enter_linear_algebra_workspace()
    assert toolbar_contract(two_d_toolbar) == two_d_baseline
    assert toolbar_contract(three_d_toolbar) == three_d_baseline

    for topic_id in plans:
        window._load_linear_algebra_topic(topic_id)
        assert statuses[-1][1] is False, statuses
        assert window.two_d_geometry_toolbar is two_d_toolbar
        assert window.three_d_geometry_toolbar is three_d_toolbar
        assert len(viewport_host.findChildren(TwoDGeometryToolbar)) == 1
        assert len(viewport_host.findChildren(ThreeDGeometryToolbar)) == 1
        assert toolbar_contract(two_d_toolbar) == two_d_baseline
        assert toolbar_contract(three_d_toolbar) == three_d_baseline

    assert opened == [(topic_id, topic_id) for topic_id in plans]
    assert statuses and all(not is_error for _text, is_error in statuses)
    assert window._undo_2d_shortcut.context() == Qt.ShortcutContext.WindowShortcut
    assert window._redo_2d_shortcut.context() == Qt.ShortcutContext.WindowShortcut
    shell.deleteLater()
