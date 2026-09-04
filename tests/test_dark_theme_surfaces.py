"""Integrated regressions for dark Qt surfaces and formula fallback content."""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from MathInputWidget.formula_preview import FormulaPreviewWidget
from rendering.lighting import LightSettings
from ui.lighting_dialog import LightingDialog
from ui.tokens import build_qss, flatten_theme


def _render(widget) -> QImage:
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("#00000000"))
    painter = QPainter(image)
    widget.render(painter, QPoint(0, 0))
    painter.end()
    return image


def _non_background_pixels(image: QImage, background: QColor) -> int:
    return sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
        and image.pixelColor(x, y) != background
    )


def test_dark_lighting_and_formula_fallback_are_token_driven() -> None:
    app = QApplication.instance() or QApplication([])
    previous_stylesheet = app.styleSheet()
    app.setStyleSheet(build_qss("dark"))
    lighting = LightingDialog(LightSettings(), effective_theme="dark")
    preview = FormulaPreviewWidget("x^2")
    try:
        lighting.show()
        preview.show()
        app.processEvents()

        colors = lighting.rotation_widget._paint_colors
        dark = flatten_theme("dark")
        assert colors["card"] == dark["bg_elevated"]
        assert colors["label"] == dark["text_secondary"]
        assert colors["value"] == dark["accent_default"]
        assert preview._fallback_label.isVisibleTo(preview)
        assert "color:" not in preview._fallback_label.styleSheet()
        assert f"#formulaPreviewFallback {{ color: {dark['text_primary']}" in build_qss("dark")

        lighting_image = _render(lighting.rotation_widget)
        assert lighting_image.pixelColor(3, 3).name() != "#f4f6f9"

        fallback_image = _render(preview._fallback_label)
        background = fallback_image.pixelColor(0, 0)
        assert _non_background_pixels(fallback_image, background) > 0
    finally:
        preview.close()
        lighting.close()
        app.setStyleSheet(previous_stylesheet)
