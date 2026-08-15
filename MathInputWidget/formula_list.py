"""使用单个 WebEngine 的函数列表与行内公式编辑器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QPoint, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from models.curve_layer import CurveLayer
from models.surface_layer import SurfaceLayer


Layer = SurfaceLayer | CurveLayer


class _FormulaListBridge(QObject):
    """接收共享 HTML 页面发出的列表和编辑器操作。"""

    edit_requested = Signal(str)
    formula_submitted = Signal(str, str)
    edit_cancelled = Signal(str)
    visibility_changed = Signal(str, bool)
    settings_requested = Signal(str, int, int)

    @Slot(str)
    def editRequested(self, layer_id: str) -> None:
        self.edit_requested.emit(layer_id)

    @Slot(str, str)
    def formulaSubmitted(self, layer_id: str, latex: str) -> None:
        self.formula_submitted.emit(layer_id, latex)

    @Slot(str)
    def editCancelled(self, layer_id: str) -> None:
        self.edit_cancelled.emit(layer_id)

    @Slot(str, bool)
    def visibilityChanged(self, layer_id: str, visible: bool) -> None:
        self.visibility_changed.emit(layer_id, visible)

    @Slot(str, int, int)
    def settingsRequested(self, layer_id: str, top: int, height: int) -> None:
        self.settings_requested.emit(layer_id, top, height)


class FormulaListWidget(QWidget):
    """在同一个 WebEngine 页面中渲染全部函数行与活动编辑器。"""

    edit_requested = Signal(str)
    formula_submitted = Signal(str, str)
    edit_cancelled = Signal(str)
    visibility_changed = Signal(str, bool)
    settings_requested = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layers: dict[str, Layer] = {}
        self._page_ready = False
        self._active_layer_id: str | None = None

        self.setObjectName("formulaListWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 将函数列表合并到一个网页，避免多个原生 QWebEngineView 相互遮挡或闪烁。
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._bridge = _FormulaListBridge(self)
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.setUrl(
            QUrl.fromLocalFile(str(Path(__file__).with_name("formula_list.html").resolve()))
        )
        layout.addWidget(self.web_view)

        self._bridge.edit_requested.connect(self._on_edit_requested)
        self._bridge.formula_submitted.connect(self.formula_submitted)
        self._bridge.edit_cancelled.connect(self._on_edit_cancelled)
        self._bridge.visibility_changed.connect(self.visibility_changed)
        self._bridge.settings_requested.connect(self._on_settings_requested)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._send_layers()

    def set_layers(self, layers: list[Layer]) -> None:
        self._layers = {layer.id: layer for layer in layers}
        self._active_layer_id = None
        self._send_layers()

    def sync_layer(self, layer_id: str, layer: Layer | None) -> None:
        if layer is None:
            return
        self._layers[layer_id] = layer
        if not self._page_ready:
            return
        # 图层单项更新直接发送增量数据，无需重新创建整张函数列表。
        self._run_javascript(
            f"window.formulaListReady && "
            f"window.formulaList.updateLayer({json.dumps(self._serialize_layer(layer))});"
        )

    def accept_edit(self) -> None:
        if self._active_layer_id is None:
            return
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.acceptEdit();"
        )
        self._active_layer_id = None

    def cancel_edit(self) -> None:
        if self._active_layer_id is None:
            return
        layer_id = self._active_layer_id
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.cancelEdit();"
        )
        self._active_layer_id = None
        self.edit_cancelled.emit(layer_id)

    def _send_layers(self) -> None:
        if not self._page_ready:
            return
        # 网页尚未完成加载时只保留 Python 端状态，待就绪后一次性发送完整快照。
        payload = [self._serialize_layer(layer) for layer in self._layers.values()]
        self._run_javascript(
            f"if (window.formulaListReady) "
            f"window.formulaList.setLayers({json.dumps(payload)});"
        )

    @staticmethod
    def _serialize_layer(layer: Layer) -> dict[str, Any]:
        return {
            "id": layer.id,
            "name": layer.name,
            "kind": layer.kind,
            "latex": layer.latex or layer.expression,
            "visible": layer.visible,
        }

    def _run_javascript(self, source: str) -> None:
        self.web_view.page().runJavaScript(source)

    def _on_load_finished(self, success: bool) -> None:
        self._page_ready = success
        if success:
            self._send_layers()

    def _on_edit_requested(self, layer_id: str) -> None:
        if layer_id not in self._layers:
            return
        self._active_layer_id = layer_id
        self.edit_requested.emit(layer_id)

    def _on_edit_cancelled(self, layer_id: str) -> None:
        if self._active_layer_id == layer_id:
            self._active_layer_id = None
        self.edit_cancelled.emit(layer_id)

    def _on_settings_requested(self, layer_id: str, top: int, height: int) -> None:
        if layer_id not in self._layers:
            return
        # HTML 提供的是网页内坐标，弹出设置菜单前需要转换为 Qt 全局坐标。
        anchor = self.web_view.mapToGlobal(
            QPoint(max(0, self.width() - 8), max(0, top + height + 4))
        )
        self.settings_requested.emit(layer_id, anchor)
