"""用于组合相互独立二维/三维公式场景的主窗口。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import time
from uuid import uuid4
from pathlib import Path

from collections import deque
from collections.abc import Callable
import inspect
from typing import Literal

from PySide6.QtCore import QEasingCurve, QEvent, QFile, QIODevice, QObject, QPropertyAnimation, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent, QShortcut, QWheelEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton, QVBoxLayout, QWidget
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
from models.linear_algebra_cases import LinearAlgebraCase, linear_algebra_case
from models.scene_mode import SceneAppearance, SceneMode
from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.axis import ThreeDAxes, add_cartesian_axes
from rendering.curve_scene import CurveRenderError, CurveSceneController
from rendering.geometry_scene import GeometrySceneController
from rendering.layer_scene import LayerRenderError, LayerSceneController
from rendering.lighting import LightSettings
from rendering.scene import build_scene, configure_3d_camera_interaction, update_lighting
from rendering.ticks import ViewportBounds, tick_spacing, visible_2d_bounds, visible_3d_axis_extent
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from ui.algebra_panel import AlgebraPanel
from ui.agent_sidebar import AgentSidebar
from ui.agent_settings import AgentSettingsDialog
from ui.lighting_dialog import LightingDialog
from ui.scene_settings import SceneSettingsPanel
from ui.two_d_tools import ToolKind, TwoDGeometryToolbar
from services.agent_worker import RuntimeTurnWorker
from services.agent_provider import (
    AgentSettings,
    AgentMessage,
    AgentResponse,
    OpenAICompatibleProvider,
    SceneContext,
)
from services.scene_commands import CommandError, CommandPlan, RuleBasedAgentProvider, SceneCommandService
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

    def __init__(self, bridge: _SceneCommandBridge) -> None:
        self._bridge = bridge

    def _invoke(self, method: str, *args: object) -> None:
        request = _SceneCommandRequest(method, tuple(args))
        if QThread.currentThread() == self._bridge.thread():
            self._bridge._dispatch(request)
        else:
            self._bridge.request.emit(request)
        if request.error is not None:
            raise request.error

    def begin_scene_command_transaction(self) -> None:
        self._invoke("begin_scene_command_transaction")

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self._invoke("apply_scene_command", operation)

    def commit_scene_command_transaction(self) -> None:
        self._invoke("commit_scene_command_transaction")

    def rollback_scene_command_transaction(self) -> None:
        self._invoke("rollback_scene_command_transaction")

    def check_scene_fingerprint(self, expected: str) -> bool:
        request = _SceneCommandRequest("check_scene_fingerprint", (expected,))
        if QThread.currentThread() == self._bridge.thread():
            self._bridge._dispatch(request)
        else:
            self._bridge.request.emit(request)
        if request.error is not None:
            raise request.error
        return bool(request.result)

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


class _GeometryInputFilter(QObject):
    """拦截二维定点缩放和激活工具的视口鼠标、键盘事件。"""

    def __init__(self, owner: "MainWindow", parent: QObject) -> None:
        super().__init__(parent)
        self.owner = owner

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
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


class MainWindow:
    """加载 Designer 窗口骨架，并协调两个相互独立的绘图工作区。"""

    def __init__(
        self,
        theme_mode: ThemeMode = "system",
        effective_theme: EffectiveTheme = "light",
    ) -> None:
        self.theme_mode = theme_mode
        self.effective_theme = effective_theme
        self.lighting = LightSettings()
        self.material_name = "光泽塑料"
        self._lighting_dialog: LightingDialog | None = None
        self.scene_mode = SceneMode.THREE_D
        self.plot_domain = PlotDomain()
        self.curve_domain = Plot2DDomain()
        self.latex_parser = LatexParser()
        self.layers: list[SurfaceLayer] = [create_builtin_layer(DEFAULT_BUILTIN_ID)]
        self.curve_layers: list[CurveLayer] = []
        self.geometry_points: list[Point2D] = []
        self.linear_objects: list[Linear2D] = []
        self.annotations: list[Annotation2D] = []
        self._agent_areas: dict[str, dict[str, object]] = {}
        self._agent_points3d: dict[str, tuple[float, float, float]] = {}
        self._two_d_object_order: list[str] = []
        self.layer_controller: LayerSceneController | None = None
        self.curve_controller: CurveSceneController | None = None
        self.geometry_controller: GeometrySceneController | None = None
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
        self._scene_settings_closing = False
        self._active_2d_tool: ToolKind | None = None
        self._pending_geometry_point_id: str | None = None
        # Preserve the exact cursor coordinate unless grid snapping is enabled.
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
        self._agent_event_relay = _AgentEventRelay(self._receive_runtime_event, self.window)
        self._install_algebra_panel()
        self._configure_viewport()
        self._install_agent_panel()
        self._bind_algebra_panel()
        self._apply_style()
        self._render_scene()

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

    def _install_agent_panel(self) -> None:
        """将 AI 助手作为主窗口最右侧的固定布局面板安装。"""
        root_layout = self.window.findChild(QHBoxLayout, "rootLayout")
        if root_layout is None:
            raise RuntimeError("Designer form must use a horizontal root layout")
        self._root_layout = root_layout
        self.agent_sidebar = AgentSidebar(self.window, dispatcher=self._dispatch_agent_web_intent)
        self.agent_sidebar.setFixedWidth(440)
        self.agent_panel = self.agent_sidebar.expanded_panel
        root_layout.addWidget(self.agent_sidebar)
        # Sidebar 默认隐藏，关闭时不占用主视口布局空间。
        self.agent_sidebar.hide()
        self.agent_sidebar.set_model_status(
            self._agent_settings.model,
            enabled=self._using_remote_agent(),
        )
        self.agent_panel.set_scene_mode(self.scene_mode is SceneMode.TWO_D)

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
        self.plotter = QtInteractor(self.viewport_host)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.plotter.interactor.setMouseTracking(True)
        layout.addWidget(self.plotter.interactor)

        self.viewport_toolbar = QFrame(self.viewport_host)
        self.viewport_toolbar.setObjectName("viewportToolbar")
        toolbar_layout = QVBoxLayout(self.viewport_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)
        self.scene_settings_button = QToolButton(self.viewport_toolbar)
        self.scene_settings_button.setText("⚙")
        self.scene_settings_button.setToolTip("场景设置")
        self.scene_settings_button.setFixedSize(38, 38)
        self.scene_mode_button = QToolButton(self.viewport_toolbar)
        self.scene_mode_button.setToolTip("切换二维和三维场景")
        self.scene_mode_button.setFixedSize(38, 38)
        self.agent_button = QToolButton(self.viewport_toolbar)
        self.agent_button.setObjectName("agentButton")
        self.agent_button.setText("✦")
        self.agent_button.setToolTip("AI 教学助手")
        self.agent_button.setCheckable(True)
        self.agent_button.setFixedSize(38, 38)
        toolbar_layout.addWidget(self.scene_settings_button)
        toolbar_layout.addWidget(self.scene_mode_button)
        toolbar_layout.addWidget(self.agent_button)
        self.viewport_toolbar.adjustSize()

        self.two_d_geometry_toolbar = TwoDGeometryToolbar(self.viewport_host)

        self.scene_settings_panel = SceneSettingsPanel(self.viewport_host)
        self.scene_settings_panel.hide()
        self._scene_settings_animation = QPropertyAnimation(self.scene_settings_panel, b"geometry", self.window)
        self._scene_settings_animation.setDuration(180)
        self._scene_settings_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scene_settings_animation.finished.connect(self._finish_scene_settings_animation)
        self._viewport_resize_filter = _ViewportResizeFilter(self._on_viewport_host_changed, self.viewport_host)
        self.viewport_host.installEventFilter(self._viewport_resize_filter)
        self._position_viewport_overlays()
        self.scene_settings_button.clicked.connect(self._toggle_scene_settings)
        self.scene_mode_button.clicked.connect(self._toggle_scene_mode)
        self.agent_button.clicked.connect(self._toggle_agent_panel)
        self.two_d_geometry_toolbar.tool_selected.connect(self._set_2d_geometry_tool)
        self.two_d_geometry_toolbar.snap_toggled.connect(self._set_snap_to_grid)
        self.two_d_geometry_toolbar.undo_requested.connect(self._undo_2d_geometry)
        self.two_d_geometry_toolbar.redo_requested.connect(self._redo_2d_geometry)
        self._configure_2d_history_shortcuts()
        self.scene_settings_panel.background_changed.connect(self._set_scene_background)
        self.scene_settings_panel.axis_color_mode_changed.connect(self._set_axis_color_mode)
        self.scene_settings_panel.grid_changed.connect(self._set_grid_visible)
        self.scene_settings_panel.ticks_changed.connect(self._set_ticks_visible)
        self.scene_settings_panel.tick_spacing_mode_changed.connect(self._set_tick_spacing_mode)
        self.scene_settings_panel.tick_spacing_changed.connect(self._set_tick_spacing)
        self.scene_settings_panel.intersections_changed.connect(self._set_global_intersections_visible)
        self.scene_settings_panel.lighting_requested.connect(self._show_lighting_dialog)
        self._viewport_refresh_timer = QTimer(self.window)
        self._viewport_refresh_timer.setSingleShot(True)
        self._viewport_refresh_timer.setInterval(130)
        self._viewport_refresh_timer.timeout.connect(self._refresh_visible_viewport)
        interactor = getattr(self.plotter, "iren", None)
        if interactor is not None:
            try:
                self._viewport_interaction_observer = interactor.add_observer(
                    "EndInteractionEvent", self._on_viewport_interaction_finished
                )
                self._viewport_motion_observer = interactor.add_observer(
                    "InteractionEvent", self._on_viewport_interacting
                )
            except (AttributeError, RuntimeError, TypeError):
                self._viewport_interaction_observer = None
                self._viewport_motion_observer = None
        self._geometry_input_filter = _GeometryInputFilter(self, self.plotter.interactor)
        self.plotter.interactor.installEventFilter(self._geometry_input_filter)
        self._update_geometry_history_controls()
        self._sync_scene_controls()

    def _configure_2d_history_shortcuts(self) -> None:
        """注册主窗口级二维几何撤回快捷键，避免依赖当前控件焦点。"""
        self._undo_2d_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self.window)
        self._redo_2d_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self.window)
        for shortcut in (self._undo_2d_shortcut, self._redo_2d_shortcut):
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._undo_2d_shortcut.activated.connect(self._undo_2d_geometry)
        self._redo_2d_shortcut.activated.connect(self._redo_2d_geometry)

    def _on_viewport_host_changed(self) -> None:
        self._position_viewport_overlays()
        self._queue_viewport_refresh()

    def _handle_viewport_wheel(self, event: QWheelEvent) -> bool:
        """二维场景按鼠标位置缩放，保持光标下的世界坐标不变。"""
        if self.scene_mode is not SceneMode.TWO_D:
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
        if self.scene_mode is not SceneMode.TWO_D or factor <= 0:
            return False
        interactor = getattr(self.plotter, "interactor", None)
        camera = getattr(self.plotter, "camera", None)
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
        if self.scene_mode is not SceneMode.TWO_D or self._viewport_refreshing:
            return
        try:
            visible = self._current_2d_bounds()
        except Exception:
            return
        # 允许只构造了视口字段的测试替身继续使用平移预取逻辑。
        if not hasattr(self, "scene_appearances"):
            current = time.monotonic()
            if current - getattr(self, "_last_interaction_refresh_time", 0.0) < 0.05:
                return
            cached_bounds = getattr(self, "_two_d_sample_bounds", None)
            if cached_bounds is not None and self._needs_2d_prefetch(visible, cached_bounds):
                self._last_interaction_refresh_time = current
                self._refresh_2d_viewport(resample=True, render=True)
            return
        appearance = self.scene_appearances[SceneMode.TWO_D]
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            previous_spacing=self._two_d_guide_spacing,
        )
        spacing_changed = (
            self._two_d_guide_spacing is None
            or abs(spacing - self._two_d_guide_spacing) > self._two_d_guide_spacing * 1e-9
        )
        # 缩放时 spacing 必定改变，立即重建网格和重采样曲线，无节流。
        if spacing_changed:
            self._last_interaction_refresh_time = time.monotonic()
            self._refresh_2d_viewport(resample=True, render=True)
            return
        # 平移时 spacing 不变，采用节流策略，只在接近边缘时补绘网格。
        current = time.monotonic()
        if current - self._last_interaction_refresh_time < 0.05:
            return
        cached_bounds = getattr(self, "_two_d_sample_bounds", None)
        if cached_bounds is None:
            return
        if self._needs_2d_prefetch(visible, cached_bounds):
            self._last_interaction_refresh_time = current
            self._refresh_2d_viewport(resample=True, render=True)

    def _queue_viewport_refresh(self) -> None:
        # 采用去抖（debounce）而非节流：每次交互事件都重启定时器，
        # 只有用户停止缩放/旋转后才触发一次重采样。这样缩放过程中曲面
        # 不会中途重建，避免卡顿与网格密度突变导致的视觉跳跃。
        if self._viewport_refreshing or self._viewport_refresh_timer is None:
            return
        self._viewport_refresh_pending = True
        self._viewport_refresh_timer.start()

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
        mode = getattr(self, "scene_mode", SceneMode.THREE_D)
        panel.set_scene_mode(mode)
        panel.set_catalog_entries(catalog_entries(mode))
        panel.set_builtin_surfaces((surface.id, surface.name) for surface in BUILTIN_SURFACES)
        panel.add_requested.connect(self._add_formula_for_scene)
        panel.catalog_requested.connect(self._add_catalog_entry)
        panel.linear_algebra_requested.connect(self._load_linear_algebra_case)
        panel.builtin_requested.connect(self._add_builtin_surface)
        panel.lighting_requested.connect(self._show_lighting_dialog)
        panel.update_requested.connect(self._update_formula_for_scene)
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

    # ------------------------------------------------------------------
    # AI 场景命令适配层
    # ------------------------------------------------------------------

    def _request_agent_plan(self, prompt: str, *, session_id: str | None = None) -> None:
        if self._agent_thread is not None and self._agent_thread.isRunning():
            return
        active_session_id = session_id or self.agent_panel.active_session_id
        turn_id = uuid4().hex
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
        if result.turn_id and result.status == "completed":
            self._agent_session_store.update_turn_scene_snapshots(
                result.turn_id,
                scene_after=self._scene_snapshot_from_current_state(),
                status=result.status,
            )

    def _receive_runtime_error(self, message: str) -> None:
        self.agent_sidebar.set_busy(False)
        self.agent_panel.show_error(message)

    def _agent_finished(self) -> None:
        self._agent_thread = None
        self._agent_worker = None

    def begin_scene_command_transaction(self) -> None:
        self._scene_command_snapshot = self._capture_scene_command_state()
        self._scene_command_active = True

    def check_scene_fingerprint(self, expected: str) -> bool:
        return self._scene_snapshot_from_current_state().fingerprint() == expected

    def commit_scene_command_transaction(self) -> None:
        if not self._scene_command_active or self._scene_command_snapshot is None:
            return
        after = self._capture_scene_command_state()
        if after != self._scene_command_snapshot:
            self._scene_command_undo_stack.append(self._scene_command_snapshot)
            self._scene_command_redo_stack.clear()
        self._scene_command_snapshot = None
        self._scene_command_active = False
        self._sync_panel_layers(self.layers if self.scene_mode is SceneMode.THREE_D else self._two_d_panel_layers())
        self._update_geometry_history_controls()
        self.plotter.render()

    def rollback_scene_command_transaction(self) -> None:
        snapshot = self._scene_command_snapshot
        self._scene_command_snapshot = None
        self._scene_command_active = False
        if snapshot is not None:
            self._restore_scene_command_state(snapshot)
        self._update_geometry_history_controls()

    def _capture_scene_command_state(self) -> _SceneCommandState:
        return _SceneCommandState(
            points=tuple(replace(point) for point in self.geometry_points),
            linears=tuple(replace(linear) for linear in self.linear_objects),
            annotations=tuple(replace(annotation) for annotation in self.annotations),
            curves=tuple(replace(layer, parameters=dict(layer.parameters)) for layer in self.curve_layers),
            object_order=tuple(self._two_d_object_order),
            surfaces=tuple(replace(layer, parameters=dict(layer.parameters)) for layer in self.layers),
            scene_mode=self.scene_mode,
            points3d=tuple((alias, tuple(coordinates)) for alias, coordinates in getattr(self, "_agent_points3d", {}).items()),
            areas=tuple((alias, dict(operation)) for alias, operation in getattr(self, "_agent_areas", {}).items()),
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
        return self._scene_snapshot_from_state(self._capture_scene_command_state())

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
        )

    def _restore_agent_scene_snapshot(self, snapshot: SceneSnapshot) -> None:
        self._restore_scene_command_state(self._state_from_scene_snapshot(snapshot))

    def _restore_scene_command_state(self, state: _SceneCommandState) -> None:
        self.geometry_points = [replace(point) for point in state.points]
        self.linear_objects = [replace(linear) for linear in state.linears]
        self.annotations = [replace(annotation) for annotation in state.annotations]
        self.curve_layers = [replace(layer, parameters=dict(layer.parameters)) for layer in state.curves]
        self.layers = [replace(layer, parameters=dict(layer.parameters)) for layer in state.surfaces]
        self._two_d_object_order = list(state.object_order)
        self._agent_points3d = {alias: tuple(coordinates) for alias, coordinates in state.points3d}
        self._agent_areas = {alias: dict(operation) for alias, operation in state.areas}
        if self.scene_mode is not state.scene_mode:
            self._set_scene_mode(state.scene_mode)
        else:
            self._render_scene()

    def _rebuild_2d_controllers(self) -> None:
        if self.scene_mode is not SceneMode.TWO_D:
            return
        old_curve_controller = getattr(self, "curve_controller", None)
        if old_curve_controller is not None:
            for layer_id in list(old_curve_controller.layers):
                old_curve_controller.remove_layer(layer_id)
        old_geometry_controller = getattr(self, "geometry_controller", None)
        if old_geometry_controller is not None:
            for object_id in [*old_geometry_controller.points, *old_geometry_controller.linears, *old_geometry_controller.annotations]:
                old_geometry_controller.remove_object(object_id)
        visible = self._current_2d_bounds()
        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        self.curve_domain = self._curve_sampling_domain(sampling_bounds)
        self.curve_controller = CurveSceneController(self.plotter, self.curve_domain)
        self.geometry_controller = GeometrySceneController(self.plotter, visible)
        for layer in self.curve_layers:
            self.curve_controller.add_layer(layer)
        for point in self.geometry_points:
            self.geometry_controller.add_point(point)
        for linear in self.linear_objects:
            self.geometry_controller.add_linear(linear)
        for annotation in getattr(self, "annotations", []):
            self.geometry_controller.add_annotation(annotation)
        self.algebra_panel.set_layers(self._two_d_panel_layers())

    def apply_scene_command(self, operation: dict[str, object]) -> None:
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
        if name == "point.upsert":
            self._command_upsert_point(operation)
            return
        if name == "linear.upsert":
            self._command_upsert_linear(operation)
            return
        if name == "annotation.upsert":
            self._command_upsert_annotation(operation)
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
            self.plotter.screenshot(str(self._managed_export_path(filename)))
            return
        if name == "geometry.intersection":
            self._command_intersection(operation)
            return
        if name.startswith("linear_algebra.") or name.startswith("calculus."):
            raise CommandError(f"宿主收到未展开的教学命令: {name}")
        raise CommandError(f"宿主不支持操作: {name}")

    def _command_clear_scope(self, scope: str) -> None:
        if scope not in {"all", "curves", "surfaces", "geometry", "annotations"}:
            raise CommandError("scene.clear.scope 不受支持。")
        if scope == "all":
            self.layers.clear()
            self._agent_points3d = {}
        if self.scene_mode is SceneMode.THREE_D:
            if scope in {"all", "surfaces"}:
                self.layers.clear()
            if scope in {"all", "geometry", "surfaces"}:
                self._agent_points3d = {}
            self._render_scene()
            return
        if scope in {"all", "geometry"}:
            self.geometry_points.clear()
            self.linear_objects.clear()
            self._agent_areas = {}
        if scope in {"all", "annotations"}:
            self.annotations.clear()
        if scope in {"all", "curves"}:
            self.curve_layers.clear()
        remaining_ids = {
            *(point.id for point in self.geometry_points),
            *(linear.id for linear in self.linear_objects),
            *(annotation.id for annotation in self.annotations),
            *(layer.id for layer in self.curve_layers),
        }
        self._two_d_object_order = [item_id for item_id in self._two_d_object_order if item_id in remaining_ids]
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
        point = next((item for item in self.geometry_points if item.agent_alias == alias), None)
        if point is None:
            point = Point2D(str(operation.get("name", alias)), *coordinates, agent_alias=alias)
            self.geometry_points.append(point)
            self._two_d_object_order.append(point.id)
            if self.geometry_controller is not None:
                self.geometry_controller.add_point(point)
        else:
            point.x, point.y = coordinates
            if self.geometry_controller is not None:
                self.geometry_controller.move_point(point.id, *coordinates)

    def _command_upsert_linear(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        start = self._command_point_alias(str(operation["start"]))
        end = self._command_point_alias(str(operation["end"]))
        linear = next((item for item in self.linear_objects if item.agent_alias == alias), None)
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
            self.linear_objects.append(linear)
            self._two_d_object_order.append(linear.id)
        else:
            linear.start_point_id = start.id
            linear.end_point_id = end.id
            linear.kind = str(operation["kind"])  # type: ignore[assignment]
            linear.color = kwargs["color"]
            linear.style = kwargs["style"]  # type: ignore[assignment]
            linear.role = kwargs["role"]  # type: ignore[assignment]
            linear.label = kwargs["label"]
        if self.geometry_controller is not None:
            self.geometry_controller.linears.pop(linear.id, None)
            self.geometry_controller.add_linear(linear)

    def _command_upsert_annotation(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        x, y = (float(value) for value in operation["position"])  # type: ignore[index]
        annotation = next((item for item in self.annotations if item.agent_alias == alias), None)
        if annotation is None:
            annotation = Annotation2D(
                str(operation.get("name", alias)), str(operation["text"]), x, y,
                latex=operation.get("latex"), color=str(operation.get("color", "#263241")), agent_alias=alias,
            )
            self.annotations.append(annotation)
            self._two_d_object_order.append(annotation.id)
        else:
            annotation.text = str(operation["text"])
            annotation.x, annotation.y = x, y
        if self.geometry_controller is not None:
            self.geometry_controller.annotations.pop(annotation.id, None)
            self.geometry_controller.add_annotation(annotation)

    def _command_create_curve(self, operation: dict[str, object]) -> None:
        if self.curve_controller is None:
            raise CommandError("二维曲线控制器尚未初始化。")
        kind = str(operation["kind"])
        expression = str(operation["expression"])
        formula, parsed = self._parse_mathlive_curve(expression, kind)
        layer = CurveLayer(
            str(operation.get("name", operation["alias"])), parsed.kind, parsed.source,
            latex=formula.latex, parameters={name: 1.0 for name in parsed.parameter_names},
            color=str(operation.get("color", "#2777b6")), agent_alias=str(operation["alias"]),
        )
        self.curve_controller.add_layer(layer)
        self.curve_layers.append(layer)
        self._two_d_object_order.append(layer.id)

    def _command_create_surface(self, operation: dict[str, object]) -> None:
        """把 3D Skill 的曲面命令交给现有 CAS + LayerSceneController。"""
        if self.scene_mode is not SceneMode.THREE_D or self.layer_controller is None:
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
            self.layer_controller.add_layer(layer)
        except (ExpressionError, LayerRenderError, LatexParseError, ValueError) as error:
            raise CommandError(f"无法创建曲面: {error}") from error
        self.layers.append(layer)
        self._sync_panel_layers(self.layers)
        self.plotter.render()

    def _command_update_surface(self, operation: dict[str, object]) -> None:
        if self.scene_mode is not SceneMode.THREE_D or self.layer_controller is None:
            raise CommandError("更新曲面需要处于三维场景。")
        alias = str(operation["alias"])
        current = next((item for item in self.layers if item.agent_alias == alias), None)
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
            self.layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError, LatexParseError, ValueError) as error:
            raise CommandError(f"无法更新曲面: {error}") from error
        self.layers = [updated if item.id == current.id else item for item in self.layers]
        self._sync_panel_layers(self.layers)
        self.plotter.render()

    def _command_fill_area(self, operation: dict[str, object]) -> None:
        if self.scene_mode is not SceneMode.TWO_D:
            raise CommandError("积分面积演示需要处于二维场景。")
        expression = dict(operation)
        alias = str(operation["alias"])
        areas = getattr(self, "_agent_areas", {})
        areas[alias] = expression
        self._agent_areas = areas
        self._render_agent_areas()

    def _render_agent_areas(self) -> None:
        if self.scene_mode is not SceneMode.TWO_D:
            return
        import numpy as np
        import pyvista as pv
        import sympy as sp
        from geometry.cas_curve import parse_curve_expression

        areas = getattr(self, "_agent_areas", {})
        for alias in areas:
            self.plotter.remove_actor(f"agent-area:{alias}", render=False)
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
                self.plotter.add_mesh(
                    mesh,
                    name=f"agent-area:{alias}",
                    color=str(operation.get("color", "#7c5ce3")),
                    opacity=float(operation.get("opacity", 0.24)),
                    show_edges=False,
                )
            except Exception:
                # 曲线本身仍由 CurveSceneController 渲染；面积失败不会破坏事务。
                continue
        self.plotter.render()

    def _command_upsert_point3d(self, operation: dict[str, object]) -> None:
        """在 3D 视口中用一个受控球体表示点。

        点的坐标数据放在宿主的 ``_agent_points3d`` 中，渲染仍由宿主统一
        通过 PyVista 执行，Agent/Skill 本身不会接触绘图器。
        """
        if self.scene_mode is not SceneMode.THREE_D:
            raise CommandError("三维点需要处于三维场景。")
        try:
            coordinates = tuple(float(value) for value in operation["coordinates"])  # type: ignore[index]
            if len(coordinates) != 3:
                raise ValueError("三维点需要三个坐标")
        except (TypeError, ValueError) as error:
            raise CommandError("三维点坐标无效。") from error
        points = getattr(self, "_agent_points3d", {})
        alias = str(operation["alias"])
        points[alias] = coordinates
        self._agent_points3d = points
        self._render_agent_points3d()

    def _render_agent_points3d(self) -> None:
        if self.scene_mode is not SceneMode.THREE_D:
            return
        import pyvista as pv

        for alias in getattr(self, "_agent_points3d", {}):
            self.plotter.remove_actor(f"agent-point:{alias}", render=False)
        for alias, coordinates in getattr(self, "_agent_points3d", {}).items():
            mesh = pv.Sphere(radius=0.08, center=coordinates, theta_resolution=16, phi_resolution=8)
            self.plotter.add_mesh(mesh, name=f"agent-point:{alias}", color="#d64545")
        self.plotter.render()

    def _command_intersection(self, operation: dict[str, object]) -> None:
        first = str(operation["first"])
        second = str(operation["second"])
        if self.scene_mode is SceneMode.THREE_D and self.layer_controller is not None:
            first_layer = next((item for item in self.layers if item.agent_alias == first or item.id == first), None)
            second_layer = next((item for item in self.layers if item.agent_alias == second or item.id == second), None)
            if first_layer is None or second_layer is None:
                raise CommandError("交集计算需要两个已存在的曲面别名。")
            self.layer_controller.set_manual_intersection_pair(first_layer.id, second_layer.id, True)
            self.plotter.render()
            return
        raise CommandError("当前交集工具只支持三维曲面。")

    def _command_update_curve(self, operation: dict[str, object]) -> None:
        alias = str(operation["alias"])
        layer = next((item for item in self.curve_layers if item.agent_alias == alias), None)
        if layer is None:
            raise CommandError(f"未知曲线别名: {alias}")
        updated = replace(layer, kind=str(operation["kind"]), expression=str(operation["expression"]))
        if self.curve_controller is not None:
            self.curve_controller.update_layer(updated)
        self.curve_layers = [updated if item.id == layer.id else item for item in self.curve_layers]
        self.algebra_panel.sync_layer(layer.id, updated)

    def _command_point_alias(self, alias: str) -> Point2D:
        point = next((item for item in self.geometry_points if item.agent_alias == alias or item.name == alias), None)
        if point is None:
            raise CommandError(f"未知点别名: {alias}")
        return point

    def _command_delete_alias(self, alias: str) -> None:
        areas = getattr(self, "_agent_areas", {})
        if alias in areas or f"{alias}_fill" in areas:
            target = alias if alias in areas else f"{alias}_fill"
            areas.pop(target, None)
            self.plotter.remove_actor(f"agent-area:{target}", render=False)
            self.plotter.render()
            return
        points3d = getattr(self, "_agent_points3d", {})
        if alias in points3d:
            points3d.pop(alias, None)
            self._render_agent_points3d()
            return
        point = next((item for item in self.geometry_points if item.agent_alias == alias), None)
        if point is not None:
            self._remove_geometry_object(point.id)
            return
        linear = next((item for item in self.linear_objects if item.agent_alias == alias), None)
        if linear is not None:
            self._remove_geometry_object(linear.id)
            return
        annotation = next((item for item in self.annotations if item.agent_alias == alias), None)
        if annotation is not None:
            self.annotations = [item for item in self.annotations if item.id != annotation.id]
            self._two_d_object_order = [item for item in self._two_d_object_order if item != annotation.id]
            if self.geometry_controller is not None:
                self.geometry_controller.remove_object(annotation.id)
            return
        layer = next((item for item in self.curve_layers if item.agent_alias == alias), None)
        if layer is not None:
            self.curve_controller.remove_layer(layer.id) if self.curve_controller else None
            self.curve_layers = [item for item in self.curve_layers if item.id != layer.id]
            self._two_d_object_order = [item for item in self._two_d_object_order if item != layer.id]
            return
        surface = next((item for item in self.layers if item.agent_alias == alias), None)
        if surface is not None:
            if self.layer_controller is not None:
                self.layer_controller.remove_layer(surface.id)
            self.layers = [item for item in self.layers if item.id != surface.id]
            self._sync_panel_layers(self.layers)
            self.plotter.render()
            return
        raise CommandError(f"未知对象别名: {alias}")

    def _fit_2d_to_command_objects(self, padding: float) -> None:
        if self.scene_mode is SceneMode.THREE_D:
            self.plotter.reset_camera()
            self.plotter.render()
            return
        points = [(point.x, point.y) for point in self.geometry_points]
        if not points:
            return
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        span = max(max_x - min_x, max_y - min_y, 1.0) * max(1.0, padding)
        self.plotter.camera.focal_point = ((min_x + max_x) / 2, (min_y + max_y) / 2, 0.0)
        self.plotter.camera.position = (self.plotter.camera.focal_point[0], self.plotter.camera.focal_point[1], 20.0)
        self.plotter.camera.parallel_scale = span / 2
        self._refresh_2d_viewport(resample=True, render=False)

    def _render_scene(self) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._render_2d_scene()
        else:
            self._render_3d_scene()

    def _render_3d_scene(self) -> None:
        appearance = self.scene_appearances[SceneMode.THREE_D]
        build_scene(
            self.plotter,
            show_axes=False,
            show_helpers=True,
            lighting=self.lighting,
            camera_position=self._three_d_camera_position,
            background_color=appearance.background_color,
            axis_color_mode=appearance.axis_color_mode,
            contrast_axis_color=appearance.contrast_axis_color,
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
            base_surface=False,
        )
        configure_3d_camera_interaction(self.plotter)
        # build_scene 内部会调用 plotter.clear() 清除全部 actor，因此坐标轴需要重新创建。
        self._three_d_axes = ThreeDAxes(self.plotter)
        extent = self._current_3d_axis_extent()
        # 切换场景会重新创建坐标轴；沿用上次三维间距，避免同一视角重建后跳到另一档刻度。
        previous_spacing = self._three_d_spacing
        spacing = self._three_d_axes.render(
            extent,
            axis_color_mode=appearance.axis_color_mode,
            contrast_color=appearance.contrast_axis_color,
            show_ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            custom_tick_spacing=appearance.tick_spacing,
            previous_spacing=previous_spacing,
        )
        self._three_d_spacing = spacing
        self._three_d_extent = extent
        focal = tuple(self.plotter.camera.focal_point)
        self.plot_domain = PlotDomain(
            x_range=(focal[0] - extent, focal[0] + extent),
            y_range=(focal[1] - extent, focal[1] + extent),
            z_range=(focal[2] - extent, focal[2] + extent),
            explicit_resolution=self.plot_domain.explicit_resolution,
            implicit_resolution=self.plot_domain.implicit_resolution,
        )
        self._last_domain_extent = extent
        self.layer_controller = LayerSceneController(
            self.plotter,
            self.plot_domain,
            ambient=self.lighting.ambient,
            material_name=self.material_name,
        )
        self.layer_controller.set_global_intersections_visible(appearance.show_intersections)
        self.curve_controller = None
        self.geometry_controller = None
        available_layers: list[SurfaceLayer] = []
        for layer in self.layers:
            try:
                self.layer_controller.add_layer(layer)
            except (ExpressionError, LayerRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self.layers = available_layers
        self._sync_panel_layers(self.layers)
        self.algebra_panel.set_status("三维场景已准备好")
        self._render_agent_points3d()
        self._refresh_3d_viewport(resample=True, render=False)
        self.plotter.render()

    def _render_2d_scene(self) -> None:
        appearance = self.scene_appearances[SceneMode.TWO_D]
        self.plotter.clear()
        self.plotter.set_background(appearance.background_color)
        configure_2d_camera(self.plotter)
        self._restore_2d_camera()
        visible = self._current_2d_bounds()
        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        sampling_domain = self._curve_sampling_domain(sampling_bounds)
        self.curve_domain = sampling_domain
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
        )
        # plotter.clear() 会清除全部 actor，因此二维辅助线池也必须重新建立。
        self._two_d_guides = TwoDGuides(self.plotter)
        self._two_d_guides.render(sampling_bounds, appearance, spacing=spacing)
        self._two_d_guide_spacing = spacing
        self._two_d_guide_bounds = sampling_bounds
        self._two_d_sample_bounds = sampling_bounds
        self.curve_controller = CurveSceneController(self.plotter, sampling_domain)
        self.geometry_controller = GeometrySceneController(self.plotter, visible)
        self.layer_controller = None
        available_layers: list[CurveLayer] = []
        for layer in self.curve_layers:
            try:
                self.curve_controller.add_layer(layer)
            except (CurveExpressionError, CurveRenderError) as error:
                self.algebra_panel.set_status(f"无法绘制 {layer.name}: {error}", is_error=True)
            else:
                available_layers.append(layer)
        self.curve_layers = available_layers
        for point in self.geometry_points:
            self.geometry_controller.add_point(point)
        for linear in self.linear_objects:
            self.geometry_controller.add_linear(linear)
        for annotation in getattr(self, "annotations", []):
            self.geometry_controller.add_annotation(annotation)
        self._render_agent_areas()
        self._sync_panel_layers(self._two_d_panel_layers())
        self.algebra_panel.set_status("二维场景已准备好")
        self.plotter.render()

    def _restore_2d_camera(self) -> None:
        # 2D 场景使用并行投影（parallel projection），这里的 parallel_scale 相当于
        # "视口的世界单位 zoom"：数值越大，视口显示的世界范围越大，图像越小；
        # 数值越小，视口显示的范围越小，图像越放大。
        #
        # 这个值会直接影响 _current_2d_bounds() 中的 visible_2d_bounds() 计算：
        #   half_height = parallel_scale
        #   half_width = half_height * aspect_ratio
        # 因此它决定了当前可见窗口的 x/y 范围，进而影响网格、刻度和采样区域。
        if self._two_d_camera_position is not None:
            self.plotter.camera_position = self._two_d_camera_position
        else:
            self.plotter.camera_position = [
                (0.0, 0.0, 20.0),    # 相机位置
                (0.0, 0.0, 0.0),     # 相机焦点
                (0.0, 1.0, 0.0),     # 相机“向上”的方向
            ]
        if self._two_d_parallel_scale is not None:
            self.plotter.camera.parallel_scale = max(1e-6, self._two_d_parallel_scale)
        else:
            self.plotter.camera.parallel_scale = 6.0
        self.plotter.camera.clipping_range = (0.01, 1000.0)

    def _current_2d_bounds(self) -> ViewportBounds:
        interactor = getattr(self.plotter, "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        focal = tuple(self.plotter.camera.focal_point)
        return visible_2d_bounds(focal, float(self.plotter.camera.parallel_scale), width / height)

    def _curve_sampling_domain(self, bounds: ViewportBounds) -> Plot2DDomain:
        # 采样域为可视区域外扩 _GUIDE_MARGIN 得到（约 6 倍视口跨度）。若固定分辨率，
        # 采样点会被稀释到整个外扩域，可视区域内密度不足而出现锯齿。这里按外扩比例
        # 放大分辨率，保证可视区域内采样密度恒定，同时设上限避免性能问题。
        span_ratio = 1.0 + 2.0 * _GUIDE_MARGIN
        curve_resolution = min(
            8000, max(self.curve_domain.curve_resolution, int(self.curve_domain.curve_resolution * span_ratio))
        )
        # 隐式曲线为二维网格（成本 O(n²)），放大比例受限以兼顾性能。
        implicit_resolution = min(
            480, max(self.curve_domain.implicit_resolution, int(self.curve_domain.implicit_resolution * span_ratio ** 0.5))
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
        geometry_controller = getattr(self, "geometry_controller", None)
        if geometry_controller is not None:
            geometry_controller.set_bounds(visible)
        appearance = self.scene_appearances[SceneMode.TWO_D]
        spacing = tick_spacing(
            visible.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
            previous_spacing=None if force else self._two_d_guide_spacing,
        )
        spacing_unchanged = (
            self._two_d_guide_spacing is not None
            and abs(spacing - self._two_d_guide_spacing) <= self._two_d_guide_spacing * 1e-9
        )
        still_covered = (
            self._two_d_guide_bounds is not None
            and self._two_d_guide_bounds.contains(visible)
        )

        # 视口接近缓存边缘时提前补绘，补绘范围始终位于当前视口外围。
        needs_prefetch = (
            self._two_d_guide_bounds is not None
            and self._needs_2d_prefetch(visible, self._two_d_guide_bounds)
        )

        if not force and spacing_unchanged and still_covered and not needs_prefetch:
            if render:
                self.plotter.render()
            return

        sampling_bounds = visible.expanded(_GUIDE_MARGIN)
        if self._two_d_guides is not None:
            self._two_d_guides.render(sampling_bounds, appearance, spacing=spacing)
        self._two_d_guide_spacing = spacing
        self._two_d_guide_bounds = sampling_bounds
        if resample and self.curve_controller is not None:
            # contains() 只能识别平移或缩小（可见区域超出已采样范围）；放大时较小的
            # 可见区域仍被旧的大采样范围包含，若不重采样就会沿用稀疏网格，放大后
            # 曲线出现折线状的不连续。这里额外判断放大幅度：采样范围由可见范围
            # expanded(_GUIDE_MARGIN) 得到，反推出采样时的可见跨度，一旦当前可见
            # 跨度明显小于它（放大约 1.4 倍以上）便按当前视口重采样，恢复精细分辨率。
            needs_resample = force or needs_prefetch or self._two_d_sample_bounds is None or (
                not self._two_d_sample_bounds.contains(visible)
            )
            if not needs_resample and self._two_d_sample_bounds is not None:
                sampled_visible_span = self._two_d_sample_bounds.x_span / (
                    1.0 + 2.0 * _GUIDE_MARGIN
                )
                # 放大约 1.05 倍即重采样（阈值 0.95），及时恢复精细分辨率消除锯齿。
                if visible.x_span < sampled_visible_span * 0.95:
                    needs_resample = True
            if needs_resample:
                sampling_domain = self._curve_sampling_domain(sampling_bounds)
                try:
                    self.curve_controller.set_domain(sampling_domain)
                except (CurveExpressionError, CurveRenderError) as error:
                    self.algebra_panel.set_status(f"无法重新绘制曲线: {error}", is_error=True)
                else:
                    self.curve_domain = sampling_domain
                    self._two_d_sample_bounds = sampling_bounds
        if render:
            self.plotter.render()

    def _current_3d_axis_extent(self) -> float:
        camera = self.plotter.camera
        distance = float(camera.distance)
        view_angle = float(camera.view_angle)
        interactor = getattr(self.plotter, "interactor", None)
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
        if force and self._three_d_axes is not None:
            appearance = self.scene_appearances[SceneMode.THREE_D]
            extent = self._three_d_extent or self._current_3d_axis_extent()
            self._three_d_spacing = self._three_d_axes.render(
                extent,
                axis_color_mode=appearance.axis_color_mode,
                contrast_color=appearance.contrast_axis_color,
                show_ticks=appearance.show_ticks,
                tick_spacing_mode=appearance.tick_spacing_mode,
                custom_tick_spacing=appearance.tick_spacing,
                previous_spacing=None,
            )
            self._three_d_extent = extent

        if render:
            self.plotter.render()

    def _refresh_visible_viewport(self) -> None:
        self._viewport_refresh_pending = False
        if self._viewport_refreshing or not hasattr(self, "plotter"):
            return
        self._viewport_refreshing = True
        try:
            if self.scene_mode is SceneMode.TWO_D:
                self._refresh_2d_viewport()
            else:
                self._refresh_3d_viewport()
        finally:
            self._viewport_refreshing = False

    def _sync_panel_layers(
        self,
        layers: list[SurfaceLayer] | list[CurveLayer] | list[CurveLayer | GeometryObject],
    ) -> None:
        self.algebra_panel.set_scene_mode(self.scene_mode)
        self.algebra_panel.set_catalog_entries(catalog_entries(self.scene_mode))
        self.algebra_panel.set_layers(layers)
        self._sync_scene_controls()

    def _add_formula_for_scene(self, kind: str, latex: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._add_cas_curve(kind, latex)
        else:
            self._add_cas_surface(kind, latex)

    def _update_formula_for_scene(self, layer_id: str, kind: str, latex: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            if self._point_2d(layer_id) is not None:
                self._update_point_coordinates(layer_id, latex)
            else:
                self._update_curve_expression(layer_id, kind, latex)
        else:
            self._update_surface_expression(layer_id, kind, latex)

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
        if self.geometry_controller is not None:
            self.geometry_controller.move_point(point_id, *coordinates)
        self.algebra_panel.sync_layer(point_id, point)
        self.algebra_panel.finish_edit()
        self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已更新点 {point.name}")
        self.plotter.render()

    def _add_catalog_entry(self, entry_id: str) -> None:
        entry = catalog_entry(entry_id, self.scene_mode)
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
    def _linear_algebra_case_plan(case: LinearAlgebraCase) -> CommandPlan:
        """Wrap a built-in case in one clear-and-load 2D command plan."""
        return CommandPlan(
            scene="2d",
            summary=case.summary,
            operations=({"op": "scene.clear", "scope": "all"}, *case.plan.operations),
        )

    def _load_linear_algebra_case(self, case_id: str) -> None:
        case = linear_algebra_case(case_id)
        if case is None:
            self.algebra_panel.set_status(f"未知线性代数案例: {case_id}", is_error=True)
            return
        plan = self._linear_algebra_case_plan(case)
        try:
            self.scene_command_service.execute(plan)
        except CommandError as error:
            self.algebra_panel.set_status(f"无法加载案例 {case.name}: {error}", is_error=True)
            return
        self.algebra_panel.set_status(f"已加载案例: {case.name}")
        if hasattr(self, "agent_panel"):
            if hasattr(self, "agent_sidebar"):
                self._open_agent_panel()
            self.agent_panel.show_math_case(case)

    def _add_cas_surface(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        layer = SurfaceLayer(
            name=f"曲面 {len(self.layers) + 1}",
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
            name=f"曲线 {len(self.curve_layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=formula.latex,
            parameters={name: 1.0 for name in parsed.parameter_names},
        )
        if self._add_curve_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_builtin_surface(self, builtin_id: str) -> None:
        if self.scene_mode is not SceneMode.THREE_D:
            return
        self._add_layer(create_builtin_layer(builtin_id))

    def _add_layer(self, layer: SurfaceLayer) -> bool:
        if self.layer_controller is None:
            return False
        try:
            self.layer_controller.add_layer(layer)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲面: {error}", is_error=True)
            return False
        self.layers.append(layer)
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status(f"已添加 {layer.name}")
        self.plotter.render()
        return True

    def _add_curve_layer(self, layer: CurveLayer) -> bool:
        if self.curve_controller is None:
            return False
        try:
            self.curve_controller.add_layer(layer)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法绘制曲线: {error}", is_error=True)
            return False
        self.curve_layers.append(layer)
        self._two_d_object_order.append(layer.id)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self.algebra_panel.set_status(f"已添加 {layer.name}")
        self.plotter.render()
        return True

    def _update_surface_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._layer(layer_id)
        if current is None or self.layer_controller is None:
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
            self.layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面: {error}", is_error=True)
            return
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self.plotter.render()

    def _update_curve_expression(self, layer_id: str, kind: str, latex: str) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self.curve_controller is None:
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
            self.curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线: {error}", is_error=True)
            return
        self.curve_layers = [updated if layer.id == layer_id else layer for layer in self.curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.finish_edit()
        self.algebra_panel.set_status(f"已更新 {updated.name}")
        self.plotter.render()

    def _parse_mathlive_surface(self, latex: str, kind: str):
        formula = self.latex_parser.parse(latex, kind)
        return formula, parse_surface_expression(formula.canonical_source, formula.kind)

    def _parse_mathlive_curve(self, latex: str, kind: str):
        formula = self.latex_parser.parse_2d(latex, kind)
        return formula, parse_curve_expression(formula.canonical_source, formula.kind)

    def _remove_layer_for_scene(self, layer_id: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                self._remove_geometry_object(layer_id)
            else:
                self._remove_curve(layer_id)
        else:
            self._remove_surface(layer_id)

    def _remove_surface(self, layer_id: str) -> None:
        if self.layer_controller is None:
            return
        self.layer_controller.remove_layer(layer_id)
        self.layers = [layer for layer in self.layers if layer.id != layer_id]
        self.algebra_panel.set_layers(self.layers)
        self.algebra_panel.set_status("已删除曲面")
        self.plotter.render()

    def _remove_curve(self, layer_id: str) -> None:
        if self.curve_controller is None:
            return
        self.curve_controller.remove_layer(layer_id)
        self.curve_layers = [layer for layer in self.curve_layers if layer.id != layer_id]
        self._two_d_object_order = [item_id for item_id in self._two_d_object_order if item_id != layer_id]
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self.algebra_panel.set_status("已删除曲线")
        self.plotter.render()

    def _remove_geometry_object(self, object_id: str) -> None:
        geometry = self._geometry_object(object_id)
        if geometry is None:
            return
        before = self._capture_geometry_state()
        removed_ids = {object_id}
        if isinstance(geometry, Point2D):
            removed_ids.update(
                linear.id
                for linear in self.linear_objects
                if object_id in {linear.start_point_id, linear.end_point_id}
            )
            self.geometry_points = [point for point in self.geometry_points if point.id != object_id]
            self.linear_objects = [
                linear for linear in self.linear_objects if linear.id not in removed_ids
            ]
        else:
            self.linear_objects = [
                linear for linear in self.linear_objects if linear.id != object_id
            ]
        self._two_d_object_order = [
            item_id for item_id in self._two_d_object_order if item_id not in removed_ids
        ]
        if self._pending_geometry_point_id in removed_ids:
            self._set_2d_geometry_tool(self._active_2d_tool)
        if self.geometry_controller is not None:
            for removed_id in removed_ids:
                self.geometry_controller.remove_object(removed_id)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self._record_geometry_change(before)
        self.algebra_panel.set_status("已删除几何对象")
        self.plotter.render()

    def _set_layer_visibility(self, layer_id: str, visible: bool) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                self._set_geometry_visibility(layer_id, visible)
            else:
                self._set_curve_visibility(layer_id, visible)
        else:
            self._set_surface_visibility(layer_id, visible)

    def _set_surface_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_visible(layer_id, visible)
        self._replace_layer(layer_id, visible=visible)
        self.plotter.render()

    def _set_curve_visibility(self, layer_id: str, visible: bool) -> None:
        if self.curve_controller is not None:
            self.curve_controller.set_visible(layer_id, visible)
        self._replace_curve_layer(layer_id, visible=visible)
        self.plotter.render()

    def _set_geometry_visibility(self, layer_id: str, visible: bool) -> None:
        geometry = self._geometry_object(layer_id)
        if geometry is None:
            return
        if geometry.visible == visible:
            return
        before = self._capture_geometry_state()
        geometry.visible = visible
        if self.geometry_controller is not None:
            self.geometry_controller.set_visible(layer_id, visible)
        self.algebra_panel.sync_layer(layer_id, geometry)
        self._record_geometry_change(before)
        self.plotter.render()

    def _set_surface_intersections_visibility(self, layer_id: str, visible: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_intersections_visible(layer_id, visible)
        self._replace_layer(layer_id, intersections_visible=visible)
        self.plotter.render()

    def _set_surface_intersection_color(self, layer_id: str, color: str) -> None:
        current = self._layer(layer_id)
        if current is None:
            return
        self._intersection_color_revision = (
            max(
                self._intersection_color_revision,
                *(layer.intersection_color_revision for layer in self.layers),
            )
            + 1
        )
        updated = replace(
            current,
            intersection_color=color,
            intersection_color_revision=self._intersection_color_revision,
        )
        if self.layer_controller is not None:
            self.layer_controller.set_intersection_color(
                layer_id, color, updated.intersection_color_revision
            )
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.plotter.render()

    def _set_layer_color(self, layer_id: str, color: str) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            if self._geometry_object(layer_id) is not None:
                return
            if self.curve_controller is not None:
                self.curve_controller.set_color(layer_id, color)
            self._replace_curve_layer(layer_id, color=color)
        else:
            if self.layer_controller is not None:
                self.layer_controller.set_color(layer_id, color)
            self._replace_layer(layer_id, color=color)
        self.plotter.render()

    def _set_surface_color(self, layer_id: str, color: str) -> None:
        self._set_layer_color(layer_id, color)

    def _set_surface_opacity(self, layer_id: str, opacity: float) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_opacity(layer_id, opacity)
        self._replace_layer(layer_id, opacity=opacity)
        self.plotter.render()

    def _set_curve_line_width(self, layer_id: str, line_width: float) -> None:
        if self.curve_controller is not None:
            self.curve_controller.set_line_width(layer_id, line_width)
        self._replace_curve_layer(layer_id, line_width=line_width)
        self.plotter.render()

    def _set_layer_range(self, layer_id: str, range_scale: float) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            self._set_curve_range(layer_id, range_scale)
        else:
            self._set_surface_range(layer_id, range_scale)

    def _set_surface_range(self, layer_id: str, range_scale: float) -> None:
        current = self._layer(layer_id)
        if current is None or self.layer_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self.layer_controller.update_layer(updated)
        except (ExpressionError, LayerRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲面范围: {error}", is_error=True)
            return
        self.layers = [updated if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 {updated.range_scale:.0%}")
        self.plotter.render()

    def _set_curve_range(self, layer_id: str, range_scale: float) -> None:
        current = self._curve_layer(layer_id)
        if current is None or self.curve_controller is None:
            return
        updated = replace(current, range_scale=range_scale)
        try:
            self.curve_controller.update_layer(updated)
        except (CurveExpressionError, CurveRenderError) as error:
            self.algebra_panel.set_status(f"无法更新曲线范围: {error}", is_error=True)
            return
        self.curve_layers = [updated if layer.id == layer_id else layer for layer in self.curve_layers]
        self.algebra_panel.sync_layer(layer_id, updated)
        self.algebra_panel.set_status(f"已将 {updated.name} 的范围设为 x{updated.range_scale:.1f}")
        self.plotter.render()

    def _set_auto_intersections(self, enabled: bool) -> None:
        if self.layer_controller is not None:
            self.layer_controller.set_auto_intersections(enabled)
        self.plotter.render()

    def _add_manual_intersection(self, first_id: str, second_id: str) -> None:
        if self.layer_controller is None:
            return
        self.layer_controller.set_manual_intersection_pair(first_id, second_id, True)
        self.plotter.render()

    def _toggle_scene_mode(self) -> None:
        next_mode = SceneMode.TWO_D if self.scene_mode is SceneMode.THREE_D else SceneMode.THREE_D
        self._set_scene_mode(next_mode)

    def _set_scene_mode(self, mode: SceneMode) -> None:
        if mode is self.scene_mode:
            return
        if self.scene_mode is SceneMode.TWO_D:
            self._set_2d_geometry_tool(None)
        self._save_current_view_state()
        self.scene_mode = mode
        self._close_scene_settings(immediate=True)
        self._render_scene()

    _TOOL_LABELS = {"line": "直线", "segment": "线段", "ray": "射线", "vector": "向量"}

    def _set_2d_geometry_tool(self, tool: ToolKind | None) -> None:
        """切换当前二维几何创建工具，并清理未完成的两点操作。"""
        if self.scene_mode is not SceneMode.TWO_D:
            tool = None
        self._pending_geometry_point_id = None
        self._dragging_point_id = None
        self._drag_start_geometry_state = None
        if self.geometry_controller is not None:
            self.geometry_controller.clear_draft()
            # 离开选择工具时清除高亮，避免遗留悬浮/选中效果。
            if tool != "select":
                self.geometry_controller.set_hover(None)
                self.geometry_controller.set_selected(None)
        self._active_2d_tool = tool
        if hasattr(self, "two_d_geometry_toolbar"):
            self.two_d_geometry_toolbar.set_active_tool(tool)
        if hasattr(self, "plotter"):
            cursor = {
                None: Qt.CursorShape.ArrowCursor,
                "select": Qt.CursorShape.ArrowCursor,
            }.get(tool, Qt.CursorShape.CrossCursor)
            self.plotter.interactor.setCursor(cursor)
            if tool is not None:
                self.plotter.interactor.setFocus()
        if tool == "select":
            self.algebra_panel.set_status("选择工具：单击选中，拖动点可移动，双击点可编辑坐标")
        elif tool == "point":
            self.algebra_panel.set_status("点工具：单击画布创建点")
        elif tool is not None:
            self.algebra_panel.set_status(f"{self._TOOL_LABELS[tool]}工具：单击第一个点")

    def _set_snap_to_grid(self, enabled: bool) -> None:
        self._snap_to_grid = bool(enabled)
        self.algebra_panel.set_status("已开启网格吸附" if enabled else "已关闭网格吸附")

    def _capture_geometry_state(self) -> _GeometryHistoryState:
        """复制当前几何状态，避免后续点移动修改历史快照。"""
        return _GeometryHistoryState(
            points=tuple(replace(point) for point in self.geometry_points),
            linears=tuple(replace(linear) for linear in self.linear_objects),
            object_order=tuple(self._two_d_object_order),
        )

    def _ensure_geometry_history(self) -> None:
        if not hasattr(self, "_geometry_undo_stack"):
            self._geometry_undo_stack = []
        if not hasattr(self, "_geometry_redo_stack"):
            self._geometry_redo_stack = []

    def _record_geometry_change(self, before: _GeometryHistoryState) -> None:
        if getattr(self, "_scene_command_active", False):
            return
        # 手动操作发生在 AI 事务之后时，撤销应优先回退最新的手动操作。
        if getattr(self, "_scene_command_undo_stack", []):
            self._scene_command_undo_stack.clear()
            self._scene_command_redo_stack.clear()
        self._ensure_geometry_history()
        after = self._capture_geometry_state()
        if before == after:
            return
        self._geometry_undo_stack.append(before)
        self._geometry_redo_stack.clear()
        self._update_geometry_history_controls()

    def _update_geometry_history_controls(self) -> None:
        toolbar = getattr(self, "two_d_geometry_toolbar", None)
        if toolbar is not None and hasattr(toolbar, "set_history_state"):
            toolbar.set_history_state(
                can_undo=bool(getattr(self, "_geometry_undo_stack", []))
                or bool(getattr(self, "_scene_command_undo_stack", [])),
                can_redo=bool(getattr(self, "_geometry_redo_stack", []))
                or bool(getattr(self, "_scene_command_redo_stack", [])),
            )

    def _undo_2d_geometry(self) -> None:
        if getattr(self, "_scene_command_undo_stack", []):
            current = self._capture_scene_command_state()
            target = self._scene_command_undo_stack.pop()
            self._scene_command_redo_stack.append(current)
            self._restore_scene_command_state(target)
            self.algebra_panel.set_status("已撤回 AI 场景命令")
            self._update_geometry_history_controls()
            return
        self._ensure_geometry_history()
        if self.scene_mode is not SceneMode.TWO_D or not self._geometry_undo_stack:
            return
        current = self._capture_geometry_state()
        target = self._geometry_undo_stack.pop()
        self._geometry_redo_stack.append(current)
        self._restore_geometry_state(target)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已撤回二维几何操作")

    _undo_scene_command = _undo_2d_geometry

    def _redo_2d_geometry(self) -> None:
        if getattr(self, "_scene_command_redo_stack", []):
            current = self._capture_scene_command_state()
            target = self._scene_command_redo_stack.pop()
            self._scene_command_undo_stack.append(current)
            self._restore_scene_command_state(target)
            self.algebra_panel.set_status("已反撤回 AI 场景命令")
            self._update_geometry_history_controls()
            return
        self._ensure_geometry_history()
        if self.scene_mode is not SceneMode.TWO_D or not self._geometry_redo_stack:
            return
        current = self._capture_geometry_state()
        target = self._geometry_redo_stack.pop()
        self._geometry_undo_stack.append(current)
        self._restore_geometry_state(target)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已反撤回二维几何操作")

    def _restore_geometry_state(self, state: _GeometryHistoryState) -> None:
        """恢复几何对象并重建几何控制器，保持函数曲线和当前工具不变。"""
        self.geometry_points = [replace(point) for point in state.points]
        self.linear_objects = [replace(linear) for linear in state.linears]
        self._two_d_object_order = list(state.object_order)
        self._pending_geometry_point_id = None
        self._dragging_point_id = None
        self._drag_moved = False
        self._drag_start_geometry_state = None

        controller = getattr(self, "geometry_controller", None)
        if controller is not None:
            controller.clear_draft()
            controller.set_hover(None)
            controller.set_selected(None)
            for object_id in [*controller.points, *controller.linears]:
                controller.remove_object(object_id)
            for point in self.geometry_points:
                controller.add_point(point)
            for linear in self.linear_objects:
                controller.add_linear(linear)
            for annotation in getattr(self, "annotations", []):
                controller.add_annotation(annotation)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self.algebra_panel.set_selected_layer(None)
        self.plotter.render()

    def _handle_geometry_mouse_press(self, event: QMouseEvent) -> bool:
        """处理被激活工具的左键单击；其他输入仍交给 PyVista。"""
        tool = self._active_2d_tool
        if (
            self.scene_mode is not SceneMode.TWO_D
            or tool is None
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        if tool == "select":
            return self._begin_select_or_drag(*coordinates)
        coordinates = self._maybe_snap(*coordinates)
        before = self._capture_geometry_state()
        point, created = self._get_or_create_geometry_point(*coordinates, record_history=False)
        if tool == "point":
            self._record_geometry_change(before)
            self.algebra_panel.set_status(
                f"{'已创建' if created else '已复用'}点 {point.name}"
            )
            self.plotter.render()
            event.accept()
            return True
        if self._pending_geometry_point_id is None:
            self._pending_geometry_point_id = point.id
            self._record_geometry_change(before)
            self.algebra_panel.set_status(
                f"已选择点 {point.name}，单击第二点创建{self._TOOL_LABELS[tool]}"
            )
            self.plotter.render()
            event.accept()
            return True

        first = self._point_2d(self._pending_geometry_point_id)
        if first is None:
            self._pending_geometry_point_id = None
            return False
        if first.id == point.id:
            self.algebra_panel.set_status("请单击与第一个点不同的位置", is_error=True)
            event.accept()
            return True
        linear = self._create_linear_geometry(tool, first, point, record_history=False)
        self._pending_geometry_point_id = None
        if self.geometry_controller is not None:
            self.geometry_controller.clear_draft()
        if not getattr(self, "_scene_command_active", False):
            self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已创建{self._TOOL_LABELS[tool]} {linear.name}")
        self.plotter.render()
        event.accept()
        return True

    def _begin_select_or_drag(self, x: float, y: float) -> bool:
        """选择工具左键按下：命中对象则选中，命中点则准备拖动。"""
        if self.geometry_controller is None:
            return False
        hit_id = self.geometry_controller.hit_test(x, y, self._hit_tolerance())
        self._select_geometry_object(hit_id)
        self._dragging_point_id = hit_id if hit_id in self.geometry_controller.points else None
        self._drag_start_geometry_state = (
            self._capture_geometry_state() if self._dragging_point_id is not None else None
        )
        self._drag_moved = False
        self.plotter.render()
        # 命中对象时拦截事件，避免触发相机平移；未命中则放行以便平移画布。
        return hit_id is not None

    def _handle_geometry_mouse_move(self, event: QMouseEvent) -> bool:
        if self.scene_mode is not SceneMode.TWO_D or self.geometry_controller is None:
            return False
        tool = self._active_2d_tool
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        if tool == "select":
            if self._dragging_point_id is not None:
                snapped = self._maybe_snap(*coordinates)
                self.geometry_controller.move_point(self._dragging_point_id, *snapped)
                point = self._point_2d(self._dragging_point_id)
                if point is not None:
                    point.x, point.y = snapped
                    self.algebra_panel.sync_layer(point.id, point)
                self._drag_moved = True
                self.plotter.render()
                return True
            # 悬浮高亮：命中变化时才重绘。
            hit_id = self.geometry_controller.hit_test(*coordinates, self._hit_tolerance())
            if self.geometry_controller.set_hover(hit_id):
                cursor = (
                    Qt.CursorShape.OpenHandCursor
                    if hit_id in self.geometry_controller.points
                    else Qt.CursorShape.PointingHandCursor
                    if hit_id is not None
                    else Qt.CursorShape.ArrowCursor
                )
                self.plotter.interactor.setCursor(cursor)
                self.plotter.render()
            return False
        if (
            tool in {"line", "segment", "ray", "vector"}
            and self._pending_geometry_point_id is not None
        ):
            first = self._point_2d(self._pending_geometry_point_id)
            if first is not None:
                self.geometry_controller.set_draft(tool, first, self._maybe_snap(*coordinates))
                self.plotter.render()
        return False

    def _handle_geometry_mouse_release(self, event: QMouseEvent) -> bool:
        if self._dragging_point_id is None:
            return False
        point = self._point_2d(self._dragging_point_id)
        if point is not None and self._drag_moved:
            if self._drag_start_geometry_state is not None:
                self._record_geometry_change(self._drag_start_geometry_state)
            self.algebra_panel.set_status(f"已移动点 {point.name}")
        self._dragging_point_id = None
        self._drag_moved = False
        self._drag_start_geometry_state = None
        return False

    def _handle_geometry_double_click(self, event: QMouseEvent) -> bool:
        if (
            self.scene_mode is not SceneMode.TWO_D
            or self._active_2d_tool != "select"
            or self.geometry_controller is None
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            return False
        hit_id = self.geometry_controller.hit_test(*coordinates, self._hit_tolerance())
        if hit_id is not None and hit_id in self.geometry_controller.points:
            self._select_geometry_object(hit_id)
            self.plotter.render()
            self.algebra_panel.begin_geometry_edit(hit_id)
            event.accept()
            return True
        return False

    def _select_geometry_object(self, object_id: str | None) -> None:
        if self.geometry_controller is not None:
            self.geometry_controller.set_selected(object_id)
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
            selected = self.geometry_controller.selected_id if self.geometry_controller else None
            if selected is not None and self._geometry_object(selected) is not None:
                self._remove_geometry_object(selected)
                event.accept()
                return True
            return False
        if key != Qt.Key.Key_Escape:
            return False
        if self._active_2d_tool == "select" and self.geometry_controller is not None:
            self._select_geometry_object(None)
            self.plotter.render()
            event.accept()
            return True
        if self._active_2d_tool is None:
            return False
        self._set_2d_geometry_tool(None)
        self.algebra_panel.set_status("已返回平移模式")
        event.accept()
        return True

    def _maybe_snap(self, x: float, y: float) -> tuple[float, float]:
        if not self._snap_to_grid:
            return x, y
        spacing = self._two_d_guide_spacing
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
        interactor = getattr(self.plotter, "interactor", None)
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
        for point in self.geometry_points:
            if (point.x - x) ** 2 + (point.y - y) ** 2 <= tolerance**2:
                return point, False
        before = self._capture_geometry_state()
        point = Point2D(self._next_point_name(), x, y)
        self.geometry_points.append(point)
        self._two_d_object_order.append(point.id)
        if self.geometry_controller is not None:
            self.geometry_controller.add_point(point)
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
        self.linear_objects.append(linear)
        self._two_d_object_order.append(linear.id)
        if self.geometry_controller is not None:
            self.geometry_controller.add_linear(linear)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        if record_history:
            self._record_geometry_change(before)
        return linear

    def _point_snap_tolerance(self) -> float:
        interactor = getattr(self.plotter, "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        bounds = self._current_2d_bounds()
        return 12.0 * max(bounds.x_span / width, bounds.y_span / height)

    def _next_point_name(self) -> str:
        existing = {point.name for point in self.geometry_points}
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for index in range(10_000):
            name = alphabet[index % len(alphabet)]
            if index >= len(alphabet):
                name += str(index // len(alphabet))
            if name not in existing:
                return name
        raise RuntimeError("无法再创建更多二维点。")

    def _next_linear_name(self, kind: LinearKind) -> str:
        existing = {linear.name for linear in self.linear_objects}
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
        if not hasattr(self, "plotter"):
            return
        if self.scene_mode is SceneMode.TWO_D:
            self._two_d_parallel_scale = float(self.plotter.camera.parallel_scale)
            self._two_d_camera_position = self._current_camera_position()
        else:
            self._three_d_camera_position = self._current_camera_position()

    def _set_scene_background(self, background: str) -> None:
        self.scene_appearances[self.scene_mode].background = background
        self._save_current_view_state()
        self._render_scene()

    def _set_axis_color_mode(self, axis_color_mode: str) -> None:
        self.scene_appearances[self.scene_mode].axis_color_mode = axis_color_mode
        self._save_current_view_state()
        self._render_scene()

    def _set_grid_visible(self, visible: bool) -> None:
        self.scene_appearances[SceneMode.TWO_D].show_grid = visible
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)

    def _set_ticks_visible(self, visible: bool) -> None:
        appearance = self.scene_appearances[self.scene_mode]
        appearance.show_ticks = visible
        self._save_current_view_state()
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing_mode(self, mode: str) -> None:
        appearance = self.scene_appearances[self.scene_mode]
        appearance.tick_spacing_mode = mode if mode in {"auto", "custom"} else "auto"
        self._save_current_view_state()
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_tick_spacing(self, spacing: float) -> None:
        if spacing <= 0:
            return
        self.scene_appearances[self.scene_mode].tick_spacing = float(spacing)
        if self.scene_mode is SceneMode.TWO_D:
            self._refresh_2d_viewport(resample=False, force=True)
        else:
            self._refresh_3d_viewport(resample=False, force=True)

    def _set_global_intersections_visible(self, visible: bool) -> None:
        self.scene_appearances[SceneMode.THREE_D].show_intersections = visible
        if self.scene_mode is SceneMode.THREE_D and self.layer_controller is not None:
            self.layer_controller.set_global_intersections_visible(visible)
            self.plotter.render()

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
        self.agent_sidebar.expand()
        self.agent_sidebar.select_tab("agent")
        self._root_layout.activate()
        self.agent_panel.view.setFocus()

    def _close_agent_panel(self, immediate: bool = False) -> None:
        self.agent_button.setChecked(False)
        self.agent_sidebar.collapse()
        self._root_layout.activate()

    def _show_agent_settings(self) -> None:
        dialog = getattr(self, "_agent_settings_dialog", None)
        if dialog is not None:
            # 重复点击设置按钮时只把已有对话框带到前面，避免多个窗口写同一份 QSettings。
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return
        dialog = AgentSettingsDialog(self.window)
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
            command_service=self.scene_command_service,
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
            for layer in self.curve_layers
        )
        point_aliases = {
            point.id: point.agent_alias or point.name
            for point in self.geometry_points
        }
        points = tuple(
            {
                "alias": point.agent_alias or point.name,
                "kind": "point",
                "coordinates": [point.x, point.y],
            }
            for point in self.geometry_points
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
            for linear in self.linear_objects
        )
        annotations = tuple(
            {
                "alias": annotation.agent_alias or annotation.name,
                "kind": "annotation",
                "text": annotation.text,
                "position": [annotation.x, annotation.y],
            }
            for annotation in self.annotations
        )
        surfaces = tuple(
            {
                "alias": layer.agent_alias or layer.name,
                "kind": layer.kind,
                "expression": layer.expression,
            }
            for layer in self.layers
        )
        points3d = tuple(
            {"alias": alias, "kind": "point3d", "coordinates": list(coordinates)}
            for alias, coordinates in getattr(self, "_agent_points3d", {}).items()
        )
        return SceneContext(
            scene_mode="2d" if self.scene_mode is SceneMode.TWO_D else "3d",
            curves=curves + surfaces,
            geometry=points + linears + annotations + points3d,
            last_plan_summary=self._last_agent_plan_summary,
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
        appearance = self.scene_appearances[self.scene_mode]
        self.scene_mode_button.setText("2D" if self.scene_mode is SceneMode.TWO_D else "3D")
        if hasattr(self, "two_d_geometry_toolbar"):
            is_2d = self.scene_mode is SceneMode.TWO_D
            self.two_d_geometry_toolbar.setVisible(is_2d)
            if not is_2d:
                self.two_d_geometry_toolbar.line_flyout.hide()
        self.scene_settings_panel.set_mode(self.scene_mode)
        if hasattr(self, "agent_panel"):
            self.agent_panel.set_scene_mode(self.scene_mode is SceneMode.TWO_D)
        self.scene_settings_panel.set_values(
            background=appearance.background,
            axis_color_mode=appearance.axis_color_mode,
            grid=appearance.show_grid,
            ticks=appearance.show_ticks,
            tick_spacing_mode=appearance.tick_spacing_mode,
            tick_spacing=appearance.tick_spacing,
            intersections=appearance.show_intersections,
        )

    def _show_lighting_dialog(self) -> None:
        if self.scene_mode is SceneMode.TWO_D:
            return
        if self._lighting_dialog is None:
            self._lighting_dialog = LightingDialog(self.lighting, self.material_name, self.window)
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
        self.lighting = settings
        if self.scene_mode is SceneMode.THREE_D:
            if self.layer_controller is not None:
                self.layer_controller.set_ambient(settings.ambient)
            update_lighting(self.plotter, settings)

    def _update_material(self, material_name: str) -> None:
        self.material_name = material_name
        if self.scene_mode is SceneMode.THREE_D and self.layer_controller is not None:
            self.layer_controller.set_material(material_name)
            self.plotter.render()

    def _replace_layer(self, layer_id: str, **changes: object) -> None:
        self.layers = [replace(layer, **changes) if layer.id == layer_id else layer for layer in self.layers]
        self.algebra_panel.sync_layer(layer_id, self._layer(layer_id))

    def _replace_curve_layer(self, layer_id: str, **changes: object) -> None:
        self.curve_layers = [
            replace(layer, **changes) if layer.id == layer_id else layer for layer in self.curve_layers
        ]
        self.algebra_panel.sync_layer(layer_id, self._curve_layer(layer_id))

    def _two_d_panel_layers(self) -> list[CurveLayer | GeometryObject]:
        objects: dict[str, CurveLayer | GeometryObject] = {
            layer.id: layer for layer in self.curve_layers
        }
        objects.update({point.id: point for point in self.geometry_points})
        objects.update({linear.id: linear for linear in self.linear_objects})
        for object_id in objects:
            if object_id not in self._two_d_object_order:
                self._two_d_object_order.append(object_id)
        return [
            objects[object_id]
            for object_id in self._two_d_object_order
            if object_id in objects
        ]

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self.layers if layer.id == layer_id), None)

    def _curve_layer(self, layer_id: str) -> CurveLayer | None:
        return next((layer for layer in self.curve_layers if layer.id == layer_id), None)

    def _point_2d(self, point_id: str | None) -> Point2D | None:
        if point_id is None:
            return None
        return next((point for point in self.geometry_points if point.id == point_id), None)

    def _geometry_object(self, object_id: str) -> GeometryObject | None:
        point = self._point_2d(object_id)
        if point is not None:
            return point
        return next((linear for linear in self.linear_objects if linear.id == object_id), None)

    def _current_camera_position(self) -> list | None:
        if not getattr(self, "plotter", None):
            return None
        try:
            return [tuple(vector) for vector in self.plotter.camera_position]
        except (AttributeError, TypeError):
            return None

    def _widget(self, name: str, widget_type: type[QWidget]) -> QWidget:
        widget = self.window.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Designer form is missing required widget: {name}")
        return widget

    def _apply_style(self) -> None:
        from ui.tokens import build_qss
        self.window.setStyleSheet(build_qss(getattr(self, "effective_theme", "light")))

    def set_theme(self, mode: ThemeMode, effective: EffectiveTheme) -> None:
        """Apply and propagate the resolved application theme."""
        self.theme_mode = mode
        self.effective_theme = effective
        from PySide6.QtCore import QSettings

        settings = QSettings()
        settings.setValue("ui/theme", mode)
        settings.sync()
        if hasattr(self, "window"):
            self._apply_style()
        # Theme-aware surfaces are optional so this remains compatible with
        # lightweight test doubles and older embedded hosts.
        for surface in (
            getattr(self, "agent_panel", None),
            getattr(self, "agent_sidebar", None),
            getattr(self, "plotter", None),
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

    def show(self) -> None:
        self.window.show()
