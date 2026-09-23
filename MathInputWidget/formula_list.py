"""使用单个 WebEngine 的函数列表与行内公式编辑器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from models.curve_layer import CurveLayer
from models.geometry_2d import Annotation2D, GeometryObject, Linear2D, Point2D, geometry_latex
from models.geometry_3d import AlgebraAnnotation3D, AlgebraPlane3D, AlgebraVector3D
from models.surface_layer import SurfaceLayer
from ui.tokens import TokenError, flatten_theme
from ui.web_surface import rebuild_web_surface

from .theme_bridge import ThemeBridge


Layer = SurfaceLayer | CurveLayer | GeometryObject | Annotation2D | AlgebraVector3D | AlgebraPlane3D | AlgebraAnnotation3D


def _panel_background(theme: str) -> QColor:
    """Return the opaque panel fill shared by the page and its host widget.

    Chromium clears its composited surface with the page background color before
    the HTML paints.  A fully transparent clear color exposes the platform
    backing store instead, which is black on Windows, so the algebra area showed
    a black rectangle from startup until the first paint.
    """
    if theme not in ("light", "dark"):
        raise TokenError(f"unknown theme: {theme}")
    return QColor(str(flatten_theme(theme)["bg_panel"]))


class _FormulaListBridge(QObject):
    """接收共享 HTML 页面发出的列表和编辑器操作。"""

    edit_requested = Signal(str)
    edit_state_changed = Signal(str, str, int)
    keyboard_requested = Signal(str, str, int)
    formula_submitted = Signal(str, str)
    edit_cancelled = Signal(str)
    visibility_changed = Signal(str, bool)
    settings_requested = Signal(str, int, int)
    matrix_submitted = Signal(str)
    matrix_settings_submitted = Signal(str, int)
    matrix_settings_requested = Signal(int, int)
    coordinate_system_visibility_changed = Signal(bool, bool)

    @Slot(str)
    def editRequested(self, layer_id: str) -> None:
        self.edit_requested.emit(layer_id)

    @Slot(str, str, int)
    def editStateChanged(self, layer_id: str, latex: str, position: int) -> None:
        self.edit_state_changed.emit(layer_id, latex, int(position))

    @Slot(str, str, int)
    def keyboardRequested(self, layer_id: str, latex: str, position: int) -> None:
        self.keyboard_requested.emit(layer_id, latex, int(position))

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

    @Slot(str)
    def matrixSubmitted(self, text: str) -> None:
        self.matrix_submitted.emit(text)

    @Slot(str, int)
    def matrixSettingsSubmitted(self, text: str, grid_range: int) -> None:
        self.matrix_settings_submitted.emit(text, int(grid_range))

    @Slot(int, int)
    def matrixSettingsRequested(self, top: int, height: int) -> None:
        self.matrix_settings_requested.emit(top, height)

    @Slot(bool, bool)
    def coordinateSystemVisibilityChanged(self, show_original: bool, show_transformed: bool) -> None:
        self.coordinate_system_visibility_changed.emit(bool(show_original), bool(show_transformed))


class FormulaListWidget(QWidget):
    """在同一个 WebEngine 页面中渲染全部函数行与活动编辑器。"""

    edit_requested = Signal(str)
    edit_state_changed = Signal(str, str, int)
    keyboard_requested = Signal(str, str, int)
    keyboard_dismissed = Signal()
    focus_lost = Signal()
    formula_submitted = Signal(str, str)
    edit_cancelled = Signal(str)
    visibility_changed = Signal(str, bool)
    settings_requested = Signal(str, object)
    matrix_submitted = Signal(str)
    matrix_settings_submitted = Signal(str, int)
    matrix_settings_requested = Signal(object)
    coordinate_system_visibility_changed = Signal(bool, bool)

    def __init__(self, parent: QWidget | None = None, initial_theme: str = "light") -> None:
        super().__init__(parent)
        self._layers: dict[str, Layer] = {}
        self._page_ready = False
        self._active_layer_id: str | None = None
        self._pending_edit_id: str | None = None
        self._matrix_transform_enabled = False
        self._matrix_transform_editable = True
        self._matrix_transform_text = r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}"
        self._matrix_transform_result = ""
        self._matrix_transform_grid_range = 5
        self._show_original_coordinate_system = True
        self._show_transformed_coordinate_system = True

        self.setObjectName("formulaListWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 将函数列表合并到一个网页，避免多个原生 QWebEngineView 相互遮挡或闪烁。
        self.web_view = QWebEngineView(self)
        self.web_view.installEventFilter(self)
        self._theme_bridge = ThemeBridge(self.web_view, initial_theme)
        self._theme_bridge.install(initial_theme)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # 页面清屏色必须不透明：透明色会在首帧绘制前透出平台 backing store（Windows 上为黑色）。
        self.web_view.page().setBackgroundColor(_panel_background(initial_theme))
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
        self._bridge.edit_state_changed.connect(self._on_edit_state_changed)
        self._bridge.keyboard_requested.connect(self._on_keyboard_requested)
        self._bridge.formula_submitted.connect(self.formula_submitted)
        self._bridge.edit_cancelled.connect(self._on_edit_cancelled)
        self._bridge.visibility_changed.connect(self.visibility_changed)
        self._bridge.settings_requested.connect(self._on_settings_requested)
        self._bridge.matrix_submitted.connect(self.matrix_submitted)
        self._bridge.matrix_settings_submitted.connect(self._on_matrix_settings_submitted)
        self._bridge.matrix_settings_requested.connect(self._on_matrix_settings_requested)
        self._bridge.coordinate_system_visibility_changed.connect(self._on_coordinate_system_visibility_changed)

    def showEvent(self, event: QShowEvent) -> None:
        """窗口显示时触发数据同步并强制 WebEngine 重绘，修复最小化后空白问题。"""
        super().showEvent(event)
        # 触发 WebEngine 重新渲染
        if hasattr(self, "web_view") and self.web_view is not None:
            self.web_view.update()
        self._send_layers()

    def restore_render_surface(self) -> None:
        """Recreate the HTML surface after the top-level window is restored.

        Qt does not guarantee a child ``showEvent`` when only the native
        window state changes.  Reloading is intentional here: all algebra
        state lives in ``_layers`` and ``loadFinished`` sends it back to the
        page, so a lost Chromium surface cannot leave the panel blank.
        """
        view = getattr(self, "web_view", None)
        if view is None:
            return
        if self._active_layer_id is not None:
            self._pending_edit_id = self._active_layer_id
            self._active_layer_id = None
        view.show()
        self.rebuild_render_surface()
        self._page_ready = False
        view.reload()

    def rebuild_render_surface(self) -> bool:
        """重新分配 WebEngine 的合成表面，不重载文档。

        最小化恢复后 Chromium 不会重建已释放的渲染表面，仅靠 ``reload()`` 无法
        让页面重新合成；这里让控件重新经历一次隐藏/显示来强制重建。
        """
        return rebuild_web_surface(getattr(self, "web_view", None))

    def set_layers(self, layers: list[Layer]) -> None:
        had_active_edit = self._active_layer_id is not None
        self._layers = {layer.id: layer for layer in layers}
        self._active_layer_id = None
        if had_active_edit:
            self.keyboard_dismissed.emit()
        if self._pending_edit_id not in self._layers:
            self._pending_edit_id = None
        self._send_layers()
        self._start_pending_edit()

    def set_matrix_transform_editor(self, enabled: bool = True, *, editable: bool = True) -> None:
        """Render the matrix editor inside the shared algebra WebEngine area."""
        self._matrix_transform_enabled = bool(enabled)
        self._matrix_transform_editable = bool(editable)
        if not self._page_ready:
            return
        payload = "true" if self._matrix_transform_enabled else "false"
        editable_payload = "true" if self._matrix_transform_editable else "false"
        self._run_javascript(
            f"if (window.formulaListReady) window.formulaList.setMatrixTransform({payload});"
        )
        self._run_javascript(
            "if (window.formulaListReady) "
            f"window.formulaList.setMatrixTransformEditable({editable_payload});"
        )
        self.set_matrix_transform_visibility(
            self._show_original_coordinate_system,
            self._show_transformed_coordinate_system,
        )

    def set_matrix_transform_visibility(self, show_original: bool, show_transformed: bool) -> None:
        """Set the two coordinate-system visibility switches in the editor."""
        self._show_original_coordinate_system = bool(show_original)
        self._show_transformed_coordinate_system = bool(show_transformed)
        if not self._page_ready:
            return
        self._run_javascript(
            "if (window.formulaListReady) "
            f"window.formulaList.setMatrixTransformVisibility({str(self._show_original_coordinate_system).lower()}, "
            f"{str(self._show_transformed_coordinate_system).lower()});"
        )

    def set_matrix_transform_grid_range(self, grid_range: float) -> None:
        """Set the matrix-grid size shown in the row settings."""
        value = max(1, min(100, int(round(float(grid_range)))))
        self._matrix_transform_grid_range = value
        if not self._page_ready:
            return
        self._run_javascript(
            f"if (window.formulaListReady) window.formulaList.setMatrixTransformGridRange({value});"
        )

    def set_matrix_transform_value(self, text: str, result: str = "") -> None:
        """Sync the editable factors and the independently read-only result."""
        value = str(text).strip()
        if not value:
            return
        self._matrix_transform_text = value
        self._matrix_transform_result = str(result).strip()
        if not self._page_ready:
            return
        payload = json.dumps(value)
        result_payload = json.dumps(self._matrix_transform_result)
        self._run_javascript(
            "if (window.formulaListReady) "
            f"window.formulaList.setMatrixTransformValue({payload}, {result_payload});"
        )

    def submit_matrix_transform(self) -> None:
        """Reapply the current matrix after a settings-only change."""
        self.matrix_settings_submitted.emit(
            self._matrix_transform_text,
            self._matrix_transform_grid_range,
        )

    def matrix_transform_grid_range(self) -> int:
        return self._matrix_transform_grid_range

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

    def set_selected(self, layer_id: str | None) -> None:
        """在网页列表中高亮当前选中的行。"""
        if not self._page_ready:
            return
        payload = json.dumps(layer_id) if layer_id is not None else "null"
        self._run_javascript(
            f"if (window.formulaListReady) window.formulaList.setSelected({payload});"
        )

    def begin_edit(self, layer_id: str) -> None:
        """请求网页对指定行进入编辑状态（用于画布双击点后编辑坐标）。"""
        if layer_id not in self._layers:
            return
        if not self._page_ready:
            self._pending_edit_id = layer_id
            return
        self._pending_edit_id = None
        self._run_javascript(
            f"if (window.formulaListReady) "
            f"window.formulaList.beginEdit({json.dumps(layer_id)});"
        )

    def accept_edit(self) -> None:
        # 标记行可能先于异步编辑回调提交，关闭请求仍需转发到页面。
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.acceptEdit();"
        )
        self._active_layer_id = None
        self.keyboard_dismissed.emit()

    def commit_active_mark(self) -> None:
        """Submit a mark row when focus moves from WebEngine into a viewport."""
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.commitActiveMark();"
        )
        self._active_layer_id = None
        self.keyboard_dismissed.emit()

    def finish_edit_on_focus_out(self) -> None:
        """Commit the active row and return it to read-only mode."""
        if self._active_layer_id is None:
            return
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.finishEditOnFocusOut();"
        )
        self._active_layer_id = None
        self.keyboard_dismissed.emit()

    def has_focus_inside(self) -> bool:
        """Return whether Qt focus is still inside this list's WebView."""
        focused = QApplication.focusWidget()
        return bool(
            focused is self.web_view
            or (focused is not None and self.web_view.isAncestorOf(focused))
        )

    def cancel_edit(self) -> None:
        self._pending_edit_id = None
        if self._active_layer_id is None:
            return
        layer_id = self._active_layer_id
        self._run_javascript(
            "if (window.formulaListReady) window.formulaList.cancelEdit();"
        )
        self._active_layer_id = None
        self.keyboard_dismissed.emit()
        self.edit_cancelled.emit(layer_id)

    def apply_external_edit(self, latex: str, position: int) -> None:
        """Apply a key press from the wide keyboard to the visible inline field."""
        if self._active_layer_id is None or not self._page_ready:
            return
        self._run_javascript(
            "if (window.formulaListReady) "
            f"window.formulaList.applyExternalEdit({json.dumps(str(latex))}, "
            f"{max(0, int(position))});"
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.web_view and event.type() == QEvent.Type.FocusOut:
            self.focus_lost.emit()
        return super().eventFilter(watched, event)

    def _send_layers(self) -> None:
        if not self._page_ready:
            return
        # 网页尚未完成加载时只保留 Python 端状态，待就绪后一次性发送完整快照。
        payload = [self._serialize_layer(layer) for layer in self._layers.values()]
        self._run_javascript(
            f"if (window.formulaListReady) "
            f"window.formulaList.setLayers({json.dumps(payload)});"
        )
        if self._matrix_transform_enabled:
            self._run_javascript(
                "if (window.formulaListReady) window.formulaList.setMatrixTransform(true);"
            )
            editable_payload = "true" if self._matrix_transform_editable else "false"
            self._run_javascript(
                "if (window.formulaListReady) "
                f"window.formulaList.setMatrixTransformEditable({editable_payload});"
            )
            self.set_matrix_transform_value(
                self._matrix_transform_text,
                self._matrix_transform_result,
            )
            self.set_matrix_transform_grid_range(self._matrix_transform_grid_range)
            self.set_matrix_transform_visibility(
                self._show_original_coordinate_system,
                self._show_transformed_coordinate_system,
            )
    def _serialize_layer(self, layer: Layer) -> dict[str, Any]:
        if isinstance(layer, Annotation2D):
            return {
                "id": layer.id,
                "name": layer.name,
                "kind": "annotation",
                "latex": layer.latex or layer.text,
                "visible": layer.visible,
                "color": layer.color,
                "editable": layer.editable,
                "commitImmediately": layer.editable,
            }
        if isinstance(layer, AlgebraAnnotation3D):
            return {
                "id": layer.id,
                "name": layer.name,
                "kind": layer.kind,
                "latex": layer.latex,
                "visible": layer.visible,
                "color": layer.color,
                "editable": True,
                "commitImmediately": True,
            }
        if isinstance(layer, AlgebraPlane3D):
            return {
                "id": layer.id,
                "name": layer.name,
                "kind": layer.kind,
                "latex": layer.latex,
                "visible": layer.visible,
                "color": layer.color,
                "editable": False,
            }
        if isinstance(layer, (Point2D, Linear2D)):
            points = {
                candidate.id: candidate
                for candidate in self._layers.values()
                if isinstance(candidate, Point2D)
            }
            return {
                "id": layer.id,
                "name": layer.name,
                "kind": layer.kind,
                "latex": geometry_latex(layer, points),
                "visible": layer.visible,
                "color": getattr(layer, "color", "#8ab4f8"),
                # 点可通过编辑坐标修改；线类对象由端点决定，保持只读。
                "editable": isinstance(layer, Point2D),
            }
        return {
            "id": layer.id,
            "name": layer.name,
            "kind": layer.kind,
            "latex": layer.latex or layer.expression,
            "visible": layer.visible,
            "color": getattr(layer, "color", "#8ab4f8"),
            "editable": True,
            "placeholder": getattr(layer, "placeholder", ""),
            "draft": bool(getattr(layer, "is_draft", False)),
        }

    def _run_javascript(self, source: str) -> None:
        self.web_view.page().runJavaScript(source)

    def _on_load_finished(self, success: bool) -> None:
        self._theme_bridge.on_load_finished(success)
        self._page_ready = success
        if success:
            self._send_layers()
            self._start_pending_edit()

    def _start_pending_edit(self) -> None:
        layer_id = self._pending_edit_id
        if layer_id is None or not self._page_ready or layer_id not in self._layers:
            return
        self._pending_edit_id = None
        QTimer.singleShot(0, lambda: self.begin_edit(layer_id))

    def set_theme(self, theme: str) -> None:
        # 主题切换时同步清屏色，避免重绘瞬间再次露出黑色 backing store。
        self.web_view.page().setBackgroundColor(_panel_background(theme))
        self._theme_bridge.set_theme(theme)

    def _on_edit_requested(self, layer_id: str) -> None:
        if layer_id not in self._layers:
            return
        self._active_layer_id = layer_id
        self.edit_requested.emit(layer_id)

    def _on_edit_state_changed(self, layer_id: str, latex: str, position: int) -> None:
        if self._active_layer_id != layer_id:
            return
        self.edit_state_changed.emit(layer_id, latex, max(0, int(position)))

    def _on_keyboard_requested(self, layer_id: str, latex: str, position: int) -> None:
        if self._active_layer_id != layer_id:
            return
        self.keyboard_requested.emit(layer_id, latex, max(0, int(position)))

    def _on_edit_cancelled(self, layer_id: str) -> None:
        if self._active_layer_id == layer_id:
            self._active_layer_id = None
        self.keyboard_dismissed.emit()
        self.edit_cancelled.emit(layer_id)

    def _on_settings_requested(self, layer_id: str, top: int, height: int) -> None:
        if layer_id not in self._layers:
            return
        # HTML 提供的是网页内坐标，弹出设置菜单前需要转换为 Qt 全局坐标。
        anchor = self.web_view.mapToGlobal(
            QPoint(max(0, self.width() - 8), max(0, top + height + 4))
        )
        self.settings_requested.emit(layer_id, anchor)

    def _on_matrix_settings_submitted(self, text: str, grid_range: int) -> None:
        value = str(text).strip()
        if value:
            self._matrix_transform_text = value
        self._matrix_transform_grid_range = max(1, min(100, int(grid_range)))
        self.matrix_settings_submitted.emit(
            self._matrix_transform_text,
            self._matrix_transform_grid_range,
        )

    def _on_matrix_settings_requested(self, top: int, height: int) -> None:
        anchor = self.web_view.mapToGlobal(
            QPoint(max(0, self.width() - 8), max(0, top + height + 4))
        )
        self.matrix_settings_requested.emit(anchor)

    def _on_coordinate_system_visibility_changed(self, show_original: bool, show_transformed: bool) -> None:
        self._show_original_coordinate_system = bool(show_original)
        self._show_transformed_coordinate_system = bool(show_transformed)
        self.coordinate_system_visibility_changed.emit(
            self._show_original_coordinate_system,
            self._show_transformed_coordinate_system,
        )
