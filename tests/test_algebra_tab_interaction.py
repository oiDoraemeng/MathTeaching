import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QEnterEvent, QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabBar, QToolButton, QWidget

from ui.algebra_panel import AlgebraPaneTabs


@pytest.fixture
def tabs():
    application = QApplication.instance() or QApplication([])
    widget = AlgebraPaneTabs()
    widget.resize(240, 120)
    for i in range(3):
        widget.addTab(QWidget(), f"窗格 {i + 1}")
    widget.show()
    application.processEvents()
    QApplication.sendEvent(widget.tabBar(), QEvent(QEvent.Type.Leave))
    yield widget
    widget.close()


def close_button(bar, index):
    return bar.tabButton(index, QTabBar.ButtonPosition.RightSide) or bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)


def hover(bar, index):
    point = QPointF(bar.tabRect(index).center())
    QApplication.sendEvent(bar, QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


def test_close_button_tracks_hover_without_mouse_press_and_closes_only_target(tabs):
    bar = tabs.tabBar()
    assert bar.hasMouseTracking()
    assert all(close_button(bar, i).isHidden() for i in range(3))
    hover(bar, 0)
    assert not close_button(bar, 0).isHidden()
    hover(bar, 1)
    assert close_button(bar, 0).isHidden()
    assert not close_button(bar, 1).isHidden()
    closed = []
    tabs.tabCloseRequested.connect(closed.append)
    QTest.mouseClick(close_button(bar, 1), Qt.MouseButton.LeftButton)
    assert closed == [1]
    QApplication.sendEvent(bar, QEvent(QEvent.Type.Leave))
    assert all(close_button(bar, i).isHidden() for i in range(3))


def test_enter_and_new_tabs_support_hover_close(tabs):
    bar = tabs.tabBar()
    point = QPointF(bar.tabRect(0).center())
    QApplication.sendEvent(bar, QEnterEvent(point, point, point))
    assert not close_button(bar, 0).isHidden()
    tabs.addTab(QWidget(), "新增窗格")
    assert close_button(bar, 3).isHidden()
    hover(bar, 3)
    assert not close_button(bar, 3).isHidden()


def test_overflow_scrolls_without_arrows_or_scrollbars_and_selection_reveals_tab(tabs):
    bar = tabs.tabBar()
    for i in range(8):
        tabs.addTab(QWidget(), f"保留的窗格 {i}")
    QApplication.processEvents()
    assert not bar.usesScrollButtons()
    assert not any(button.isVisible() for button in bar.findChildren(QToolButton))
    assert not tabs.scroll.horizontalScrollBar().isVisible()
    assert tabs.scroll.frameWidth() == 0
    scrollbar = tabs.scroll.horizontalScrollBar()
    assert scrollbar.maximum() > 0
    tabs.setCurrentIndex(0)
    changes = []
    tabs.currentChanged.connect(changes.append)
    event = QWheelEvent(QPointF(30, 10), QPointF(30, 10), QPoint(), QPoint(0, -120), Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(tabs.scroll.viewport(), event)
    assert scrollbar.value() > 0
    assert tabs.currentIndex() == 0
    assert changes == []

    # The tab bar itself receives wheel events when the pointer is over its
    # visible labels.  Its default implementation would change the current
    # tab, so this must have the same inspect-only behaviour as the viewport.
    QApplication.sendEvent(bar, event)
    assert tabs.currentIndex() == 0
    assert changes == []

    # Selection remains an intentional click or keyboard operation.
    QTest.mouseClick(bar, Qt.MouseButton.LeftButton, pos=bar.tabRect(1).center())
    assert tabs.currentIndex() == 1
    assert changes == [1]
    bar.setFocus()
    QTest.keyClick(bar, Qt.Key.Key_Right)
    assert tabs.currentIndex() == 2
    assert changes == [1, 2]

    tabs.setCurrentIndex(tabs.count() - 1)
    assert tabs._pages.currentIndex() == tabs.count() - 1
    assert scrollbar.value() > 120
    tabs.setCurrentIndex(0)
    assert scrollbar.value() == 0
