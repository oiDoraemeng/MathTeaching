"""Rounded-corner contracts for floating Qt chrome.

Qt only clips a QSS ``border-radius`` when it paints the widget background into
a surface it owns. Two situations break that and leave the corner showing raw
backing store (black on Windows):

* frameless top-level popups without ``WA_TranslucentBackground``
* viewport overlays that Qt force-promotes to native windows because they are
  siblings of the native VTK interactor

Both need an explicit opt-in, so assert it here rather than trusting the QSS.
"""

from __future__ import annotations

from ui.scene_pane_manager import ScenePaneManager

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from ui.algebra_panel import AlgebraPanel
from ui.scene_settings import SceneSettingsPanel
from ui.tokens import apply_rounded_overlay, flatten_theme
from ui.two_d_tools import TwoDGeometryToolbar


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _radius(key: str) -> int:
    return int(flatten_theme("light")[f"radius_{key}"])


def test_frameless_popups_are_translucent_so_corners_are_not_black() -> None:
    panel = AlgebraPanel()
    popups = (
        panel.settings_popup,
        panel.geometry_settings_popup,
        panel.intersection_popup,
        panel.catalog_popup,
        panel.formula_popup,
        panel.linear_algebra_popup,
    )
    for popup in popups:
        assert popup.isWindow(), popup.objectName()
        assert popup.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground), popup.objectName()


def test_viewport_child_overlays_carry_rounded_masks() -> None:
    host = QWidget()
    host.resize(600, 400)
    toolbar = TwoDGeometryToolbar(host)
    settings = SceneSettingsPanel(host)
    host.show()

    for widget in (toolbar, toolbar.line_flyout, settings):
        widget.resize(120, 90)
        widget.show()
        QApplication.processEvents()
        mask = widget.mask()
        assert not mask.isEmpty(), widget.objectName()
        assert not mask.contains(QPoint(0, 0)), widget.objectName()
        assert mask.contains(QPoint(60, 45)), widget.objectName()


def test_viewport_toolbar_built_by_configure_viewport_is_masked(monkeypatch) -> None:
    """The main viewport toolbar is created inside ``_configure_viewport``, so it
    needs its own coverage — a plain constructor test never reaches it."""
    from unittest.mock import MagicMock

    from PySide6.QtWidgets import QBoxLayout, QHBoxLayout

    from models.scene_mode import SceneMode
    from rendering.scene import SceneAppearance
    from ui.designer_window import MainWindow

    class FakeInteractor:
        def __init__(self, parent: QWidget) -> None:
            self.interactor = QWidget(parent)
            self.iren = None

        def setFocusPolicy(self, policy) -> None:
            self.interactor.setFocusPolicy(policy)

    monkeypatch.setattr("ui.designer_window.QtInteractor", FakeInteractor)
    shell = QWidget()
    viewport_host = QWidget(shell)
    viewport_host.setObjectName("viewportHost")
    QHBoxLayout(shell).addWidget(viewport_host)
    window = object.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window.window = shell
    window._pane_scene().scene_mode = SceneMode.THREE_D
    window._pane_scene().scene_appearances = {
        SceneMode.TWO_D: SceneAppearance(),
        SceneMode.THREE_D: SceneAppearance(),
    }
    window._update_geometry_history_controls = MagicMock()

    MainWindow._configure_viewport(window)
    shell.resize(600, 400)
    shell.show()
    QApplication.processEvents()

    toolbar = window.viewport_toolbar
    window._position_viewport_overlays()
    assert toolbar.layout().direction() == QBoxLayout.Direction.TopToBottom
    assert toolbar.x() == viewport_host.width() - toolbar.width() - 12
    assert toolbar.y() == (viewport_host.height() - toolbar.height()) // 2
    assert window.two_d_geometry_toolbar.layout().direction() == QBoxLayout.Direction.TopToBottom
    assert window.two_d_geometry_toolbar.x() == 12
    assert window.two_d_geometry_toolbar.y() == max(8, (viewport_host.height() - window.two_d_geometry_toolbar.height()) // 2)
    assert window.three_d_geometry_toolbar.layout().direction() == QBoxLayout.Direction.TopToBottom
    assert window.three_d_geometry_toolbar.x() == 12
    assert window.three_d_geometry_toolbar.y() == (viewport_host.height() - window.three_d_geometry_toolbar.height()) // 2
    mask = toolbar.mask()
    # An empty region "contains" nothing, so the emptiness check must come first
    # or a missing mask would pass the corner assertion vacuously.
    assert not mask.isEmpty(), "viewport toolbar must carry a rounded mask"
    assert not mask.contains(QPoint(0, 0))
    assert mask.contains(QPoint(toolbar.width() // 2, toolbar.height() // 2))


def test_rounded_mask_follows_resize() -> None:
    host = QWidget()
    host.resize(400, 400)
    overlay = QFrame(host)
    apply_rounded_overlay(overlay, "md")
    overlay.resize(80, 60)
    host.show()
    overlay.show()
    QApplication.processEvents()
    assert not overlay.mask().contains(QPoint(0, 0))
    assert overlay.mask().contains(QPoint(40, 30))

    overlay.resize(200, 160)
    QApplication.processEvents()
    assert overlay.mask().contains(QPoint(100, 80)), "mask must grow with the widget"
    assert not overlay.mask().contains(QPoint(0, 0))


def test_apply_rounded_overlay_uses_translucency_for_windows() -> None:
    window = QFrame()
    window.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
    apply_rounded_overlay(window, "lg")
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def test_overlay_radius_tokens_are_distinct() -> None:
    assert _radius("md") != _radius("lg")
