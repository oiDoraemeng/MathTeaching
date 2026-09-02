"""Tests for linear algebra toolbar."""

import pytest
from PySide6.QtWidgets import QApplication

from ui.linear_algebra_toolbar import LinearAlgebraToolbar


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_toolbar_creation(qapp):
    """Test toolbar creation and layout."""
    toolbar = LinearAlgebraToolbar(None, theme="light")

    # Verify tool buttons exist
    assert toolbar.select_tool is not None
    assert toolbar.point_tool is not None
    assert toolbar.vector_tool is not None
    assert toolbar.angle_tool is not None
    assert toolbar.projection_tool is not None
    assert toolbar.polygon_tool is not None
    assert toolbar.transform_tool is not None
    assert toolbar.subspace_tool is not None
    assert toolbar.area_tool is not None

    # Verify history buttons
    assert toolbar.undo_button is not None
    assert toolbar.redo_button is not None

    # Verify default tool
    assert toolbar.get_active_tool() == "select"
    assert toolbar.select_tool.isChecked()


def test_toolbar_tool_selection(qapp):
    """Test tool selection signals."""
    toolbar = LinearAlgebraToolbar(None)

    signal_received = []
    toolbar.tool_selected.connect(lambda tool: signal_received.append(tool))

    # Click angle tool
    toolbar.angle_tool.click()
    assert "angle" in signal_received
    assert toolbar.get_active_tool() == "angle"
    assert toolbar.angle_tool.isChecked()
    assert not toolbar.select_tool.isChecked()


def test_toolbar_set_active_tool(qapp):
    """Test programmatic tool selection."""
    toolbar = LinearAlgebraToolbar(None)

    signal_received = []
    toolbar.tool_selected.connect(lambda tool: signal_received.append(tool))

    # Set projection tool programmatically
    toolbar.set_active_tool("projection")
    assert toolbar.get_active_tool() == "projection"
    assert toolbar.projection_tool.isChecked()
    assert not toolbar.select_tool.isChecked()
    assert "projection" in signal_received


def test_toolbar_theme_switching(qapp):
    """Test theme switching."""
    toolbar = LinearAlgebraToolbar(None, theme="light")

    # Switch to dark theme
    toolbar.set_theme("dark")
    assert toolbar._theme == "dark"

    # Switch back to light
    toolbar.set_theme("light")
    assert toolbar._theme == "light"


def test_toolbar_undo_redo_signals(qapp):
    """Test undo/redo signals."""
    toolbar = LinearAlgebraToolbar(None)

    undo_called = []
    redo_called = []

    toolbar.undo_requested.connect(lambda: undo_called.append(True))
    toolbar.redo_requested.connect(lambda: redo_called.append(True))

    # Click undo
    toolbar.undo_button.click()
    assert len(undo_called) == 1

    # Click redo
    toolbar.redo_button.click()
    assert len(redo_called) == 1


def test_toolbar_button_sizes(qapp):
    """Test button sizes are correct."""
    toolbar = LinearAlgebraToolbar(None)

    # All tool buttons should be 32x32
    for btn in [
        toolbar.select_tool,
        toolbar.point_tool,
        toolbar.vector_tool,
        toolbar.angle_tool,
        toolbar.projection_tool,
        toolbar.polygon_tool,
        toolbar.transform_tool,
        toolbar.subspace_tool,
        toolbar.area_tool,
        toolbar.undo_button,
        toolbar.redo_button,
    ]:
        assert btn.width() == 32
        assert btn.height() == 32


def test_toolbar_only_one_tool_active(qapp):
    """Test that only one tool can be active at a time."""
    toolbar = LinearAlgebraToolbar(None)

    # Select is initially active
    assert toolbar.select_tool.isChecked()

    # Click vector tool
    toolbar.vector_tool.click()
    assert toolbar.vector_tool.isChecked()
    assert not toolbar.select_tool.isChecked()

    # Click polygon tool
    toolbar.polygon_tool.click()
    assert toolbar.polygon_tool.isChecked()
    assert not toolbar.vector_tool.isChecked()
    assert not toolbar.select_tool.isChecked()
