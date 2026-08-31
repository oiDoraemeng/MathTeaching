import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QToolButton

import ui.icons as icons
from ui.icons import apply_icon, icon


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _opaque_pixel_count(rendered, size=16, dpr=1.0):
    """Count actually painted pixels so a fully transparent icon cannot pass."""
    image = rendered.pixmap(QSize(size, size), dpr).toImage()
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    )


@pytest.mark.parametrize(
    "name",
    ["settings-2", "sparkles", "play", "circle-dot", "slash", "type", "undo-2", "redo-2", "plus", "ellipsis"],
)
def test_required_icons_render(name):
    rendered = icon(name, "#123456")
    assert not rendered.isNull()
    assert rendered.pixmap(QSize(16, 16)).size() == QSize(16, 16)


@pytest.mark.parametrize("name", sorted(icons.LUCIDE_SVG))
def test_every_icon_paints_visible_strokes(name):
    """A QIcon built from a transparent pixmap is not null, so assert pixels."""
    assert _opaque_pixel_count(icon(name, "#1f2937")) > 0


def test_icon_stroke_color_is_svg_compatible():
    """Qt's SVG parser only accepts #RRGGBB, not Qt's #AARRGGBB HexArgb form."""
    assert icons._svg_color("#1f2937") == "#1f2937"
    assert icons._svg_color(QColor("#1f2937")) == "#1f2937"


def test_icon_tint_reaches_rendered_pixels():
    image = icon("plus", "#b3b8c0").pixmap(QSize(16, 16)).toImage()
    strongest = max(
        (image.pixelColor(x, y) for y in range(16) for x in range(16)),
        key=lambda color: color.alpha(),
    )
    assert strongest.alpha() > 0
    assert abs(strongest.red() - 0xB3) <= 2
    assert abs(strongest.green() - 0xB8) <= 2
    assert abs(strongest.blue() - 0xC0) <= 2


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


def test_apply_icon_uses_window_screen_dpr(monkeypatch):
    seen = {}

    def fake_icon(name, color, size=16, dpr=1.0):
        seen["args"] = (name, color, size, dpr)
        return icon(name, color, size, dpr)

    class _Screen:
        def devicePixelRatio(self):
            return 2.5

    class _WindowHandle:
        def screen(self):
            return _Screen()

    class _Window:
        def windowHandle(self):
            return _WindowHandle()

    class _Button:
        def setText(self, _text):
            pass

        def window(self):
            return _Window()

        def setIcon(self, _icon):
            pass

        def setIconSize(self, _size):
            pass

        def setFixedSize(self, _w, _h):
            pass

    monkeypatch.setattr(icons, "icon", fake_icon)
    apply_icon(_Button(), "plus", "#123456")
    assert seen["args"] == ("plus", "#123456", 16, 2.5)


def test_apply_icon_falls_back_to_one_without_screen(monkeypatch):
    seen = {}

    def fake_icon(name, color, size=16, dpr=1.0):
        seen["args"] = (name, color, size, dpr)
        return icon(name, color, size, dpr)

    class _Button:
        def setText(self, _text):
            pass

        def window(self):
            return None

        def setIcon(self, _icon):
            pass

        def setIconSize(self, _size):
            pass

        def setFixedSize(self, _w, _h):
            pass

    monkeypatch.setattr(icons, "icon", fake_icon)
    monkeypatch.setattr(icons.QApplication, "primaryScreen", staticmethod(lambda: None))
    apply_icon(_Button(), "plus", "#123456")
    assert seen["args"] == ("plus", "#123456", 16, 1.0)
