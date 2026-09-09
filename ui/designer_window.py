"""用于组合相互独立二维/三维公式场景的主窗口。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import time
from uuid import uuid4
from pathlib import Path

from collections import deque
from collections.abc import Callable
import inspect
from typing import Literal

from PySide6.QtCore import QEasingCurve, QEvent, QFile, QIODevice, QObject, QPoint, QPropertyAnimation, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent, QShortcut, QWheelEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QInputDialog, QLineEdit, QRubberBand, QToolButton, QVBoxLayout, QWidget
from shiboken6 import isValid
from pyvistaqt import QtInteractor

from MathInputWidget import LatexParseError, LatexParser
from geometry.cas_curve import CurveExpressionError, parse_curve_expression
from geometry.cas_surface import ExpressionError, parse_surface_expression
from geometry.standard_surfaces import BUILTIN_SURFACES, DEFAULT_BUILTIN_ID, create_builtin_layer
from models.curve_layer import CurveLayer, Plot2DDomain
from models.geometry_2d import (
    Annotation2D,
    GeometryObject,
    Linear2D,
    LinearKind,
    Point2D,
    parse_point_coordinates,
)
from models.function_catalog import catalog_entries, catalog_entry
from linear_algebra.registry import catalog_registry, runtime_teaching_store
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import CompiledVisualization, storyboard_visibility
from models.scene_mode import SceneAppearance, SceneMode
from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.axis import ThreeDAxes, add_cartesian_axes
from rendering.curve_scene import CurveRenderError, CurveSceneController
from rendering.geometry_scene import GeometrySceneController
from rendering.geometry_3d_scene import Geometry3DSceneController
from rendering.layer_scene import LayerRenderError, LayerSceneController
from rendering.lighting import LightSettings
from rendering.scene import build_scene, configure_3d_camera_interaction, update_lighting
from rendering.ticks import ViewportBounds, tick_spacing, visible_2d_bounds, visible_3d_axis_extent
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from ui.algebra_panel import AlgebraPanel
from ui.agent_sidebar import AgentSidebar
from ui.agent_settings import AgentSettingsDialog
from ui.lighting_dialog import LightingDialog
from ui.icons import apply_icon, icon_color, retint_icons
from ui.scene_settings import SceneSettingsPanel
from ui.scene_pane_manager import ScenePaneManager
from ui.scene_pane_state import ScenePaneState
from ui.scene_pane_widget import ScenePaneWidget
from ui.status_bar import AppStatusBar
from ui.panel_resize_handle import PanelResizeSpec, _PanelResizeHandle
from ui.tokens import apply_drop_shadow, apply_rounded_overlay
from ui.native_chrome import CustomTitleBar, apply_native_titlebar_theme
from ui.two_d_tools import ToolKind, TwoDGeometryToolbar
from ui.linear_algebra_tools import (
    build_polygon_tool_plan,
    build_transform_tool_plan,
    build_vector_tool_plan,
    parse_matrix,
)
from ui.teaching_case_panes import PANE_COUNTS, TeachingCasePaneGrid
from services.agent_worker import RuntimeTurnWorker
from services.agent_provider import (
    AgentSettings,
    AgentMessage,
    AgentResponse,
    OpenAICompatibleProvider,
    SceneContext,
)
from services.scene_commands import CommandError, CommandPlan, RuleBasedAgentProvider, SceneCommandService
from services.scene_clipboard import SceneClipboard
from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore
from agent.conversation import ConversationService
from agent.context_broker import AttachmentInput, ContextBroker
from agent.providers import ModelProvider


# 辅助线在视口四周额外绘制此比例；小幅平移和缩放仍落在既有区域内，
# 因而无需立刻重建辅助线和曲线采样。
_GUIDE_MARGIN = 2.5

ThemeMode = Literal["light", "dark", "system"]
EffectiveTheme = Literal["light", "dark"]


class _UnavailableAgentProvider:
    """Provider used when the user has not configured the selected remote model."""

    def __init__(self, reason: str = "provider_unconfigured") -> None:
        self.reason = reason

    def create_plan(self, messages: tuple[AgentMessage, ...], scene_context: SceneContext) -> AgentResponse:
        raise RuntimeError(self.reason)

    def stream(self, messages, *, tools=()):
        raise RuntimeError(self.reason)


@dataclass
class _SceneCommandRequest:
    """One validated scene-host call crossing the worker/GUI boundary."""

    method: str
    args: tuple[object, ...] = ()
    error: BaseException | None = None
    result: object | None = None


class _SceneCommandBridge(QObject):
    """Dispatch SceneCommandService host calls on the Qt GUI thread."""

    request = Signal(object)

    def __init__(self, host: object) -> None:
        super().__init__()
        self._host = host
        self.request.connect(self._dispatch, Qt.ConnectionType.BlockingQueuedConnection)

    @Slot(object)
    def _dispatch(self, request: _SceneCommandRequest) -> None:
        try:
            request.result = getattr(self._host, request.method)(*request.args)
        except Exception as error:
            # BlockingQueuedConnection does not propagate Python exceptions from
            # a slot, so carry it back explicitly for SceneCommandService.
            request.error = error


class _SceneCommandHostProxy:
    """Minimal SceneCommandHost adapter safe to call from any thread."""

    def __init__(self, bridge: _SceneCommandBridge, pane_id: str | None = None) -> None:
        self._bridge = bridge
        self._pane_id = pane_id

    def _invoke(self, method: str, *args: object) -> object:
        request = _SceneCommandRequest(method, tuple(args))
        if QThread.currentThread() == self._bridge.thread():
            self._bridge._dispatch(request)
        else:
            self._bridge.request.emit(request)
        if request.error is not None:
            raise request.error
        return request.result

    def for_pane(self, pane_id: str | None = None) -> "_SceneCommandHostProxy":
        target = self._invoke("resolve_scene_pane_id", pane_id if pane_id is not None else self._pane_id)
        return _SceneCommandHostProxy(self._bridge, str(target))

    def activate_for_tool(self) -> None:
        self._invoke("activate_scene_pane_for_tool", self._pane_id)

    @property
    def scene_mode(self):
        """Expose the pinned pane mode for command validation."""
        return self._invoke("_pane_scene_mode", self._pane_id)

    def _invoke_scene(self, method: str, *args: object) -> object:
        if self._pane_id is not None:
            return self._invoke(method, *args, self._pane_id)
        return self._invoke(method, *args)

    def begin_scene_command_transaction(self) -> None:
        self._invoke_scene("begin_scene_command_transaction")

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self._invoke_scene("apply_scene_command", operation)

    def commit_scene_command_transaction(self) -> None:
        self._invoke_scene("commit_scene_command_transaction")

    def rollback_scene_command_transaction(self) -> None:
        self._invoke_scene("rollback_scene_command_transaction")

    def check_scene_fingerprint(self, expected: str) -> bool:
        return bool(self._invoke_scene("check_scene_fingerprint", expected))

    def _undo_scene_command(self) -> None:
        self._invoke("_undo_scene_command")

    def _undo_2d_geometry(self) -> None:
        self._invoke("_undo_2d_geometry")


class _AgentEventRelay(QObject):
    """GUI-thread receiver for streaming events produced by a worker thread."""

    def __init__(self, callback: Callable[[object], None], parent: QObject) -> None:
        super().__init__(parent)
        self._callback = callback

    @Slot(object)
    def deliver(self, event: object) -> None:
        self._callback(event)


def _provider_configuration_error(provider: str) -> str:
    """Return a user-facing configuration error without exposing secrets."""
    labels = {
        "deepseek": "DeepSeek",
        "openai": "OpenAI",
        "local": "本地模型",
    }
    label = labels.get(str(provider).strip().lower(), "当前模型")
    return f"provider_unconfigured: {label} API Key 或模型信息未配置，请打开设置完成配置后重试。"


class _ViewportResizeFilter(QObject):
    """在原生 VTK 视口调整尺寸时，让 Qt 覆盖控件保持位于上层。"""

    def __init__(self, callback: Callable[[], None], parent: QObject) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._callback()
        return False


class _WindowRestoreFilter(QObject):
    """在主窗口从最小化恢复后重新激活原生/网页渲染表面。"""

    def __init__(self, callback: Callable[[], None], parent: QObject) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowStateChange and isinstance(watched, QWidget):
            if not watched.isMinimized():
                QTimer.singleShot(0, self._callback)
        return False


class _GeometryInputFilter(QObject):
    """拦截二维定点缩放和激活工具的视口鼠标、键盘事件。"""

    def __init__(self, owner: "MainWindow", parent: QObject) -> None:
        super().__init__(parent)
        self.owner = owner

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Route every viewport interaction to the pane that received it first.
        container = getattr(self.owner, "scene_pane_widget", None)
        if container is not None and event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn):
            for pane_id, widget in container.interactors.items():
                if watched is widget or watched is getattr(widget, "interactor", None):
                    self.owner.pane_manager.activate_for_tool(pane_id)
                    break
        if event.type() == QEvent.Type.Wheel and isinstance(event, QWheelEvent):
            return self.owner._handle_viewport_wheel(event)
        if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
            return self.owner._handle_geometry_mouse_press(event)
        if event.type() == QEvent.Type.MouseButtonDblClick and isinstance(event, QMouseEvent):
            return self.owner._handle_geometry_double_click(event)
        if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            return self.owner._handle_geometry_mouse_move(event)
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            return self.owner._handle_geometry_mouse_release(event)
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            return self.owner._handle_geometry_key_press(event)
        return False


@dataclass(frozen=True)
class _GeometryHistoryState:
    """可恢复的二维几何状态，不包含函数曲线和相机状态。"""

    points: tuple[Point2D, ...]
    linears: tuple[Linear2D, ...]
    object_order: tuple[str, ...]
    annotations: tuple[Annotation2D, ...] = ()
    curves: tuple[CurveLayer, ...] = ()


@dataclass(frozen=True)
class _SceneCommandState:
    """Agent 事务快照，覆盖二维曲线、几何对象、标注和顺序。"""

    points: tuple[Point2D, ...]
    linears: tuple[Linear2D, ...]
    annotations: tuple[Annotation2D, ...]
    curves: tuple[CurveLayer, ...]
    object_order: tuple[str, ...]
    surfaces: tuple[SurfaceLayer, ...] = ()
    scene_mode: SceneMode = SceneMode.TWO_D
    points3d: tuple[tuple[str, tuple[float, float, float]], ...] = ()
    areas: tuple[tuple[str, dict[str, object]], ...] = ()
    teaching_2d: tuple[tuple[str, dict[str, object]], ...] = ()
    geometry_3d: tuple[tuple[str, dict[str, object]], ...] = ()


class _PaneSceneRuntime:
    """Models, controllers and interaction caches owned by one pane.

    Qt/PyVista references are runtime-only; pane snapshots remain JSON-safe.
    """

    def __init__(self, pane: ScenePaneState) -> None:
        self.pane = pane
        self.lighting = LightSettings()
        self.material_name = "光泽塑料"
        self.plot_domain = PlotDomain()
        self.curve_domain = Plot2DDomain()
        self.layers: list[SurfaceLayer] = []
        self.curve_layers: list[CurveLayer] = []
        self.geometry_points: list[Point2D] = []
        self.linear_objects: list[Linear2D] = []
        self.annotations: list[Annotation2D] = []
        self._agent_areas: dict[str, dict[str, object]] = {}
        self._agent_points3d: dict[str, tuple[float, float, float]] = {}
        self._agent_teaching_2d: dict[str, dict[str, object]] = {}
        self._agent_geometry3d: dict[str, dict[str, object]] = {}
        self._two_d_object_order: list[str] = []
        self.layer_controller: LayerSceneController | None = None
        self.curve_controller: CurveSceneController | None = None
        self.geometry_controller: GeometrySceneController | None = None
        self.geometry3d_controller: Geometry3DSceneController | None = None
        self.scene_appearances = {
            SceneMode.THREE_D: SceneAppearance(show_grid=False, show_intersections=False),
            SceneMode.TWO_D: SceneAppearance(show_grid=True, show_intersections=False),
        }
        self._three_d_camera_position: list | None = None
        self._two_d_parallel_scale: float | None = None
        self._two_d_camera_position: list | None = None
        self._two_d_guide_spacing: float | None = None
        self._two_d_guide_bounds: ViewportBounds | None = None
        self._two_d_sample_bounds: ViewportBounds | None = None
        self._two_d_guides: TwoDGuides | None = None
        self._three_d_axes: ThreeDAxes | None = None
        self._three_d_spacing: float | None = None
        self._three_d_extent: float | None = None
        self._last_domain_extent: float | None = None
        self._viewport_refreshing = False
        self._viewport_refresh_pending = False
        self._viewport_refresh_timer: QTimer | None = None
        self._viewport_interaction_observer: int | None = None
        self._viewport_motion_observer: int | None = None
        self._last_interaction_refresh_time = 0.0
        self._intersection_color_revision = 0
        self._active_2d_tool: ToolKind | None = None
        self._active_linear_algebra_tool: str | None = None
        self._linear_algebra_pending_vector_ids: list[str] = []
        self._linear_algebra_polygon_point_ids: list[str] = []
        self._linear_algebra_tool_sequence = 0
        self._linear_algebra_tool_preclear_state: _SceneCommandState | None = None
        self._pending_geometry_point_id: str | None = None
        self._snap_to_grid = False
        self._dragging_point_id: str | None = None
        self._drag_moved = False
        self._drag_start_geometry_state: _GeometryHistoryState | None = None
        self._geometry_undo_stack: list[_GeometryHistoryState] = []
        self._geometry_redo_stack: list[_GeometryHistoryState] = []
        self._scene_command_undo_stack: list[_SceneCommandState] = []
        self._scene_command_redo_stack: list[_SceneCommandState] = []
        self._scene_command_snapshot: _SceneCommandState | None = None
        self._scene_command_active = False

    @property
    def scene_mode(self) -> SceneMode:
        return SceneMode(self.pane.scene_mode)

    @scene_mode.setter
    def scene_mode(self, mode: SceneMode) -> None:
        self.pane.scene_mode = str(mode)


class MainWindow:
    def copy_selected_scene_objects(self, pane_id: str | None = None) -> str:
        """Serialize selected 2-D objects to the process clipboard."""
        pane = self._pane(pane_id)
        runtime = self._pane_scene(pane.pane_id)
        ids = set(getattr(pane, "selected_object_ids", []))
        all_objects = (*runtime.geometry_points, *runtime.linear_objects, *runtime.annotations, *runtime.curve_layers)
        objects = [o for o in all_objects if o.id in ids]
        selected_ids = {o.id for o in objects}
        point_by_id = {o.id: o for o in runtime.geometry_points}
        for linear in runtime.linear_objects:
            if linear.id in selected_ids:
                for point_id in (linear.start_point_id, linear.end_point_id):
                    point = point_by_id.get(point_id)
                    if point is not None and point.id not in selected_ids:
                        objects.append(point); selected_ids.add(point.id)
        if not hasattr(self, "scene_clipboard"): self.scene_clipboard = SceneClipboard()
        return self.scene_clipboard.copy(objects, pane_id=pane.pane_id)

    def paste_scene_objects(self, pane_id: str | None = None):
        if not getattr(self, "scene_clipboard", None) or not self.scene_clipboard.payload: return []
        pane = self._pane(pane_id)
        from services.scene_clipboard import paste_objects
        with self._using_pane(pane.pane_id):
            runtime = self._pane_scene(pane.pane_id)
            before = self._capture_geometry_state()
            previous_repeat = self.scene_clipboard._repeat
            same_pane = pane.pane_id == self.scene_clipboard.source_pane
            try:
                existing_ids = {
                    getattr(obj, "id", "")
                    for obj in (*runtime.geometry_points, *runtime.linear_objects,
                                *runtime.annotations, *runtime.curve_layers)
                    if getattr(obj, "id", "")
                }
                repeat = previous_repeat + 1 if same_pane else previous_repeat
                pasted = paste_objects(
                    self.scene_clipboard.payload,
                    point_cls=Point2D, linear_cls=Linear2D,
                    annotation_cls=Annotation2D, curve_cls=CurveLayer,
                    existing_ids=existing_ids,
                    offset=(repeat, repeat) if same_pane else (0, 0),
                    max_bytes=self.scene_clipboard.max_bytes,
                )
                runtime.geometry_points.extend(o for o in pasted if isinstance(o, Point2D))
                runtime.linear_objects.extend(o for o in pasted if isinstance(o, Linear2D))
                runtime.annotations.extend(o for o in pasted if isinstance(o, Annotation2D))
                runtime.curve_layers.extend(o for o in pasted if isinstance(o, CurveLayer))
                runtime._two_d_object_order.extend(getattr(o, "id", "") for o in pasted if getattr(o, "id", ""))
                controller = getattr(runtime, "geometry_controller", None)
                if controller is not None:
                    for obj in pasted:
                        if isinstance(obj, Point2D): controller.add_point(obj)
                        elif isinstance(obj, Linear2D): controller.add_linear(obj)
                        elif isinstance(obj, Annotation2D): controller.add_annotation(obj)
                curve_controller = getattr(runtime, "curve_controller", None)
                if curve_controller is not None:
                    for obj in pasted:
                        if isinstance(obj, CurveLayer): curve_controller.add_layer(obj)
                self._sync_pane_state()
                renderer = self._pane_renderer(required=False)
                if renderer is not None and callable(getattr(renderer, "render", None)):
                    renderer.render()
                self.scene_clipboard._repeat = repeat
                self._record_geometry_change(before)
                return pasted
            except Exception:
                self.scene_clipboard._repeat = previous_repeat
                self._restore_geometry_state(before)
                self._sync_pane_state()
                renderer = self._pane_renderer(required=False)
                if renderer is not None and callable(getattr(renderer, "render", None)):
                    renderer.render()
                raise
    """加载 Designer 窗口骨架，并协调两个相互独立的绘图工作区。"""

    def __init__(
        self,
        theme_mode: ThemeMode = "system",
        effective_theme: EffectiveTheme = "light",
    ) -> None:
        self.theme_mode = theme_mode
        self.effective_theme = effective_theme
        self.pane_manager = ScenePaneManager()
        self._scene_target_pane_id: str | None = None
        self._transaction_pane_id: str | None = None
        self._transaction_scene: _PaneSceneRuntime | None = None
        self._pane_scene().scene_mode = SceneMode.THREE_D
        self._pane_scene().layers = [create_builtin_layer(DEFAULT_BUILTIN_ID)]
        self._lighting_dialog: LightingDialog | None = None
        self.latex_parser = LatexParser()
        self._active_linear_algebra_topic_id: str | None = None
        self._active_linear_algebra_compiled: CompiledVisualization | None = None
        self._active_linear_algebra_stage_id: str | None = None
        self._hidden_linear_algebra_aliases: set[str] = set()
        self._teaching_case_pane_grid: TeachingCasePaneGrid | None = None
        self._scene_settings_closing = False
        self._agent_thread: QThread | None = None
        self._agent_worker: RuntimeTurnWorker | None = None
        self._agent_processed_requests: dict[str, deque[tuple[str, str]]] = {}
        self._agent_settings_dialog: AgentSettingsDialog | None = None
        self._last_agent_plan_summary = ""
        self._agent_settings = AgentSettingsDialog.load_settings()
        self._agent_provider = self._create_agent_provider()
        self._scene_command_bridge = _SceneCommandBridge(self)
        self._scene_command_host_proxy = _SceneCommandHostProxy(self._scene_command_bridge)
        self.scene_command_service = SceneCommandService(self._scene_command_host_proxy)
        self._agent_session_store = SessionStore()
        self._agent_context_broker = ContextBroker(attachments_root=self._agent_session_store.math_root)
        self._agent_conversations = ConversationService(self._agent_session_store)
        self._agent_runtime = AgentRuntime(
            provider=self._agent_provider,
            command_service=self.scene_command_service,
            session_store=self._agent_session_store,
        )
        self._math_teacher_agent = self._agent_runtime.agent

        self.window = self._load_designer_form()
        self._window_restore_filter = _WindowRestoreFilter(self._restore_render_surfaces, self.window)
        self.window.installEventFilter(self._window_restore_filter)
        self.window.effective_theme = self.effective_theme
        self._install_custom_titlebar()
        self._agent_event_relay = _AgentEventRelay(self._receive_runtime_event, self.window)
        self._install_algebra_panel()
        self._configure_viewport()
        self._install_agent_panel()
        self._bind_algebra_panel()
        self._apply_style()
        self._render_scene()
        self._pane_widgets_ready = True
        for pane_id in tuple(getattr(self, "_pending_pane_redraws", ())):
            with self._using_pane(pane_id):
                self._render_scene()
        self._pending_pane_redraws = set()

    def _pane(self, pane_id: str | None = None) -> ScenePaneState:
        manager = getattr(self, "pane_manager", None)
        if manager is None:
            raise CommandError("场景窗格管理器尚未初始化。")
        if pane_id is not None:
            target = pane_id
        else:
            pinned = getattr(self, "_scene_target_pane_id", None)
            target = pinned or getattr(manager.active_pane(), "pane_id", manager.active_pane_id)
        if not isinstance(target, str) or not target.strip():
            raise CommandError("缺少有效的场景 pane_id。")
        try:
            return manager.pane(target)
        except ValueError as error:
            raise CommandError(f"场景窗格不存在: {target}") from error

    def resolve_scene_pane_id(self, pane_id: str | None = None) -> str:
        return self._pane(pane_id).pane_id

    def activate_scene_pane_for_tool(self, pane_id: str | None = None) -> str:
        return self.pane_manager.activate_for_tool(self.resolve_scene_pane_id(pane_id))

    def _pane_scene_mode(self, pane_id: str | None = None) -> SceneMode:
        """Return a pane's mode without creating a renderer or mutating it."""
        return self._pane(pane_id).scene_mode

    def _command_pane_id(self, pane_id: str | None = None) -> str:
        transaction_pane = getattr(self, "_transaction_pane_id", None)
        target = self.resolve_scene_pane_id(pane_id if pane_id is not None else transaction_pane)
        if transaction_pane is not None and target != transaction_pane:
            raise CommandError("场景命令不能跨越当前事务的目标窗格。")
        return target

    def _pane_scene(self, pane_id: str | None = None) -> _PaneSceneRuntime:
        pane = self._pane(pane_id)
        if pane.runtime is None:
            pane.runtime = _PaneSceneRuntime(pane)
        return pane.runtime

    def _pane_renderer(self, pane_id: str | None = None, *, required: bool = True):
        pane = self._pane(pane_id)
        renderer = pane.renderer_2d if pane.scene_mode == "2d" else pane.renderer_3d
        if required and renderer is None:
            raise CommandError(f"场景窗格渲染器尚未初始化: {pane.pane_id}")
        return renderer

    @contextmanager
    def _using_pane(self, pane_id: str | None = None):
        pane = self._pane(pane_id)
        previous = getattr(self, "_scene_target_pane_id", None)
        self._scene_target_pane_id = pane.pane_id
        try:
            yield pane
        finally:
            self._scene_target_pane_id = previous

    def _sync_pane_state(self) -> None:
        """Keep the pane's serializable models current after scene commands."""
        pane = self._pane()
        scene = self._pane_scene()
        snapshot = self._scene_snapshot_from_current_state().to_dict()
        pane.scene_2d = {
            "geometry": snapshot["geometry"], "curves": snapshot["curves"],
            "object_order": list(scene._two_d_object_order),
            "areas": snapshot["metadata"].get("areas", []),
            "teaching_2d": snapshot["metadata"].get("teaching_2d", []),
        }
        pane.scene_3d = {
            "layers": snapshot["layers"],
            "points3d": snapshot["metadata"].get("points3d", []),
            "geometry_3d": snapshot["metadata"].get("geometry_3d", []),
        }
        renderer = self._pane_renderer(required=False)
        if renderer is not None:
            camera = {"position": self._current_camera_position()}
            if pane.scene_mode == "2d":
                camera["parallel_scale"] = float(renderer.camera.parallel_scale)
                pane.camera_2d = camera
            else:
                pane.camera_3d = camera

    def _restore_render_surfaces(self) -> None:
        """恢复最小化后的 Qt/VTK/WebEngine 合成表面。"""
        window = getattr(self, "window", None)
        if window is None or window.isMinimized():
            return
        root_layout = getattr(self, "_root_layout", None)
        if root_layout is not None:
            root_layout.activate()

        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            def redraw(pane_id: str) -> None:
                with self._using_pane(pane_id):
                    self._render_scene()
            container.refresh_visible_panes(on_refresh=redraw)

        plotter = self._pane_renderer(required=False)
        if plotter is not None:
            interactor = getattr(plotter, "interactor", None)
            if interactor is not None:
                interactor.show()
                interactor.update()
            if container is None:
                try:
                    self._render_scene()
                except Exception:
                    # Lightweight hosts without a container retain one pane.
                    pass
            try:
                self._apply_linear_algebra_storyboard_visibility()
            except Exception:
                pass

        case_host = getattr(self, "teaching_case_pane_host", None)
        case_grid = getattr(self, "_teaching_case_pane_grid", None)
        if case_host is not None and case_grid is not None:
            case_host.show()
            if plotter is not None and getattr(plotter, "interactor", None) is not None:
                plotter.interactor.hide()
            case_grid.updateGeometry()
            case_grid.update()

        panel = getattr(self, "agent_panel", None)
        view = getattr(panel, "view", None) if panel is not None else None
        if view is not None:
            view.show()
            view.update()
            view.repaint()
            page = getattr(panel, "page", None)
            if page is not None:
                try:
                    page.runJavaScript("window.dispatchEvent(new Event('resize')); void document.body.offsetHeight;")
                except Exception:
                    pass
        window.update()
        QTimer.singleShot(120, self._deferred_render_surfaces)

    def _deferred_render_surfaces(self) -> None:
        """在窗口合成器完成恢复后再补一次轻量刷新。"""
        window = getattr(self, "window", None)
        if window is None or window.isMinimized():
            return
        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            container.refresh_visible_panes()
        plotter = self._pane_renderer(required=False) if container is None else None
        if plotter is not None:
            try:
                plotter.render()
            except Exception:
                pass
        panel = getattr(self, "agent_panel", None)
        view = getattr(panel, "view", None) if panel is not None else None
        if view is not None:
            view.update()

    def _load_designer_form(self) -> QWidget:
        form_path = Path(__file__).with_name("main_window.ui")
        form_file = QFile(str(form_path))
        if not form_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Unable to open Designer form: {form_path}")
        try:
            window = QUiLoader().load(form_file)
        finally:
            form_file.close()
        if window is None:
            raise RuntimeError(f"Unable to load Designer form: {form_path}")
        return window

    def _install_custom_titlebar(self) -> None:
        """Replace the delayed OS title bar with a theme-synchronous Qt chrome."""
        self.window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.window.setProperty("math3d_custom_titlebar", True)
        central = self.window.centralWidget()
        layout = central.layout() if central is not None else None
        if central is None or not isinstance(layout, QVBoxLayout):
            raise RuntimeError("Designer form must provide a vertical central layout")
        self.title_bar = CustomTitleBar(self.window)
        layout.insertWidget(0, self.title_bar)

    def _install_algebra_panel(self) -> None:
        root_layout = self.window.findChild(QHBoxLayout, "rootLayout")
        if root_layout is None:
            raise RuntimeError("Designer form must use a horizontal root layout")
        legacy_sidebar = self.window.findChild(QWidget, "sidebar")
        if legacy_sidebar is not None:
            root_layout.removeWidget(legacy_sidebar)
            legacy_sidebar.deleteLater()
        self.algebra_panel = AlgebraPanel(self.window)
        root_layout.insertWidget(0, self.algebra_panel)
        self.algebra_resize_handle = _PanelResizeHandle(
            PanelResizeSpec(
                self.algebra_panel.MIN_WIDTH,
                self.algebra_panel.MAX_WIDTH,
                self.algebra_panel.DEFAULT_WIDTH,
                "ui/algebra_panel_width",
                "right",
            ),
            parent=self.window,
        )
        self.algebra_panel.setFixedWidth(self.algebra_resize_handle.restore_width())
        self.algebra_resize_handle.width_changed.connect(self.algebra_panel.setFixedWidth)
        root_layout.insertWidget(1, self.algebra_resize_handle)

    def _install_agent_panel(self) -> None:
        """将 AI 助手作为主窗口最右侧的固定布局面板安装。"""
        root_layout = self.window.findChild(QHBoxLayout, "rootLayout")
        if root_layout is None:
            raise RuntimeError("Designer form must use a horizontal root layout")
        self._root_layout = root_layout
        self.agent_sidebar = AgentSidebar(self.window, dispatcher=self._dispatch_agent_web_intent)
        self.agent_sidebar.set_panel_width(self.agent_sidebar.DEFAULT_WIDTH)
        self.agent_resize_handle = _PanelResizeHandle(
            PanelResizeSpec(
                self.agent_sidebar.MIN_WIDTH,
                self.agent_sidebar.MAX_WIDTH,
                self.agent_sidebar.DEFAULT_WIDTH,
                "ui/agent_panel_width",
                "left",
            ),
            parent=self.window,
        )
        self.agent_sidebar.set_panel_width(self.agent_resize_handle.restore_width())
        self.agent_resize_handle.width_changed.connect(self.agent_sidebar.set_panel_width)
        self.agent_panel = self.agent_sidebar.expanded_panel
        root_layout.addWidget(self.agent_sidebar)
        root_layout.insertWidget(root_layout.indexOf(self.agent_sidebar), self.agent_resize_handle)
        self.agent_resize_handle.hide()
        # Sidebar 默认隐藏，关闭时不占用主视口布局空间。
        self.agent_sidebar.hide()
        self.agent_sidebar.set_model_status(
            self._agent_settings.model,
            enabled=self._using_remote_agent(),
        )
        self.agent_panel.set_scene_mode(self._pane_scene().scene_mode is SceneMode.TWO_D)
        self.status_bar = AppStatusBar(self.window)
        self.status_bar.agent_toggle_requested.connect(self._toggle_agent_panel)
        self.status_bar.theme_cycle_requested.connect(self.cycle_theme_mode)
        self.status_bar.set_scene_mode(self._pane_scene().scene_mode)
        self.status_bar.set_agent_status("就绪" if self._using_remote_agent() else "未配置")
        central = self.window.centralWidget()
        if central is not None:
            central_layout = central.layout()
            if isinstance(central_layout, QVBoxLayout):
                central_layout.addWidget(self.status_bar)

    def _dispatch_agent_web_intent(self, envelope) -> None:
        """Handle validated Web UI intents without exposing scene services."""
        message_type = getattr(envelope, "type", "")
        payload = getattr(envelope, "payload", {}) or {}
        session_id = str(getattr(envelope, "session_id", "") or "")
        request_id = str(getattr(envelope, "request_id", "") or "")
        previous_active_id = self.agent_panel.active_session_id
        if message_type not in {"request_snapshot", "open_history", "open_settings", "restore_session_view", "open_skills"} and request_id:
            ledger = self._agent_processed_requests.setdefault(session_id, deque(maxlen=128))
            signature = (request_id, message_type)
            if any(item[0] == request_id and item[1] != message_type for item in ledger):
                raise ValueError("request_reuse_conflict")
            if signature in ledger:
                return
            ledger.append(signature)
        if message_type == "create_session":
            try:
                self._agent_session_store.get_session(session_id)
            except KeyError:
                self._agent_session_store.create_session(
                    str(payload.get("title", "New Chat")),
                    session_id=session_id,
                    model=str(payload.get("model", self._agent_settings.model)),
                    active_mode=str(payload.get("mode", "Agent")),
                    execution_mode=str(payload.get("execution_mode", "continuous")),
                )
        elif session_id in {"boot", ""}:
            sessions = self._agent_session_store.list_sessions(include_closed=False)
            if sessions:
                session_id = sessions[0].id
            else:
                session_id = self._agent_session_store.create_session(model=self._agent_settings.model).id
        else:
            try:
                self._agent_session_store.get_session(session_id)
            except KeyError:
                self._agent_session_store.create_session(session_id=session_id, model=self._agent_settings.model)
        self.agent_panel.set_active_session(session_id)
        if message_type == "create_session":
            self._emit_agent_snapshot(session_id, request_id or "create-session")
            return
        if message_type in {"open_history", "open_settings"}:
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
            return
        if message_type == "open_skills":
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
            return
        if message_type == "select_math_stage":
            self._select_linear_algebra_stage(str(payload.get("case_id", "")), str(payload.get("stage_id", "")))
            return
        if message_type == "select_math_case_pane":
            topic_id = str(payload.get("case_id", ""))
            pane_id = str(payload.get("pane_id", ""))
            stage_id = str(payload.get("stage_id", "")) or None
            grid = getattr(self, "_teaching_case_pane_grid", None)
            if grid is not None and topic_id == getattr(self, "_active_linear_algebra_topic_id", None):
                self._set_teaching_case_pane_count(1)
                self._on_teaching_case_focus(pane_id, stage_id or "")
            return
        if message_type == "set_math_case_pane_count":
            topic_id = str(payload.get("case_id", ""))
            pane_count = payload.get("pane_count")
            grid = getattr(self, "_teaching_case_pane_grid", None)
            if grid is not None and topic_id == getattr(self, "_active_linear_algebra_topic_id", None) and isinstance(pane_count, int):
                self._set_teaching_case_pane_count(pane_count)
            return
        if message_type == "save_model_provider":
            from ui.agent_settings import AgentSettingsDialog
            draft = AgentSettings(
                base_url=str(payload.get("base_url", "")),
                api_key=str(payload.get("api_key", "")),
                model=str(payload.get("model", "")),
                timeout_seconds=float(payload.get("timeout_seconds", 60.0)),
                provider=str(payload.get("provider", "openai")),
                protocol=str(payload.get("protocol", "responses")),
            )
            AgentSettingsDialog.save_settings(draft, enabled=bool(payload.get("enabled", draft.is_complete)))
            self._agent_settings = draft
            self._agent_provider = self._create_agent_provider()
            self._agent_runtime = AgentRuntime(provider=self._agent_provider, command_service=self.scene_command_service, session_store=self._agent_session_store)
            self._math_teacher_agent = self._agent_runtime.agent
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "provider"))
            return
        if message_type == "test_model_provider":
            from agent.providers import ModelProvider
            draft = AgentSettings(
                base_url=str(payload.get("base_url", "")),
                api_key=str(payload.get("api_key", "")),
                model=str(payload.get("model", "")),
                timeout_seconds=min(10.0, max(1.0, float(payload.get("timeout_seconds", 10.0)))),
                provider=str(payload.get("provider", "openai")),
                protocol=str(payload.get("protocol", "responses")),
            )
            try:
                ModelProvider.create(draft.provider, draft).test_connection()
            except Exception as error:
                message = str(error).replace(draft.api_key, "***") if draft.api_key else str(error)
                result = {"ok": False, "message": message[:512]}
            else:
                result = {"ok": True, "message": "connection_ok"}
            self.agent_panel.bridge.emit_event({"protocol_version": 1, "type": "provider_test_result", "request_id": getattr(envelope, "request_id", "provider-test"), "session_id": session_id, "payload": result})
            return
        if message_type == "restore_session_view":
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
        elif message_type == "rename_session":
            title = str(payload.get("title", ""))
            self._agent_session_store.rename_session(session_id, title)
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
        elif message_type == "hide_session":
            self._agent_session_store.hide_session(session_id)
            fallback = self._agent_session_store.select_visible_fallback(excluding=session_id)
            self._emit_agent_snapshot(fallback.id, getattr(envelope, "request_id", message_type))
        elif message_type == "restore_hidden_session":
            self._agent_session_store.restore_hidden_session(session_id)
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
        elif message_type in {"save_custom_model", "update_custom_model"}:
            from agent.model_catalog import CustomModelStore
            model_id = str(payload.get("id", payload.get("model_id", "")))
            CustomModelStore.save(model_id, payload)
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
        elif message_type == "delete_custom_model":
            from agent.model_catalog import CustomModelStore
            CustomModelStore.delete(str(payload.get("id", payload.get("model_id", ""))))
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", message_type))
        elif message_type == "close_session":
            visible = self._agent_session_store.list_sessions(include_closed=False)
            if len(visible) > 1:
                self._agent_session_store.close_session(session_id)
                active_id = previous_active_id
                remaining = [item for item in visible if item.id != session_id]
                if active_id == session_id or not any(item.id == active_id for item in remaining):
                    active = self._agent_session_store.select_visible_fallback(excluding=session_id)
                else:
                    active = self._agent_session_store.get_session(active_id)
                self.agent_panel.set_active_session(active.id)
                self._emit_agent_snapshot(active.id, request_id or "close-session")
            else:
                self._emit_agent_snapshot(session_id, request_id or "close-session")
        elif message_type == "reopen_session":
            self._agent_session_store.reopen_session(session_id)
            self.agent_panel.set_active_session(session_id)
            self._emit_agent_snapshot(session_id, request_id or "reopen-session")
        elif message_type == "send_message":
            text = str(payload.get("text", "")).strip()
            if text:
                self._request_agent_plan(text, session_id=session_id)
        elif message_type in {"stop_turn", "stop_session"}:
            self._agent_runtime.stop(session_id)
            self.agent_sidebar.set_busy(False)
        elif message_type in {"set_mode", "change_mode"}:
            self._agent_session_store.set_session_preferences(session_id, active_mode=str(payload.get("mode", "Agent")))
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "mode"))
        elif message_type in {"set_execution_mode", "change_execution_mode"}:
            self._agent_session_store.set_session_preferences(session_id, execution_mode=str(payload.get("execution_mode", "confirm")))
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "execution-mode"))
        elif message_type in {"set_model", "change_model"}:
            self._agent_session_store.set_session_preferences(session_id, model=str(payload.get("model", "")))
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "model"))
        elif message_type == "set_selected_model":
            self._agent_session_store.set_session_preferences(session_id, model=str(payload.get("model", "")))
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "model"))
        elif message_type == "set_thinking_preferences":
            enabled = payload.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError("thinking_enabled must be boolean")
            self._agent_session_store.set_session_preferences(
                session_id,
                thinking_enabled=enabled,
                thinking_level=str(payload.get("level", "High")),
            )
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "thinking"))
        elif message_type == "attach_files":
            raw_paths = payload.get("paths", [])
            if not isinstance(raw_paths, list):
                raise ValueError("附件路径必须是数组")
            inputs = [
                AttachmentInput(Path(str(item.get("path", ""))), str(item.get("mime_type", "application/octet-stream")))
                for item in raw_paths
                if isinstance(item, dict)
            ]
            stored = self._agent_context_broker.store_attachments(inputs)
            for item in stored:
                self._agent_session_store.add_attachment(
                    session_id,
                    turn_id=None,
                    relative_path=item.relative_path,
                    mime_type=item.mime_type,
                    byte_size=item.byte_size,
                    sha256=item.sha256,
                )
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "attachments"))
        elif message_type == "approve_plan":
            turn_id = str(getattr(envelope, "turn_id", ""))
            turn = self._agent_session_store.get_turn(turn_id)
            if turn.session_id != session_id:
                raise ValueError("stale_approval")
            if turn.execution_status not in {"approval_required", "plan_pending", "undone"}:
                raise ValueError("stale_approval")
            if not self._agent_runtime.consume_approval(session_id, turn_id):
                # Approval tickets live in the runtime, while the turn state is
                # persisted. Rehydrate a one-shot ticket after a runtime restart.
                self._agent_runtime.register_approval(session_id, turn_id)
                if not self._agent_runtime.consume_approval(session_id, turn_id):
                    raise ValueError("stale_approval")
            if turn.command_plan is None:
                raise ValueError("该回合没有可执行的命令计划")
            self.agent_panel.bridge.emit_event({
                "protocol_version": 1,
                "type": "execution",
                "request_id": getattr(envelope, "request_id", "approve"),
                "session_id": session_id,
                "turn_id": turn.id,
                "payload": {"status": "started", "summary": turn.command_plan.get("summary", "")},
            })
            fingerprint = turn.validation.get("base_scene_fingerprint") if turn.validation else None
            try:
                self._agent_runtime.execute(CommandPlan.from_dict(turn.command_plan), expected_scene_fingerprint=fingerprint)
            except CommandError as error:
                if str(error) == "scene_changed_since_plan":
                    self._agent_session_store.update_turn_scene_snapshots(turn.id, status="scene_changed_since_plan")
                    self._agent_session_store.append_event(session_id, "scene_conflict", {"code": "scene_changed_since_plan", "message": "场景已在计划生成后发生变化"}, turn_id=turn.id)
                raise
            after = self._scene_snapshot_from_current_state()
            self._agent_session_store.update_turn_scene_snapshots(turn.id, scene_after=after, status="completed")
            self._agent_session_store.append_event(session_id, "execution_finished", {"status": "completed"}, turn_id=turn.id)
            self._agent_session_store.append_event(session_id, "turn_finished", {"status": "completed"}, turn_id=turn.id)
            self.agent_panel.bridge.emit_event({
                "protocol_version": 1,
                "type": "turn_finished",
                "request_id": getattr(envelope, "request_id", "approve"),
                "session_id": session_id,
                "turn_id": turn.id,
                "payload": {"status": "completed"},
            })
        elif message_type == "branch_turn":
            branch = self._agent_conversations.branch_from_turn(str(getattr(envelope, "turn_id", "")))
            self.agent_panel.set_active_session(branch.id)
        elif message_type in {"restore_turn", "undo_turn"}:
            turn = self._agent_session_store.get_turn(str(getattr(envelope, "turn_id", "")))
            if turn.session_id != session_id:
                raise ValueError("stale_turn")
            snapshot = turn.scene_after if message_type == "restore_turn" else turn.scene_before
            if snapshot is None:
                raise ValueError("该回合没有可恢复的场景快照")
            self._restore_agent_scene_snapshot(snapshot)
            self._agent_session_store.set_current_turn(turn.session_id, turn.id)
            if message_type == "undo_turn":
                self._agent_session_store.update_turn_scene_snapshots(turn.id, scene_after=None, status="undone")
                self._agent_runtime.register_approval(session_id, turn.id)
            self.agent_panel.bridge.emit_event({
                "protocol_version": 1,
                "type": "execution",
                "request_id": getattr(envelope, "request_id", message_type),
                "session_id": session_id,
                "turn_id": turn.id,
                "payload": {"status": "restored" if message_type == "restore_turn" else "undone"},
            })
        elif message_type == "request_snapshot":
            self._emit_agent_snapshot(session_id, getattr(envelope, "request_id", "snapshot"))

    def _emit_agent_snapshot(self, session_id: str, request_id: str) -> None:
        from agent.ui_projection import build_session_snapshot
        snapshot = build_session_snapshot(
            self._agent_session_store,
            active_session_id=session_id or None,
            model_status={"model": self._agent_settings.model, "connected": self._using_remote_agent()},
            settings_state={
                "provider": self._agent_settings.provider,
                "protocol": self._agent_settings.normalized_protocol,
                "base_url": self._agent_settings.base_url,
                "model": self._agent_settings.model,
                "key_configured": bool(self._agent_settings.api_key),
                "key_suffix": self._agent_settings.api_key[-4:] if self._agent_settings.api_key else "",
            },
        )
        self.agent_panel.bridge.emit_event({
            "protocol_version": 1,
            "type": "session_snapshot",
            "request_id": request_id,
            "session_id": session_id,
            "payload": snapshot,
        })

    def _create_agent_provider(self):
        if not AgentSettingsDialog.is_enabled():
            return RuleBasedAgentProvider()
        if self._agent_settings.provider == "local":
            return ModelProvider.create("local", self._agent_settings)
        if self._agent_settings.is_complete:
            try:
                return ModelProvider.create(self._agent_settings.provider, self._agent_settings)
            except ValueError:
                return _UnavailableAgentProvider(_provider_configuration_error(self._agent_settings.provider))
        return _UnavailableAgentProvider(_provider_configuration_error(self._agent_settings.provider))

    def _using_remote_agent(self) -> bool:
        return isinstance(self._agent_provider, OpenAICompatibleProvider)

    def _configure_viewport(self) -> None:
        self.viewport_host = self._widget("viewportHost", QWidget)
        layout = QVBoxLayout(self.viewport_host)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scene_pane_widget = ScenePaneWidget(
            self.pane_manager, self.viewport_host,
            on_interactor_created=self._on_pane_interactor_created,
        )
        layout.addWidget(self.scene_pane_widget, 1)
        self.scene_pane_widget.interactor().interactor.setMouseTracking(True)
        self.teaching_case_pane_host = QFrame(self.viewport_host)
        self.teaching_case_pane_host.setObjectName("teachingCasePaneHost")
        self.teaching_case_pane_layout = QVBoxLayout(self.teaching_case_pane_host)
        self.teaching_case_pane_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.teaching_case_pane_host)
        self.teaching_case_pane_host.hide()

        self.viewport_toolbar = QFrame(self.viewport_host)
        self.viewport_toolbar.setObjectName("viewportToolbar")
        apply_drop_shadow(self.viewport_toolbar, "overlay")
        apply_rounded_overlay(self.viewport_toolbar, "md")
        toolbar_layout = QVBoxLayout(self.viewport_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)
        self.scene_settings_button = QToolButton(self.viewport_toolbar)
        self.scene_settings_button.setToolTip("场景设置")
        self.scene_settings_button.setAccessibleName("场景设置")
        apply_icon(self.scene_settings_button, "settings-2", icon_color(getattr(self, "effective_theme", "light")), icon_size=16, hit_size=36)
        self.scene_mode_button = QToolButton(self.viewport_toolbar)
        self.scene_mode_button.setObjectName("sceneModeButton")
        self.scene_mode_button.setToolTip("切换二维和三维场景")
        self.scene_mode_button.setAccessibleName("切换二维和三维场景")
        self.scene_mode_button.setFixedSize(36, 36)
        self.agent_button = QToolButton(self.viewport_toolbar)
        self.agent_button.setObjectName("agentButton")
        self.agent_button.setToolTip("AI 教学助手")
        self.agent_button.setAccessibleName("AI 教学助手")
        self.agent_button.setCheckable(True)
        apply_icon(self.agent_button, "sparkles", icon_color(getattr(self, "effective_theme", "light")), icon_size=16, hit_size=36)
        self._install_layout_buttons(toolbar_layout)
        toolbar_layout.addWidget(self.scene_settings_button)
        toolbar_layout.addWidget(self.scene_mode_button)
        toolbar_layout.addWidget(self.agent_button)
        self.viewport_toolbar.adjustSize()

        # 线性代数工具直接扩展现有二维工具栏；不创建第二个可见工具栏。
        self.two_d_geometry_toolbar = TwoDGeometryToolbar(
            self.viewport_host,
            theme=getattr(self, "effective_theme", "light"),
        )
        self.scene_settings_panel = SceneSettingsPanel(self.viewport_host)
        self.scene_settings_panel.hide()
        self._scene_settings_animation = QPropertyAnimation(self.scene_settings_panel, b"geometry", self.window)
        self._scene_settings_animation.setDuration(200)
        self._scene_settings_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scene_settings_animation.finished.connect(self._finish_scene_settings_animation)
        self._viewport_resize_filter = _ViewportResizeFilter(self._on_viewport_host_changed, self.viewport_host)
        self.viewport_host.installEventFilter(self._viewport_resize_filter)
        self._position_viewport_overlays()
        self.scene_settings_button.clicked.connect(self._toggle_scene_settings)
        self.scene_mode_button.clicked.connect(self._toggle_scene_mode)
        self.agent_button.clicked.connect(self._toggle_agent_panel)
        self.two_d_geometry_toolbar.tool_selected.connect(self._on_unified_2d_tool_selected)
        self.two_d_geometry_toolbar.snap_toggled.connect(self._set_snap_to_grid)
        self.two_d_geometry_toolbar.undo_requested.connect(self._undo_2d_geometry)
        self.two_d_geometry_toolbar.redo_requested.connect(self._redo_2d_geometry)
        self._configure_2d_history_shortcuts()
        self._pane_scene()._viewport_refresh_timer = QTimer(self.window)
        self._pane_scene()._viewport_refresh_timer.setSingleShot(True)
        self._pane_scene()._viewport_refresh_timer.setInterval(130)
        self._pane_scene()._viewport_refresh_timer.timeout.connect(self._refresh_visible_viewport)
        interactor = getattr(self._pane_renderer(), "iren", None)
        if interactor is not None:
            try:
                self._pane_scene()._viewport_interaction_observer = interactor.add_observer("EndInteractionEvent", self._on_viewport_interaction_finished)
                self._pane_scene()._viewport_motion_observer = interactor.add_observer("InteractionEvent", self._on_viewport_interacting)
            except (AttributeError, RuntimeError, TypeError):
                self._pane_scene()._viewport_interaction_observer = None
                self._pane_scene()._viewport_motion_observer = None
        self._geometry_input_filter = _GeometryInputFilter(self, self._pane_renderer().interactor)
        self._pane_renderer().interactor.installEventFilter(self._geometry_input_filter)
        self._update_geometry_history_controls()
        self._sync_scene_controls()

        self.scene_settings_panel.background_changed.connect(self._set_scene_background)
        self.scene_settings_panel.axis_color_mode_changed.connect(self._set_axis_color_mode)
        self.scene_settings_panel.grid_changed.connect(self._set_grid_visible)
        self.scene_settings_panel.ticks_changed.connect(self._set_ticks_visible)
        self.scene_settings_panel.tick_spacing_mode_changed.connect(self._set_tick_spacing_mode)
        self.scene_settings_panel.tick_spacing_changed.connect(self._set_tick_spacing)
        self.scene_settings_panel.intersections_changed.connect(self._set_global_intersections_visible)
        self.scene_settings_panel.lighting_requested.connect(self._show_lighting_dialog)

    def _install_layout_buttons(self, toolbar_layout: QVBoxLayout) -> None:
        self.layout_buttons = {}
        labels = {1: "单窗格布局", 2: "双窗格布局", 3: "三窗格布局", 4: "四窗格布局"}
        for count, label in labels.items():
            button = QToolButton(self.viewport_toolbar)
            button.setObjectName(f"layout{count}Button")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolTip(label)
            button.setAccessibleName(label)
            apply_icon(button, f"layout-{count}", icon_color(getattr(self, "effective_theme", "light")), icon_size=16, hit_size=36)
            button.clicked.connect(lambda _checked=False, value=count: self._on_layout_button_clicked(value))
            self.layout_buttons[count] = button
            toolbar_layout.addWidget(button)
        self._sync_layout_buttons()

    def _configure_2d_history_shortcuts(self) -> None:
        """注册主窗口级二维几何撤回快捷键，避免依赖当前控件焦点。"""
        self._undo_2d_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self.window)
        self._redo_2d_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self.window)
        self._copy_2d_shortcut = QShortcut(QKeySequence("Ctrl+C"), self.window)
        self._paste_2d_shortcut = QShortcut(QKeySequence("Ctrl+V"), self.window)
        for shortcut in (self._undo_2d_shortcut, self._redo_2d_shortcut, self._copy_2d_shortcut, self._paste_2d_shortcut):
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._undo_2d_shortcut.activated.connect(self._undo_2d_geometry)
        self._redo_2d_shortcut.activated.connect(self._redo_2d_geometry)
        self._copy_2d_shortcut.activated.connect(self.copy_selected_scene_objects)
        self._paste_2d_shortcut.activated.connect(self.paste_scene_objects)

    def _on_viewport_host_changed(self) -> None:
        self._position_viewport_overlays()
        self._queue_viewport_refresh()

    def _handle_viewport_wheel(self, event: QWheelEvent) -> bool:
        """二维场景按鼠标位置缩放，保持光标下的世界坐标不变。"""
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            return False
        delta = event.angleDelta().y()
        if delta == 0:
            return False
        self._zoom_2d_at_viewport(
            event.position().x(),
            event.position().y(),
            0.9 ** (float(delta) / 120.0),
        )
        event.accept()
        return True

    def _zoom_2d_at_viewport(self, screen_x: float, screen_y: float, factor: float) -> bool:
        """缩放并移动相机，使缩放前光标下的世界点保持在原屏幕位置。"""
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or factor <= 0:
            return False
        interactor = getattr(self._pane_renderer(), "interactor", None)
        camera = getattr(self._pane_renderer(), "camera", None)
        if interactor is None or camera is None:
            return False
        width = max(1, int(interactor.width()))
        height = max(1, int(interactor.height()))
        if not 0 <= screen_x <= width or not 0 <= screen_y <= height:
            return False

        old_scale = max(1e-6, float(camera.parallel_scale))
        new_scale = max(1e-6, min(1e9, old_scale * factor))
        focal = tuple(float(value) for value in camera.focal_point)
        aspect = width / height
        normalized_x = 2.0 * float(screen_x) / width - 1.0
        normalized_y = 1.0 - 2.0 * float(screen_y) / height
        anchor_x = focal[0] + normalized_x * old_scale * aspect
        anchor_y = focal[1] + normalized_y * old_scale
        new_focal_x = anchor_x - normalized_x * new_scale * aspect
        new_focal_y = anchor_y - normalized_y * new_scale
        shift_x = new_focal_x - focal[0]
        shift_y = new_focal_y - focal[1]

        camera.parallel_scale = new_scale
        camera.focal_point = (new_focal_x, new_focal_y, focal[2])
        try:
            position = tuple(float(value) for value in camera.position)
        except (AttributeError, TypeError):
            position = None
        if position is not None:
            camera.position = (position[0] + shift_x, position[1] + shift_y, position[2])
        self._refresh_2d_viewport(resample=True, render=True)
        self._queue_viewport_refresh()
        return True

    def _on_viewport_interaction_finished(self, *_args: object) -> None:
        self._queue_viewport_refresh()

    @staticmethod
    def _needs_2d_prefetch(visible: ViewportBounds, cached: ViewportBounds) -> bool:
        """判断视口是否接近缓存边缘，提前在可视区域外补绘。"""
        if not cached.contains(visible):
            return True
        visible_center_x = (visible.x_range[0] + visible.x_range[1]) / 2
        visible_center_y = (visible.y_range[0] + visible.y_range[1]) / 2
        cached_center_x = (cached.x_range[0] + cached.x_range[1]) / 2
        cached_center_y = (cached.y_range[0] + cached.y_range[1]) / 2
        prefetch_distance = 0.35
        return (
            abs(visible_center_x - cached_center_x) >= visible.x_span * prefetch_distance
            or abs(visible_center_y - cached_center_y) >= visible.y_span * prefetch_distance
        )

    def _on_viewport_interacting(self, *_args: object) -> None:
        # 缩放立即响应（spacing 必变），平移采用节流策略（只补绘网格）。
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene()._viewport_refreshing:
            return
        try:
            visible = self._current_2d_bounds()
        except Exception:
            return
        # 允许只构造了视口字段的测试替身继续使用平移预取逻辑。
        if not hasattr(self._pane_scene(), "scene_appearances"):
            current = time.monotonic()
            if current - getattr(self._pane_scene(), "_last_interaction_refresh_time", 0.0) < 0.05:
                return
            cached_bounds = getattr(self._pane_scene(), "_two_d_sample_bounds", None)
            if cached_bounds is not None and self._needs_2d_prefetch(visible, cached_bounds):
                self._pane_scene()._last_interaction_refresh_time = current
                self._refresh_2d_viewport(resample=True, render=True)
            return
        appearance = self._pane_scene().scene_appearances[SceneMode.TWO_D]
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            previous_spacing=self._pane_scene()._two_d_guide_spacing,
        )
        spacing_changed = (
            self._pane_scene()._two_d_guide_spacing is None
            or abs(spacing - self._pane_scene()._two_d_guide_spacing) > self._pane_scene()._two_d_guide_spacing * 1e-9
        )
        # 缩放时 spacing 必定改变，立即重建网格和重采样曲线，无节流。
        if spacing_changed:
            self._pane_scene()._last_interaction_refresh_time = time.monotonic()
            self._refresh_2d_viewport(resample=True, render=True)
            return
        # 平移时 spacing 不变，采用节流策略，只在接近边缘时补绘网格。
        current = time.monotonic()
        if current - self._pane_scene()._last_interaction_refresh_time < 0.05:
            return
        cached_bounds = getattr(self._pane_scene(), "_two_d_sample_bounds", None)
        if cached_bounds is None:
            return
        if self._needs_2d_prefetch(visible, cached_bounds):
            self._pane_scene()._last_interaction_refresh_time = current
            self._refresh_2d_viewport(resample=True, render=True)

    def _queue_viewport_refresh(self) -> None:
        # 采用去抖（debounce）而非节流：每次交互事件都重启定时器，
        # 只有用户停止缩放/旋转后才触发一次重采样。这样缩放过程中曲面
        # 不会中途重建，避免卡顿与网格密度突变导致的视觉跳跃。
        if self._pane_scene()._viewport_refreshing or self._pane_scene()._viewport_refresh_timer is None:
            return
        self._pane_scene()._viewport_refresh_pending = True
        self._pane_scene()._viewport_refresh_timer.start()

    def _position_viewport_overlays(self) -> None:
        if not hasattr(self, "viewport_toolbar"):
            return
        host = self.viewport_host
        toolbar_width = self.viewport_toolbar.width()
        self.viewport_toolbar.move(max(8, host.width() - toolbar_width - 12), 12)
        self.viewport_toolbar.raise_()
        if hasattr(self, "two_d_geometry_toolbar"):
            self.two_d_geometry_toolbar.position_in_host()
            self.two_d_geometry_toolbar.raise_()
        if (
            self.scene_settings_panel.isVisible()
            and self._scene_settings_animation.state() != QPropertyAnimation.State.Running
        ):
            self.scene_settings_panel.setGeometry(self._scene_settings_target_geometry())
            self.scene_settings_panel.raise_()

    def _scene_settings_target_geometry(self) -> QRect:
        host = self.viewport_host
        width = self.scene_settings_panel.width()
        return QRect(
            max(8, host.width() - self.viewport_toolbar.width() - width - 20),
            12,
            width,
            max(240, host.height() - 24),
        )

    def _bind_algebra_panel(self) -> None:
        panel = self.algebra_panel
        # Keep the editable algebra tab synchronized with the scene pane focus.
        manager = getattr(self, "pane_manager", None)
        if manager is not None:
            panel.set_pane_manager(manager)
            panel.set_pane_id(manager.active_pane_id, getattr(manager.pane(manager.active_pane_id), "name", None))
            manager.active_pane_changed.connect(self._on_algebra_pane_focus_changed)
        mode = getattr(self._pane_scene(), "scene_mode", SceneMode.THREE_D)
        panel.set_scene_mode(mode)
        panel.set_catalog_entries(catalog_entries(mode))
        panel.set_builtin_surfaces((surface.id, surface.name) for surface in BUILTIN_SURFACES)
        panel.add_requested.connect(self._add_formula_for_scene)
        panel.catalog_requested.connect(self._add_catalog_entry)
        panel.linear_algebra_opened.connect(self._enter_linear_algebra_workspace)
        panel.linear_algebra_requested.connect(self._load_linear_algebra_topic)
        panel.builtin_requested.connect(self._add_builtin_surface)
        panel.lighting_requested.connect(self._show_lighting_dialog)
        panel.pane_update_requested.connect(self._update_formula_for_scene)
        panel.pane_visibility_requested.connect(self._reveal_algebra_pane)
        panel.delete_requested.connect(self._remove_layer_for_scene)
        panel.visibility_changed.connect(self._set_layer_visibility)
        panel.intersections_visibility_changed.connect(self._set_surface_intersections_visibility)
        panel.intersection_color_changed.connect(self._set_surface_intersection_color)
        panel.color_changed.connect(self._set_layer_color)
        panel.opacity_changed.connect(self._set_surface_opacity)
        panel.line_width_changed.connect(self._set_curve_line_width)
        panel.range_changed.connect(self._set_layer_range)
        # 扩展程序仍可能连接旧信号；界面中已不再提供对应的工具栏操作。
        panel.auto_intersections_changed.connect(self._set_auto_intersections)
        panel.manual_intersection_requested.connect(self._add_manual_intersection)

    def _on_algebra_pane_focus_changed(self, pane_id: str) -> None:
        panel = getattr(self, "algebra_panel", None)
        manager = getattr(self, "pane_manager", None)
        if panel is None:
            return
        title = None
        if manager is not None:
            try:
                title = manager.pane(pane_id).name
            except (KeyError, ValueError, AttributeError):
                pass
        panel.set_pane_id(pane_id, title)
        with self._using_pane(pane_id):
            mode = self._pane_scene().scene_mode
            panel.set_scene_mode(mode)
            panel.set_layers(self._two_d_panel_layers() if mode is SceneMode.TWO_D else self._pane_scene().layers)

    # ------------------------------------------------------------------
    # AI 场景命令适配层
    # ------------------------------------------------------------------

    def _request_agent_plan(self, prompt: str, *, session_id: str | None = None) -> None:
        if self._agent_thread is not None and self._agent_thread.isRunning():
            return
        active_session_id = session_id or self.agent_panel.active_session_id
        turn_id = uuid4().hex
        # Lock the target pane for the entire Agent turn; subsequent UI focus
        # changes must not redirect commands to another pane.
        locked_pane_id = self.pane_manager.active_pane_id
        self.agent_panel.set_active_session(active_session_id)
        self.agent_panel.bridge.emit_event({
            "protocol_version": 1,
            "type": "user_message",
            "request_id": "user-message",
            "session_id": active_session_id,
            "turn_id": turn_id,
            "payload": {"text": prompt},
        })
        self.agent_sidebar.set_busy(True)
        if hasattr(self, "status_bar"):
            self.status_bar.set_agent_status("生成中")
        thread = QThread(self.window)
        session = self._agent_session_store.get_session(active_session_id)
        worker = RuntimeTurnWorker(
            self._agent_runtime,
            active_session_id,
            prompt,
            mode=session.active_mode,
            execution_mode=session.execution_mode,
            scene_context=self._build_scene_context(),
            scene_before=self._scene_snapshot_from_current_state(),
            turn_id=turn_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.event_ready.connect(self._agent_event_relay.deliver, Qt.ConnectionType.QueuedConnection)
        worker.turn_finished.connect(self._receive_runtime_result, Qt.ConnectionType.QueuedConnection)
        worker.error.connect(self._receive_runtime_error, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._agent_finished)
        self._agent_thread = thread
        self._agent_worker = worker
        thread.start()

    def _receive_runtime_event(self, event) -> None:
        from agent.ui_projection import project_runtime_event
        key = str(event.session_id or "")
        sequence = getattr(self, "_agent_event_sequences", {}).get(key, 0) + 1
        if not hasattr(self, "_agent_event_sequences"):
            self._agent_event_sequences = {}
        self._agent_event_sequences[key] = sequence
        self.agent_panel.bridge.emit_event(project_runtime_event(event, sequence=sequence))

    def _receive_runtime_result(self, result) -> None:
        self.agent_sidebar.set_busy(False)
        if hasattr(self, "status_bar"):
            self.status_bar.set_agent_status("就绪")
        if result.turn_id and result.status == "completed":
            self._agent_session_store.update_turn_scene_snapshots(
                result.turn_id,
                scene_after=self._scene_snapshot_from_current_state(),
                status=result.status,
            )

    def _receive_runtime_error(self, message: str) -> None:
        self.agent_sidebar.set_busy(False)
        if hasattr(self, "status_bar"):
            self.status_bar.set_agent_status("就绪")
        self.agent_panel.show_error(message)

    def _agent_finished(self) -> None:
        self._agent_thread = None
        self._agent_worker = None

    def begin_scene_command_transaction(self, pane_id: str | None = None) -> None:
        if getattr(self, "_transaction_pane_id", None) is not None:
            raise CommandError("已有场景命令事务正在执行。")
        with self._using_pane(pane_id):
            self._pane_renderer()
            scene = self._pane_scene()
            scene._scene_command_snapshot = self._capture_scene_command_state()
            scene._scene_command_active = True
            # Keep bookkeeping reachable if the manager deletes this pane
            # before the transaction can finish or roll back.
            self._transaction_scene = scene
            self._transaction_pane_id = self._pane().pane_id

    def check_scene_fingerprint(self, expected: str, pane_id: str | None = None) -> bool:
        with self._using_pane(pane_id):
            return self._scene_snapshot_from_current_state().fingerprint() == expected

    def commit_scene_command_transaction(self, pane_id: str | None = None) -> None:
        with self._using_pane(self._command_pane_id(pane_id)):
            scene = self._pane_scene()
            if not scene._scene_command_active or scene._scene_command_snapshot is None:
                return
            after = self._capture_scene_command_state()
            self._sync_panel_layers(scene.layers if scene.scene_mode is SceneMode.THREE_D else self._two_d_panel_layers())
            self._pane_renderer().render()
            self._sync_pane_state()
            if after != scene._scene_command_snapshot:
                scene._scene_command_undo_stack.append(scene._scene_command_snapshot)
                scene._scene_command_redo_stack.clear()
            scene._scene_command_snapshot = None
            scene._scene_command_active = False
            self._transaction_pane_id = None
            self._transaction_scene = None
            self._update_geometry_history_controls()

    def rollback_scene_command_transaction(self, pane_id: str | None = None) -> None:
        transaction_pane = getattr(self, "_transaction_pane_id", None)
        if transaction_pane is not None and pane_id is not None and pane_id != transaction_pane:
            # A caller targeting another pane has not requested this
            # transaction's rollback. Preserve its snapshot and lock.
            raise CommandError("场景命令不能跨越当前事务的目标窗格。")
        scene = getattr(self, "_transaction_scene", None)
        try:
            with self._using_pane(self._command_pane_id(pane_id)):
                scene = self._pane_scene()
                snapshot = scene._scene_command_snapshot
                if snapshot is not None:
                    self._restore_scene_command_state(snapshot)
                self._sync_pane_state()
        finally:
            # Resolution itself can fail after pane deletion. Cleanup must
            # therefore surround resolution as well as scene restoration.
            if scene is not None:
                scene._scene_command_snapshot = None
                scene._scene_command_active = False
            self._transaction_pane_id = None
            self._transaction_scene = None
            self._update_geometry_history_controls()

    def _capture_scene_command_state(self) -> _SceneCommandState:
        return _SceneCommandState(
            points=tuple(replace(point) for point in self._pane_scene().geometry_points),
            linears=tuple(replace(linear) for linear in self._pane_scene().linear_objects),
            annotations=tuple(replace(annotation) for annotation in self._pane_scene().annotations),
            curves=tuple(replace(layer, parameters=dict(layer.parameters)) for layer in self._pane_scene().curve_layers),
            object_order=tuple(self._pane_scene()._two_d_object_order),
            surfaces=tuple(replace(layer, parameters=dict(layer.parameters)) for layer in self._pane_scene().layers),
            scene_mode=self._pane_scene().scene_mode,
            points3d=tuple((alias, tuple(coordinates)) for alias, coordinates in getattr(self._pane_scene(), "_agent_points3d", {}).items()),
            areas=tuple((alias, dict(operation)) for alias, operation in getattr(self._pane_scene(), "_agent_areas", {}).items()),
            teaching_2d=tuple((alias, dict(operation)) for alias, operation in getattr(self._pane_scene(), "_agent_teaching_2d", {}).items()),
            geometry_3d=tuple((alias, dict(operation)) for alias, operation in getattr(self._pane_scene(), "_agent_geometry3d", {}).items()),
        )

    @staticmethod
    def _snapshot_record(value: object, *, object_type: str | None = None) -> dict[str, object]:
        record = asdict(value)
        # Point2D exposes an init=False ``kind`` marker; constructors restore
        # that marker themselves, while Linear2D uses its kind as data.
        if isinstance(value, Point2D):
            record.pop("kind", None)
        if object_type:
            record["object_type"] = object_type
        return record

    def _scene_snapshot_from_current_state(self) -> SceneSnapshot:
        active = self._scene_snapshot_from_state(self._capture_scene_command_state())
        manager = getattr(self, "pane_manager", None)
        if manager is None:
            return active
        pane_records = []
        for pane_id, pane in manager.panes.items():
            if pane_id == manager.active_pane_id:
                pane_scene = active
            else:
                # Pane models are kept synchronized even while hidden.
                scene_2d = dict(getattr(pane, "scene_2d", {}) or {})
                scene_3d = dict(getattr(pane, "scene_3d", {}) or {})
                mode = str(getattr(pane, "scene_mode", "2d"))
                pane_scene = SceneSnapshot(
                    scene_mode=mode,
                    geometry=tuple(scene_2d.get("geometry", ())),
                    curves=tuple(scene_2d.get("curves", ())),
                    layers=tuple(scene_3d.get("layers", ())),
                    metadata={"object_order": scene_2d.get("object_order", []), "areas": scene_2d.get("areas", []), "teaching_2d": scene_2d.get("teaching_2d", []), "points3d": scene_3d.get("points3d", []), "geometry_3d": scene_3d.get("geometry_3d", [])},
                    camera=dict(getattr(pane, "camera_2d", {}) if mode == "2d" else getattr(pane, "camera_3d", {})),
                )
            pane_records.append({"pane_id": pane_id, "name": pane.name, "source": pane.source, "source_id": pane.source_id, "visible": pane_id in manager.visible_pane_ids(), "snapshot": pane_scene.to_dict()})
        return replace(active, panes=tuple(pane_records), active_pane_id=manager.active_pane_id)

    @classmethod
    def _scene_snapshot_from_state(cls, state: _SceneCommandState) -> SceneSnapshot:
        geometry: list[dict[str, object]] = []
        geometry.extend(cls._snapshot_record(point, object_type="point") for point in state.points)
        geometry.extend(cls._snapshot_record(linear, object_type="linear") for linear in state.linears)
        geometry.extend(cls._snapshot_record(annotation, object_type="annotation") for annotation in state.annotations)
        metadata = {
            "object_order": list(state.object_order),
            "points3d": [[alias, list(coordinates)] for alias, coordinates in state.points3d],
            "areas": [[alias, dict(operation)] for alias, operation in state.areas],
            "teaching_2d": [[alias, dict(operation)] for alias, operation in state.teaching_2d],
            "geometry_3d": [[alias, dict(operation)] for alias, operation in state.geometry_3d],
        }
        return SceneSnapshot(
            scene_mode=state.scene_mode.value,
            curves=tuple(cls._snapshot_record(layer) for layer in state.curves),
            geometry=tuple(geometry),
            layers=tuple(cls._snapshot_record(layer) for layer in state.surfaces),
            metadata=metadata,
        )

    @staticmethod
    def _without_snapshot_marker(record: dict[str, object]) -> dict[str, object]:
        value = dict(record)
        value.pop("object_type", None)
        return value

    @classmethod
    def _state_from_scene_snapshot(cls, snapshot: SceneSnapshot) -> _SceneCommandState:
        points: list[Point2D] = []
        linears: list[Linear2D] = []
        annotations: list[Annotation2D] = []
        for raw in snapshot.geometry:
            record = cls._without_snapshot_marker(raw)
            object_type = str(raw.get("object_type", ""))
            if object_type == "point":
                points.append(Point2D(**record))
            elif object_type == "linear":
                linears.append(Linear2D(**record))
            elif object_type == "annotation":
                annotations.append(Annotation2D(**record))
        metadata = dict(snapshot.metadata)
        points3d = tuple(
            (str(item[0]), tuple(float(value) for value in item[1]))
            for item in metadata.get("points3d", [])
            if isinstance(item, (list, tuple)) and len(item) == 2
        )
        areas = tuple(
            (str(item[0]), dict(item[1]))
            for item in metadata.get("areas", [])
            if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict)
        )
        teaching_2d = tuple(
            (str(item[0]), dict(item[1]))
            for item in metadata.get("teaching_2d", [])
            if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict)
        )
        geometry_3d = tuple(
            (str(item[0]), dict(item[1]))
            for item in metadata.get("geometry_3d", [])
            if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict)
        )
        return _SceneCommandState(
            points=tuple(points),
            linears=tuple(linears),
            annotations=tuple(annotations),
            curves=tuple(CurveLayer(**dict(item)) for item in snapshot.curves),
            object_order=tuple(str(value) for value in metadata.get("object_order", [])),
            surfaces=tuple(SurfaceLayer(**dict(item)) for item in snapshot.layers),
            scene_mode=SceneMode(snapshot.scene_mode),
            points3d=points3d,
            areas=areas,
            teaching_2d=teaching_2d,
            geometry_3d=geometry_3d,
        )

    def _restore_agent_scene_snapshot(self, snapshot: SceneSnapshot) -> None:
        manager = getattr(self, "pane_manager", None)
        records = snapshot.panes
        if manager is None or not records:
            self._restore_scene_command_state(self._state_from_scene_snapshot(snapshot))
            return
        for record in records:
            pane_id = str(record.get("pane_id", ""))
            if not pane_id or pane_id not in manager.panes:
                continue
            name = record.get("name")
            if isinstance(name, str) and name.strip():
                manager.panes[pane_id].name = name
            raw = record.get("snapshot")
            if not isinstance(raw, dict):
                continue
            with self._using_pane(pane_id):
                self._restore_scene_command_state(self._state_from_scene_snapshot(SceneSnapshot.from_dict(raw)))
        visible_ids = [
            str(record.get("pane_id"))
            for record in records
            if record.get("visible") is True and str(record.get("pane_id")) in manager.panes
        ][: manager.MAX_PANES]
        if visible_ids:
            manager.set_visible_panes(visible_ids)
        active = snapshot.active_pane_id
        if active in manager.panes and active in manager.visible_pane_ids():
            manager.focus_pane(active)

    def _restore_scene_command_state(self, state: _SceneCommandState) -> None:
        self._pane_scene().geometry_points = [replace(point) for point in state.points]
        self._pane_scene().linear_objects = [replace(linear) for linear in state.linears]
        self._pane_scene().annotations = [replace(annotation) for annotation in state.annotations]
        self._pane_scene().curve_layers = [replace(layer, parameters=dict(layer.parameters)) for layer in state.curves]
        self._pane_scene().layers = [replace(layer, parameters=dict(layer.parameters)) for layer in state.surfaces]
        self._pane_scene()._two_d_object_order = list(state.object_order)
        self._pane_scene()._agent_points3d = {alias: tuple(coordinates) for alias, coordinates in state.points3d}
        self._pane_scene()._agent_areas = {alias: dict(operation) for alias, operation in state.areas}
        self._pane_scene()._agent_teaching_2d = {alias: dict(operation) for alias, operation in state.teaching_2d}
        self._pane_scene()._agent_geometry3d = {alias: dict(operation) for alias, operation in state.geometry_3d}
        if self._pane_scene().scene_mode is not state.scene_mode:
            # Hidden panes do not own a renderer yet.  Restore their serializable
            # state directly and let pane creation render it later.
            pane = self._pane()
            renderer = pane.renderer_2d if state.scene_mode is SceneMode.TWO_D else pane.renderer_3d
            if renderer is None:
                self._pane_scene().scene_mode = state.scene_mode
                self._pane_scene().curve_controller = None
                self._pane_scene().geometry_controller = None
                self._pane_scene().geometry3d_controller = None
                return
            self._set_scene_mode(state.scene_mode)
            return
        else:
            renderer = self._pane_renderer(required=False)
        if renderer is not None:
            self._render_scene()
        elif self._pane_scene().scene_mode is SceneMode.TWO_D:
            # A lightweight/headless pane may retain controllers while its
            # renderer is temporarily unavailable.  Keep models authoritative;
            # controllers will be rebuilt when the pane becomes visible.
            return

    def _rebuild_2d_controllers(self) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            return
        old_curve_controller = getattr(self._pane_scene(), "curve_controller", None)
        if old_curve_controller is not None:
            for layer_id in list(old_curve_controller.layers):
                old_curve_controller.remove_layer(layer_id)
        old_geometry_controller = getattr(self._pane_scene(), "geometry_controller", None)
        if old_geometry_controller is not None:
            for object_id in [*old_geometry_controller.points, *old_geometry_controller.linears, *old_geometry_controller.annotations]:
                old_geometry_controller.remove_object(object_id)
        visible = self._current_2d_bounds()
        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        self._pane_scene().curve_domain = self._curve_sampling_domain(sampling_bounds)
        self._pane_scene().curve_controller = CurveSceneController(self._pane_renderer(), self._pane_scene().curve_domain)
        self._pane_scene().geometry_controller = GeometrySceneController(self._pane_renderer(), visible)
        for layer in self._pane_scene().curve_layers:
            self._pane_scene().curve_controller.add_layer(layer)
        for point in self._pane_scene().geometry_points:
            self._pane_scene().geometry_controller.add_point(point)
        for linear in self._pane_scene().linear_objects:
            self._pane_scene().geometry_controller.add_linear(linear)
        for annotation in getattr(self._pane_scene(), "annotations", []):
            self._pane_scene().geometry_controller.add_annotation(annotation)
        self.algebra_panel.set_layers(self._two_d_panel_layers())

    def apply_scene_command(self, operation: dict[str, object], pane_id: str | None = None) -> None:
        with self._using_pane(self._command_pane_id(pane_id)):
            self._pane_renderer()
            self._apply_scene_command(operation)
            self._sync_pane_state()

    def _apply_scene_command(self, operation: dict[str, object]) -> None:
        name = operation["op"]
        if name == "scene.set_mode":
            mode_value = str(operation.get("mode", "2d"))
            try:
                mode = SceneMode(mode_value)
            except ValueError as error:
                raise CommandError(f"未知场景模式: {mode_value}") from error
            self._set_scene_mode(mode)
            return
        if name == "scene.clear":
            self._command_clear_scope(str(operation.get("scope", "all")))
            return
        if name == "point3d.upsert":
            self._command_upsert_point3d(operation)
            return
        if name == "linear3d.upsert":
            self._command_upsert_linear3d(operation)
            return
        if name == "plane3d.upsert":
            self._command_upsert_plane3d(operation)
            return
        if name in {"geometry.parallelogram3d", "geometry.parallelepiped", "geometry.oriented_volume"}:
            self._command_upsert_solid3d(operation)
            return
        if name == "point.upsert":
            self._command_upsert_point(operation)
            return
        if name == "linear.upsert":
            self._command_upsert_linear(operation)
            return
        if name == "annotation.upsert":
            self._command_upsert_annotation(operation)
            return
        if name == "annotation.formula":
            self._command_formula_annotation(operation)
            return
        if name.startswith("geometry."):
            self._command_teaching_geometry(operation)
            return
        if name.endswith(".delete"):
            self._command_delete_alias(str(operation["alias"]))
            return
        if name == "curve.create":
            self._command_create_curve(operation)
            return
        if name == "curve.update":
            self._command_update_curve(operation)
            return
        if name == "surface.create":
            self._command_create_surface(operation)
            return
        if name == "surface.update":
            self._command_update_surface(operation)
            return
        if name == "area.fill":
            self._command_fill_area(operation)
            return
        if name == "view.fit":
            self._fit_2d_to_command_objects(float(operation.get("padding", 1.15)))
            return
        if name == "scene.export_png":
            filename = str(operation.get("filename", ""))
            self._pane_renderer().screenshot(str(self._managed_export_path(filename)))
            return
        if name == "geometry.intersection":
            self._command_intersection(operation)
            return
        if name.startswith("linear_algebra.") or name.startswith("calculus."):
            raise CommandError(f"宿主收到未展开的教学命令: {name}")
        raise CommandError(f"宿主不支持操作: {name}")

    def _command_upsert_linear3d(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().geometry3d_controller is None:
            raise CommandError("三维线性对象需要处于三维场景。")
        alias = str(operation["alias"])
        payload = dict(operation)
        self._pane_scene()._agent_geometry3d[alias] = payload
        self._pane_scene().geometry3d_controller.add_linear(
            alias,
            tuple(float(value) for value in operation["start"]),  # type: ignore[arg-type]
            tuple(float(value) for value in operation["end"]),  # type: ignore[arg-type]
            kind=str(operation.get("kind", "vector")),
            color=str(operation.get("color", "#2777b6")),
            role=str(operation.get("role", "primary")),
        )

    def _command_upsert_plane3d(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().geometry3d_controller is None:
            raise CommandError("三维平面需要处于三维场景。")
        alias = str(operation["alias"])
        self._pane_scene()._agent_geometry3d[alias] = dict(operation)
        self._pane_scene().geometry3d_controller.add_plane(
            alias,
            tuple(float(value) for value in operation["origin"]),  # type: ignore[arg-type]
            tuple(float(value) for value in operation["normal"]),  # type: ignore[arg-type]
            size=float(operation.get("size", 2.0)),
            opacity=float(operation.get("opacity", 0.24)),
            color=str(operation.get("color", "#5b8def")),
        )

    def _command_upsert_solid3d(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().geometry3d_controller is None:
            raise CommandError("三维体几何需要处于三维场景。")
        alias = str(operation["alias"])
        vectors = tuple(tuple(float(value) for value in vector) for vector in operation["vectors"])  # type: ignore[index]
        self._pane_scene()._agent_geometry3d[alias] = dict(operation)
        kwargs = {
            "opacity": float(operation.get("opacity", 0.24)),
            "color": str(operation.get("color", "#4c9f70")),
        }
        origin = tuple(float(value) for value in operation["origin"])  # type: ignore[arg-type]
        if operation["op"] == "geometry.parallelogram3d":
            self._pane_scene().geometry3d_controller.add_parallelogram(alias, origin, vectors, **kwargs)
        elif operation["op"] == "geometry.oriented_volume":
            self._pane_scene().geometry3d_controller.add_oriented_volume(alias, origin, vectors, **kwargs)
        else:
            self._pane_scene().geometry3d_controller.add_parallelepiped(alias, origin, vectors, **kwargs)

    def _command_formula_annotation(self, operation: dict[str, object]) -> None:
        position = tuple(float(value) for value in operation["position"])  # type: ignore[arg-type]
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._command_upsert_annotation({
                "op": "annotation.upsert",
                "alias": operation["alias"],
                "text": operation["text"],
                "position": position,
            })
            return
        if len(position) != 3:
            raise CommandError("三维公式标注需要三个坐标。")
        self._pane_scene()._agent_geometry3d[f"annotation:{operation['alias']}"] = dict(operation)
        add_labels = getattr(self._pane_renderer(), "add_point_labels", None)
        if callable(add_labels):
            name = f"geometry3d:annotation:{operation['alias']}"
            self._pane_renderer().remove_actor(name, render=False)
            add_labels(
                [position], [str(operation["text"])], name=name, shape=None, show_points=False,
                always_visible=True, render=False,
            )

    def _command_teaching_geometry(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
            raise CommandError("该教学几何操作需要处于二维场景。")
        name = str(operation["op"])
        alias = str(operation.get("alias", operation.get("result_alias", "teaching")))
        self._pane_scene()._agent_teaching_2d[alias] = dict(operation)
        if name == "geometry.polygon":
            self._pane_scene().geometry_controller.add_teaching_polygon(alias, tuple(tuple(float(v) for v in p) for p in operation["vertices"]), color=str(operation.get("color", "#5b8def")), opacity=float(operation.get("opacity", 0.24)), outline=bool(operation.get("outline", True)))  # type: ignore[index]
        elif name == "geometry.angle_arc":
            self._pane_scene().geometry_controller.add_teaching_angle_arc(alias, tuple(float(v) for v in operation["vertex"]), tuple(float(v) for v in operation["first"]), tuple(float(v) for v in operation["second"]), radius=float(operation["radius"]), color=str(operation.get("color", "#d97845")))  # type: ignore[arg-type]
        elif name == "geometry.right_angle_marker":
            self._pane_scene().geometry_controller.add_teaching_right_angle_marker(alias, tuple(float(v) for v in operation["vertex"]), tuple(float(v) for v in operation["first"]), tuple(float(v) for v in operation["second"]), size=float(operation["size"]), color=str(operation.get("color", "#d97845")))  # type: ignore[arg-type]
        elif name == "geometry.projection":
            self._pane_scene().geometry_controller.add_teaching_projection(tuple(float(v) for v in operation["vector"]), tuple(float(v) for v in operation["direction"]), result_alias=str(operation["result_alias"]), foot_alias=str(operation["foot_alias"]), residual_alias=str(operation["residual_alias"]), alias=str(operation["alias"]) if operation.get("alias") else None, origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#2777b6")))  # type: ignore[arg-type]
        elif name == "geometry.transformed_grid":
            matrix = tuple(tuple(float(v) for v in row) for row in operation["matrix"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_transformed_grid(matrix, tuple(float(v) for v in operation["bounds"]), step=float(operation.get("step", 1.0)), alias=str(operation["alias"]) if operation.get("alias") else None, color=str(operation.get("color", "#5b8def")))  # type: ignore[arg-type]
        elif name == "geometry.subspace_region":
            basis = tuple(tuple(float(v) for v in row) for row in operation["basis"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_subspace_region(basis, tuple(float(v) for v in operation["bounds"]), alias=str(operation["alias"]) if operation.get("alias") else None, origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#4c9f70")), opacity=float(operation.get("opacity", 0.2)))  # type: ignore[arg-type]
        elif name == "geometry.staged_transform":
            matrices = tuple(tuple(tuple(float(v) for v in row) for row in matrix) for matrix in operation["matrices"])  # type: ignore[index]
            points = tuple(tuple(float(v) for v in point) for point in operation["points"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_staged_transform(matrices, points, tuple(str(v) for v in operation["aliases"]), alias=str(operation["alias"]) if operation.get("alias") else None)  # type: ignore[arg-type]
        elif name == "geometry.oriented_area":
            vectors = tuple(tuple(float(v) for v in vector) for vector in operation["vectors"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_oriented_area(vectors, alias=str(operation.get("alias", "oriented-area")), origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#d97845")), opacity=float(operation.get("opacity", 0.28)))  # type: ignore[arg-type]
        else:
            raise CommandError(f"宿主不支持操作: {name}")

    def _command_clear_scope(self, scope: str) -> None:
        if scope not in {"all", "curves", "surfaces", "geometry", "annotations"}:
            raise CommandError("scene.clear.scope 不受支持。")
        if scope == "all":
            self._close_teaching_case_panes()
            self._active_linear_algebra_topic_id = None
            self._active_linear_algebra_compiled = None
            self._active_linear_algebra_stage_id = None
            self._hidden_linear_algebra_aliases = set()
            self._pane_scene()._active_linear_algebra_tool = None
            self._pane_scene()._linear_algebra_pending_vector_ids = []
            self._pane_scene()._linear_algebra_polygon_point_ids = []
            self._pane_scene()._linear_algebra_tool_preclear_state = None
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool(None, emit_signal=False)
            self._pane_scene().layers.clear()
            self._pane_scene()._agent_points3d = {}
            self._pane_scene()._agent_geometry3d = {}
            self._pane_scene()._agent_teaching_2d = {}
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            if scope in {"all", "surfaces"}:
                self._pane_scene().layers.clear()
            if scope in {"all", "geometry", "surfaces"}:
                self._pane_scene()._agent_points3d = {}
                self._pane_scene()._agent_geometry3d = {}
                if self._pane_scene().geometry3d_controller is not None:
                    self._pane_scene().geometry3d_controller.clear()
            self._render_scene()
            return
        if scope in {"all", "geometry"}:
            self._pane_scene().geometry_points.clear()
            self._pane_scene().linear_objects.clear()
            self._pane_scene()._agent_areas = {}
            self._pane_scene()._agent_teaching_2d = {}
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.clear_teaching()
        if scope in {"all", "annotations"}:
            self._pane_scene().annotations.clear()
        if scope in {"all", "curves"}:
            self._pane_scene().curve_layers.clear()
        remaining_ids = {
            *(point.id for point in self._pane_scene().geometry_points),
            *(linear.id for linear in self._pane_scene().linear_objects),
            *(annotation.id for annotation in self._pane_scene().annotations),
            *(layer.id for layer in self._pane_scene().curve_layers),
        }
        self._pane_scene()._two_d_object_order = [item_id for item_id in self._pane_scene()._two_d_object_order if item_id in remaining_ids]
        self._rebuild_2d_controllers()

    def _managed_export_path(self, filename: str) -> Path:
        name = Path(filename).name
        if name != filename or not name.lower().endswith(".png"):
            raise CommandError("scene.export_png 需要安全的 PNG 文件名。")
        exports_root = self._agent_session_store.exports_root.resolve()
        target = (exports_root / name).resolve()
        if target.parent != exports_root:
            raise CommandError("scene.export_png 不能写入导出目录之外。")
        return target

    def _command_upsert_point(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        coordinates = tuple(float(value) for value in operation["coordinates"])  # type: ignore[index]
        point = next((item for item in self._pane_scene().geometry_points if item.agent_alias == alias), None)
        if point is None:
            point = Point2D(str(operation.get("name", alias)), *coordinates, agent_alias=alias)
            self._pane_scene().geometry_points.append(point)
            self._pane_scene()._two_d_object_order.append(point.id)
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.add_point(point)
        else:
            point.x, point.y = coordinates
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.move_point(point.id, *coordinates)

    def _command_upsert_linear(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        start = self._command_point_alias(str(operation["start"]))
        end = self._command_point_alias(str(operation["end"]))
        linear = next((item for item in self._pane_scene().linear_objects if item.agent_alias == alias), None)
        kwargs = {
            "color": str(operation.get("color", "#2777b6")),
            "style": str(operation.get("style", "solid")),
            "role": str(operation.get("role", "primary")),
            "label": operation.get("label"),
        }
        if linear is None:
            linear = Linear2D(
                str(operation.get("name", alias)),
                str(operation["kind"]),
                start.id,
                end.id,
                agent_alias=alias,
                **kwargs,
            )
            self._pane_scene().linear_objects.append(linear)
            self._pane_scene()._two_d_object_order.append(linear.id)
        else:
            linear.start_point_id = start.id
            linear.end_point_id = end.id
            linear.kind = str(operation["kind"])  # type: ignore[assignment]
            linear.color = kwargs["color"]
            linear.style = kwargs["style"]  # type: ignore[assignment]
            linear.role = kwargs["role"]  # type: ignore[assignment]
            linear.label = kwargs["label"]
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.linears.pop(linear.id, None)
            self._pane_scene().geometry_controller.add_linear(linear)

    def _command_upsert_annotation(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        x, y = (float(value) for value in operation["position"])  # type: ignore[index]
        annotation = next((item for item in self._pane_scene().annotations if item.agent_alias == alias), None)
        if annotation is None:
            annotation = Annotation2D(
                str(operation.get("name", alias)), str(operation["text"]), x, y,
                latex=operation.get("latex"), color=str(operation.get("color", "#263241")), agent_alias=alias,
            )
            self._pane_scene().annotations.append(annotation)
            self._pane_scene()._two_d_object_order.append(annotation.id)
        else:
            annotation.text = str(operation["text"])
            annotation.x, annotation.y = x, y
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.annotations.pop(annotation.id, None)
            self._pane_scene().geometry_controller.add_annotation(annotation)

    def _command_create_curve(self, operation: dict[str, object]) -> None:
        if self._pane_scene().curve_controller is None:
            raise CommandError("二维曲线控制器尚未初始化。")
        kind = str(operation["kind"])
        expression = str(operation["expression"])
        formula, parsed = self._parse_mathlive_curve(expression, kind)
        layer = CurveLayer(
            str(operation.get("name", operation["alias"])), parsed.kind, parsed.source,
            latex=formula.latex, parameters={name: 1.0 for name in parsed.parameter_names},
            color=str(operation.get("color", "#2777b6")), agent_alias=str(operation["alias"]),
        )
        self._pane_scene().curve_controller.add_layer(layer)
        self._pane_scene().curve_layers.append(layer)
        self._pane_scene()._two_d_object_order.append(layer.id)

    def _command_create_surface(self, operation: dict[str, object]) -> None:
        """把 3D Skill 的曲面命令交给现有 CAS + LayerSceneController。"""
        if self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().layer_controller is None:
            raise CommandError("创建曲面需要处于三维场景。")
        kind = str(operation["kind"])
        expression = str(operation["expression"])
        try:
            formula, parsed = self._parse_mathlive_surface(expression, kind)
            layer = SurfaceLayer(
                str(operation.get("name", operation["alias"])),
                parsed.kind,
                parsed.source,
                latex=formula.latex,
                parameters={name: 1.0 for name in parsed.parameter_names},
                color=str(operation.get("color", "#4f7cac")),
                opacity=float(operation.get("opacity", 0.62)),
                agent_alias=str(operation["alias"]),
            )
            self._pane_scene().layer_controller.add_layer(layer)
        except (ExpressionError, LayerRenderError, LatexParseError, ValueError) as error:
            raise CommandError(f"无法创建曲面: {error}") from error
        self._pane_scene().layers.append(layer)
        self._sync_panel_layers(self._pane_scene().layers)
        self._pane_renderer().render()

    def _command_update_surface(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().layer_controller is None:
            raise CommandError("更新曲面需要处于三维场景。")
        alias = str(operation["alias"])
        current = next((item for item in self._pane_scene().layers if item.agent_alias == alias), None)
        if current is None:
            raise CommandError(f"未知曲面别名: {alias}")
        try:
            formula, parsed = self._parse_mathlive_surface(str(operation["expression"]), str(operation["kind"]))
            updated = replace(
                current,
                kind=parsed.kind,
                expression=parsed.source,
                latex=formula.latex,
                parameters={name: current.parameters.get(name, 1.0) for name in parsed.parameter_names},
            )
            self._pane_scene().layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError, LatexParseError, ValueError) as error:
            raise CommandError(f"无法更新曲面: {error}") from error
        self._pane_scene().layers = [updated if item.id == current.id else item for item in self._pane_scene().layers]
        self._sync_panel_layers(self._pane_scene().layers)
        self._pane_renderer().render()

    def _command_fill_area(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            raise CommandError("积分面积演示需要处于二维场景。")
        expression = dict(operation)
        alias = str(operation["alias"])
        areas = getattr(self._pane_scene(), "_agent_areas", {})
        areas[alias] = expression
        self._pane_scene()._agent_areas = areas
        self._render_agent_areas()

    def _render_agent_areas(self) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            return
        import numpy as np
        import pyvista as pv
        import sympy as sp
        from geometry.cas_curve import parse_curve_expression

        areas = getattr(self._pane_scene(), "_agent_areas", {})
        for alias in areas:
            self._pane_renderer().remove_actor(f"agent-area:{alias}", render=False)
        for alias, operation in areas.items():
            try:
                interval = operation.get("interval", (-1.0, 1.0))
                start, end = float(interval[0]), float(interval[1])  # type: ignore[index]
                parsed = parse_curve_expression(str(operation["expression"]), "explicit")
                if parsed.dependent_axis != "y":
                    continue
                x = sp.Symbol("x", real=True)
                function = sp.lambdify(x, parsed.simplified, modules="numpy")
                values = np.linspace(start, end, 220)
                y_values = np.asarray(function(values), dtype=float)
                if y_values.ndim == 0:
                    y_values = np.full(values.shape, float(y_values))
                if not np.all(np.isfinite(y_values)):
                    continue
                points = np.column_stack(
                    [
                        np.concatenate([values, values[::-1]]),
                        np.concatenate([y_values, np.zeros_like(y_values)[::-1]]),
                        np.zeros(values.size * 2),
                    ]
                )
                faces = np.concatenate([[len(points)], np.arange(len(points))])
                mesh = pv.PolyData(points, faces)
                self._pane_renderer().add_mesh(
                    mesh,
                    name=f"agent-area:{alias}",
                    color=str(operation.get("color", "#7c5ce3")),
                    opacity=float(operation.get("opacity", 0.24)),
                    show_edges=False,
                )
            except Exception:
                # 曲线本身仍由 CurveSceneController 渲染；面积失败不会破坏事务。
                continue
        self._pane_renderer().render()

    def _select_linear_algebra_stage(self, case_id: str, stage_id: str) -> None:
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if compiled is None or compiled.topic_id != case_id:
            return
        try:
            all_aliases, visible_aliases = storyboard_visibility(compiled, stage_id)
        except ValueError:
            return
        self._active_linear_algebra_stage_id = stage_id
        visible = set(visible_aliases)
        self._hidden_linear_algebra_aliases = {alias for alias in all_aliases if alias not in visible}
        self._apply_linear_algebra_storyboard_visibility()

    def _on_teaching_case_focus(self, pane_id: str, stage_id: str) -> None:
        """Focus one pane while retaining every other pane on screen."""
        grid = getattr(self, "_teaching_case_pane_grid", None)
        topic_id = getattr(self, "_active_linear_algebra_topic_id", None)
        if grid is None or not topic_id:
            return
        if not grid.select_case(pane_id, stage_id or None, emit=False):
            return
        try:
            manager_pane = next((pid for pid, state in self.pane_manager.panes.items()
                                 if state.source == "case" and state.source_id == pane_id), None)
            if manager_pane is not None and manager_pane in self.pane_manager.visible_pane_ids():
                self.pane_manager.focus_pane(manager_pane)
        except (AttributeError, ValueError):
            pass
        pane = next((item for item in grid.panes if getattr(item, "case", None) is not None and str(getattr(item.case, "id", "")) == pane_id), None)
        selected_stage = stage_id or (str(getattr(pane, "_stage_id", lambda: "")()) if pane is not None else "")
        if selected_stage:
            self._select_linear_algebra_stage(topic_id, selected_stage)
        if hasattr(self, "agent_panel"):
            self.agent_panel.show_math_case_focus(topic_id, pane_id)

    def _close_teaching_case_panes(self) -> None:
        grid = getattr(self, "_teaching_case_pane_grid", None)
        if grid is not None:
            self.teaching_case_pane_layout.removeWidget(grid)
            grid.close()
            grid.deleteLater()
        self._teaching_case_pane_grid = None
        try:
            self.pane_manager.leave_lecture()
        except (AttributeError, ValueError):
            pass
        if hasattr(self, "teaching_case_pane_host"):
            self.teaching_case_pane_host.hide()
        if (self._pane_renderer(required=False) is not None):
            self._pane_renderer().interactor.show()
        self._sync_layout_buttons()

    def _sync_layout_buttons(self) -> None:
        """Reflect the manager's visible pane count in the exclusive buttons."""
        buttons = getattr(self, "layout_buttons", {})
        count = len(self.pane_manager.visible_pane_ids()) if hasattr(self, "pane_manager") else 1
        for value, button in buttons.items():
            button.blockSignals(True)
            button.setChecked(value == count)
            button.blockSignals(False)

    def _on_layout_button_clicked(self, count: int) -> None:
        """Route layout selection through ScenePaneManager only."""
        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            container.set_layout(count)
        else:
            self.pane_manager.set_layout(count)
        self._sync_layout_buttons()

    def _on_pane_interactor_created(self, pane_id: str, renderer: object) -> None:
        """Rebind runtime controllers and redraw retained state after recreation."""
        interactor = getattr(renderer, "interactor", None)
        if interactor is not None:
            try:
                interactor.setMouseTracking(True)
                # Every recreated pane receives the same input routing filter.
                interactor.installEventFilter(_GeometryInputFilter(self, interactor))
            except (AttributeError, RuntimeError):
                pass
        if not getattr(self, "_pane_widgets_ready", False):
            self._pending_pane_redraws = set(getattr(self, "_pending_pane_redraws", ())) | {pane_id}
            return
        pane = self.pane_manager.pane(pane_id)
        if pane.runtime is not None:
            for name in ("curve_controller", "geometry_controller", "geometry3d_controller", "layer_controller"):
                setattr(pane.runtime, name, None)
        if getattr(self, "window", None) is not None and hasattr(self, "_render_scene"):
            with self._using_pane(pane_id):
                self._render_scene()

    def _set_teaching_case_pane_count(self, count: int) -> bool:
        grid = getattr(self, "_teaching_case_pane_grid", None)
        if grid is None:
            return False
        if not grid.set_pane_count(count):
            self.algebra_panel.set_status("案例窗格数量无效", is_error=True)
            return False
        self._sync_layout_buttons()
        self._on_teaching_case_focus(grid.selected_case_id, "")
        return True

    def _open_teaching_case_panes(self, explanation_case: object, compiled: object | None) -> None:
        self._close_teaching_case_panes()
        if not hasattr(self, "teaching_case_pane_host") or not hasattr(self, "teaching_case_pane_layout"):
            return
        if compiled is None or getattr(compiled, "plan", None) is None:
            return
        explanation = getattr(explanation_case, "explanation", explanation_case)
        layout = getattr(explanation, "case_layout", None)
        cases = tuple(getattr(layout, "cases", ()))[:4] if layout is not None else ()
        if not cases or getattr(compiled.plan, "scene", "") != "2d":
            return
        for case in cases:
            self.pane_manager.register_case(
                str(getattr(case, "id", "")),
                name=str(getattr(case, "purpose", "案例")),
            )
        self.pane_manager.enter_lecture(
            str(getattr(cases[0], "id", "")),
            [str(getattr(case, "id", "")) for case in cases],
        )
        grid = TeachingCasePaneGrid(compiled, cases, self.teaching_case_pane_host, pane_manager=self.pane_manager)
        grid.case_focused.connect(self._on_teaching_case_focus)
        grid.case_closed.connect(self._on_teaching_case_closed)
        self.teaching_case_pane_layout.addWidget(grid)
        self._teaching_case_pane_grid = grid
        self._pane_renderer().interactor.hide()
        self.teaching_case_pane_host.show()
        default_count = int(getattr(layout, "default_pane_count", len(cases)))
        self._set_teaching_case_pane_count(default_count)
        self._sync_layout_buttons()

    def _on_teaching_case_closed(self, case_id: str) -> None:
        """Remove a retained case pane and return to the lecture selection."""
        try:
            self.pane_manager.close_case(case_id)
        except (AttributeError, RuntimeError, ValueError):
            return
        grid = getattr(self, "_teaching_case_pane_grid", None)
        if grid is not None:
            remaining = tuple(case for case in grid.cases if str(getattr(case, "id", "")) != case_id)
            grid.cases = remaining
            if remaining:
                grid.selected_case_id = str(getattr(remaining[0], "id", ""))
                self._set_teaching_case_pane_count(min(grid.pane_count, len(remaining)))
            else:
                self._close_teaching_case_panes()

    def _apply_linear_algebra_storyboard_visibility(self) -> None:
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if compiled is None:
            return
        hidden = getattr(self, "_hidden_linear_algebra_aliases", set())
        all_aliases = tuple(dict.fromkeys(alias for item in compiled.storyboard for alias in item.visible_aliases))
        geometry_controller = getattr(self._pane_scene(), "geometry_controller", None)
        if self._pane_scene().scene_mode is SceneMode.TWO_D and geometry_controller is not None:
            for alias in all_aliases:
                visible = alias not in hidden
                geometry_controller.set_agent_alias_visible(alias, visible)
                geometry_controller.set_teaching_visible(alias, visible)
            plotter = self._pane_renderer(required=False)
            if plotter is not None:
                plotter.render()
            return
        geometry3d_controller = getattr(self._pane_scene(), "geometry3d_controller", None)
        if self._pane_scene().scene_mode is SceneMode.THREE_D and geometry3d_controller is not None:
            for alias in all_aliases:
                geometry3d_controller.set_visible(alias, alias not in hidden)
            self._render_agent_points3d()

    def _command_upsert_point3d(self, operation: dict[str, object]) -> None:
        """在 3D 视口中用一个受控球体表示点。

        点的坐标数据放在宿主的 ``_agent_points3d`` 中，渲染仍由宿主统一
        通过 PyVista 执行，Agent/Skill 本身不会接触绘图器。
        """
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            raise CommandError("三维点需要处于三维场景。")
        try:
            coordinates = tuple(float(value) for value in operation["coordinates"])  # type: ignore[index]
            if len(coordinates) != 3:
                raise ValueError("三维点需要三个坐标")
        except (TypeError, ValueError) as error:
            raise CommandError("三维点坐标无效。") from error
        points = getattr(self._pane_scene(), "_agent_points3d", {})
        alias = str(operation["alias"])
        points[alias] = coordinates
        self._pane_scene()._agent_points3d = points
        self._render_agent_points3d()

    def _render_agent_points3d(self) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            return
        import pyvista as pv

        for alias in getattr(self._pane_scene(), "_agent_points3d", {}):
            self._pane_renderer().remove_actor(f"agent-point:{alias}", render=False)
        hidden = getattr(self, "_hidden_linear_algebra_aliases", set())
        for alias, coordinates in getattr(self._pane_scene(), "_agent_points3d", {}).items():
            if any(alias == hidden_alias or alias.startswith(f"{hidden_alias}__") for hidden_alias in hidden):
                continue
            mesh = pv.Sphere(radius=0.08, center=coordinates, theta_resolution=16, phi_resolution=8)
            self._pane_renderer().add_mesh(mesh, name=f"agent-point:{alias}", color="#d64545")
        self._pane_renderer().render()

    def _command_intersection(self, operation: dict[str, object]) -> None:
        first = str(operation["first"])
        second = str(operation["second"])
        if self._pane_scene().scene_mode is SceneMode.THREE_D and self._pane_scene().layer_controller is not None:
            first_layer = next((item for item in self._pane_scene().layers if item.agent_alias == first or item.id == first), None)
            second_layer = next((item for item in self._pane_scene().layers if item.agent_alias == second or item.id == second), None)
            if first_layer is None or second_layer is None:
                raise CommandError("交集计算需要两个已存在的曲面别名。")
            self._pane_scene().layer_controller.set_manual_intersection_pair(first_layer.id, second_layer.id, True)
            self._pane_renderer().render()
            return
        raise CommandError("当前交集工具只支持三维曲面。")

    def _command_update_curve(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        layer = next((item for item in self._pane_scene().curve_layers if item.agent_alias == alias), None)
        if layer is None:
            raise CommandError(f"未知曲线别名: {alias}")
        updated = replace(layer, kind=str(operation["kind"]), expression=str(operation["expression"]))
        if self._pane_scene().curve_controller is not None:
            self._pane_scene().curve_controller.update_layer(updated)
        self._pane_scene().curve_layers = [updated if item.id == layer.id else item for item in self._pane_scene().curve_layers]
        self.algebra_panel.sync_layer(layer.id, updated)

    def _command_point_alias(self, alias: str) -> Point2D:
        point = next((item for item in self._pane_scene().geometry_points if item.agent_alias == alias or item.name == alias), None)
        if point is None:
            raise CommandError(f"未知点别名: {alias}")
        return point

    def _command_delete_alias(self, alias: str) -> None:
        areas = getattr(self._pane_scene(), "_agent_areas", {})
        if alias in areas or f"{alias}_fill" in areas:
            target = alias if alias in areas else f"{alias}_fill"
            areas.pop(target, None)
            self._pane_renderer().remove_actor(f"agent-area:{target}", render=False)
            self._pane_renderer().render()
            return
        points3d = getattr(self._pane_scene(), "_agent_points3d", {})
        if alias in points3d:
            points3d.pop(alias, None)
            self._render_agent_points3d()
            return
        geometry3d = getattr(self._pane_scene(), "_agent_geometry3d", {})
        if alias in geometry3d or f"annotation:{alias}" in geometry3d:
            geometry3d.pop(alias, None)
            geometry3d.pop(f"annotation:{alias}", None)
            if self._pane_scene().geometry3d_controller is not None:
                self._pane_scene().geometry3d_controller.remove_alias(alias)
            self._pane_renderer().remove_actor(f"geometry3d:annotation:{alias}", render=False)
            self._pane_renderer().render()
            return
        teaching = getattr(self._pane_scene(), "_agent_teaching_2d", {})
        if alias in teaching:
            teaching.pop(alias, None)
            if self._pane_scene().geometry_controller is not None:
                # The controller uses stable prefixes for every teaching actor.
                for prefix in ("polygon", "arc", "right-angle", "oriented-area", "projection"):
                    self._pane_renderer().remove_actor(f"geometry:teaching:{prefix}:{alias}", render=False)
            self._pane_renderer().render()
            return
        point = next((item for item in self._pane_scene().geometry_points if item.agent_alias == alias), None)
        if point is not None:
            self._remove_geometry_object(point.id)
            return
        linear = next((item for item in self._pane_scene().linear_objects if item.agent_alias == alias), None)
        if linear is not None:
            self._remove_geometry_object(linear.id)
            return
        annotation = next((item for item in self._pane_scene().annotations if item.agent_alias == alias), None)
        if annotation is not None:
            self._pane_scene().annotations = [item for item in self._pane_scene().annotations if item.id != annotation.id]
            self._pane_scene()._two_d_object_order = [item for item in self._pane_scene()._two_d_object_order if item != annotation.id]
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.remove_object(annotation.id)
            return
        layer = next((item for item in self._pane_scene().curve_layers if item.agent_alias == alias), None)
        if layer is not None:
            self._pane_scene().curve_controller.remove_layer(layer.id) if self._pane_scene().curve_controller else None
            self._pane_scene().curve_layers = [item for item in self._pane_scene().curve_layers if item.id != layer.id]
            self._pane_scene()._two_d_object_order = [item for item in self._pane_scene()._two_d_object_order if item != layer.id]
            return
        surface = next((item for item in self._pane_scene().layers if item.agent_alias == alias), None)
        if surface is not None:
            if self._pane_scene().layer_controller is not None:
                self._pane_scene().layer_controller.remove_layer(surface.id)
            self._pane_scene().layers = [item for item in self._pane_scene().layers if item.id != surface.id]
            self._sync_panel_layers(self._pane_scene().layers)
            self._pane_renderer().render()
            return
        raise CommandError(f"未知对象别名: {alias}")

    def _fit_2d_to_command_objects(self, padding: float) -> None:
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            self._pane_renderer().reset_camera()
            self._pane_renderer().render()
            return
        points = [(point.x, point.y) for point in self._pane_scene().geometry_points]
        if not points:
            return
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        span = max(max_x - min_x, max_y - min_y, 1.0) * max(1.0, padding)
        self._pane_renderer().camera.focal_point = ((min_x + max_x) / 2, (min_y + max_y) / 2, 0.0)
        self._pane_renderer().camera.position = (self._pane_renderer().camera.focal_point[0], self._pane_renderer().camera.focal_point[1], 20.0)
        self._pane_renderer().camera.parallel_scale = span / 2
        self._refresh_2d_viewport(resample=True, render=False)

    def _render_scene(self) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._render_2d_scene()
        else:
            self._render_3d_scene()

    def _render_3d_scene(self) -> None:
        appearance = self._pane_scene().scene_appearances[SceneMode.THREE_D]
        effective_theme = getattr(self, "effective_theme", "light")
        build_scene(
            self._pane_renderer(),
            show_axes=False,
            show_helpers=True,
            lighting=self._pane_scene().lighting,
            camera_position=self._pane_scene()._three_d_camera_position,
            appearance=appearance,
            effective_theme=effective_theme,
            axis_color_mode=appearance.axis_color_mode,
            contrast_axis_color=appearance.contrast_axis_color(effective_theme),
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
            base_surface=False,
        )
        configure_3d_camera_interaction(self._pane_renderer())
        # build_scene 内部会调用 plotter.clear() 清除全部 actor，因此坐标轴需要重新创建。
        self._pane_scene()._three_d_axes = ThreeDAxes(self._pane_renderer())
        extent = self._current_3d_axis_extent()
        # 切换场景会重新创建坐标轴；沿用上次三维间距，避免同一视角重建后跳到另一档刻度。
        previous_spacing = self._pane_scene()._three_d_spacing
        spacing = self._pane_scene()._three_d_axes.render(
            extent,
            axis_color_mode=appearance.axis_color_mode,
            contrast_color=appearance.contrast_axis_color(effective_theme),
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
            previous_spacing=previous_spacing,
        )
        self._pane_scene()._three_d_spacing = spacing
        self._pane_scene()._three_d_extent = extent
        focal = tuple(self._pane_renderer().camera.focal_point)
        self._pane_scene().plot_domain = PlotDomain(
            x_range=(focal[0] - extent, focal[0] + extent),
            y_range=(focal[1] - extent, focal[1] + extent),
            z_range=(focal[2] - extent, focal[2] + extent),
            explicit_resolution=self._pane_scene().plot_domain.explicit_resolution,
            implicit_resolution=self._pane_scene().plot_domain.implicit_resolution,
        )
        self._pane_scene()._last_domain_extent = extent
        self._pane_scene().layer_controller = LayerSceneController(
            self._pane_renderer(),
            self._pane_scene().plot_domain,
            ambient=self._pane_scene().lighting.ambient,
            material_name=self._pane_scene().material_name,
        )
        self._pane_scene().layer_controller.set_global_intersections_visible(appearance.show_intersections)
        self._pane_scene().curve_controller = None
        self._pane_scene().geometry_controller = None
        self._pane_scene().geometry3d_controller = Geometry3DSceneController(self._pane_renderer())
        available_layers: list[SurfaceLayer] = []
        for layer in self._pane_scene().layers:
            try:
                self._pane_scene().layer_controller.add_layer(layer)
            except (ExpressionError, LayerRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self._pane_scene().layers = available_layers
        self._sync_panel_layers(self._pane_scene().layers)
        self.algebra_panel.set_status("三维场景已准备好")
        for operation in tuple(getattr(self._pane_scene(), "_agent_geometry3d", {}).values()):
            if operation.get("op") == "linear3d.upsert":
                self._command_upsert_linear3d(operation)
            elif operation.get("op") == "plane3d.upsert":
                self._command_upsert_plane3d(operation)
            elif operation.get("op") in {"geometry.parallelogram3d", "geometry.parallelepiped", "geometry.oriented_volume"}:
                self._command_upsert_solid3d(operation)
            elif operation.get("op") == "annotation.formula":
                self._command_formula_annotation(operation)
        self._render_agent_points3d()
        self._apply_linear_algebra_storyboard_visibility()
        self._refresh_3d_viewport(resample=True, render=False)
        self._pane_renderer().render()

    def _render_2d_scene(self) -> None:
        appearance = self._pane_scene().scene_appearances[SceneMode.TWO_D]
        effective_theme = getattr(self, "effective_theme", "light")
        self._pane_renderer().clear()
        self._pane_renderer().set_background(appearance.background_color(effective_theme))
        configure_2d_camera(self._pane_renderer())
        self._restore_2d_camera()
        visible = self._current_2d_bounds()
        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        sampling_domain = self._curve_sampling_domain(sampling_bounds)
        self._pane_scene().curve_domain = sampling_domain
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
        )
        # plotter.clear() 会清除全部 actor，因此二维辅助线池也必须重新建立。
        self._pane_scene()._two_d_guides = TwoDGuides(self._pane_renderer())
        self._pane_scene()._two_d_guides.render(
            sampling_bounds,
            appearance,
            effective_theme=effective_theme,
            spacing=spacing,
        )
        self._pane_scene()._two_d_guide_spacing = spacing
        self._pane_scene()._two_d_guide_bounds = sampling_bounds
        self._pane_scene()._two_d_sample_bounds = sampling_bounds
        self._pane_scene().curve_controller = CurveSceneController(self._pane_renderer(), sampling_domain)
        self._pane_scene().geometry_controller = GeometrySceneController(self._pane_renderer(), visible)
        self._pane_scene().geometry3d_controller = None
        self._pane_scene().layer_controller = None
        available_layers: list[CurveLayer] = []
        for layer in self._pane_scene().curve_layers:
            try:
                self._pane_scene().curve_controller.add_layer(layer)
            except (CurveExpressionError, CurveRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self._pane_scene().curve_layers = available_layers
        for point in self._pane_scene().geometry_points:
            self._pane_scene().geometry_controller.add_point(point)
        for linear in self._pane_scene().linear_objects:
            self._pane_scene().geometry_controller.add_linear(linear)
        for annotation in getattr(self._pane_scene(), "annotations", []):
            self._pane_scene().geometry_controller.add_annotation(annotation)
        for operation in tuple(getattr(self._pane_scene(), "_agent_teaching_2d", {}).values()):
            self._command_teaching_geometry(operation)
        self._render_agent_areas()
        self._sync_panel_layers(self._two_d_panel_layers())
        self._apply_linear_algebra_storyboard_visibility()
        self.algebra_panel.set_status("二维场景已准备好")
        self._pane_renderer().render()

    def _restore_2d_camera(self) -> None:
        # 2D 场景使用并行投影（parallel projection），这里的 parallel_scale 相当于
        # "视口的世界单位 zoom"：数值越大，视口显示的世界范围越大，图像越小；
        # 数值越小，视口显示的范围越小，图像越放大。
        #
        # 这个值会直接影响 _current_2d_bounds() 中的 visible_2d_bounds() 计算：
        #   half_height = parallel_scale
        #   half_width = half_height * aspect_ratio
        # 因此它决定了当前可见窗口的 x/y 范围，进而影响网格、刻度和采样区域。
        if self._pane_scene()._two_d_camera_position is not None:
            self._pane_renderer().camera_position = self._pane_scene()._two_d_camera_position
        else:
            self._pane_renderer().camera_position = [
                (0.0, 0.0, 20.0),    # 相机位置
                (0.0, 0.0, 0.0),     # 相机焦点
                (0.0, 1.0, 0.0),     # 相机“向上”的方向
            ]
        if self._pane_scene()._two_d_parallel_scale is not None:
            self._pane_renderer().camera.parallel_scale = max(1e-6, self._pane_scene()._two_d_parallel_scale)
        else:
            self._pane_renderer().camera.parallel_scale = 6.0
        self._pane_renderer().camera.clipping_range = (0.01, 1000.0)

    def _current_2d_bounds(self) -> ViewportBounds:
        interactor = getattr(self._pane_renderer(), "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        focal = tuple(self._pane_renderer().camera.focal_point)
        return visible_2d_bounds(focal, float(self._pane_renderer().camera.parallel_scale), width / height)

    def _curve_sampling_domain(self, bounds: ViewportBounds) -> Plot2DDomain:
        # 采样域为可视区域外扩 _GUIDE_MARGIN 得到（约 6 倍视口跨度）。若固定分辨率，
        # 采样点会被稀释到整个外扩域，可视区域内密度不足而出现锯齿。这里按外扩比例
        # 放大分辨率，保证可视区域内采样密度恒定，同时设上限避免性能问题。
        span_ratio = 1.0 + 2.0 * _GUIDE_MARGIN
        curve_resolution = min(
            8000, max(self._pane_scene().curve_domain.curve_resolution, int(self._pane_scene().curve_domain.curve_resolution * span_ratio))
        )
        # 隐式曲线为二维网格（成本 O(n²)），放大比例受限以兼顾性能。
        implicit_resolution = min(
            480, max(self._pane_scene().curve_domain.implicit_resolution, int(self._pane_scene().curve_domain.implicit_resolution * span_ratio ** 0.5))
        )
        return Plot2DDomain(
            x_range=bounds.x_range,
            y_range=bounds.y_range,
            curve_resolution=curve_resolution,
            implicit_resolution=implicit_resolution,
        )

    def _refresh_2d_viewport(
        self, *, resample: bool = True, render: bool = True, force: bool = False
    ) -> None:
        visible = self._current_2d_bounds()
        # Guide and curve sampling use hysteresis; geometry must follow the
        # actual visible viewport on every camera interaction.
        geometry_controller = getattr(self._pane_scene(), "geometry_controller", None)
        if geometry_controller is not None:
            geometry_controller.set_bounds(visible)
        appearance = self._pane_scene().scene_appearances[SceneMode.TWO_D]
        effective_theme = getattr(self, "effective_theme", "light")
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            previous_spacing=None if force else self._pane_scene()._two_d_guide_spacing,
        )
        spacing_unchanged = (
            self._pane_scene()._two_d_guide_spacing is not None
            and abs(spacing - self._pane_scene()._two_d_guide_spacing) <= self._pane_scene()._two_d_guide_spacing * 1e-9
        )
        still_covered = (
            self._pane_scene()._two_d_guide_bounds is not None
            and self._pane_scene()._two_d_guide_bounds.contains(visible)
        )

        # 视口接近缓存边缘时提前补绘，补绘范围始终位于当前视口外围。
        needs_prefetch = (
            self._pane_scene()._two_d_guide_bounds is not None
            and self._needs_2d_prefetch(visible, self._pane_scene()._two_d_guide_bounds)
        )

        if not force and spacing_unchanged and still_covered and not needs_prefetch:
            if render:
                self._pane_renderer().render()
            return

        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        if self._pane_scene()._two_d_guides is not None:
            self._pane_scene()._two_d_guides.render(
                sampling_bounds,
                appearance,
                effective_theme=effective_theme,
                spacing=spacing,
            )
        self._pane_scene()._two_d_guide_spacing = spacing
        self._pane_scene()._two_d_guide_bounds = sampling_bounds
        if resample and self._pane_scene().curve_controller is not None:
            # contains() 只能识别平移或缩小（可见区域超出已采样范围）；放大时较小的
            # 可见区域仍被旧的大采样范围包含，若不重采样就会沿用稀疏网格，放大后
            # 曲线出现折线状的不连续。这里额外判断放大幅度：采样范围由可见范围
            # expanded(_GUIDE_MARGIN) 得到，反推出采样时的可见跨度，一旦当前可见
            # 跨度明显小于它（放大约 1.4 倍以上）便按当前视口重采样，恢复精细分辨率。
            needs_resample = force or needs_prefetch or self._pane_scene()._two_d_sample_bounds is None or (
                not self._pane_scene()._two_d_sample_bounds.contains(visible)
            )
            if not needs_resample and self._pane_scene()._two_d_sample_bounds is not None:
                sampled_visible_span = self._pane_scene()._two_d_sample_bounds.x_span / (
                    1.0 + 2.0 * _GUIDE_MARGIN
                )
                # 放大约 1.05 倍即重采样（阈值 0.95），及时恢复精细分辨率消除锯齿。
                if visible.x_span < sampled_visible_span * 0.95:
                    needs_resample = True
            if needs_resample:
                sampling_domain = self._curve_sampling_domain(sampling_bounds)
                try:
                    self._pane_scene().curve_controller.set_domain(sampling_domain)
                except (CurveExpressionError, CurveRenderError) as error:
                    self.algebra_panel.set_status(f"无法重新绘制曲线: {error}", is_error=True)
                else:
                    self._pane_scene().curve_domain = sampling_domain
                    self._pane_scene()._two_d_sample_bounds = sampling_bounds
        if render:
            self._pane_renderer().render()

    def _current_3d_axis_extent(self) -> float:
        camera = self._pane_renderer().camera
        distance = float(camera.distance)
        view_angle = float(camera.view_angle)
        interactor = getattr(self._pane_renderer(), "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        return visible_3d_axis_extent(distance, view_angle, width / height)

    def _refresh_3d_viewport(
        self, *, resample: bool = True, render: bool = True, force: bool = False
    ) -> None:
        """刷新三维视口。

        坐标轴范围由定义域决定，与相机无关：缩放是纯相机操作，坐标轴会随
        投影自然变大变小，无需重建几何。只有外观设置变化（force=True）才
        重新生成坐标轴。
        """
        if force and self._pane_scene()._three_d_axes is not None:
            appearance = self._pane_scene().scene_appearances[SceneMode.THREE_D]
            effective_theme = getattr(self, "effective_theme", "light")
            extent = self._pane_scene()._three_d_extent or self._current_3d_axis_extent()
            self._pane_scene()._three_d_spacing = self._pane_scene()._three_d_axes.render(
                extent,
                axis_color_mode=appearance.axis_color_mode,
                contrast_color=appearance.contrast_axis_color(effective_theme),
                show_ticks=appearance.show_ticks,
                tick_spacing_mode=appearance.tick_spacing_mode,
                custom_tick_spacing=appearance.tick_spacing,
                previous_spacing=None,
            )
            self._pane_scene()._three_d_extent = extent

        if render:
            self._pane_renderer().render()

    def _refresh_visible_viewport(self) -> None:
        self._pane_scene()._viewport_refresh_pending = False
        if self._pane_scene()._viewport_refreshing or not (self._pane_renderer(required=False) is not None):
            return
        self._pane_scene()._viewport_refreshing = True
        try:
            if self._pane_scene().scene_mode is SceneMode.TWO_D:
                self._refresh_2d_viewport()
            else:
                self._refresh_3d_viewport()
        finally:
            self._pane_scene()._viewport_refreshing = False

    def _sync_panel_layers(
        self,
        layers: list[SurfaceLayer] | list[CurveLayer] | list[CurveLayer | GeometryObject],
    ) -> None:
        self.algebra_panel.set_scene_mode(self._pane_scene().scene_mode)
        self.algebra_panel.set_catalog_entries(catalog_entries(self._pane_scene().scene_mode))
        self.algebra_panel.set_layers(layers)
        self._sync_scene_controls()

    def _add_formula_for_scene(self, kind: str, latex: str) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._add_cas_curve(kind, latex)
        else:
            self._add_cas_surface(kind, latex)

    def _reveal_algebra_pane(self, _pane_id: str, count: int) -> None:
        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            container.set_layout(count)

    def _update_formula_for_scene(self, *args: str) -> None:
        pane_id = args[0] if len(args) == 4 else None
        layer_id, kind, latex = args[-3:]
        manager = getattr(self, "pane_manager", None)
        previous = getattr(manager, "active_pane_id", None)
        if pane_id and manager is not None and pane_id != previous:
            try:
                manager.focus_pane(pane_id)
            except (AttributeError, ValueError):
                pane_id = None
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            if self._point_2d(layer_id) is not None:
                self._update_point_coordinates(layer_id, latex)
            else:
                self._update_curve_expression(layer_id, kind, latex)
        else:
            self._update_surface_expression(layer_id, kind, latex)
        if pane_id and previous and previous != pane_id:
            try:
                manager.focus_pane(previous)
            except (AttributeError, ValueError):
                pass

    def _update_point_coordinates(self, point_id: str, latex: str) -> None:
        point = self._point_2d(point_id)
        if point is None:
            return
        coordinates = parse_point_coordinates(latex)
        if coordinates is None:
            self.algebra_panel.set_status("坐标格式无效，请输入形如 (x, y)", is_error=True)
            return
        before = self._capture_geometry_state()
        point.x, point.y = coordinates
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.move_point(point_id, *coordinates)
        self.algebra_panel.sync_layer(point_id, point)
        self.algebra_panel.finish_edit()
        self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已更新点 {point.name}")
        self._pane_renderer().render()

    def _add_catalog_entry(self, entry_id: str) -> None:
        entry = catalog_entry(entry_id, self._pane_scene().scene_mode)
        if entry is None:
            return
        if entry.mode is SceneMode.THREE_D:
            self._add_builtin_surface(entry.builtin_id or entry.id)
            return
        layer = CurveLayer(
            name=entry.name,
            kind=entry.kind,
            expression=entry.expression,
            latex=entry.latex,
            parameters=dict(entry.parameters),
            builtin_id=entry.id,
            color=entry.color,
        )
        self._add_curve_layer(layer)

    @staticmethod
    def _linear_algebra_lesson_plan(topic_id: str) -> CommandPlan:
        """Build and validate one atomic clear-and-load lecture plan."""
        registry = catalog_registry()
        topic = registry.get_topic(topic_id)
        recipe = registry.get_recipe(topic.visualization_id)
        lesson_plan = recipe.builder(RenderContext.default(topic.id))
        validation = SceneCommandService().validate(lesson_plan)
        if not validation.valid:
            raise CommandError("；".join(validation.messages))
        return CommandPlan(
            scene=lesson_plan.scene,
            summary=lesson_plan.summary,
            operations=({"op": "scene.clear", "scope": "all"}, *lesson_plan.operations),
        )

    @staticmethod
    def _linear_algebra_source_repository() -> LectureSourceRepository:
        return LectureSourceRepository(Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md")

    def _load_linear_algebra_topic(self, topic_id: str) -> None:
        registry = catalog_registry()
        try:
            bundle = registry.resolve_bundle(
                topic_id,
                artifact_store=runtime_teaching_store(),
                source_repository=self._linear_algebra_source_repository(),
            )
            topic = bundle.topic
            explanation_case = bundle.artifact or registry.get_explanation(topic.explanation_id)
            lesson_plan = bundle.compiled.plan if bundle.compiled is not None else bundle.recipe.builder(RenderContext.default(topic.id))
            validation = SceneCommandService().validate(lesson_plan)
            if not validation.valid:
                raise CommandError("；".join(validation.messages))
            plan = CommandPlan(
                scene=lesson_plan.scene,
                summary=lesson_plan.summary,
                operations=(
                    {"op": "scene.clear", "scope": "all"},
                    *lesson_plan.operations,
                ),
            )
        except (KeyError, CommandError, ValueError) as error:
            self.algebra_panel.set_status(f"未知或无效的线性代数主题 {topic_id}: {error}", is_error=True)
            return
        try:
            self.scene_command_service.execute(plan)
        except CommandError as error:
            self.algebra_panel.set_status(f"无法加载主题 {topic.title}: {error}", is_error=True)
            return
        self._active_linear_algebra_topic_id = topic.id
        self._active_linear_algebra_compiled = bundle.compiled
        self._active_linear_algebra_stage_id = None
        self._hidden_linear_algebra_aliases = set()
        if plan.scene == "2d":
            self._set_2d_geometry_tool("select")
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool("select", emit_signal=False)
        self._sync_scene_controls()
        if bundle.compiled is not None and bundle.compiled.storyboard:
            self._select_linear_algebra_stage(topic.id, bundle.compiled.storyboard[0].id)
        try:
            self._open_teaching_case_panes(explanation_case, bundle.compiled)
            if hasattr(self, "agent_panel"):
                if hasattr(self, "agent_sidebar"):
                    self._open_agent_panel()
                self.agent_panel.show_math_case(
                    explanation_case,
                    case_id=topic.id,
                    category=topic.source_path[1],
                    scene_mode=plan.scene,
                    compiled=bundle.compiled,
                )
        except Exception as error:
            # 场景已成功加载时，案例窗格/WebView 的异常不应中断主界面；
            # 清理半成品窗格并保留代数区域可用，同时给出可见错误。
            self._close_teaching_case_panes()
            self.algebra_panel.set_status(f"主题已加载，但案例面板显示失败: {error}", is_error=True)
            return
        if bundle.source_diagnostic is not None:
            _, old_hash, current_hash = bundle.source_diagnostic
            self.algebra_panel.set_status(f"已加载主题: {topic.title}（stale_source: {old_hash} → {current_hash}）")
        else:
            self.algebra_panel.set_status(f"已加载主题: {topic.title}")

    def _enter_linear_algebra_workspace(self) -> None:
        """Open the lecture catalog without changing the current scene."""
        self.algebra_panel.set_status("已打开线性代数讲义目录")

    def _add_cas_surface(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        layer = SurfaceLayer(
            name=f"曲面 {len(self._pane_scene().layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: 1.0 for name in parsed.parameter_names},
        )
        if self._add_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_cas_curve(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_curve(latex, kind)
        except (CurveExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        layer = CurveLayer(
            name=f"曲线 {len(self._pane_scene().curve_layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: 1.0 for name in parsed.parameter_names},
        )
        if self._add_curve_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_builtin_surface(self, builtin_id: str) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            return
        self._add_layer(create_builtin_layer(builtin_id))

    def _add_layer(self, layer: SurfaceLayer) -> bool:
        if self._pane_scene().layer_controller is None:
            return False
        try:
            self._pane_scene().layer_controller.add_layer(layer)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲面: {error}", is_error=True)
            return False
        self._pane_scene().layers.append(layer)
        self.algebra_panel.set_layers(self._pane_scene().layers)
        self.algebra_panel.set_status(f"已添加 {layer.name}")
        self._pane_renderer().render()
        return True

    def _add_curve_layer(self, layer: CurveLayer) -> bool:
        if self._pane_scene().curve_controller is None:
            return False
        try:
            self._pane_scene().curve_controller.add_layer(layer)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲线: {error}", is_error=True)
            return False
        self._pane_scene().curve_layers.append(layer)
        self._pane_scene()._two_d_object_order.append(layer.id)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self.algebra_panel.set_status(f"已添加 {layer.name}")
        self._pane_renderer().render()
        return True

    def _update_surface_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._layer(layer_id)
        if current is None or self._pane_scene().layer_controller is None:
            return
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        updated = replace(
            current,
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: current.parameters.get(name, 1.0) for name in parsed.parameter_names},
            builtin_id=None,
        )
        try:
            self._pane_scene().layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面: {error}", is_error=True)
            return
        self._pane_scene().layers = [updated if layer.id == layer_id else layer for layer in self._pane_scene().layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self._pane_renderer().render()

    def _update_curve_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self._pane_scene().curve_controller is None:
            return
        try:
            formula, parsed = self._parse_mathlive_curve(latex, kind)
        except (CurveExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        updated = replace(
            current,
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: current.parameters.get(name, 1.0) for name in parsed.parameter_names},
            builtin_id=None,
        )
        try:
            self._pane_scene().curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线: {error}", is_error=True)
            return
        self._pane_scene().curve_layers = [updated if layer.id == layer_id else layer for layer in self._pane_scene().curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self._pane_renderer().render()

    def _parse_mathlive_surface(self, latex: str, kind: str):
        formula = self.latex_parser.parse(latex, kind)
        return formula, parse_surface_expression(formula.canonical_source, formula.kind)

    def _parse_mathlive_curve(self, latex: str, kind: str):
        formula = self.latex_parser.parse_2d(latex, kind)
        return formula, parse_curve_expression(formula.canonical_source, formula.kind)

    def _remove_layer_for_scene(self, layer_id: str) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                self._remove_geometry_object(layer_id)
            else:
                self._remove_curve(layer_id)
        else:
            self._remove_surface(layer_id)

    def _remove_surface(self, layer_id: str) -> None:
        if self._pane_scene().layer_controller is None:
            return
        self._pane_scene().layer_controller.remove_layer(layer_id)
        self._pane_scene().layers = [layer for layer in self._pane_scene().layers if layer.id != layer_id]
        self.algebra_panel.set_layers(self._pane_scene().layers)
        self.algebra_panel.set_status("已删除曲面")
        self._pane_renderer().render()

    def _remove_curve(self, layer_id: str) -> None:
        if self._pane_scene().curve_controller is None:
            return
        self._pane_scene().curve_controller.remove_layer(layer_id)
        self._pane_scene().curve_layers = [layer for layer in self._pane_scene().curve_layers if layer.id != layer_id]
        self._pane_scene()._two_d_object_order = [item_id for item_id in self._pane_scene()._two_d_object_order if item_id != layer_id]
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self.algebra_panel.set_status("已删除曲线")
        self._pane_renderer().render()

    def _remove_geometry_object(self, object_id: str) -> None:
        geometry = self._geometry_object(object_id)
        if geometry is None:
            return
        before = self._capture_geometry_state()
        removed_ids = {object_id}
        if isinstance(geometry, Point2D):
            removed_ids.update(
                linear.id
                for linear in self._pane_scene().linear_objects
                if object_id in {linear.start_point_id, linear.end_point_id}
            )
            self._pane_scene().geometry_points = [point for point in self._pane_scene().geometry_points if point.id != object_id]
            self._pane_scene().linear_objects = [
                linear for linear in self._pane_scene().linear_objects if linear.id not in removed_ids
            ]
        else:
            self._pane_scene().linear_objects = [
                linear for linear in self._pane_scene().linear_objects if linear.id != object_id
            ]
        self._pane_scene()._two_d_object_order = [
            item_id for item_id in self._pane_scene()._two_d_object_order if item_id not in removed_ids
        ]
        if self._pane_scene()._pending_geometry_point_id in removed_ids:
            self._set_2d_geometry_tool(self._pane_scene()._active_2d_tool)
        if self._pane_scene().geometry_controller is not None:
            for removed_id in removed_ids:
                self._pane_scene().geometry_controller.remove_object(removed_id)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self._record_geometry_change(before)
        self.algebra_panel.set_status("已删除几何对象")
        self._pane_renderer().render()

    def _set_layer_visibility(self, layer_id: str, visible: bool) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                self._set_geometry_visibility(layer_id, visible)
            else:
                self._set_curve_visibility(layer_id, visible)
        else:
            self._set_surface_visibility(layer_id, visible)

    def _set_surface_visibility(self, layer_id: str, visible: bool) -> None:
        if self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_visible(layer_id, visible)
        self._replace_layer(layer_id, visible=visible)
        self._pane_renderer().render()

    def _set_curve_visibility(self, layer_id: str, visible: bool) -> None:
        if self._pane_scene().curve_controller is not None:
            self._pane_scene().curve_controller.set_visible(layer_id, visible)
        self._replace_curve_layer(layer_id, visible=visible)
        self._pane_renderer().render()

    def _set_geometry_visibility(self, layer_id: str, visible: bool) -> None:
        geometry = self._geometry_object(layer_id)
        if geometry is None:
            return
        if geometry.visible == visible:
            return
        before = self._capture_geometry_state()
        geometry.visible = visible
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.set_visible(layer_id, visible)
        self.algebra_panel.sync_layer(layer_id, geometry)
        self._record_geometry_change(before)
        self._pane_renderer().render()

    def _set_surface_intersections_visibility(self, layer_id: str, visible: bool) -> None:
        if self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_intersections_visible(layer_id, visible)
        self._replace_layer(layer_id, intersections_visible=visible)
        self._pane_renderer().render()

    def _set_surface_intersection_color(self, layer_id: str, color: str) -> None:
        current = self._layer(layer_id)
        if current is None:
            return
        self._pane_scene()._intersection_color_revision = (
            max(
                self._pane_scene()._intersection_color_revision,
                *(layer.intersection_color_revision for layer in self._pane_scene().layers),
            )
            + 1
        )
        updated = replace(
            current,
            intersection_color=color,
            intersection_color_revision=self._pane_scene()._intersection_color_revision,
        )
        if self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_intersection_color(
                layer_id, color, updated.intersection_color_revision
            )
        self._pane_scene().layers = [updated if layer.id == layer_id else layer for layer in self._pane_scene().layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self._pane_renderer().render()

    def _set_layer_color(self, layer_id: str, color: str) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                return
            if self._pane_scene().curve_controller is not None:
                self._pane_scene().curve_controller.set_color(layer_id, color)
            self._replace_curve_layer(layer_id, color=color)
        else:
            if self._pane_scene().layer_controller is not None:
                self._pane_scene().layer_controller.set_color(layer_id, color)
            self._replace_layer(layer_id, color=color)
        self._pane_renderer().render()

    def _set_surface_color(self, layer_id: str, color: str) -> None:
        self._set_layer_color(layer_id, color)

    def _set_surface_opacity(self, layer_id: str, opacity: float) -> None:
        if self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_opacity(layer_id, opacity)
        self._replace_layer(layer_id, opacity=opacity)
        self._pane_renderer().render()

    def _set_curve_line_width(self, layer_id: str, line_width: float) -> None:
        if self._pane_scene().curve_controller is not None:
            self._pane_scene().curve_controller.set_line_width(layer_id, line_width)
        self._replace_curve_layer(layer_id, line_width=line_width)
        self._pane_renderer().render()

    def _set_layer_range(self, layer_id: str, range_scale: float) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._set_curve_range(layer_id, range_scale)
        else:
            self._set_surface_range(layer_id, range_scale)

    def _set_surface_range(self, layer_id: str, range_scale: float) -> None:
        current = self._layer(layer_id)
        if current is None or self._pane_scene().layer_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self._pane_scene().layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面范围: {error}", is_error=True)
            return
        self._pane_scene().layers = [updated if layer.id == layer_id else layer for layer in self._pane_scene().layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 {updated.range_scale:.0%}")
        self._pane_renderer().render()

    def _set_curve_range(self, layer_id: str, range_scale: float) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self._pane_scene().curve_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self._pane_scene().curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线范围: {error}", is_error=True)
            return
        self._pane_scene().curve_layers = [updated if layer.id == layer_id else layer for layer in self._pane_scene().curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 x{updated.range_scale:.1f}")
        self._pane_renderer().render()

    def _set_auto_intersections(self, enabled: bool) -> None:
        if self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_auto_intersections(enabled)
        self._pane_renderer().render()

    def _add_manual_intersection(self, first_id: str, second_id: str) -> None:
        if self._pane_scene().layer_controller is None:
            return
        self._pane_scene().layer_controller.set_manual_intersection_pair(first_id, second_id, True)
        self._pane_renderer().render()

    def _toggle_scene_mode(self) -> None:
        next_mode = SceneMode.TWO_D if self._pane_scene().scene_mode is SceneMode.THREE_D else SceneMode.THREE_D
        self._set_scene_mode(next_mode)

    def cycle_theme_mode(self) -> None:
        """Cycle the persisted theme preference and apply it immediately."""
        modes: tuple[ThemeMode, ...] = ("system", "light", "dark")
        current = self.theme_mode if self.theme_mode in modes else "system"
        mode = modes[(modes.index(current) + 1) % len(modes)]
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        scheme = app.styleHints().colorScheme() if app is not None else Qt.ColorScheme.Light
        effective = "dark" if mode == "dark" or (mode == "system" and scheme == Qt.ColorScheme.Dark) else "light"
        self.set_theme(mode, effective)

    def _set_scene_mode(self, mode: SceneMode) -> None:
        if mode is self._pane_scene().scene_mode:
            return
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._close_teaching_case_panes()
            self._set_2d_geometry_tool(None)
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool(None, emit_signal=False)
        self._save_current_view_state()
        self._pane_scene().scene_mode = mode
        if hasattr(self, "status_bar"):
            self.status_bar.set_scene_mode(mode)
        self._close_scene_settings(immediate=True)
        self._render_scene()

    _TOOL_LABELS = {"line": "直线", "segment": "线段", "ray": "射线", "vector": "向量"}

    def _set_2d_geometry_tool(self, tool: ToolKind | None) -> None:
        """切换当前二维几何创建工具，并清理未完成的两点操作。"""
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            tool = None
        self._pane_scene()._pending_geometry_point_id = None
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._drag_start_geometry_state = None
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.clear_draft()
            # 离开选择工具时清除高亮，避免遗留悬浮/选中效果。
            if tool != "select":
                self._pane_scene().geometry_controller.set_hover(None)
                self._pane_scene().geometry_controller.set_selected(None)
        self._pane_scene()._active_2d_tool = tool
        self._pane_scene()._active_linear_algebra_tool = None
        self._pane_scene()._linear_algebra_pending_vector_ids = []
        self._pane_scene()._linear_algebra_polygon_point_ids = []
        if hasattr(self, "status_bar"):
            self.status_bar.set_active_tool(self._TOOL_LABELS.get(tool or ""))
        if hasattr(self, "two_d_geometry_toolbar"):
            self.two_d_geometry_toolbar.set_active_tool(tool)
        if (self._pane_renderer(required=False) is not None):
            cursor = {
                None: Qt.CursorShape.ArrowCursor,
                "select": Qt.CursorShape.ArrowCursor,
            }.get(tool, Qt.CursorShape.CrossCursor)
            self._pane_renderer().interactor.setCursor(cursor)

    def _on_unified_2d_tool_selected(self, tool: ToolKind | None) -> None:
        """Route the single toolbar's selection to the active workspace."""
        self.pane_manager.activate_for_tool()
        if tool is not None and self._pane_scene().scene_mode is not SceneMode.TWO_D:
            self._set_scene_mode(SceneMode.TWO_D)
        if tool in {"angle", "projection", "polygon", "transform", "subspace", "area"}:
            self._on_linear_algebra_tool_selected(str(tool))
            return
        self._set_2d_geometry_tool(tool)

    def _on_linear_algebra_tool_selected(self, tool: str) -> None:
        """Handle linear algebra toolbar tool selection."""
        tool_labels = {
            "angle": "角度测量",
            "projection": "投影",
            "polygon": "多边形",
            "transform": "矩阵变换",
            "subspace": "子空间",
            "area": "有向面积",
        }
        # Map the basic tools to the existing 2D geometry infrastructure.
        tool_mapping = {
            "select": "select",
            "point": "point",
            "vector": "vector",
        }

        mapped_tool = tool_mapping.get(tool)
        if mapped_tool is not None:
            self._set_2d_geometry_tool(mapped_tool)
        else:
            self._set_2d_geometry_tool(None)
            # `_set_2d_geometry_tool` also synchronizes the shared toolbar;
            # restore the specialized selection after clearing the basic tool.
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool(tool)
            self._pane_scene()._active_linear_algebra_tool = tool
            if hasattr(self, "status_bar"):
                self.status_bar.set_active_tool(tool_labels.get(tool, tool))
            if tool is not None:
                self._pane_renderer().interactor.setFocus()
        if tool == "select":
            self.algebra_panel.set_status("选择工具：单击选中，拖动点可移动，双击点可编辑坐标")
        elif tool == "point":
            self.algebra_panel.set_status("点工具：单击画布创建点")
        elif tool is not None:
            if tool == "polygon":
                self.algebra_panel.set_status("多边形工具：依次单击顶点，双击完成")
            elif tool == "transform":
                self.algebra_panel.set_status("矩阵变换工具：单击后输入 2×2 矩阵")
            else:
                self.algebra_panel.set_status(f"{tool_labels.get(tool, tool)}工具：单击第一个向量")

    def _next_linear_algebra_tool_alias(self, kind: str) -> str:
        self._pane_scene()._linear_algebra_tool_sequence = getattr(self._pane_scene(), "_linear_algebra_tool_sequence", 0) + 1
        return f"la_tool_{kind}_{self._pane_scene()._linear_algebra_tool_sequence}"

    def _clear_linear_algebra_tool_overlays(self) -> None:
        """Remove only interactive overlays created by the linear algebra toolbar."""
        teaching = getattr(self._pane_scene(), "_agent_teaching_2d", {})
        aliases = {
            annotation.agent_alias
            for annotation in getattr(self._pane_scene(), "annotations", [])
            if isinstance(annotation.agent_alias, str)
            and annotation.agent_alias.startswith("la_tool_")
        }
        has_overlays = bool(aliases) or any(str(alias).startswith("la_tool_") for alias in teaching)
        if has_overlays and getattr(self._pane_scene(), "_linear_algebra_tool_preclear_state", None) is None:
            capture = getattr(self, "_capture_scene_command_state", None)
            if callable(capture):
                try:
                    self._pane_scene()._linear_algebra_tool_preclear_state = capture()
                except AttributeError:
                    # Lightweight test hosts do not carry the full scene state.
                    self._pane_scene()._linear_algebra_tool_preclear_state = None
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None and hasattr(controller, "clear_teaching_prefix"):
            controller.clear_teaching_prefix("la_tool_")
        if aliases:
            removed_ids = {annotation.id for annotation in self._pane_scene().annotations if annotation.agent_alias in aliases}
            self._pane_scene().annotations = [annotation for annotation in self._pane_scene().annotations if annotation.agent_alias not in aliases]
            self._pane_scene()._two_d_object_order = [item_id for item_id in self._pane_scene()._two_d_object_order if item_id not in removed_ids]
            if controller is not None:
                for object_id in removed_ids:
                    controller.remove_object(object_id)
        self._pane_scene()._agent_teaching_2d = {
            alias: operation for alias, operation in teaching.items() if not str(alias).startswith("la_tool_")
        }

    def _restore_linear_algebra_preclear_state(self) -> None:
        state = getattr(self._pane_scene(), "_linear_algebra_tool_preclear_state", None)
        self._pane_scene()._linear_algebra_tool_preclear_state = None
        if state is not None:
            self._restore_scene_command_state(state)

    def _linear_algebra_vector_at(self, x: float, y: float) -> Linear2D | None:
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is None:
            return None
        hit_id = controller.hit_test(x, y, self._hit_tolerance())
        if hit_id is None or hit_id not in controller.linears:
            return None
        linear = self._geometry_object(hit_id)
        if isinstance(linear, Linear2D) and linear.kind == "vector":
            return linear
        return None

    def _build_linear_algebra_tool_plan(self, tool: str, vectors: tuple[Linear2D, Linear2D]) -> CommandPlan | None:
        alias = self._next_linear_algebra_tool_alias(tool)
        points = {point.id: point for point in self._pane_scene().geometry_points}
        return build_vector_tool_plan(tool, vectors, points, self._current_2d_bounds(), alias)

    def _apply_linear_algebra_tool_plan(self, plan: CommandPlan) -> bool:
        preclear_state = getattr(self._pane_scene(), "_linear_algebra_tool_preclear_state", None)
        try:
            self.scene_command_service.execute(plan)
        except (CommandError, ValueError) as error:
            self._restore_linear_algebra_preclear_state()
            self.algebra_panel.set_status(f"无法执行{plan.summary}: {error}", is_error=True)
            return False
        self._pane_scene()._linear_algebra_tool_preclear_state = None
        if preclear_state is not None and getattr(self._pane_scene(), "_scene_command_undo_stack", None):
            # The interactive overlay replacement happened just before the
            # command service opened its transaction.  Point the new undo entry
            # at the true pre-replacement scene so undo restores the old tool.
            self._pane_scene()._scene_command_undo_stack[-1] = preclear_state
        self._pane_renderer().render()
        return True

    def _handle_linear_algebra_vector_click(self, x: float, y: float) -> bool:
        vector = self._linear_algebra_vector_at(x, y)
        if vector is None:
            self.algebra_panel.set_status("请单击已有的向量线段", is_error=True)
            return True
        pending = getattr(self._pane_scene(), "_linear_algebra_pending_vector_ids", [])
        if vector.id in pending:
            self.algebra_panel.set_status("请再选择另一条向量", is_error=True)
            return True
        pending.append(vector.id)
        self._pane_scene()._linear_algebra_pending_vector_ids = pending
        self._select_geometry_object(vector.id)
        if len(pending) == 1:
            self.algebra_panel.set_status("已选择第一条向量，请单击第二条向量")
            self._pane_renderer().render()
            return True
        first = self._geometry_object(pending[0])
        second = self._geometry_object(pending[1])
        self._pane_scene()._linear_algebra_pending_vector_ids = []
        if not isinstance(first, Linear2D) or not isinstance(second, Linear2D):
            return True
        self._clear_linear_algebra_tool_overlays()
        plan = self._build_linear_algebra_tool_plan(self._pane_scene()._active_linear_algebra_tool or "", (first, second))
        if plan is not None and self._apply_linear_algebra_tool_plan(plan):
            self.algebra_panel.set_status(f"已完成{self._pane_scene()._active_linear_algebra_tool}计算")
        elif plan is None:
            self._restore_linear_algebra_preclear_state()
            self.algebra_panel.set_status("所选向量不能用于该工具，请检查向量长度", is_error=True)
        self._select_geometry_object(None)
        return True

    def _handle_linear_algebra_polygon_click(self, x: float, y: float) -> bool:
        x, y = self._maybe_snap(x, y)
        before = self._capture_geometry_state()
        point, _created = self._get_or_create_geometry_point(x, y, record_history=False)
        pending = getattr(self._pane_scene(), "_linear_algebra_polygon_point_ids", [])
        if len(pending) >= 3 and point.id == pending[0]:
            return self._finish_linear_algebra_polygon(x, y)
        if point.id not in pending:
            pending.append(point.id)
            self._pane_scene()._linear_algebra_polygon_point_ids = pending
            self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已添加顶点 {point.name}，当前 {len(pending)} 个顶点；双击完成")
        self._pane_renderer().render()
        return True

    def _finish_linear_algebra_polygon(self, x: float, y: float) -> bool:
        pending = getattr(self._pane_scene(), "_linear_algebra_polygon_point_ids", [])
        if len(pending) < 3:
            self.algebra_panel.set_status("多边形至少需要三个顶点", is_error=True)
            return True
        points = [self._point_2d(point_id) for point_id in pending]
        if any(point is None for point in points):
            self._pane_scene()._linear_algebra_polygon_point_ids = []
            return True
        alias = self._next_linear_algebra_tool_alias("polygon")
        self._clear_linear_algebra_tool_overlays()
        plan = build_polygon_tool_plan(tuple(point for point in points if point is not None), alias)
        self._pane_scene()._linear_algebra_polygon_point_ids = []
        if self._apply_linear_algebra_tool_plan(plan):
            self.algebra_panel.set_status("已完成多边形")
        return True

    @staticmethod
    def _parse_linear_algebra_matrix(text: str) -> tuple[tuple[float, float], tuple[float, float]] | None:
        return parse_matrix(text)

    def _handle_linear_algebra_transform(self) -> bool:
        parent = getattr(self, "window", None)
        text, accepted = QInputDialog.getText(
            parent,
            "矩阵变换",
            "输入 2×2 矩阵（例如 1,0;0,1）：",
            QLineEdit.EchoMode.Normal,
            "1,0;0,1",
        )
        if not accepted:
            return True
        matrix = self._parse_linear_algebra_matrix(text)
        if matrix is None:
            self.algebra_panel.set_status("矩阵格式无效，请使用 a,b;c,d", is_error=True)
            return True
        self._clear_linear_algebra_tool_overlays()
        alias = self._next_linear_algebra_tool_alias("transform")
        points = [(point.x, point.y) for point in self._pane_scene().geometry_points] or [(1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        bounds = self._current_2d_bounds()
        plan = build_transform_tool_plan(matrix, points, bounds, alias)
        if self._apply_linear_algebra_tool_plan(plan):
            self.algebra_panel.set_status("已应用矩阵变换")
        return True

    def _set_snap_to_grid(self, enabled: bool) -> None:
        self._pane_scene()._snap_to_grid = bool(enabled)
        self.algebra_panel.set_status("已开启网格吸附" if enabled else "已关闭网格吸附")

    def _capture_geometry_state(self) -> _GeometryHistoryState:
        """复制当前几何状态，避免后续点移动修改历史快照。"""
        return _GeometryHistoryState(
            points=tuple(replace(point) for point in self._pane_scene().geometry_points),
            linears=tuple(replace(linear) for linear in self._pane_scene().linear_objects),
            object_order=tuple(self._pane_scene()._two_d_object_order),
            annotations=tuple(replace(a) for a in getattr(self._pane_scene(), "annotations", [])),
            curves=tuple(replace(c) for c in getattr(self._pane_scene(), "curve_layers", [])),
        )

    def _ensure_geometry_history(self) -> None:
        if not hasattr(self._pane_scene(), "_geometry_undo_stack"):
            self._pane_scene()._geometry_undo_stack = []
        if not hasattr(self._pane_scene(), "_geometry_redo_stack"):
            self._pane_scene()._geometry_redo_stack = []

    def _record_geometry_change(self, before: _GeometryHistoryState) -> None:
        if getattr(self._pane_scene(), "_scene_command_active", False):
            return
        # 手动操作发生在 AI 事务之后时，撤销应优先回退最新的手动操作。
        if getattr(self._pane_scene(), "_scene_command_undo_stack", []):
            self._pane_scene()._scene_command_undo_stack.clear()
            self._pane_scene()._scene_command_redo_stack.clear()
        self._ensure_geometry_history()
        after = self._capture_geometry_state()
        if before == after:
            return
        self._pane_scene()._geometry_undo_stack.append(before)
        pane_id = self._pane_scene().pane.pane_id
        self.pane_manager.push(
            pane_id,
            lambda b=before, p=pane_id: self._restore_geometry_state_for_pane(p, b),
            lambda a=after, p=pane_id: self._restore_geometry_state_for_pane(p, a),
            "二维场景",
        )

    def _restore_geometry_state_for_pane(self, pane_id: str, state: _GeometryHistoryState) -> None:
        with self._using_pane(pane_id):
            self._restore_geometry_state(state)
            self._pane_scene()._geometry_redo_stack.clear()
        self._update_geometry_history_controls()

    def _update_geometry_history_controls(self) -> None:
        can_undo = bool(getattr(self._pane_scene(), "_geometry_undo_stack", [])) or bool(
            getattr(self._pane_scene(), "_scene_command_undo_stack", [])
        )
        can_redo = bool(getattr(self._pane_scene(), "_geometry_redo_stack", [])) or bool(
            getattr(self._pane_scene(), "_scene_command_redo_stack", [])
        )
        for toolbar in (getattr(self, "two_d_geometry_toolbar", None),):
            if toolbar is None or not hasattr(toolbar, "set_history_state"):
                continue
            toolbar.set_history_state(
                can_undo=can_undo,
                can_redo=can_redo,
            )

    def _undo_2d_geometry(self) -> None:
        if self.pane_manager.undo():
            for state in self.pane_manager.panes.values():
                runtime = getattr(state, "runtime", None)
                if runtime is not None:
                    runtime._geometry_undo_stack.clear()
                    runtime._geometry_redo_stack.clear()
            self._update_geometry_history_controls()
            return
        if getattr(self._pane_scene(), "_scene_command_undo_stack", []):
            current = self._capture_scene_command_state()
            target = self._pane_scene()._scene_command_undo_stack.pop()
            self._pane_scene()._scene_command_redo_stack.append(current)
            self._restore_scene_command_state(target)
            self.algebra_panel.set_status("已撤回 AI 场景命令")
            self._update_geometry_history_controls()
            return
        self._ensure_geometry_history()
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or not self._pane_scene()._geometry_undo_stack:
            return
        current = self._capture_geometry_state()
        target = self._pane_scene()._geometry_undo_stack.pop()
        self._pane_scene()._geometry_redo_stack.append(current)
        self._restore_geometry_state(target)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已撤回二维几何操作")

    _undo_scene_command = _undo_2d_geometry

    def _redo_2d_geometry(self) -> None:
        if self.pane_manager.redo():
            for state in self.pane_manager.panes.values():
                runtime = getattr(state, "runtime", None)
                if runtime is not None:
                    runtime._geometry_undo_stack.clear()
                    runtime._geometry_redo_stack.clear()
            self._update_geometry_history_controls()
            return
        if getattr(self._pane_scene(), "_scene_command_redo_stack", []):
            current = self._capture_scene_command_state()
            target = self._pane_scene()._scene_command_redo_stack.pop()
            self._pane_scene()._scene_command_undo_stack.append(current)
            self._restore_scene_command_state(target)
            self.algebra_panel.set_status("已反撤回 AI 场景命令")
            self._update_geometry_history_controls()
            return
        self._ensure_geometry_history()
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or not self._pane_scene()._geometry_redo_stack:
            return
        current = self._capture_geometry_state()
        target = self._pane_scene()._geometry_redo_stack.pop()
        self._pane_scene()._geometry_undo_stack.append(current)
        self._restore_geometry_state(target)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已反撤回二维几何操作")

    def _restore_geometry_state(self, state: _GeometryHistoryState) -> None:
        """恢复几何对象并重建几何控制器，保持函数曲线和当前工具不变。"""
        self._pane_scene().geometry_points = [replace(point) for point in state.points]
        self._pane_scene().linear_objects = [replace(linear) for linear in state.linears]
        self._pane_scene().annotations = [replace(a) for a in state.annotations]
        self._pane_scene().curve_layers = [replace(c) for c in state.curves]
        self._pane_scene()._two_d_object_order = list(state.object_order)
        self._pane_scene()._pending_geometry_point_id = None
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._drag_moved = False
        self._pane_scene()._drag_start_geometry_state = None

        renderer = self._pane_renderer(required=False)
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if renderer is not None and controller is not None:
            controller.clear_draft()
            controller.set_hover(None)
            controller.set_selected(None)
            for object_id in [*controller.points, *controller.linears, *controller.annotations]:
                controller.remove_object(object_id)
            for point in self._pane_scene().geometry_points:
                controller.add_point(point)
            for linear in self._pane_scene().linear_objects:
                controller.add_linear(linear)
            for annotation in getattr(self._pane_scene(), "annotations", []):
                controller.add_annotation(annotation)
        curve_controller = getattr(self._pane_scene(), "curve_controller", None)
        if renderer is not None and curve_controller is not None:
            for layer_id in list(curve_controller.layers):
                curve_controller.remove_layer(layer_id)
            for layer in self._pane_scene().curve_layers:
                curve_controller.add_layer(layer)
        if self.pane_manager.active_pane_id == self._pane_scene().pane.pane_id:
            self.algebra_panel.set_layers(self._two_d_panel_layers())
            self.algebra_panel.set_selected_layer(None)
        if renderer is not None and callable(getattr(renderer, "render", None)):
            renderer.render()

    def _handle_geometry_mouse_press(self, event: QMouseEvent) -> bool:
        """处理被激活工具的左键单击；其他输入仍交给 PyVista。"""
        tool = self._pane_scene()._active_2d_tool
        linear_algebra_tool = getattr(self._pane_scene(), "_active_linear_algebra_tool", None)
        if (
            self._pane_scene().scene_mode is not SceneMode.TWO_D
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        if tool is None and linear_algebra_tool is None:
            return False
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        if linear_algebra_tool is not None:
            if linear_algebra_tool == "transform":
                handled = self._handle_linear_algebra_transform()
                if handled:
                    event.accept()
                return handled
            coordinates = self._maybe_snap(*coordinates)
            if linear_algebra_tool == "polygon":
                event.accept()
                return self._handle_linear_algebra_polygon_click(*coordinates)
            if linear_algebra_tool in {"angle", "projection", "subspace", "area"}:
                event.accept()
                return self._handle_linear_algebra_vector_click(*coordinates)
            return False
        if tool == "select":
            if self._begin_select_or_drag(*coordinates):
                return True
            scene = self._pane_scene()
            scene._selection_start = coordinates
            scene._selection_pixel_start = QPoint(int(event.position().x()), int(event.position().y()))
            surface = self._pane_renderer().interactor
            if isinstance(surface, QWidget):
                if scene._selection_band is None or not isValid(scene._selection_band):
                    scene._selection_band = QRubberBand(QRubberBand.Shape.Rectangle, surface)
                scene._selection_band.setGeometry(QRect(scene._selection_pixel_start, scene._selection_pixel_start))
                scene._selection_band.show()
            event.accept()
            return True
        coordinates = self._maybe_snap(*coordinates)
        before = self._capture_geometry_state()
        point, created = self._get_or_create_geometry_point(*coordinates, record_history=False)
        if tool == "point":
            self._record_geometry_change(before)
            self.algebra_panel.set_status(
                f"{'已创建' if created else '已复用'}点 {point.name}"
            )
            self._pane_renderer().render()
            event.accept()
            return True
        if self._pane_scene()._pending_geometry_point_id is None:
            self._pane_scene()._pending_geometry_point_id = point.id
            self._record_geometry_change(before)
            self.algebra_panel.set_status(
                f"已选择点 {point.name}，单击第二点创建{self._TOOL_LABELS[tool]}"
            )
            self._pane_renderer().render()
            event.accept()
            return True

        first = self._point_2d(self._pane_scene()._pending_geometry_point_id)
        if first is None:
            self._pane_scene()._pending_geometry_point_id = None
            return False
        if first.id == point.id:
            self.algebra_panel.set_status("请单击与第一个点不同的位置", is_error=True)
            event.accept()
            return True
        linear = self._create_linear_geometry(tool, first, point, record_history=False)
        self._pane_scene()._pending_geometry_point_id = None
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.clear_draft()
        if not getattr(self._pane_scene(), "_scene_command_active", False):
            self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已创建{self._TOOL_LABELS[tool]} {linear.name}")
        self._pane_renderer().render()
        event.accept()
        return True

    def _begin_select_or_drag(self, x: float, y: float) -> bool:
        """选择工具左键按下：命中对象则选中，命中点则准备拖动。"""
        if self._pane_scene().geometry_controller is None:
            return False
        hit_id = self._pane_scene().geometry_controller.hit_test(x, y, self._hit_tolerance())
        self._select_geometry_object(hit_id)
        self._pane_scene()._dragging_point_id = hit_id if hit_id in self._pane_scene().geometry_controller.points else None
        self._pane_scene()._drag_start_geometry_state = (
            self._capture_geometry_state() if self._pane_scene()._dragging_point_id is not None else None
        )
        self._pane_scene()._drag_moved = False
        self._pane_renderer().render()
        # 命中对象时拦截事件，避免触发相机平移；未命中则放行以便平移画布。
        return hit_id is not None

    def _handle_geometry_mouse_move(self, event: QMouseEvent) -> bool:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
            return False
        tool = self._pane_scene()._active_2d_tool
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        if tool == "select":
            if self._pane_scene()._selection_start is not None:
                scene = self._pane_scene()
                if scene._selection_band is not None and isValid(scene._selection_band):
                    position = QPoint(int(event.position().x()), int(event.position().y()))
                    scene._selection_band.setGeometry(QRect(scene._selection_pixel_start, position).normalized())
                event.accept()
                return True
            if self._pane_scene()._dragging_point_id is not None:
                snapped = self._maybe_snap(*coordinates)
                self._pane_scene().geometry_controller.move_point(self._pane_scene()._dragging_point_id, *snapped)
                point = self._point_2d(self._pane_scene()._dragging_point_id)
                if point is not None:
                    point.x, point.y = snapped
                    self.algebra_panel.sync_layer(point.id, point)
                self._pane_scene()._drag_moved = True
                self._pane_renderer().render()
                return True
            # 悬浮高亮：命中变化时才重绘。
            hit_id = self._pane_scene().geometry_controller.hit_test(*coordinates, self._hit_tolerance())
            if self._pane_scene().geometry_controller.set_hover(hit_id):
                cursor = (
                    Qt.CursorShape.OpenHandCursor
                    if hit_id in self._pane_scene().geometry_controller.points
                    else Qt.CursorShape.PointingHandCursor
                    if hit_id is not None
                    else Qt.CursorShape.ArrowCursor
                )
                self._pane_renderer().interactor.setCursor(cursor)
                self._pane_renderer().render()
            return False
        if (
            tool in {"line", "segment", "ray", "vector"}
            and self._pane_scene()._pending_geometry_point_id is not None
        ):
            first = self._point_2d(self._pane_scene()._pending_geometry_point_id)
            if first is not None:
                self._pane_scene().geometry_controller.set_draft(tool, first, self._maybe_snap(*coordinates))
                self._pane_renderer().render()
        return False

    def _handle_geometry_mouse_release(self, event: QMouseEvent) -> bool:
        scene = self._pane_scene()
        if scene._selection_start is not None:
            from services.scene_clipboard import rectangle_select
            end = self._viewport_to_world(event.position().x(), event.position().y())
            start, scene._selection_start = scene._selection_start, None
            if scene._selection_band is not None and isValid(scene._selection_band):
                scene._selection_band.hide()
            if end is not None:
                objects = (*scene.geometry_points, *scene.linear_objects, *scene.annotations, *scene.curve_layers)
                selected = rectangle_select(objects, (*start, *end))
                self._pane().selected_object_ids = [item.id for item in selected]
                self.algebra_panel.set_status(f"已选择 {len(selected)} 个对象，可复制到其他窗格")
            event.accept()
            return True
        if self._pane_scene()._dragging_point_id is None:
            return False
        point = self._point_2d(self._pane_scene()._dragging_point_id)
        if point is not None and self._pane_scene()._drag_moved:
            if self._pane_scene()._drag_start_geometry_state is not None:
                self._record_geometry_change(self._pane_scene()._drag_start_geometry_state)
            self.algebra_panel.set_status(f"已移动点 {point.name}")
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._drag_moved = False
        self._pane_scene()._drag_start_geometry_state = None
        return False

    def _handle_geometry_double_click(self, event: QMouseEvent) -> bool:
        linear_algebra_tool = getattr(self._pane_scene(), "_active_linear_algebra_tool", None)
        if (
            self._pane_scene().scene_mode is SceneMode.TWO_D
            and linear_algebra_tool == "polygon"
            and event.button() == Qt.MouseButton.LeftButton
        ):
            coordinates = self._viewport_to_world(event.position().x(), event.position().y())
            if coordinates is None:
                return False
            event.accept()
            return self._finish_linear_algebra_polygon(*self._maybe_snap(*coordinates))
        if (
            self._pane_scene().scene_mode is not SceneMode.TWO_D
            or self._pane_scene()._active_2d_tool != "select"
            or self._pane_scene().geometry_controller is None
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        hit_id = self._pane_scene().geometry_controller.hit_test(*coordinates, self._hit_tolerance())
        if hit_id is not None and hit_id in self._pane_scene().geometry_controller.points:
            self._select_geometry_object(hit_id)
            self._pane_renderer().render()
            self.algebra_panel.begin_geometry_edit(hit_id)
            event.accept()
            return True
        return False

    def _select_geometry_object(self, object_id: str | None) -> None:
        self._pane().selected_object_ids = [object_id] if object_id is not None else []
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.set_selected(object_id)
        self.algebra_panel.set_selected_layer(object_id)

    def _handle_geometry_key_press(self, event: QKeyEvent) -> bool:
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_Z:
            if modifiers == Qt.KeyboardModifier.ControlModifier:
                self._undo_2d_geometry()
                event.accept()
                return True
            if modifiers == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
                self._redo_2d_geometry()
                event.accept()
                return True
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self._pane_scene().geometry_controller.selected_id if self._pane_scene().geometry_controller else None
            if selected is not None and self._geometry_object(selected) is not None:
                self._remove_geometry_object(selected)
                event.accept()
                return True
            return False
        if key != Qt.Key.Key_Escape:
            return False
        if getattr(self._pane_scene(), "_active_linear_algebra_tool", None) is not None:
            self._pane_scene()._active_linear_algebra_tool = None
            self._pane_scene()._linear_algebra_pending_vector_ids = []
            self._pane_scene()._linear_algebra_polygon_point_ids = []
            self._set_2d_geometry_tool(None)
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool(None, emit_signal=False)
            self.algebra_panel.set_status("已返回平移模式")
            event.accept()
            return True
        if self._pane_scene()._active_2d_tool == "select" and self._pane_scene().geometry_controller is not None:
            self._select_geometry_object(None)
            self._pane_renderer().render()
            event.accept()
            return True
        if self._pane_scene()._active_2d_tool is None:
            return False
        self._set_2d_geometry_tool(None)
        if hasattr(self, "two_d_geometry_toolbar"):
            self.two_d_geometry_toolbar.set_active_tool(None, emit_signal=False)
        self.algebra_panel.set_status("已返回平移模式")
        event.accept()
        return True

    def _maybe_snap(self, x: float, y: float) -> tuple[float, float]:
        if not self._pane_scene()._snap_to_grid:
            return x, y
        spacing = self._pane_scene()._two_d_guide_spacing
        if spacing is None or spacing <= 0:
            return x, y
        # 吸附强度：仅当落点距最近网格线小于步长的 25% 时才对齐，避免"抢"走自由位置。
        threshold = spacing * 0.25
        snapped_x = round(x / spacing) * spacing
        snapped_y = round(y / spacing) * spacing
        result_x = snapped_x if abs(snapped_x - x) <= threshold else x
        result_y = snapped_y if abs(snapped_y - y) <= threshold else y
        return result_x, result_y

    def _hit_tolerance(self) -> float:
        return self._point_snap_tolerance()

    def _viewport_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float] | None:
        interactor = getattr(self._pane_renderer(), "interactor", None)
        if interactor is None:
            return None
        width = max(1, int(interactor.width()))
        height = max(1, int(interactor.height()))
        if not 0 <= screen_x <= width or not 0 <= screen_y <= height:
            return None
        bounds = self._current_2d_bounds()
        x = bounds.x_range[0] + float(screen_x) / width * bounds.x_span
        y = bounds.y_range[1] - float(screen_y) / height * bounds.y_span
        return x, y

    def _get_or_create_geometry_point(
        self,
        x: float,
        y: float,
        *,
        record_history: bool = True,
    ) -> tuple[Point2D, bool]:
        tolerance = self._point_snap_tolerance()
        for point in self._pane_scene().geometry_points:
            if (point.x - x) ** 2 + (point.y - y) ** 2 <= tolerance**2:
                return point, False
        before = self._capture_geometry_state()
        point = Point2D(self._next_point_name(), x, y)
        self._pane_scene().geometry_points.append(point)
        self._pane_scene()._two_d_object_order.append(point.id)
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.add_point(point)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        if record_history:
            self._record_geometry_change(before)
        return point, True

    def _create_linear_geometry(
        self,
        kind: LinearKind,
        start: Point2D,
        end: Point2D,
        *,
        record_history: bool = True,
    ) -> Linear2D:
        before = self._capture_geometry_state()
        linear = Linear2D(
            name=self._next_linear_name(kind),
            kind=kind,
            start_point_id=start.id,
            end_point_id=end.id,
        )
        self._pane_scene().linear_objects.append(linear)
        self._pane_scene()._two_d_object_order.append(linear.id)
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.add_linear(linear)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        if record_history:
            self._record_geometry_change(before)
        return linear

    def _point_snap_tolerance(self) -> float:
        interactor = getattr(self._pane_renderer(), "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        bounds = self._current_2d_bounds()
        return 12.0 * max(bounds.x_span / width, bounds.y_span / height)

    def _next_point_name(self) -> str:
        existing = {point.name for point in self._pane_scene().geometry_points}
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for index in range(10_000):
            name = alphabet[index % len(alphabet)]
            if index >= len(alphabet):
                name += str(index // len(alphabet))
            if name not in existing:
                return name
        raise RuntimeError("无法再创建更多二维点。")

    def _next_linear_name(self, kind: LinearKind) -> str:
        existing = {linear.name for linear in self._pane_scene().linear_objects}
        if kind == "line":
            alphabet = "abcdefghijklmnopqrstuvwxyz"
            for index in range(10_000):
                name = alphabet[index % len(alphabet)]
                if index >= len(alphabet):
                    name += str(index // len(alphabet))
                if name not in existing:
                    return name
        prefix = {"segment": "s", "ray": "r", "vector": "v"}[kind]
        for index in range(1, 10_000):
            name = f"{prefix}_{index}"
            if name not in existing:
                return name
        raise RuntimeError("无法再创建更多二维线对象。")

    def _save_current_view_state(self) -> None:
        if not (self._pane_renderer(required=False) is not None):
            return
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._pane_scene()._two_d_parallel_scale = float(self._pane_renderer().camera.parallel_scale)
            self._pane_scene()._two_d_camera_position = self._current_camera_position()
            self._pane().camera_2d = {
                "position": self._pane_scene()._two_d_camera_position,
                "parallel_scale": self._pane_scene()._two_d_parallel_scale,
            }
        else:
            self._pane_scene()._three_d_camera_position = self._current_camera_position()
            self._pane().camera_3d = {"position": self._pane_scene()._three_d_camera_position}

    def _set_scene_background(self, background: str) -> None:
        self._pane_scene().scene_appearances[self._pane_scene().scene_mode].background = background
        self._save_current_view_state()
        self._render_scene()

    def _set_axis_color_mode(self, axis_color_mode: str) -> None:
        self._pane_scene().scene_appearances[self._pane_scene().scene_mode].axis_color_mode = axis_color_mode
        self._save_current_view_state()
        self._render_scene()

    def _set_grid_visible(self, visible: bool) -> None:
        self._pane_scene().scene_appearances[SceneMode.TWO_D].show_grid = visible
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)

    def _set_ticks_visible(self, visible: bool) -> None:
        appearance = self._pane_scene().scene_appearances[self._pane_scene().scene_mode]
        appearance.show_ticks = visible
        self._save_current_view_state()
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing_mode(self, mode: str) -> None:
        appearance = self._pane_scene().scene_appearances[self._pane_scene().scene_mode]
        appearance.tick_spacing_mode = mode if mode in {"auto", "custom"} else "auto"
        self._save_current_view_state()
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing(self, spacing: float) -> None:
        if spacing <= 0:
            return
        self._pane_scene().scene_appearances[self._pane_scene().scene_mode].tick_spacing = float(spacing)
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_global_intersections_visible(self, visible: bool) -> None:
        self._pane_scene().scene_appearances[SceneMode.THREE_D].show_intersections = visible
        if self._pane_scene().scene_mode is SceneMode.THREE_D and self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_global_intersections_visible(visible)
            self._pane_renderer().render()

    def _toggle_agent_panel(self) -> None:
        if hasattr(self, "agent_sidebar") and self.agent_sidebar.state.value == "expanded":
            self._close_agent_panel()
        else:
            self._open_agent_panel()

    def _open_agent_panel(self) -> None:
        if self.scene_settings_panel.isVisible():
            self._close_scene_settings(immediate=True)
        self.agent_button.setChecked(True)
        self.agent_sidebar.show()
        self.agent_resize_handle.show()
        self.agent_sidebar.expand()
        self.agent_sidebar.select_tab("agent")
        self._root_layout.activate()
        self.agent_panel.view.setFocus()

    def _close_agent_panel(self, immediate: bool = False) -> None:
        self.agent_button.setChecked(False)
        self.agent_sidebar.collapse()
        self.agent_resize_handle.hide()
        self._root_layout.activate()

    def _show_agent_settings(self) -> None:
        dialog = getattr(self, "_agent_settings_dialog", None)
        if dialog is not None:
            # 重复点击设置按钮时只把已有对话框带到前面，避免多个窗口写同一份 QSettings。
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return
        dialog = AgentSettingsDialog(self.window, effective_theme=self.effective_theme)
        dialog.settings_saved.connect(self._apply_agent_settings)
        dialog.demo_requested.connect(self._restore_demo_agent)
        dialog.finished.connect(self._forget_agent_settings_dialog)
        self._agent_settings_dialog = dialog
        dialog.open()

    def _forget_agent_settings_dialog(self) -> None:
        dialog = getattr(self, "_agent_settings_dialog", None)
        self._agent_settings_dialog = None
        if dialog is not None:
            dialog.deleteLater()

    def _apply_agent_settings(self, settings: AgentSettings) -> None:
        self._agent_settings = settings
        self._agent_provider = self._create_agent_provider()
        self._agent_runtime = AgentRuntime(
            provider=self._agent_provider,
            command_service=SceneCommandService(self._scene_command_host_proxy.for_pane(locked_pane_id)),
            session_store=self._agent_session_store,
        )
        self._math_teacher_agent = self._agent_runtime.agent
        remote = self._using_remote_agent()
        self.agent_sidebar.set_model_status(settings.model, enabled=remote)
        if settings.provider != "local" and settings.is_complete and not remote:
            self.agent_panel.show_error(_provider_configuration_error(settings.provider))

    def _restore_demo_agent(self) -> None:
        # 只切换 provider；保留已填写的连接信息，方便随时切回远程模型。
        self._agent_provider = RuleBasedAgentProvider()
        self._agent_runtime = AgentRuntime(
            provider=self._agent_provider,
            command_service=self.scene_command_service,
            session_store=self._agent_session_store,
        )
        self._math_teacher_agent = self._agent_runtime.agent
        self.agent_sidebar.set_model_status("", enabled=False)

    def _build_scene_context(self) -> SceneContext:
        curves = tuple(
            {
                "alias": layer.agent_alias or layer.name,
                "kind": layer.kind,
                "expression": layer.expression,
            }
            for layer in self._pane_scene().curve_layers
        )
        point_aliases = {
            point.id: point.agent_alias or point.name
            for point in self._pane_scene().geometry_points
        }
        points = tuple(
            {
                "alias": point.agent_alias or point.name,
                "kind": "point",
                "coordinates": [point.x, point.y],
            }
            for point in self._pane_scene().geometry_points
        )
        linears = tuple(
            {
                "alias": linear.agent_alias or linear.name,
                "kind": linear.kind,
                "start": point_aliases.get(linear.start_point_id, linear.start_point_id),
                "end": point_aliases.get(linear.end_point_id, linear.end_point_id),
                "style": linear.style,
                "role": linear.role,
            }
            for linear in self._pane_scene().linear_objects
        )
        annotations = tuple(
            {
                "alias": annotation.agent_alias or annotation.name,
                "kind": "annotation",
                "text": annotation.text,
                "position": [annotation.x, annotation.y],
            }
            for annotation in self._pane_scene().annotations
        )
        surfaces = tuple(
            {
                "alias": layer.agent_alias or layer.name,
                "kind": layer.kind,
                "expression": layer.expression,
            }
            for layer in self._pane_scene().layers
        )
        points3d = tuple(
            {"alias": alias, "kind": "point3d", "coordinates": list(coordinates)}
            for alias, coordinates in getattr(self._pane_scene(), "_agent_points3d", {}).items()
        )
        return SceneContext(
            scene_mode="2d" if self._pane_scene().scene_mode is SceneMode.TWO_D else "3d",
            curves=curves + surfaces,
            geometry=points + linears + annotations + points3d,
            last_plan_summary=self._last_agent_plan_summary,
            panes=tuple(
                {"pane_id": pid, "name": pane.name, "source": pane.source, "scene_mode": pane.scene_mode}
                for pid, pane in getattr(self.pane_manager, "panes", {}).items()
            ),
            active_pane_id=getattr(self.pane_manager, "active_pane_id", None),
        )

    def _toggle_scene_settings(self) -> None:
        if self.agent_panel.isVisible():
            self._close_agent_panel(immediate=True)
        if self.scene_settings_panel.isVisible():
            self._close_scene_settings()
            return
        self._sync_scene_controls()
        target = self._scene_settings_target_geometry()
        start = QRect(self.viewport_host.width() + 4, target.y(), target.width(), target.height())
        self._scene_settings_closing = False
        self.scene_settings_panel.setGeometry(start)
        self.scene_settings_panel.show()
        self.scene_settings_panel.raise_()
        self._scene_settings_animation.stop()
        self._scene_settings_animation.setStartValue(start)
        self._scene_settings_animation.setEndValue(target)
        self._scene_settings_animation.start()

    def _close_scene_settings(self, immediate: bool = False) -> None:
        if not hasattr(self, "scene_settings_panel") or not self.scene_settings_panel.isVisible():
            return
        if immediate:
            self._scene_settings_animation.stop()
            self.scene_settings_panel.hide()
            self._scene_settings_closing = False
            return
        current = self.scene_settings_panel.geometry()
        end = QRect(self.viewport_host.width() + 4, current.y(), current.width(), current.height())
        self._scene_settings_closing = True
        self._scene_settings_animation.stop()
        self._scene_settings_animation.setStartValue(current)
        self._scene_settings_animation.setEndValue(end)
        self._scene_settings_animation.start()

    def _finish_scene_settings_animation(self) -> None:
        if self._scene_settings_closing:
            self.scene_settings_panel.hide()
            self._scene_settings_closing = False

    def _sync_scene_controls(self) -> None:
        if not hasattr(self, "scene_mode_button"):
            return
        appearance = self._pane_scene().scene_appearances[self._pane_scene().scene_mode]
        self.scene_mode_button.setText("2D" if self._pane_scene().scene_mode is SceneMode.TWO_D else "3D")
        if hasattr(self, "two_d_geometry_toolbar"):
            is_2d = self._pane_scene().scene_mode is SceneMode.TWO_D
            # The existing toolbar is the complete toolbar and is always
            # expanded. It stays visible in both scenes for discoverability.
            self.two_d_geometry_toolbar.set_linear_algebra_mode(True)
            # The unified toolbar is a persistent canvas affordance. It stays
            # visible even while the 3D scene is active so users can discover
            # the complete set of tools without opening another panel.
            self.two_d_geometry_toolbar.setVisible(True)
            if not is_2d:
                self.two_d_geometry_toolbar.line_flyout.hide()
        self.scene_settings_panel.set_mode(self._pane_scene().scene_mode)
        if hasattr(self, "agent_panel"):
            self.agent_panel.set_scene_mode(self._pane_scene().scene_mode is SceneMode.TWO_D)
        self.scene_settings_panel.set_values(
            background=appearance.background,
            axis_color_mode=appearance.axis_color_mode,
            grid=appearance.show_grid,
            ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            tick_spacing=appearance.tick_spacing,
            intersections=appearance.show_intersections,
        )

    def _is_linear_algebra_context(self) -> bool:
        """Check if current scene is in linear algebra context."""
        if getattr(self._pane_scene(), "scene_mode", None) is not SceneMode.TWO_D:
            return False
        topic_id = getattr(self, "_active_linear_algebra_topic_id", None)
        if not topic_id:
            return True
        try:
            topic = catalog_registry().get_topic(topic_id)
            recipe = catalog_registry().get_recipe(topic.visualization_id)
        except (KeyError, ValueError):
            return False
        return recipe.scene == "2d"

    def _show_lighting_dialog(self) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            return
        if self._lighting_dialog is None:
            self._lighting_dialog = LightingDialog(
                self._pane_scene().lighting,
                self._pane_scene().material_name,
                self.window,
                effective_theme=self.effective_theme,
            )
            self._lighting_dialog.setWindowModality(Qt.WindowModality.NonModal)
            self._lighting_dialog.settings_changed.connect(self._update_lighting)
            self._lighting_dialog.material_changed.connect(self._update_material)
            self._lighting_dialog.finished.connect(self._clear_lighting_dialog)
        self._lighting_dialog.show()
        self._lighting_dialog.raise_()
        self._lighting_dialog.activateWindow()

    def _clear_lighting_dialog(self, _result: int) -> None:
        self._lighting_dialog = None

    def _update_lighting(self, settings: LightSettings) -> None:
        self._pane_scene().lighting = settings
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            if self._pane_scene().layer_controller is not None:
                self._pane_scene().layer_controller.set_ambient(settings.ambient)
            update_lighting(self._pane_renderer(), settings)

    def _update_material(self, material_name: str) -> None:
        self._pane_scene().material_name = material_name
        if self._pane_scene().scene_mode is SceneMode.THREE_D and self._pane_scene().layer_controller is not None:
            self._pane_scene().layer_controller.set_material(material_name)
            self._pane_renderer().render()

    def _replace_layer(self, layer_id: str, **changes: object) -> None:
        self._pane_scene().layers = [replace(layer, **changes) if layer.id == layer_id else layer for layer in self._pane_scene().layers]
        self.algebra_panel.sync_layer(layer_id, self._layer(layer_id))

    def _replace_curve_layer(self, layer_id: str, **changes: object) -> None:
        self._pane_scene().curve_layers = [
            replace(layer, **changes) if layer.id == layer_id else layer for layer in self._pane_scene().curve_layers
        ]
        self.algebra_panel.sync_layer(layer_id, self._curve_layer(layer_id))

    def _two_d_panel_layers(self) -> list[CurveLayer | GeometryObject | Annotation2D]:
        objects: dict[str, CurveLayer | GeometryObject | Annotation2D] = {
            layer.id: layer for layer in self._pane_scene().curve_layers
        }
        objects.update({point.id: point for point in self._pane_scene().geometry_points})
        objects.update({linear.id: linear for linear in self._pane_scene().linear_objects})
        objects.update({annotation.id: annotation for annotation in self._pane_scene().annotations})
        for object_id in objects:
            if object_id not in self._pane_scene()._two_d_object_order:
                self._pane_scene()._two_d_object_order.append(object_id)
        return [
            objects[object_id]
            for object_id in self._pane_scene()._two_d_object_order
            if object_id in objects
        ]

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self._pane_scene().layers if layer.id == layer_id), None)

    def _curve_layer(self, layer_id: str) -> CurveLayer | None:
        return next((layer for layer in self._pane_scene().curve_layers if layer.id == layer_id), None)

    def _point_2d(self, point_id: str | None) -> Point2D | None:
        if point_id is None:
            return None
        return next((point for point in self._pane_scene().geometry_points if point.id == point_id), None)

    def _geometry_object(self, object_id: str) -> GeometryObject | None:
        point = self._point_2d(object_id)
        if point is not None:
            return point
        return next((linear for linear in self._pane_scene().linear_objects if linear.id == object_id), None)

    def _current_camera_position(self) -> list | None:
        if not self._pane_renderer(required=False):
            return None
        try:
            return [tuple(vector) for vector in self._pane_renderer().camera_position]
        except (AttributeError, TypeError):
            return None

    def _widget(self, name: str, widget_type: type[QWidget]) -> QWidget:
        widget = self.window.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Designer form is missing required widget: {name}")
        return widget

    def _apply_style(self) -> None:
        from ui.tokens import build_qss
        effective_theme = getattr(self, "effective_theme", "light")
        self.window.setStyleSheet(build_qss(effective_theme))
        self.window.effective_theme = effective_theme
        title_bar = getattr(self, "title_bar", None)
        if title_bar is not None:
            title_bar.set_theme(effective_theme)
        application = QApplication.instance()
        if application is not None:
            application.setProperty("math3d_effective_theme", effective_theme)
            for top_level in application.topLevelWidgets():
                apply_native_titlebar_theme(top_level, effective_theme)
        for widget in (
            getattr(self, "viewport_toolbar", None),
            getattr(self, "two_d_geometry_toolbar", None),
            getattr(getattr(self, "two_d_geometry_toolbar", None), "line_flyout", None),
            getattr(self, "scene_settings_panel", None),
        ):
            if widget is not None:
                apply_drop_shadow(widget, "overlay", effective_theme)
                # QSS cannot restyle a QIcon, so icons need an explicit repaint.
                retint_icons(widget, effective_theme)
        status_bar = getattr(self, "status_bar", None)
        if status_bar is not None and hasattr(status_bar, "set_theme"):
            status_bar.set_theme(effective_theme)
        two_d_toolbar = getattr(self, "two_d_geometry_toolbar", None)
        if two_d_toolbar is not None and hasattr(two_d_toolbar, "set_theme"):
            two_d_toolbar.set_theme(effective_theme)
        agent_settings_dialog = getattr(self, "_agent_settings_dialog", None)
        if agent_settings_dialog is not None:
            agent_settings_dialog.set_effective_theme(effective_theme)
            instructions_dialog = getattr(agent_settings_dialog, "_instructions_dialog", None)
            if instructions_dialog is not None:
                instructions_dialog.set_effective_theme(effective_theme)
        memory_dialog = getattr(getattr(self, "agent_sidebar", None), "_memory_dialog", None)
        if memory_dialog is not None:
            memory_dialog.set_effective_theme(effective_theme)
        lighting_dialog = getattr(self, "_lighting_dialog", None)
        if lighting_dialog is not None:
            lighting_dialog.set_effective_theme(effective_theme)
        algebra_panel = getattr(self, "algebra_panel", None)
        if algebra_panel is not None:
            algebra_panel.sync_overlay_theme(effective_theme)

    def set_theme(self, mode: ThemeMode, effective: EffectiveTheme) -> None:
        """Apply and propagate the resolved application theme."""
        self.theme_mode = mode
        self.effective_theme = effective
        if hasattr(self, "window"):
            self.window.effective_theme = effective
        from PySide6.QtCore import QSettings

        settings = QSettings()
        settings.setValue("ui/theme", mode)
        settings.sync()
        if hasattr(self, "window"):
            self._apply_style()
        if hasattr(self, "status_bar"):
            self.status_bar.set_theme_mode(mode)
        # Theme-aware surfaces are optional so this remains compatible with
        # lightweight test doubles and older embedded hosts.
        for surface in (
            getattr(self, "agent_panel", None),
            getattr(self, "agent_sidebar", None),
            self._pane_renderer(required=False),
        ):
            callback = getattr(surface, "set_theme", None)
            if callable(callback):
                try:
                    parameters = inspect.signature(callback).parameters
                except (TypeError, ValueError):
                    parameters = None
                if parameters is None:
                    callback(effective)
                elif "effective" in parameters:
                    callback(effective=effective)
                elif "theme" in parameters:
                    callback(theme=effective)
                elif parameters:
                    callback(effective)
                else:
                    callback()
        active_appearance = getattr(self._pane_scene(), "scene_appearances", {}).get(
            getattr(self._pane_scene(), "scene_mode", SceneMode.THREE_D)
        )
        if (
            active_appearance is not None
            and active_appearance.background == "auto"
            and self._pane_renderer(required=False) is not None
        ):
            self._render_scene()

    def show(self) -> None:
        self.window.show()
