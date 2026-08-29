"""Stable headless Qt defaults for the WebEngine integration tests."""

from __future__ import annotations

import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-software-rasterizer --single-process",
)

# QtWebEngine requires this before QApplication exists, including in offscreen
# test runs where WebEngine views are constructed by layout fixtures.
from PySide6.QtCore import QCoreApplication, Qt

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
