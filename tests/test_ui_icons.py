import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QToolButton

from ui.icons import apply_icon, icon


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "name",
    ["settings-2", "sparkles", "play", "circle-dot", "slash", "type", "undo-2", "redo-2", "plus", "ellipsis"],
)
def test_required_icons_render(name):
    rendered = icon(name, "#123456")
    assert not rendered.isNull()
    assert rendered.pixmap(QSize(16, 16)).size() == QSize(16, 16)


def test_icon_supports_high_dpi_and_cache():
    first = icon("plus", "#123456", 16, 2.0)
    second = icon("plus", "#123456", 16, 2.0)
    pixmap = first.pixmap(QSize(16, 16), 2.0)
    assert first.cacheKey() == second.cacheKey()
    assert pixmap.size() == QSize(32, 32)
    assert pixmap.devicePixelRatio() == 2.0


def test_unknown_icon_and_invalid_color_fail():
    with pytest.raises(KeyError):
        icon("missing", "#123456")
    with pytest.raises(ValueError):
        icon("plus", "not-a-color")


def test_apply_icon_clears_text_and_sets_metrics():
    button = QToolButton()
    button.setText("+")
    apply_icon(button, "plus", "#123456")
    assert button.text() == ""
    assert button.width() == 36 and button.height() == 36
    assert button.iconSize() == QSize(16, 16)
