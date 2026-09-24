"""用于组合相互独立二维/三维公式场景的主窗口。"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass, replace
from math import acos, degrees, hypot, isfinite
import re
import time
from uuid import uuid4
from pathlib import Path

from collections import deque
from collections.abc import Callable
import inspect
from typing import Literal

from PySide6.QtCore import QEasingCurve, QEvent, QFile, QIODevice, QObject, QPoint, QPropertyAnimation, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QWindowStateChangeEvent
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent, QShortcut, QWheelEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QRubberBand, QToolButton, QVBoxLayout, QWidget
from shiboken6 import isValid
from pyvistaqt import QtInteractor

from MathInputWidget import LatexParseError, LatexParser
from geometry.cas_curve import CurveExpressionError, parse_curve_expression
from geometry.cas_surface import ExpressionError, parse_surface_expression
from geometry.parameter_display import format_parameterized_latex
from geometry.standard_surfaces import BUILTIN_SURFACES, create_builtin_layer
from models.curve_layer import CurveLayer, Plot2DDomain
from models.geometry_2d import (
    Annotation2D,
    GeometryObject,
    Linear2D,
    LinearKind,
    Point2D,
    format_number,
    operation_label,
    parse_point_coordinates,
)
from models.geometry_3d import AlgebraAnnotation3D, AlgebraPlane3D, AlgebraVector3D
from models.function_catalog import catalog_entries, catalog_entry
from linear_algebra.registry import CurriculumRegistry, catalog_registry, runtime_teaching_store
from linear_algebra.teaching.authoring import (
    AuthoringSyncResult,
    synchronize_topic,
    workspace_authoring_available,
)
from linear_algebra.teaching.load_states import LoadPhase, fingerprint
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
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
from rendering import math_labels
from rendering.scene import DEFAULT_3D_AXIS_EXTENT, build_scene, configure_3d_camera_interaction, update_lighting
from rendering.ticks import ViewportBounds, tick_spacing, visible_2d_bounds
from rendering.two_d_scene import CoordinateTransform, TwoDGuides, configure_2d_camera, coordinate_source_bounds
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
from ui.three_d_tools import ThreeDGeometryToolbar
from ui.two_d_tools import ToolKind, TwoDGeometryToolbar
from ui.web_surface import rebuild_web_surface
from ui.linear_algebra_tools import (
    build_matrix_grid_tool_plan,
    build_polygon_tool_plan,
    build_vector_tool_plan,
    parse_matrix_expression,
    parse_matrix,
)
from ui.teaching_case_panes import (
    PANE_COUNTS,
    StoryboardVisibility,
    StoryboardVisibilityController,
    TeachingCasePaneGrid,
    case_plan,
)
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


# 辅助线预绘到视口外，减少平移和缩放时的重建。
_GUIDE_MARGIN = 2.5

_CHAPTER_TWO_MATRIX_TOOL_TOPICS = frozenset(
    {
        "ch02.matrix.additive-distributivity",
        "ch02.matrix.transformed-grid",
        "ch02.matrix.composition",
        "ch02.matrix.basis",
        "ch02.matrix.powers",
    }
)
_CHAPTER_SEVEN_MATRIX_TOOL_TOPICS = frozenset(
    {
        "ch07.eigen.direction",
        "ch07.characteristic-polynomial",
        "ch07.eigenspace",
        "ch07.diagonalization",
    }
)
_DETERMINANT_MATRIX_TOOL_TOPICS = frozenset(
    {
        "ch03.det.basic-properties",
        "ch03.det.multiplicativity",
        "ch03.det.transpose",
    }
)
_CHAPTER_FOUR_MATRIX_TOOL_TOPICS = frozenset(
    {
        "ch04.basis.definition",
        "ch04.linear-map.definition",
    }
)
_ANNOTATION_TEXT_COMMAND = re.compile(r"\\(?:text|mathrm|operatorname)\{([^{}]*)\}")


def _annotation_display_text(source: str) -> str:
    """Keep ordinary language legible when MathLive wraps it in text commands."""
    text = _ANNOTATION_TEXT_COMMAND.sub(lambda match: match.group(1), source.strip())
    return text.replace(r"\,", " ").replace(r"\ ", " ")

ThemeMode = Literal["light", "dark", "system"]
EffectiveTheme = Literal["light", "dark"]


_VECTOR_3D_COORDINATE_PATTERN = re.compile(
    r"""
    ^\s*
    (?:[A-Za-z][A-Za-z0-9_]*\s*=\s*)?          # optional v= prefix
    \\?[(\[]?\s*
    (?P<x>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)
    \s*,\s*
    (?P<y>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)
    \s*,\s*
    (?P<z>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)
    \s*\\?[)\]]?\s*$
    """,
    re.VERBOSE,
)
_VECTOR_3D_COLUMN_PATTERN = re.compile(
    r"\\begin\{(?P<delimiter>pmatrix|bmatrix|matrix|vmatrix)\}(?P<values>.*?)"
    r"\\end\{(?P=delimiter)\}",
    re.DOTALL,
)
_VECTOR_3D_FRACTION_PATTERN = re.compile(
    r"^(?P<sign>[+-]?)(?:"
    r"(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|\\frac\{(?P<numerator>[-+]?(?:\d+(?:\.\d*)?|\.\d+))\}"
    r"\{(?P<denominator>[-+]?(?:\d+(?:\.\d*)?|\.\d+))\}"
    r")$"
)


def _parse_3d_vector_component(text: str) -> float | None:
    """Read one finite number or a simple MathLive fraction."""
    compact = str(text).replace(r"\,", "").replace(" ", "")
    match = _VECTOR_3D_FRACTION_PATTERN.fullmatch(compact)
    if match is None:
        return None
    try:
        sign = -1.0 if match.group("sign") == "-" else 1.0
        if match.group("number") is not None:
            value = float(match.group("number"))
        else:
            denominator = float(match.group("denominator"))
            if abs(denominator) <= 1e-18:
                return None
            value = float(match.group("numerator")) / denominator
    except (TypeError, ValueError):
        return None
    value *= sign
    return value if isfinite(value) else None


def parse_3d_vector_endpoint(text: str) -> tuple[float, float, float] | None:
    """Parse a finite endpoint from tuple or column-vector MathLive input."""
    source = str(text)
    column = _VECTOR_3D_COLUMN_PATTERN.search(source)
    if column is not None:
        components = column.group("values").split(r"\\")
        if len(components) != 3:
            return None
        endpoint = tuple(_parse_3d_vector_component(component) for component in components)
        if any(value is None for value in endpoint):
            return None
        values = tuple(float(value) for value in endpoint)
        return values if all(isfinite(value) for value in values) else None

    cleaned = source.replace("\\left", "").replace("\\right", "").replace("{", "").replace("}", "")
    match = _VECTOR_3D_COORDINATE_PATTERN.match(cleaned)
    if match is None:
        return None
    try:
        endpoint = tuple(float(match.group(component)) for component in ("x", "y", "z"))
    except ValueError:
        return None
    return endpoint if all(isfinite(value) for value in endpoint) else None


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
            # BlockingQueuedConnection 不会传播槽函数异常，需显式返回。
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
        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(callback)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # 显示和恢复时同步 Qt 窗口映射状态，避免渲染停滞。
        if event.type() == QEvent.Type.Show:
            if isinstance(watched, QWidget):
                watched.setAttribute(Qt.WidgetAttribute.WA_Mapped)

        if event.type() == QEvent.Type.WindowStateChange and isinstance(event, QWindowStateChangeEvent):
            if (event.oldState() & Qt.WindowState.WindowMinimized) and not watched.isMinimized():
                if isinstance(watched, QWidget):
                    watched.setAttribute(Qt.WidgetAttribute.WA_Mapped)
                # 合并连续恢复事件，避免重复重绘。
                self._restore_timer.start(150)
        return False


class _GeometryInputFilter(QObject):
    """拦截二维定点缩放和激活工具的视口鼠标、键盘事件。"""

    def __init__(self, owner: "MainWindow", parent: QObject) -> None:
        super().__init__(parent)
        self.owner = owner

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # 视口交互始终路由到最先接收事件的窗格。
        container = getattr(self.owner, "scene_pane_widget", None)
        if container is not None and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.FocusIn,
            QEvent.Type.Wheel,
        ):
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
        if event.type() == QEvent.Type.Leave:
            return self.owner._handle_geometry_mouse_leave()
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
    teaching_2d: tuple[tuple[str, dict[str, object]], ...] = ()
    vector_additions: tuple[dict[str, object], ...] = ()


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
    vector_additions: tuple[dict[str, object], ...] = ()


def _coerce_coordinate_transform(value: object) -> CoordinateTransform | None:
    """Read a persisted 2 x 2 transform without allowing malformed pane data."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    rows: list[tuple[float, float]] = []
    try:
        for row in value:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                return None
            numbers = tuple(float(item) for item in row)
            if not all(isfinite(item) for item in numbers):
                return None
            rows.append((numbers[0], numbers[1]))
    except (TypeError, ValueError):
        return None
    matrix = (rows[0], rows[1])
    if abs(matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) <= 1e-12:
        return None
    return matrix


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
        self._vector_additions: list[dict[str, object]] = []
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
        self._two_d_coordinate_transform: CoordinateTransform | None = _coerce_coordinate_transform(
            pane.scene_2d.get("coordinate_transform")
        )
        self._two_d_show_original_coordinate_system = pane.scene_2d.get(
            "show_original_coordinate_system", True
        ) is not False
        self._two_d_show_transformed_coordinate_system = pane.scene_2d.get(
            "show_transformed_coordinate_system", True
        ) is not False
        try:
            stored_grid_range = float(pane.scene_2d.get("matrix_transform_grid_range", 5.0))
        except (TypeError, ValueError):
            stored_grid_range = 5.0
        self._matrix_transform_grid_range = max(1.0, min(stored_grid_range, 100.0))
        self._two_d_original_guides: TwoDGuides | None = None
        self._three_d_axes: ThreeDAxes | None = None
        self._three_d_spacing: float | None = None
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
        self._pending_point_tool_point_id: str | None = None
        self._pending_point_tool_linear_id: str | None = None
        self._snap_to_grid = False
        self._dragging_point_id: str | None = None
        self._dragging_annotation_id: str | None = None
        self._selection_start: tuple[float, float] | None = None
        self._selection_pixel_start: QPoint | None = None
        self._selection_band: QRubberBand | None = None
        self._drag_moved = False
        self._drag_start_geometry_state: _GeometryHistoryState | None = None
        self._dragging_3d_annotation_alias: str | None = None
        self._dragging_3d_annotation_moved = False
        self._drag_start_3d_annotation_state: _SceneCommandState | None = None
        self._hovered_3d_annotation_alias: str | None = None
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
        if runtime.scene_mode is not SceneMode.TWO_D:
            return ""
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
        if self._pane_scene(pane.pane_id).scene_mode is not SceneMode.TWO_D:
            return []
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
                    offset=tuple(repeat * (runtime._two_d_guide_spacing or 1.0) for _ in range(2)) if same_pane else (0, 0),
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
        *,
        enable_teaching_authoring: bool = False,
    ) -> None:
        self.theme_mode = theme_mode
        self.effective_theme = effective_theme
        self.pane_manager = ScenePaneManager()
        self._scene_target_pane_id: str | None = None
        self._transaction_pane_id: str | None = None
        self._transaction_scene: _PaneSceneRuntime | None = None
        self._initialize_default_scene()
        self._lighting_dialog: LightingDialog | None = None
        self.latex_parser = LatexParser()
        self._active_linear_algebra_topic_id: str | None = None
        self._active_linear_algebra_compiled: CompiledVisualization | None = None
        self._active_linear_algebra_explanation_case: object | None = None
        self._active_linear_algebra_category: str | None = None
        self._active_linear_algebra_source_diagnostic: object | None = None
        self._teaching_authoring_enabled = enable_teaching_authoring
        self._active_linear_algebra_stage_id: str | None = None
        self._active_linear_algebra_stage_metadata: StoryboardVisibility | None = None
        self._pending_curriculum_transaction = None
        self._pending_curriculum_bundle = None
        self._pending_curriculum_explanation = None
        self._pending_curriculum_plan = None
        self._pending_curriculum_previous_scene = None
        self._pending_curriculum_host_executed = False
        self._pending_curriculum_finalized = False
        self._linear_algebra_load_generation = 0
        self._pending_linear_algebra_scene_request: dict[str, object] | None = None
        self._linear_algebra_source_repository_instance: LectureSourceRepository | None = None
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

    def _initialize_default_scene(self) -> None:
        """Prepare a blank 3-D workspace; axes are rendered separately.

        Built-in surfaces remain available from the algebra menu, but a new
        workspace must not inject a sample function before the user asks for
        one.  The 3-D renderer creates the coordinate system independently.
        """
        scene = self._pane_scene()
        scene.scene_mode = SceneMode.THREE_D
        scene.layers = []

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
        snapshot = self._scene_snapshot_from_state(self._capture_scene_command_state()).to_dict()
        pane.scene_2d = {
            **pane.scene_2d,
            "geometry": snapshot["geometry"], "curves": snapshot["curves"],
            "object_order": list(scene._two_d_object_order),
            "areas": snapshot["metadata"].get("areas", []),
            "teaching_2d": snapshot["metadata"].get("teaching_2d", []),
            "vector_additions": snapshot["metadata"].get("vector_additions", []),
        }
        pane.scene_3d = {
            **pane.scene_3d,
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
                camera["view_angle"] = float(getattr(renderer.camera, "view_angle", 30.0))
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
                    # 无容器的轻量宿主保留一个窗格。
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

        # 仅重建子控件表面，避免最大化窗口的尺寸和标题栏短暂失步。

        algebra_panel = getattr(self, "algebra_panel", None)
        if algebra_panel is not None:
            rebuild_algebra = getattr(algebra_panel, "rebuild_render_surface", None)
            if callable(rebuild_algebra):
                rebuild_algebra()

        panel = getattr(self, "agent_panel", None)
        if panel is not None:
            rebuild_agent = getattr(panel, "rebuild_render_surface", None)
            if callable(rebuild_agent):
                rebuild_agent()
            else:
                view = getattr(panel, "view", None)
                if view is not None:
                    view.show()
                    rebuild_web_surface(view)
                    view.update()
        window.update()
        QTimer.singleShot(120, self._deferred_render_surfaces)

    _WEB_SURFACE_RETRY_MS = 600
    _WEB_SURFACE_RETRY_COUNT = 1  # 映射状态已同步，只保留一次兜底重试。

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
        # 延迟检查一次，兼容 Windows 恢复动画。
        self._schedule_web_surface_retries(retry_count=self._WEB_SURFACE_RETRY_COUNT)

    def _schedule_web_surface_retries(self, retry_count: int) -> None:
        """调度 WebEngine 表面重建重试。"""
        if retry_count <= 0:
            return
        delay_ms = self._WEB_SURFACE_RETRY_MS * (self._WEB_SURFACE_RETRY_COUNT - retry_count + 1)
        QTimer.singleShot(delay_ms, lambda: self._retry_web_render_surfaces(retry_count - 1))

    def _retry_web_render_surfaces(self, remaining_retries: int) -> None:
        """重建 WebEngine 表面并继续剩余重试。"""
        self._rebuild_web_render_surfaces()
        if remaining_retries > 0:
            self._schedule_web_surface_retries(remaining_retries)

    def _rebuild_web_render_surfaces(self) -> None:
        """重新分配两侧 WebEngine 面板的合成表面，不重载文档。

        最小化会释放窗口的渲染表面，Chromium 恢复后不会自动重建；仅调用
        ``update()`` 无法让页面重新合成，代数区与数学解释区因此永久空白。
        """
        window = getattr(self, "window", None)
        if window is None or window.isMinimized():
            return
        for panel in (getattr(self, "algebra_panel", None), getattr(self, "agent_panel", None)):
            if panel is None:
                continue
            rebuild = getattr(panel, "rebuild_render_surface", None)
            if callable(rebuild):
                rebuild()
                continue
            rebuild_web_surface(getattr(panel, "view", None))

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
        self.title_bar.right_panel_toggle_requested.connect(self._toggle_agent_panel)
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
        viewport_host = self.window.findChild(QWidget, "viewportHost")
        if viewport_host is not None:
            self.algebra_panel.set_floating_keyboard_anchor(viewport_host)
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
        self.status_bar.theme_cycle_requested.connect(self.cycle_theme_mode)
        self.status_bar.set_scene_mode(self._pane_scene().scene_mode)
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
            if topic_id == getattr(self, "_active_linear_algebra_topic_id", None):
                self._on_teaching_case_focus(pane_id, stage_id or "")
            return
        if message_type == "set_math_case_pane_count":
            topic_id = str(payload.get("case_id", ""))
            pane_count = payload.get("pane_count")
            if topic_id == getattr(self, "_active_linear_algebra_topic_id", None) and type(pane_count) is int:
                self._set_teaching_case_pane_count(pane_count)
            return
        if message_type == "math_case_preview_ready":
            self._start_deferred_linear_algebra_scene_load(
                str(payload.get("case_id", "")),
                str(payload.get("preview_token", "")),
            )
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
                # 运行时重启后按持久化轮次恢复一次性审批票据。
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
            pane_id = (turn.validation or {}).get("pane_id") or (turn.scene_before.active_pane_id if turn.scene_before else None)
            try:
                validation = self._agent_runtime.execute(CommandPlan.from_dict(turn.command_plan), expected_scene_fingerprint=fingerprint,
                                                         **({"pane_id": pane_id} if pane_id is not None else {}))
                if validation is not None and not validation.valid:
                    raise CommandError("；".join(validation.messages))
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
            on_pane_viewport_changed=self._on_pane_viewport_changed,
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
        # 视口工具栏的 AI 快捷入口与标题栏开关并存，均切换同一个右侧面板。
        self.agent_button = QToolButton(self.viewport_toolbar)
        self.agent_button.setObjectName("agentButton")
        self.agent_button.setToolTip("AI 教学助手")
        self.agent_button.setAccessibleName("AI 教学助手")
        self.agent_button.setCheckable(True)
        apply_icon(
            self.agent_button,
            "sparkles",
            icon_color(getattr(self, "effective_theme", "light")),
            icon_size=16,
            hit_size=36,
        )
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
        self.three_d_geometry_toolbar = ThreeDGeometryToolbar(
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
        self.two_d_geometry_toolbar.function_requested.connect(self._open_function_catalog)
        self.two_d_geometry_toolbar.snap_toggled.connect(self._set_snap_to_grid)
        self.two_d_geometry_toolbar.undo_requested.connect(self._undo_2d_geometry)
        self.two_d_geometry_toolbar.redo_requested.connect(self._redo_2d_geometry)
        self.three_d_geometry_toolbar.vector_requested.connect(self._on_3d_vector_requested)
        self.three_d_geometry_toolbar.function_requested.connect(self._open_function_catalog)
        self.three_d_geometry_toolbar.annotation_requested.connect(self._on_3d_annotation_requested)
        self.three_d_geometry_toolbar.undo_requested.connect(self._undo_2d_geometry)
        self.three_d_geometry_toolbar.redo_requested.connect(self._redo_2d_geometry)
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
        # 文本输入框和 WebEngine 编辑器使用各自的剪贴板。
        for shortcut in (self._copy_2d_shortcut, self._paste_2d_shortcut):
            shortcut.setParent(getattr(self, "viewport_host", self.window))
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

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
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            # 兼容只在此处上报最终相机状态的后端。
            self._refresh_3d_arrows_for_camera()
            self._save_current_view_state()
            return
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
        if self._pane_scene()._viewport_refreshing:
            return
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            # 箭杆已按屏幕像素计宽，只需更新箭头锥体。
            self._refresh_3d_arrows_for_camera()
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
        # 停止缩放或旋转后再重采样，避免交互中频繁重建曲面。
        if self._pane_scene()._viewport_refreshing or self._pane_scene()._viewport_refresh_timer is None:
            return
        self._pane_scene()._viewport_refresh_pending = True
        self._pane_scene()._viewport_refresh_timer.start()

    def _position_viewport_overlays(self) -> None:
        if not hasattr(self, "viewport_toolbar"):
            return
        host = self.viewport_host
        toolbar_width = self.viewport_toolbar.width()
        toolbar_height = self.viewport_toolbar.height()
        self.viewport_toolbar.move(
            max(8, host.width() - toolbar_width - 12),
            max(8, (host.height() - toolbar_height) // 2),
        )
        self.viewport_toolbar.raise_()
        # 左侧工具固定在整个视口的左侧中部，不随焦点窗格移动。
        for toolbar in (
            getattr(self, "two_d_geometry_toolbar", None),
            getattr(self, "three_d_geometry_toolbar", None),
        ):
            if toolbar is None:
                continue
            toolbar.position_in_host(host.rect())
            toolbar.raise_()
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
        # 可编辑代数标签跟随场景焦点。
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
        panel.matrix_transform_requested.connect(self._apply_matrix_transform_from_tab)
        panel.matrix_transform_settings_requested.connect(self._apply_matrix_transform_from_tab)
        panel.matrix_transform_visibility_requested.connect(self._set_matrix_coordinate_system_visibility)
        panel.matrix_transform_delete_requested.connect(self._delete_matrix_transform_grid)
        panel.builtin_requested.connect(self._add_builtin_surface)
        panel.lighting_requested.connect(self._show_lighting_dialog)
        panel.pane_update_requested.connect(self._update_formula_for_scene)
        panel.three_d_vector_updated.connect(self._update_3d_vector_from_algebra)
        panel.annotation_updated.connect(self._update_annotation_from_algebra)
        panel.pane_visibility_requested.connect(self._reveal_algebra_pane)
        panel.delete_requested.connect(self._remove_layer_for_scene)
        panel.visibility_changed.connect(self._set_layer_visibility)
        panel.intersections_visibility_changed.connect(self._set_surface_intersections_visibility)
        panel.intersection_color_changed.connect(self._set_surface_intersection_color)
        panel.color_changed.connect(self._set_layer_color)
        panel.opacity_changed.connect(self._set_surface_opacity)
        panel.line_width_changed.connect(self._set_curve_line_width)
        panel.range_changed.connect(self._set_layer_range)
        panel.parameter_changed.connect(self._set_layer_parameter)
        panel.status_changed.connect(self._show_status_message)
        # 扩展程序仍可能连接旧信号；界面中已不再提供对应的工具栏操作。
        panel.auto_intersections_changed.connect(self._set_auto_intersections)
        panel.manual_intersection_requested.connect(self._add_manual_intersection)

    def _show_status_message(self, message: str, _is_error: bool = False) -> None:
        """Render every scene/action description in the single bottom status area."""
        status_bar = getattr(self, "status_bar", None)
        if status_bar is not None:
            status_bar.set_render_status(message)

    def _open_function_catalog(self, anchor: QPoint | None = None) -> None:
        """Open the function catalog for the active 2-D or 3-D scene."""
        self.pane_manager.activate_for_tool()
        self.algebra_panel.set_catalog_entries(catalog_entries(self._pane_scene().scene_mode))
        self.algebra_panel.open_function_catalog(anchor)

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
            # The 2-D toolbar is shared by all visible panes, while the
            # concrete mouse-tool state lives on each pane runtime.  A case
            # pane that was materialized after the first pane therefore used
            # to have no active tool at all: clicking its point C (or any
            # other point) was passed through to PyVista instead of the
            # selection/drag handler.  Mirror the shared toolbar selection
            # into the newly focused pane before routing the click.
            if mode is SceneMode.TWO_D:
                runtime = self._pane_scene()
                toolbar = getattr(self, "two_d_geometry_toolbar", None)
                shared_tool = getattr(toolbar, "_active_tool", None)
                linear_tools = {
                    "addition", "angle", "projection", "polygon",
                    "transform", "subspace", "area",
                }
                basic_tools = {
                    "select", "point", "annotation", "line", "segment",
                    "dashed_segment", "ray", "vector",
                }
                if shared_tool in linear_tools:
                    runtime._active_2d_tool = None
                    runtime._active_linear_algebra_tool = shared_tool
                elif shared_tool in basic_tools:
                    runtime._active_2d_tool = shared_tool
                    runtime._active_linear_algebra_tool = None
                elif (
                    runtime._active_2d_tool is None
                    and runtime._active_linear_algebra_tool is None
                    and getattr(self._pane(pane_id), "source", "user") == "case"
                ):
                    # Case panes open in the same editable/selectable state as
                    # the first pane, even when the toolbar has no explicit
                    # selection (for example after a pane was restored).
                    runtime._active_2d_tool = "select"
            panel.set_scene_mode(mode)
            panel.set_layers(
                self._two_d_panel_layers() if mode is SceneMode.TWO_D else self._three_d_panel_layers()
            )
        self._sync_teaching_algebra_panel_visibility(pane_id)
        self._sync_scene_controls()

    def _sync_teaching_algebra_panel_visibility(self, pane_id: str | None = None) -> None:
        """Keep the algebra column while a lecture is loaded; hide it only when a focused case pane is genuinely empty."""
        panel = getattr(self, "algebra_panel", None)
        if panel is None:
            return
        manager = getattr(self, "pane_manager", None)
        active_pane_id = pane_id or getattr(manager, "active_pane_id", None)
        is_case_pane = active_pane_id in tuple(getattr(self, "_teaching_case_pane_ids", ()))
        # Registering a case pane and materializing its renderer happen in
        # separate callbacks.  During that short hand-off the panel has no
        # layers yet, but hiding it would let the VTK viewport expand into the
        # left column for one frame.  Keep the column stable until the final
        # layer/matrix synchronization decides its steady-state visibility.
        materializing = getattr(self, "_teaching_case_materializing", False)
        visible = True
        if is_case_pane and not materializing:
            has_layers = bool(getattr(panel, "_layers", ()))
            matrix_editor = getattr(panel, "matrix_transform_editor", None)
            has_matrix_editor = bool(matrix_editor(active_pane_id)) if callable(matrix_editor) else False
            # 已加载的讲义把讲解内容放在代数区。切换 2D/3D 后当前案例可能暂时没有
            # 可显示的场景图元，但代数区不能被中间视口吞掉，否则讲解列会整列消失。
            loaded_lecture = bool(
                getattr(self, "_active_linear_algebra_topic_id", None)
                and getattr(self, "_active_linear_algebra_explanation_case", None) is not None
            )
            visible = has_layers or has_matrix_editor or loaded_lecture
        set_panel_visible = getattr(panel, "setVisible", None)
        if callable(set_panel_visible):
            set_panel_visible(visible)
        resize_handle = getattr(self, "algebra_resize_handle", None)
        set_handle_visible = getattr(resize_handle, "setVisible", None)
        if callable(set_handle_visible):
            set_handle_visible(visible)

    # AI 场景命令适配层

    def _request_agent_plan(self, prompt: str, *, session_id: str | None = None) -> None:
        if self._agent_thread is not None and self._agent_thread.isRunning():
            return
        active_session_id = session_id or self.agent_panel.active_session_id
        turn_id = uuid4().hex
        # 整轮命令锁定目标窗格，不受后续焦点变化影响。
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
            self.status_bar.set_render_status("AI 助手正在生成…")
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
            pane_id=locked_pane_id,
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
            self.status_bar.set_render_status("AI 助手已完成响应")
        if result.turn_id and result.status == "completed":
            self._agent_session_store.update_turn_scene_snapshots(
                result.turn_id,
                scene_after=self._scene_snapshot_from_current_state(),
                status=result.status,
            )

    def _receive_runtime_error(self, message: str) -> None:
        self.agent_sidebar.set_busy(False)
        if hasattr(self, "status_bar"):
            self.status_bar.set_render_status("AI 助手响应失败")
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
            scene._agent_areas_render_pending = False
            scene._agent_points3d_render_pending = False
            scene._scene_geometry_batch_controller = None
            self._ensure_scene_geometry_batch()
            # 即使窗格提前删除，也要保留事务记录供提交或回滚。
            self._transaction_scene = scene
            self._transaction_pane_id = self._pane().pane_id

    def check_scene_fingerprint(self, expected: str, pane_id: str | None = None) -> bool:
        with self._using_pane(pane_id):
            snapshot = self._scene_snapshot_from_current_state()
            return (snapshot.fingerprint_for_pane(pane_id) if pane_id and snapshot.panes else snapshot.fingerprint()) == expected

    def commit_scene_command_transaction(self, pane_id: str | None = None) -> None:
        with self._using_pane(self._command_pane_id(pane_id)):
            scene = self._pane_scene()
            if not scene._scene_command_active or scene._scene_command_snapshot is None:
                return
            after = self._capture_scene_command_state()
            self._end_scene_geometry_batch(scene)
            # 先发布事务，再刷新事务期间延迟的聚合演员。
            scene._scene_command_active = False
            if getattr(scene, "_agent_areas_render_pending", False):
                scene._agent_areas_render_pending = False
                self._render_agent_areas(render=False)
            if getattr(scene, "_agent_points3d_render_pending", False):
                scene._agent_points3d_render_pending = False
                self._render_agent_points3d(render=False)
            self._sync_panel_layers(self._three_d_panel_layers() if scene.scene_mode is SceneMode.THREE_D else self._two_d_panel_layers())
            renderer = self._pane_renderer()
            renderer.render()
            if scene.scene_mode is SceneMode.THREE_D:
                # 首帧后再重建箭头，使其使用真实相机和视口尺寸。
                self._refresh_3d_arrows_for_camera()
                renderer.render()
            self._sync_pane_state()
            if after != scene._scene_command_snapshot:
                scene._scene_command_undo_stack.append(scene._scene_command_snapshot)
                scene._scene_command_redo_stack.clear()
            scene._scene_command_snapshot = None
            self._transaction_pane_id = None
            self._transaction_scene = None
            self._update_geometry_history_controls()

    def rollback_scene_command_transaction(self, pane_id: str | None = None) -> None:
        transaction_pane = getattr(self, "_transaction_pane_id", None)
        if transaction_pane is not None and pane_id is not None and pane_id != transaction_pane:
            # 目标窗格不匹配时保留当前事务及其快照。
            raise CommandError("场景命令不能跨越当前事务的目标窗格。")
        scene = getattr(self, "_transaction_scene", None)
        try:
            with self._using_pane(self._command_pane_id(pane_id)):
                scene = self._pane_scene()
                self._end_scene_geometry_batch(scene)
                snapshot = scene._scene_command_snapshot
                if snapshot is not None:
                    self._restore_scene_command_state(snapshot)
                self._sync_pane_state()
        finally:
            # 窗格删除后解析也可能失败，清理逻辑需覆盖整个恢复过程。
            if scene is not None:
                self._end_scene_geometry_batch(scene)
                scene._scene_command_snapshot = None
                scene._scene_command_active = False
                scene._agent_areas_render_pending = False
                scene._agent_points3d_render_pending = False
            self._transaction_pane_id = None
            self._transaction_scene = None
            self._update_geometry_history_controls()

    def _ensure_scene_geometry_batch(self) -> None:
        """Keep one geometry-controller batch open for a command transaction."""
        scene = self._pane_scene()
        controller = getattr(scene, "geometry_controller", None)
        current = getattr(scene, "_scene_geometry_batch_controller", None)
        if controller is current:
            return
        if current is not None:
            end_batch = getattr(current, "end_batch_update", None)
            if callable(end_batch):
                end_batch()
        scene._scene_geometry_batch_controller = controller
        begin_batch = getattr(controller, "begin_batch_update", None)
        if callable(begin_batch):
            begin_batch()

    @staticmethod
    def _end_scene_geometry_batch(scene: object) -> None:
        controller = getattr(scene, "_scene_geometry_batch_controller", None)
        if controller is not None:
            end_batch = getattr(controller, "end_batch_update", None)
            if callable(end_batch):
                end_batch()
        setattr(scene, "_scene_geometry_batch_controller", None)

    def _render_scene_after_command(self) -> None:
        """Render standalone mutations, but let a command plan render once on commit."""
        if getattr(self._pane_scene(), "_scene_command_active", False):
            return
        self._pane_renderer().render()

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
            vector_additions=tuple(dict(relation) for relation in getattr(self._pane_scene(), "_vector_additions", ())),
        )

    @staticmethod
    def _snapshot_record(value: object, *, object_type: str | None = None) -> dict[str, object]:
        record = asdict(value)
        # Point2D 的 `kind` 由构造器恢复，Linear2D 则把它作为数据。
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
            state = pane.to_snapshot()
            if pane.runtime is not None:
                with self._using_pane(pane_id):
                    pane_scene = self._scene_snapshot_from_state(self._capture_scene_command_state())
                state["scene_2d"].update({"geometry": list(pane_scene.geometry), "curves": list(pane_scene.curves),
                                          **{key: pane_scene.metadata.get(key, []) for key in ("object_order", "areas", "teaching_2d", "vector_additions")}})
                state["scene_3d"].update({"layers": list(pane_scene.layers),
                                          **{key: pane_scene.metadata.get(key, []) for key in ("points3d", "geometry_3d")}})
            else:
                pane_scene = self._snapshot_from_pane_data(state)
            renderer = pane.renderer_2d if pane.scene_mode == "2d" else pane.renderer_3d
            if renderer is not None:
                camera = dict(state[f"camera_{pane.scene_mode}"])
                position = getattr(renderer, "camera_position", None)
                if position is not None:
                    camera["position"] = [list(vector) for vector in position]
                renderer_camera = getattr(renderer, "camera", None)
                if renderer_camera is not None:
                    if pane.scene_mode == "2d":
                        camera["parallel_scale"] = float(renderer_camera.parallel_scale)
                    else:
                        camera["view_angle"] = float(getattr(renderer_camera, "view_angle", 30.0))
                state[f"camera_{pane.scene_mode}"] = camera
            pane_scene = replace(pane_scene, camera=state[f"camera_{pane.scene_mode}"])
            pane_records.append({"pane_id": pane_id, "name": pane.name, "source": pane.source, "source_id": pane.source_id,
                                 "visible": pane_id in manager.visible_pane_ids(), "state": state, "snapshot": pane_scene.to_dict()})
        target = self._pane().pane_id
        active = SceneSnapshot.from_dict(next(record["snapshot"] for record in pane_records if record["pane_id"] == target))
        teaching_pane_ids = tuple(getattr(self, "_teaching_case_pane_ids", ()))
        return replace(active, panes=tuple(pane_records), active_pane_id=manager.active_pane_id,
                       metadata={**active.metadata, "workspace": manager.workspace_metadata(),
                                 "teaching_case": {
                                     "pane_ids": list(teaching_pane_ids),
                                     "stage_refs": {pane_id: list(refs) for pane_id, refs in
                                                    getattr(self, "_teaching_case_stage_refs", {}).items()
                                                    if pane_id in teaching_pane_ids},
                                     "topic_id": getattr(self, "_active_linear_algebra_topic_id", None),
                                     "stage_id": getattr(self, "_active_linear_algebra_stage_id", None),
                                 }})

    @staticmethod
    def _snapshot_from_pane_data(state: dict) -> SceneSnapshot:
        scene_2d, scene_3d = state["scene_2d"], state["scene_3d"]
        return SceneSnapshot(
            scene_mode=state["scene_mode"], geometry=tuple(scene_2d.get("geometry", ())),
            curves=tuple(scene_2d.get("curves", ())), layers=tuple(scene_3d.get("layers", ())),
            metadata={**{key: scene_2d.get(key, []) for key in ("object_order", "areas", "teaching_2d", "vector_additions")},
                      **{key: scene_3d.get(key, []) for key in ("points3d", "geometry_3d")}},
            camera=state[f"camera_{state['scene_mode']}"])

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
            "vector_additions": [dict(relation) for relation in state.vector_additions],
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
        vector_additions = tuple(
            dict(item) for item in metadata.get("vector_additions", [])
            if isinstance(item, dict)
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
            vector_additions=vector_additions,
        )

    def _restore_agent_scene_snapshot(self, snapshot: SceneSnapshot) -> None:
        manager = getattr(self, "pane_manager", None)
        records = snapshot.panes
        if manager is None or not records:
            self._restore_scene_command_state(self._state_from_scene_snapshot(snapshot))
            return
        states, scene_states = [], {}
        for record in records:
            if "state" in record:
                pane = ScenePaneState.from_snapshot(record["state"])
                scene_snapshot = self._snapshot_from_pane_data(pane.to_snapshot())
            else:
                # 兼容仅保存旧窗格视图的历史轮次。
                scene_snapshot = SceneSnapshot.from_dict(record["snapshot"])
                pane = ScenePaneState(record["pane_id"], record.get("name", record["pane_id"]),
                                      source=record.get("source", "user"), source_id=record.get("source_id"),
                                      scene_mode=scene_snapshot.scene_mode)
                metadata = scene_snapshot.metadata
                pane.scene_2d = {"geometry": list(scene_snapshot.geometry), "curves": list(scene_snapshot.curves),
                                 **{key: metadata.get(key, []) for key in ("object_order", "areas", "teaching_2d", "vector_additions")}}
                pane.scene_3d = {"layers": list(scene_snapshot.layers),
                                 **{key: metadata.get(key, []) for key in ("points3d", "geometry_3d")}}
                setattr(pane, f"camera_{pane.scene_mode}", scene_snapshot.camera)
            if pane.pane_id != record["pane_id"]:
                raise ValueError("snapshot pane ID mismatch")
            states.append(pane)
            scene_states[pane.pane_id] = self._state_from_scene_snapshot(scene_snapshot)
        workspace = snapshot.metadata.get("workspace", {})
        visible_ids = workspace.get("visible_pane_ids", [record["pane_id"] for record in records if record.get("visible") is True])
        if not visible_ids:
            visible_ids = [snapshot.active_pane_id or states[0].pane_id]
        active = snapshot.active_pane_id or visible_ids[0]
        removed_ids = set(manager.panes) - set(scene_states)
        was_blocked = manager.blockSignals(True)
        try:
            manager.restore_workspace(states, visible_ids, active,
                                      lecture_case_ids=tuple(workspace.get("lecture_case_ids", ())),
                                      lecture_user_visible=(tuple(workspace["lecture_user_visible"])
                                                            if workspace.get("lecture_user_visible") is not None else None))
            for pane in manager.panes.values():
                with self._using_pane(pane.pane_id):
                    runtime = self._pane_scene()
                    runtime._two_d_camera_position = pane.camera_2d.get("position")
                    runtime._two_d_parallel_scale = pane.camera_2d.get("parallel_scale")
                    runtime._three_d_camera_position = pane.camera_3d.get("position")
                    self._restore_scene_command_state(scene_states[pane.pane_id])
                    renderer = self._pane_renderer(required=False)
                    camera = pane.camera_2d if pane.scene_mode == "2d" else pane.camera_3d
                    if renderer is not None:
                        if camera.get("position") is not None:
                            renderer.camera_position = camera["position"]
                        if pane.scene_mode == "2d" and "parallel_scale" in camera:
                            renderer.camera.parallel_scale = camera["parallel_scale"]
                        elif pane.scene_mode == "3d" and "view_angle" in camera:
                            renderer.camera.view_angle = camera["view_angle"]
        finally:
            manager.blockSignals(was_blocked)
        teaching = snapshot.metadata.get("teaching_case", {})
        lecture_ids = tuple(workspace.get("lecture_case_ids", ()))
        if lecture_ids:
            restored_ids = [pane_id for pane_id in teaching.get("pane_ids", lecture_ids)
                            if pane_id in manager.panes and pane_id in lecture_ids]
            self._teaching_case_pane_ids = restored_ids
            raw_refs = teaching.get("stage_refs", {})
            self._teaching_case_stage_refs = {
                pane_id: tuple(raw_refs.get(pane_id, ())) for pane_id in restored_ids
            }
            topic_id = teaching.get("topic_id")
            self._active_linear_algebra_topic_id = topic_id if isinstance(topic_id, str) and topic_id else None
            # 快照只记录讲义身份，不能复用恢复前可能属于其他主题的编译对象。
            self._active_linear_algebra_compiled = (
                self._resolve_linear_algebra_compiled(self._active_linear_algebra_topic_id)
                if self._active_linear_algebra_topic_id else None
            )
            stage_id = teaching.get("stage_id")
            self._active_linear_algebra_stage_id = stage_id if isinstance(stage_id, str) and stage_id else None
            self._hidden_linear_algebra_aliases = set()
            if self._active_linear_algebra_compiled is not None and self._active_linear_algebra_stage_id:
                try:
                    all_aliases, visible_aliases = storyboard_visibility(
                        self._active_linear_algebra_compiled, self._active_linear_algebra_stage_id
                    )
                    self._hidden_linear_algebra_aliases = set(all_aliases) - set(visible_aliases)
                except ValueError:
                    # 旧快照引用已删除阶段时仍保留已恢复窗格。
                    self._active_linear_algebra_stage_id = None
        else:
            # 恢复普通工作区时清除失效的案例标识。
            self._teaching_case_pane_ids = []
            self._teaching_case_stage_refs = {}
            self._active_linear_algebra_topic_id = None
            self._active_linear_algebra_compiled = None
            self._active_linear_algebra_stage_id = None
            self._hidden_linear_algebra_aliases = set()
        for pane_id in removed_ids:
            manager.pane_deleted.emit(pane_id)
        manager.workspace_restored.emit()
        manager.active_pane_changed.emit(active)
        manager.active_pane_id_changed.emit(active)

    def _resolve_linear_algebra_compiled(self, topic_id: str) -> CompiledVisualization | None:
        """Rebuild the runtime-only lecture compiler state for a snapshot."""
        try:
            registry = catalog_registry()
            store = runtime_teaching_store()
            source_repository = self._linear_algebra_source_repository()
            self._synchronize_linear_algebra_authoring(
                topic_id,
                registry=registry,
                store=store,
                source_repository=source_repository,
            )
            return registry.resolve_bundle(
                topic_id,
                artifact_store=store,
                source_repository=source_repository,
            ).compiled
        except (KeyError, ValueError, OSError):
            return None

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
        self._pane_scene()._vector_additions = [dict(relation) for relation in state.vector_additions]
        self._pane_scene()._pending_point_tool_point_id = None
        self._pane_scene()._pending_point_tool_linear_id = None
        self._pane_scene()._dragging_3d_annotation_alias = None
        self._pane_scene()._dragging_3d_annotation_moved = False
        self._pane_scene()._drag_start_3d_annotation_state = None
        self._pane_scene()._hovered_3d_annotation_alias = None
        if self._pane_scene().scene_mode is not state.scene_mode:
            # 隐藏窗格尚无渲染器，只恢复状态，待创建时再渲染。
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
            # 无渲染器时以模型为准，窗格显示后再重建控制器。
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
        coordinate_transform = self._pane_scene()._two_d_coordinate_transform
        curve_sampling_bounds = (
            coordinate_source_bounds(sampling_bounds, coordinate_transform)
            if coordinate_transform is not None
            else sampling_bounds
        )
        self._pane_scene().curve_domain = self._curve_sampling_domain(curve_sampling_bounds)
        self._pane_scene().curve_controller = CurveSceneController(
            self._pane_renderer(),
            self._pane_scene().curve_domain,
            coordinate_transform,
        )
        self._pane_scene().geometry_controller = GeometrySceneController(self._pane_renderer(), visible)
        for layer in self._pane_scene().curve_layers:
            self._pane_scene().curve_controller.add_layer(layer)
        geometry_controller = self._pane_scene().geometry_controller
        batch_update = getattr(geometry_controller, "batch_update", None)
        geometry_batch = batch_update() if callable(batch_update) else nullcontext()
        with geometry_batch:
            for point in self._pane_scene().geometry_points:
                geometry_controller.add_point(point)
            for linear in self._pane_scene().linear_objects:
                geometry_controller.add_linear(linear)
            for annotation in getattr(self._pane_scene(), "annotations", []):
                geometry_controller.add_annotation(annotation)
        self.algebra_panel.set_layers(self._two_d_panel_layers())

    def apply_scene_command(self, operation: dict[str, object], pane_id: str | None = None) -> None:
        with self._using_pane(self._command_pane_id(pane_id)):
            self._pane_renderer()
            self._apply_scene_command(operation)
            if getattr(self._pane_scene(), "_scene_command_active", False):
                # `scene.set_mode` 可能替换控制器，需重新绑定批处理。
                self._ensure_scene_geometry_batch()
            # 命令计划只在事务结束时写一次快照，避免随对象数平方增长。
            if not getattr(self._pane_scene(), "_scene_command_active", False):
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
        if name == "linear_algebra.coordinate_transform":
            if self._pane_scene().scene_mode is not SceneMode.TWO_D:
                raise CommandError("坐标系矩阵变换需要处于二维场景。")
            matrix = tuple(
                tuple(float(value) for value in row) for row in operation["matrix"]  # type: ignore[index]
            )
            determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
            if abs(determinant) <= 1e-12:
                raise CommandError("坐标系矩阵变换必须使用可逆矩阵。")
            runtime = self._pane_scene()
            runtime._two_d_coordinate_transform = matrix  # type: ignore[assignment]
            runtime._two_d_show_original_coordinate_system = bool(operation.get("show_original", True))
            runtime._two_d_show_transformed_coordinate_system = bool(operation.get("show_transformed", True))
            pane = self._pane()
            pane.scene_2d["coordinate_transform"] = [list(matrix[0]), list(matrix[1])]
            pane.scene_2d["show_original_coordinate_system"] = runtime._two_d_show_original_coordinate_system
            pane.scene_2d["show_transformed_coordinate_system"] = runtime._two_d_show_transformed_coordinate_system
            # 坐标变换复用矩阵编辑器管线，不额外叠加教学网格。
            self._render_2d_scene()
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
        if name == "geometry.quadratic_level_set" and self._pane_scene().geometry3d_controller is not None:
            controller = self._pane_scene().geometry3d_controller
            controller.add_quadratic_mesh(str(operation.get("alias", "quadratic")), operation.get("mesh_vertices", ()), operation.get("mesh_faces", ()))
            return
        if name in {"geometry.projection3d", "geometry.orthogonalization", "geometry.spectrum"}:
            controller = self._pane_scene().geometry3d_controller
            if controller is None:
                raise CommandError("该教学几何操作需要处于三维场景。")
            alias = str(operation.get("alias", "spectrum"))
            self._pane_scene()._agent_geometry3d[alias] = dict(operation)
            if name == "geometry.projection3d":
                controller.add_projection3d(alias, tuple(operation["vector"]), tuple(operation["foot"]), tuple(operation["residual"]))
            elif name == "geometry.orthogonalization":
                for stage in operation["stages"]:
                    controller.add_orthogonalization_stage(str(stage["id"]), tuple(stage["residual"]), tuple(stage["normalized"]))
            else:
                for root, eigenspace in dict(operation.get("eigenspaces", {})).items():
                    for index, vector in enumerate(eigenspace):
                        if len(vector) == 3:
                            controller.add_linear(f"{root}__direction_{index}", (0.0, 0.0, 0.0), tuple(vector))
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
        if name == "geometry.intersection":
            self._command_intersection(operation)
            return
        if name == "geometry.constraint":
            self._command_constraint(operation)
            return
        if name == "geometry.mapping_bundle":
            if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
                raise CommandError("mapping bundle requires a 2D scene.")
            bounds = tuple(float(v) for v in operation.get("bounds", (-2,2,-2,2)))
            controller = self._pane_scene().geometry_controller
            for lane_name, lane in dict(operation.get("lanes", {})).items():
                basis = lane.get("basis", ()) if isinstance(lane, dict) else ()
                if basis:
                    alias = f"{operation.get('alias','mapping')}__{lane_name}"
                    lane_operation={"op":"geometry.subspace_region","alias":alias,"basis":basis,"origin":lane.get("origin",[0.0,0.0]),"bounds":list(bounds),"opacity":0.18}
                    self._command_teaching_geometry(lane_operation)
            return
        if name == "geometry.vector_addition":
            self._command_register_vector_addition(operation)
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
            self._fit_2d_to_command_objects(
                float(operation.get("padding", 1.15)), operation.get("bounds")
            )
            return
        if name == "scene.export_png":
            filename = str(operation.get("filename", ""))
            self._pane_renderer().screenshot(str(self._managed_export_path(filename)))
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
        kind = str(operation.get("kind", "vector"))
        style_kwargs = (
            {"line_width": float(operation["line_width"])}
            if kind != "vector" and "line_width" in operation
            else {}
        )
        arrow_kwargs = (
            {"arrow_head_scale": float(operation["arrow_head_scale"])}
            if kind == "vector" and "arrow_head_scale" in operation
            else {}
        )
        self._pane_scene().geometry3d_controller.add_linear(
            alias,
            tuple(float(value) for value in operation["start"]),  # type: ignore[arg-type]
            tuple(float(value) for value in operation["end"]),  # type: ignore[arg-type]
            kind=kind,
            color=str(operation.get("color", "#2777b6")),
            role=str(operation.get("role", "primary")),
            # 计划里声明的虚线必须传下去：被压到零的方向、投影连线等辅助构造全靠它。
            style=str(operation.get("style", "solid")),
            **style_kwargs,
            **arrow_kwargs,
        )
        if operation.get("visible") is False:
            self._pane_scene().geometry3d_controller.set_visible(alias, False)

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
        if operation.get("visible") is False:
            self._pane_scene().geometry3d_controller.set_visible(alias, False)

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
        latex_value = operation.get("latex")
        formula_source = (
            latex_value
            if isinstance(latex_value, str) and latex_value.strip()
            else str(operation.get("text", ""))
        )
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._command_upsert_annotation({
                "op": "annotation.upsert",
                "alias": operation["alias"],
                "text": operation["text"],
                "position": position,
                "latex": formula_source,
            })
            return
        if len(position) != 3:
            raise CommandError("三维公式标注需要三个坐标。")
        alias = str(operation["alias"])
        self._pane_scene()._agent_geometry3d[f"annotation:{alias}"] = dict(operation)
        add_labels = getattr(self._pane_renderer(), "add_point_labels", None)
        if callable(add_labels):
            name = f"geometry3d:annotation:{alias}"
            remove_actor = getattr(self._pane_renderer(), "remove_actor", None)
            if callable(remove_actor):
                remove_actor(name, render=False)
            controller = getattr(self._pane_scene(), "geometry3d_controller", None)
            controller_actors = getattr(controller, "actors", None)
            if isinstance(controller_actors, dict):
                controller_actors.pop(name, None)
            if operation.get("visible") is False:
                return
            text = math_labels.display_text(
                _annotation_display_text(str(operation.get("text", ""))),
                formula_source,
                font_size=math_labels.CASE_LABEL_FONT_SIZE,
                bold=True,
            )
            if not text:
                return
            color = str(
                operation.get(
                    "color",
                    "#f3f6fa" if getattr(self, "effective_theme", "light") == "dark" else "#263241",
                )
            )
            is_hovered = (
                alias.startswith("manual_annotation_")
                and alias == getattr(self._pane_scene(), "_hovered_3d_annotation_alias", None)
            )
            label_style: dict[str, object] = {}
            if is_hovered:
                label_style = {
                    "shape_color": "#1a73e8",
                    "fill_shape": False,
                    "shape_opacity": 1.0,
                    "margin": 6,
                }
            actor = add_labels(
                [position], [text], name=name,
                shape=None if not is_hovered else "rounded_rect", show_points=False,
                font_size=math_labels.CASE_LABEL_FONT_SIZE, text_color=color, always_visible=True,
                font_file=math_labels.label_font_file(), render=False,
                render_points_as_spheres=False,
                **label_style,
            )
            # Stage masks operate through Geometry3DSceneController. Register
            # formula-label actors there as well, otherwise labels from sibling
            # case panes remain visible after their vectors are hidden.
            if isinstance(controller_actors, dict) and actor is not None:
                controller_actors[name] = actor

    def _command_teaching_geometry(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
            raise CommandError("该教学几何操作需要处于二维场景。")
        name = str(operation["op"])
        if name == "geometry.constraint":
            self._command_constraint(operation)
            return
        alias = str(operation.get("alias", operation.get("result_alias", "teaching")))
        self._pane_scene()._agent_teaching_2d[alias] = dict(operation)
        if name == "geometry.polygon":
            self._pane_scene().geometry_controller.add_teaching_polygon(alias, tuple(tuple(float(v) for v in p) for p in operation["vertices"]), color=str(operation.get("color", "#5b8def")), opacity=float(operation.get("opacity", 0.24)), outline=bool(operation.get("outline", True)))  # type: ignore[index]
        elif name == "geometry.angle_arc":
            self._pane_scene().geometry_controller.add_teaching_angle_arc(alias, tuple(float(v) for v in operation["vertex"]), tuple(float(v) for v in operation["first"]), tuple(float(v) for v in operation["second"]), radius=float(operation["radius"]), color=str(operation.get("color", "#d97845")))  # type: ignore[arg-type]
            self._sync_vector_tool_direction_copy(operation)
        elif name == "geometry.right_angle_marker":
            self._pane_scene().geometry_controller.add_teaching_right_angle_marker(alias, tuple(float(v) for v in operation["vertex"]), tuple(float(v) for v in operation["first"]), tuple(float(v) for v in operation["second"]), size=float(operation["size"]), color=str(operation.get("color", "#d97845")))  # type: ignore[arg-type]
        elif name == "geometry.projection":
            # Toolbar projections are always auxiliary dashed guides.  Keep
            # the ordinary solid default for lecture-authored projections.
            projection_style = str(
                operation.get(
                    "style",
                    "dashed" if alias.startswith("la_tool_projection") else "solid",
                )
            )
            operation["style"] = projection_style
            self._pane_scene()._agent_teaching_2d[alias]["style"] = projection_style
            self._pane_scene().geometry_controller.add_teaching_projection(tuple(float(v) for v in operation["vector"]), tuple(float(v) for v in operation["direction"]), result_alias=str(operation["result_alias"]), foot_alias=str(operation["foot_alias"]), residual_alias=str(operation["residual_alias"]), alias=str(operation["alias"]) if operation.get("alias") else None, origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#2777b6")), style=projection_style)  # type: ignore[arg-type]
            self._sync_vector_tool_direction_copy(operation)
        elif name == "geometry.transformed_grid":
            matrix = tuple(tuple(float(v) for v in row) for row in operation["matrix"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_transformed_grid(matrix, tuple(float(v) for v in operation["bounds"]), step=float(operation.get("step", 1.0)), alias=str(operation["alias"]) if operation.get("alias") else None, color=str(operation.get("color", "#5b8def")), origin=tuple(float(v) for v in operation.get("origin",(0.0,0.0))), show_source_grid=bool(operation.get("show_source_grid", True)), show_basis=bool(operation.get("show_basis", False)))  # type: ignore[arg-type]
        elif name == "geometry.subspace_region":
            basis = tuple(tuple(float(v) for v in row) for row in operation["basis"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_subspace_region(basis, tuple(float(v) for v in operation["bounds"]), alias=str(operation["alias"]) if operation.get("alias") else None, origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#4c9f70")), opacity=float(operation.get("opacity", 0.2)))  # type: ignore[arg-type]
        elif name == "geometry.affine_solution":
            # 仿射解集与线性子空间共用同一图元渲染，但平移量来自 ``offset``
            # （``origin`` 在编译产物中恒为零向量）。第五章的平移解集必须
            # 落在这个偏移点上，不能再用原点。
            basis = tuple(tuple(float(v) for v in row) for row in operation["basis"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_subspace_region(basis, tuple(float(v) for v in operation["bounds"]), alias=str(operation["alias"]) if operation.get("alias") else None, origin=tuple(float(v) for v in operation.get("offset", (0.0, 0.0))), color=str(operation.get("color", "#4c9f70")), opacity=float(operation.get("opacity", 0.2)))  # type: ignore[arg-type]
        elif name in {"geometry.matrix_tableau", "geometry.elimination_tableau"}:
            # 阶梯矩阵只提供代数读数；几何解释由同一计划里的向量与标注绘制。
            # 这里仅登记别名（上面已写入 _agent_teaching_2d），故事板与代数区
            # 依靠该别名按阶段切换，宿主无需创建额外演员。
            pass
        elif name == "geometry.basis_grid":
            basis = tuple(tuple(float(v) for v in row) for row in operation["basis_matrix"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_basis_grid(basis, tuple(float(v) for v in operation["bounds"]), alias=str(operation.get("alias", "basis-grid")), color=str(operation.get("color", "#5b8def")))  # type: ignore[arg-type]
        elif name == "geometry.coordinate_readout":
            self._pane_scene().geometry_controller.add_teaching_coordinate_readout(tuple(float(v) for v in operation["standard_vector"]), tuple(float(v) for v in operation["alternate_coordinates"]), alias=str(operation.get("alias", "coordinate-readout")))  # type: ignore[arg-type]
        elif name == "geometry.least_squares":
            self._pane_scene().geometry_controller.add_teaching_least_squares(tuple(float(v) for v in operation["values"]), tuple(float(v) for v in operation["fit"]), tuple(float(v) for v in operation["residual"]), alias=str(operation.get("alias", "least-squares")))  # type: ignore[arg-type]
        elif name == "geometry.staged_transform":
            matrices = tuple(tuple(tuple(float(v) for v in row) for row in matrix) for matrix in operation["matrices"])  # type: ignore[index]
            points = tuple(tuple(float(v) for v in point) for point in operation["points"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_staged_transform(matrices, points, tuple(str(v) for v in operation["aliases"]), alias=str(operation["alias"]) if operation.get("alias") else None)  # type: ignore[arg-type]
        elif name == "geometry.oriented_area":
            vectors = tuple(tuple(float(v) for v in vector) for vector in operation["vectors"])  # type: ignore[index]
            self._pane_scene().geometry_controller.add_teaching_oriented_area(vectors, alias=str(operation.get("alias", "oriented-area")), origin=tuple(float(v) for v in operation.get("origin", (0.0, 0.0))), color=str(operation.get("color", "#d97845")), opacity=float(operation.get("opacity", 0.28)))  # type: ignore[arg-type]
        elif name == "geometry.quadratic_level_set":
            controller = self._pane_scene().geometry_controller
            controller.add_teaching_quadratic_contour(operation.get("contour_vertices", ()), segments=operation.get("contour_segments", ()), alias=str(operation.get("alias", "quadratic")), color=str(operation.get("color", "#4c9f70")))
            controller.add_teaching_quadratic_axes(operation.get("axis_segments", ()), alias=str(operation.get("alias", "quadratic")))
        else:
            raise CommandError(f"宿主不支持操作: {name}")

    def _command_constraint(self, operation: dict[str, object]) -> None:
        """Render the rank-classified solution geometry emitted by the compiler."""
        try:
            dimension = int(operation["dimension"])
            alias = str(operation["alias"])
            geometry = operation["solution_geometry"]
            if not isinstance(geometry, dict):
                raise ValueError("solution_geometry must be an object")
            geometry_op = str(geometry["op"])
            state_alias = str(operation.get("state_alias", geometry.get("alias", f"{alias}__solution")))
        except (KeyError, TypeError, ValueError) as error:
            raise CommandError("约束解集几何数据无效。") from error

        if dimension == 2:
            if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
                raise CommandError("二维约束需要处于二维场景。")
            self._pane_scene()._agent_teaching_2d[alias] = dict(operation)
            if geometry_op == "point.upsert":
                self._command_upsert_point({"op": "point.upsert", "alias": state_alias, "name": state_alias, "coordinates": geometry["coordinates"]})
            elif geometry_op == "linear.upsert":
                start_alias = f"{state_alias}__start"
                end_alias = f"{state_alias}__end"
                self._command_upsert_point({"op": "point.upsert", "alias": start_alias, "name": start_alias, "coordinates": geometry["start"]})
                self._command_upsert_point({"op": "point.upsert", "alias": end_alias, "name": end_alias, "coordinates": geometry["end"]})
                self._command_upsert_linear({"op": "linear.upsert", "alias": state_alias, "kind": "line", "start": start_alias, "end": end_alias, "role": "result", "color": "#d64545"})
            elif geometry_op == "annotation.upsert":
                self._command_upsert_annotation({"op": "annotation.upsert", "alias": state_alias, "text": geometry.get("text", ""), "position": geometry["position"], "color": "#d64545"})
            else:
                raise CommandError(f"二维约束不支持解集操作: {geometry_op}")
            return

        if dimension != 3 or self._pane_scene().scene_mode is not SceneMode.THREE_D or self._pane_scene().geometry3d_controller is None:
            raise CommandError("三维约束需要处于三维场景。")
        self._pane_scene()._agent_geometry3d[alias] = dict(operation)
        if geometry_op == "point3d.upsert":
            self._command_upsert_point3d({"op": "point3d.upsert", "alias": state_alias, "coordinates": geometry["coordinates"]})
        elif geometry_op == "linear3d.upsert":
            self._pane_scene().geometry3d_controller.add_linear(
                state_alias,
                tuple(float(value) for value in geometry["start"]),  # type: ignore[arg-type]
                tuple(float(value) for value in geometry["end"]),  # type: ignore[arg-type]
                kind="segment",
                role="result",
                color="#d64545",
            )
        elif geometry_op == "plane3d.upsert":
            self._pane_scene().geometry3d_controller.add_plane(
                state_alias,
                tuple(float(value) for value in geometry["origin"]),  # type: ignore[arg-type]
                tuple(float(value) for value in geometry["normal"]),  # type: ignore[arg-type]
                size=float(geometry.get("size", 2.0)),
                opacity=0.24,
                color="#d64545",
            )
        elif geometry_op == "annotation.formula":
            self._command_formula_annotation({"op": "annotation.formula", "alias": state_alias, "text": geometry.get("text", ""), "position": geometry["position"]})
        else:
            raise CommandError(f"三维约束不支持解集操作: {geometry_op}")

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
            self._pane_scene()._vector_additions = []
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
            self._pane_scene()._vector_additions = []
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
            point = Point2D(operation_label(operation), *coordinates, color=str(operation.get("color", "#d64545")), agent_alias=alias)
            self._pane_scene().geometry_points.append(point)
            self._pane_scene()._two_d_object_order.append(point.id)
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.add_point(point)
        else:
            point.x, point.y = coordinates
            point.color = str(operation.get("color", point.color))
            if self._pane_scene().geometry_controller is not None:
                self._pane_scene().geometry_controller.move_point(point.id, *coordinates)
        self._update_vector_additions_for_point(point.id)

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
            "label_side": str(operation.get("label_side", "below")),
        }
        if linear is None:
            linear = Linear2D(
                operation_label(operation),
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
            linear.label_side = kwargs["label_side"]  # type: ignore[assignment]
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
            annotation.latex = operation.get("latex") if operation.get("latex") is not None else annotation.latex
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
        self._render_scene_after_command()

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
        self._render_scene_after_command()

    def _command_fill_area(self, operation: dict[str, object]) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            raise CommandError("积分面积演示需要处于二维场景。")
        expression = dict(operation)
        alias = str(operation["alias"])
        areas = getattr(self._pane_scene(), "_agent_areas", {})
        areas[alias] = expression
        self._pane_scene()._agent_areas = areas
        self._render_agent_areas()

    def _render_agent_areas(self, *, render: bool = True) -> None:
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            return
        if getattr(self._pane_scene(), "_scene_command_active", False):
            self._pane_scene()._agent_areas_render_pending = True
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
                    render=False,
                )
            except Exception:
                # 面积计算失败不影响曲线事务。
                continue
        if render:
            self._pane_renderer().render()

    def _select_linear_algebra_stage(self, case_id: str, stage_id: str) -> None:
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if compiled is None or compiled.topic_id != case_id:
            return
        try:
            selection = StoryboardVisibilityController(compiled).select(stage_id)
        except ValueError:
            return
        self._active_linear_algebra_stage_id = stage_id
        self._hidden_linear_algebra_aliases = set(selection.hidden_aliases)
        self._apply_linear_algebra_storyboard_visibility(selection=selection)
        self._publish_linear_algebra_stage_metadata(selection)

    def _publish_linear_algebra_stage_metadata(self, selection: StoryboardVisibility) -> None:
        """Update presentation metadata without regenerating a teaching case."""

        self._active_linear_algebra_stage_metadata = selection
        # 动态分派兼容无 Qt 对话框的宿主和旧版内容视图。
        candidates = [getattr(self, "linear_algebra_content_view", None)]
        panel = getattr(self, "algebra_panel", None)
        popup = getattr(panel, "linear_algebra_popup", None)
        candidates.extend((getattr(popup, "content_view", None), getattr(panel, "content_view", None)))
        for target in candidates:
            setter = getattr(target, "set_storyboard_stage", None)
            if callable(setter):
                setter(selection)
                break

    def _on_teaching_case_focus(self, pane_id: str, stage_id: str) -> None:
        """Focus one pane while retaining every other pane on screen."""
        topic_id = getattr(self, "_active_linear_algebra_topic_id", None)
        if not topic_id:
            return
        target = next((pid for pid in getattr(self, "_teaching_case_pane_ids", ())
                       if pid in self.pane_manager.panes and
                       self.pane_manager.pane(pid).source_id == pane_id), None)
        if target is None:
            return
        self._reveal_algebra_pane(target, 0)
        refs = getattr(self, "_teaching_case_stage_refs", {}).get(target, ())
        self._active_linear_algebra_stage_id = stage_id or next(iter(refs), "")
        if hasattr(self, "agent_panel"):
            self.agent_panel.show_math_case_focus(topic_id, pane_id)

    def _close_teaching_case_panes(self) -> None:
        grid = getattr(self, "_teaching_case_pane_grid", None)
        if grid is not None:
            self.teaching_case_pane_layout.removeWidget(grid)
            grid.close()
            grid.deleteLater()
        self._teaching_case_pane_grid = None
        if getattr(self.pane_manager, "_lecture_user_visible", None) is not None:
            self.pane_manager.leave_lecture()
        for pane_id, pane in tuple(self.pane_manager.panes.items()):
            if pane.source == "case":
                self.pane_manager.delete_pane(pane_id)
        self._teaching_case_pane_ids = []
        self._teaching_case_stage_refs = {}
        self._pending_determinant_matrix_sync = set()
        if hasattr(self, "teaching_case_pane_host"):
            self.teaching_case_pane_host.hide()
        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            container.sync_layout()
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

    def _clear_pending_curriculum_plans(self) -> None:
        """Remove staged lecture plans that an already materialized pane must not replay.

        ``ScenePaneWidget.sync_layout`` may recreate more than one renderer.  A
        pending plan is a hand-off token for one renderer: the pane consumes it
        inside its own ``_on_pane_interactor_created`` callback, so a token left
        on a pane that already has its renderer belongs to a recreated surface
        and must not be replayed (that would re-run the whole plan).

        Panes whose renderer is not bound yet must keep their token.  ``MathCaseView``
        layouts with more than one visible pane (4.1.3 is the first) materialize
        their renderers one by one, so clearing the whole list here would leave
        every later case pane empty: no plan executed, nothing to mask.  A pane
        can own a runtime (bookkeeping such as vector-sum bindings creates one)
        while still waiting for its renderer, so the renderer binding is the real
        materialization signal.
        """

        manager = getattr(self, "pane_manager", None)
        if manager is None:
            return
        for pane_id in tuple(getattr(self, "_teaching_case_pane_ids", ())):
            if pane_id not in manager.panes:
                continue
            pane = manager.pane(pane_id)
            if pane.renderer_2d is None and pane.renderer_3d is None:
                continue
            data = pane.scene_2d if pane.scene_mode == "2d" else pane.scene_3d
            data.pop("pending_plan", None)

    def _on_pane_interactor_created(self, pane_id: str, renderer: object) -> None:
        """Rebind runtime controllers and redraw retained state after recreation."""
        interactor = getattr(renderer, "interactor", None)
        if interactor is not None:
            try:
                interactor.setMouseTracking(True)
                # 重建的窗格统一安装输入路由过滤器。
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
                data = pane.scene_2d if pane.scene_mode == "2d" else pane.scene_3d
                pending = data.pop("pending_plan", None)
                if pending is not None:
                    try:
                        transaction = getattr(self, "_pending_curriculum_transaction", None)
                        if (transaction is not None and transaction.plan is not None
                                and not getattr(self, "_pending_curriculum_host_executed", False)):
                            if str(transaction.topic_id).startswith(("ch04.", "ch05.", "ch06.", "ch07.", "ch08.")):
                                transaction.pane_id = pane_id
                                transaction.commit_host(
                                    self.scene_command_service.execute,
                                    expected_scene_fingerprint=None,
                                    finalize=False,
                                )
                                if transaction.phase is LoadPhase.REJECTED:
                                    raise CommandError(transaction.diagnostic.message if transaction.diagnostic else "host transaction failed")
                                self._pending_curriculum_host_executed = True
                                bundle = getattr(self, "_pending_curriculum_bundle", None)
                                explanation = getattr(self, "_pending_curriculum_explanation", None)
                                plan = getattr(self, "_pending_curriculum_plan", None) or transaction.plan
                                if bundle is None or explanation is None:
                                    raise CommandError("curriculum transaction lost its staged explanation")
                                try:
                                    self._finalize_linear_algebra_topic_load(
                                        bundle.topic, bundle, explanation, plan,
                                    )
                                    transaction.advance(LoadPhase.COMMITTED)
                                except Exception as error:
                                    if transaction.phase is LoadPhase.STAGED:
                                        transaction.reject(
                                            "explanation_publish_failed", LoadPhase.STAGED,
                                            "explanation", str(error),
                                        )
                                    raise
                                self._pending_curriculum_finalized = True
                                self._clear_pending_curriculum_plans()
                                self._pending_curriculum_transaction = None
                                return
                        # 每个窗格拥有独立演员，仍需在本运行时执行阶段计划。
                        result = self.scene_command_service.execute(
                            CommandPlan.from_dict(pending), pane_id=pane_id, activate_pane=False,
                        )
                        if not result.valid:
                            raise CommandError("；".join(result.messages))
                        # 阶段掩码只保留当前窗格绑定的步骤。矩阵工具初始化
                        # 会触碰 WebEngine 与 VTK，必须等当前原生回调返回后再做。
                        # 保留外层的物化状态：批量打开案例窗格时它一直是 True，
                        # 这里若直接写回 False 会让后续窗格误以为已结束物化，
                        # 从而同步触发矩阵工具等重活，拖慢多窗格切换。
                        was_materializing = getattr(self, "_teaching_case_materializing", False)
                        self._teaching_case_materializing = True
                        try:
                            self._apply_linear_algebra_storyboard_visibility()
                        finally:
                            self._teaching_case_materializing = was_materializing
                    except Exception:
                        data = pane.scene_2d if pane.scene_mode == "2d" else pane.scene_3d
                        data["pending_plan"] = pending
                        raise

    def _on_pane_viewport_changed(self, pane_id: str) -> None:
        """Refit 2-D cases and rebuild 3-D arrow heads after layout changes.

        Case panes materialize their interactor before Qt assigns the final
        geometry.  A 2-D ``view.fit`` computed against the pre-layout viewport
        can therefore crop wide vectors once two tall panes are shown, while
        3-D vector heads can come out oversized.  This callback runs after
        ``setGeometry`` and repeats once on the next event-loop turn.
        """
        self._refresh_case_pane_2d_view_fit(pane_id)
        self._refresh_case_pane_3d_arrow_heads(pane_id)

        pending = getattr(self, "_pane_viewport_refresh_pending", None)
        if pending is None:
            pending = self._pane_viewport_refresh_pending = set()
        if pane_id in pending:
            return
        pending.add(pane_id)

        def refresh() -> None:
            self._pane_viewport_refresh_pending.discard(pane_id)
            self._refresh_case_pane_2d_view_fit(pane_id, render=True)
            self._refresh_case_pane_3d_arrow_heads(pane_id, render=True)

        QTimer.singleShot(0, refresh)

    def _refresh_case_pane_2d_view_fit(self, pane_id: str, *, render: bool = False) -> bool:
        """Reapply a teaching pane's last 2-D fit using its assigned rectangle."""
        manager = getattr(self, "pane_manager", None)
        if manager is None or pane_id not in manager.panes:
            return False
        pane = manager.pane(pane_id)
        if pane.source != "case" or pane.scene_mode != "2d" or pane.renderer_2d is None:
            return False
        view_fit = pane.scene_2d.get("view_fit")
        if not isinstance(view_fit, dict):
            return False
        container = getattr(self, "scene_pane_widget", None)
        rect = container.pane_rect(pane_id) if container is not None else None
        width = float(rect.width()) if rect is not None else 0.0
        height = float(rect.height()) if rect is not None else 0.0
        if width <= 0.0 or height <= 0.0:
            return False
        with self._using_pane(pane_id):
            self._fit_2d_to_command_objects(
                float(view_fit.get("padding", 1.15)),
                view_fit.get("bounds"),
                viewport_aspect=width / height,
            )
            if render:
                render_fn = getattr(self._pane_renderer(required=False), "render", None)
                if callable(render_fn):
                    render_fn()
        return True

    def _refresh_case_pane_3d_arrow_heads(self, pane_id: str, *, render: bool = False) -> None:
        """Re-measure the pane's vector heads; ``render`` also repaints it."""
        manager = getattr(self, "pane_manager", None)
        if manager is None or pane_id not in manager.panes:
            return
        if not getattr(self, "_pane_widgets_ready", False):
            return
        pane = manager.pane(pane_id)
        if pane.scene_mode != "3d" or pane.renderer_3d is None:
            return
        try:
            with self._using_pane(pane_id):
                self._refresh_3d_arrows_for_camera()
                if render:
                    renderer = self._pane_renderer(required=False)
                    render_fn = getattr(renderer, "render", None)
                    if callable(render_fn):
                        render_fn()
        except Exception:
            pass

    def _set_teaching_case_pane_count(self, count: int) -> bool:
        ids = [pid for pid in getattr(self, "_teaching_case_pane_ids", ()) if pid in self.pane_manager.panes]
        if not ids:
            return False
        if type(count) is not int or count not in PANE_COUNTS:
            self.algebra_panel.set_status("案例窗格数量无效", is_error=True)
            return False
        selected = self.pane_manager.active_pane_id
        shown = [selected] if count == 1 and selected in ids else ids[:count]
        self.pane_manager.set_visible_panes(shown)
        container = getattr(self, "scene_pane_widget", None)
        if container is not None:
            container.sync_layout()
        self._sync_layout_buttons()
        return True

    def _open_teaching_case_panes(self, explanation_case: object, compiled: object | None) -> None:
        return self._open_teaching_case_panes_impl(explanation_case, compiled, defer_render=False)

    def _open_teaching_case_panes_impl(self, explanation_case: object, compiled: object | None, *, defer_render: bool = False) -> None:
        container = getattr(self, "scene_pane_widget", None)
        batching = (
            container is not None
            and not defer_render
            and hasattr(container, "begin_layout_batch")
            and hasattr(container, "end_layout_batch")
        )
        if batching:
            # 打开案例窗格会在同一调用栈里多次改动可见集合；先合并，结束时
            # 一次性物化最终布局，避免出现「先整屏单窗格、再拆成多窗格」的闪动。
            container.begin_layout_batch()
        try:
            self._materialize_teaching_case_panes(explanation_case, compiled, defer_render=defer_render)
        finally:
            if batching:
                container.end_layout_batch()

    def _materialize_teaching_case_panes(self, explanation_case: object, compiled: object | None, *, defer_render: bool = False) -> None:
        self._close_teaching_case_panes()
        if compiled is None or getattr(compiled, "plan", None) is None:
            return
        explanation = getattr(explanation_case, "explanation", explanation_case)
        layout = getattr(explanation, "case_layout", None)
        cases = tuple(getattr(layout, "cases", ())) if layout is not None else ()
        from linear_algebra.catalog.model import display_math_text

        descriptors = [
            (
                str(case.id),
                display_math_text(str(getattr(case, "purpose", "案例"))),
                tuple(getattr(case, "stage_refs", ())),
            )
            for case in cases
        ]
        if not descriptors:
            descriptors = [(str(compiled.topic_id), "案例", ())]
        user_pane_count = sum(
            pane.source == "user" for pane in self.pane_manager.panes.values()
        )
        case_capacity = max(
            1,
            self.pane_manager.MAX_RETAINED_PANES - user_pane_count,
        )
        descriptors = descriptors[:case_capacity]
        self._teaching_case_pane_ids = []
        self._teaching_case_stage_refs = {}
        for case_id, name, refs in descriptors:
            # 丢弃旧案例窗格，避免重放旧阶段和旧配色。
            try:
                self.pane_manager.close_case(case_id)
            except (AttributeError, RuntimeError, ValueError):
                pass
            pane_id = self.pane_manager.register_case(case_id, name=name)
            pane = self.pane_manager.pane(pane_id)
            topic_id = str(getattr(compiled, "topic_id", ""))
            extended = topic_id.startswith(("ch04.", "ch05.", "ch06.", "ch07.", "ch08."))
            # 矩阵案例必须走与工具栏相同的阶段筛选和矩阵网格计划工厂；
            # 这样案例窗格、代数区和"矩阵变换"设置使用同一条链路。
            if (
                (topic_id.startswith("ch07.") or topic_id in _CHAPTER_FOUR_MATRIX_TOOL_TOPICS)
                and refs
            ):
                plan = case_plan(compiled, refs[0])
            else:
                plan = compiled.plan if extended and getattr(compiled, "storyboard", ()) else (case_plan(compiled, refs[0]) if refs else compiled.plan)
            pane.scene_mode = plan.scene
            data = pane.scene_2d if plan.scene == "2d" else pane.scene_3d
            data["pending_plan"] = plan.to_dict()
            self._teaching_case_pane_ids.append(pane_id)
            self._teaching_case_stage_refs[pane_id] = refs
        self._teaching_case_pane_ids = [
            pane_id for pane_id in self._teaching_case_pane_ids
            if pane_id in self.pane_manager.panes
        ]
        self._teaching_case_stage_refs = {
            pane_id: refs for pane_id, refs in self._teaching_case_stage_refs.items()
            if pane_id in self.pane_manager.panes
        }
        live_case_ids = [
            self.pane_manager.pane(pane_id).source_id
            for pane_id in self._teaching_case_pane_ids
            if self.pane_manager.pane(pane_id).source_id is not None
        ]
        if not live_case_ids:
            return
        self.pane_manager.enter_lecture(live_case_ids[0], live_case_ids)
        # 首屏窗格数由 `default_pane_count` 决定。
        if int(getattr(layout, "default_pane_count", 1) or 1) > 1 and len(live_case_ids) > 1:
            self.pane_manager.show_all_cases()
        panel = getattr(self, "algebra_panel", None)
        if panel is not None and hasattr(panel, "sync_pane_tabs"):
            panel.sync_pane_tabs()
        container = getattr(self, "scene_pane_widget", None)
        if container is not None and not defer_render:
            container.sync_layout()
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

    def _apply_linear_algebra_storyboard_visibility(
        self,
        *,
        selection: StoryboardVisibility | None = None,
    ) -> None:
        """Apply one compiled stage mask to already materialized case panes.

        This is deliberately a visibility-only operation.  It does not call
        the command service, materialize a renderer, alter pane layout, or
        touch Agent/session/artifact data.  Ordinary user panes are excluded
        by the explicit lecture-pane ID list.
        """

        # Rebuilding the 2-D scene is part of the first matrix-tool sync.  The
        # rebuild calls this method from its tail; the outer sync will finish
        # the visibility pass, so the nested invocation must be a no-op.
        if (
            getattr(self, "_determinant_matrix_sync_in_progress", False)
            or getattr(self, "_matrix_transform_apply_in_progress", False)
        ):
            return

        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if compiled is None:
            return
        stage_id = getattr(self, "_active_linear_algebra_stage_id", None)
        controller = StoryboardVisibilityController(compiled)
        # 1–3 章的流程案例没有全局活动阶段，但每个独立窗格仍绑定了
        # 自己的唯一阶段。这些窗格也必须继续同步代数区的矩阵行。
        selected = selection
        if selected is None and isinstance(stage_id, str) and stage_id:
            # 修改运行时前先解析阶段，旧阶段无效时保留现有演员。
            selected = controller.select(stage_id)
        pane_manager = getattr(self, "pane_manager", None)
        if pane_manager is None:
            return
        for pane_id in tuple(getattr(self, "_teaching_case_pane_ids", ())):
            if pane_id not in pane_manager.panes:
                continue
            pane = pane_manager.pane(pane_id)
            runtime = getattr(pane, "runtime", None)
            if runtime is None:
                continue
            # 单步骤窗格固定使用自身掩码，多步骤窗格才跟随当前阶段。
            refs = tuple(
                str(ref) for ref in getattr(self, "_teaching_case_stage_refs", {}).get(pane_id, ()) if ref
            )
            pane_selection = selected
            if len(refs) == 1:
                try:
                    pane_selection = controller.select(refs[0])
                except ValueError:
                    pane_selection = selected
            if pane_selection is None:
                continue
            # Relation refreshes use the host's current pane implicitly.  Pin
            # every per-pane synchronization so derived geometry from a later
            # step cannot be written into the active earlier-step pane.
            with self._using_pane(pane_id):
                # 固定步骤窗格的 pending plan 已按各自阶段过滤。没有全局阶段时
                # 只同步矩阵工具与代数区，不再对占位渲染器重放阶段可见性。
                if selected is not None:
                    controller.apply(runtime, pane_selection.stage_id, render=False)
                self._sync_teaching_matrix_grid(pane_id, pane_selection)
                for relation in tuple(getattr(runtime, "_vector_additions", ())):
                    self._refresh_vector_addition(relation, create_missing=True)
                if selected is not None:
                    renderer = pane.renderer_2d if pane.scene_mode == "2d" else pane.renderer_3d
                    render = getattr(renderer, "render", None)
                    if callable(render):
                        render()

        # 阶段切换只改变场景演员不会自动重建代数列表；当前焦点若是讲案例窗格，
        # 立即用同一阶段掩码刷新列表，避免隐藏向量继续出现在代数区。
        panel = getattr(self, "algebra_panel", None)
        active_pane_id = getattr(pane_manager, "active_pane_id", None)
        if (
            panel is not None
            and callable(getattr(panel, "set_layers", None))
            and active_pane_id in tuple(getattr(self, "_teaching_case_pane_ids", ()))
        ):
            with self._using_pane(active_pane_id):
                mode = self._pane_scene().scene_mode
                panel.set_layers(
                    self._two_d_panel_layers() if mode is SceneMode.TWO_D else self._three_d_panel_layers()
                )
        self._sync_teaching_algebra_panel_visibility(active_pane_id)

    @staticmethod
    def _basis_matrix_latex(matrix: object) -> str | None:
        """Format a finite square matrix for the shared MathLive matrix row."""
        if not isinstance(matrix, (list, tuple)) or not matrix:
            return None
        size = len(matrix)
        rows: list[str] = []
        for row in matrix:
            if not isinstance(row, (list, tuple)) or len(row) != size:
                return None
            try:
                values = tuple(float(value) for value in row)
            except (TypeError, ValueError):
                return None
            if not all(isfinite(value) for value in values):
                return None
            rows.append("&".join(format_number(value) for value in values))
        return r"\begin{pmatrix}" + r"\\".join(rows) + r"\end{pmatrix}"

    def _sync_teaching_matrix_grid(
        self,
        pane_id: str,
        selection: StoryboardVisibility,
    ) -> None:
        """Show the matrix belonging to the visible teaching grid in its algebra tab."""
        panel = getattr(self, "algebra_panel", None)
        manager = getattr(self, "pane_manager", None)
        if panel is None or manager is None or pane_id not in manager.panes:
            return
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        topic_id = str(getattr(compiled, "topic_id", ""))
        if topic_id in _DETERMINANT_MATRIX_TOOL_TOPICS:
            self._sync_determinant_matrix_transform_tool(pane_id, selection)
            return
        selected = self._visible_teaching_matrix_grid(pane_id, selection)
        if selected is None:
            return
        _runtime, _alias, grid = selected
        matrix_value = (
            grid.get("basis_matrix")
            if grid.get("op") == "geometry.basis_grid"
            else grid.get("matrix")
        )
        latex = self._basis_matrix_latex(matrix_value)
        if latex is None:
            return
        if (
            topic_id in _CHAPTER_TWO_MATRIX_TOOL_TOPICS
            or topic_id in _CHAPTER_SEVEN_MATRIX_TOOL_TOPICS
            or topic_id in _CHAPTER_FOUR_MATRIX_TOOL_TOPICS
        ):
            # 第二章矩阵案例使用工具栏“矩阵变换”的标准代数表达式；画布上的
            # 矩阵标注只负责就地说明，不再充当第二条代数记录。
            latex = f"A={latex}"
        pane = manager.pane(pane_id)
        model = panel.add_matrix_transform_tab(
            pane_id,
            pane.name,
            editable=False,
            activate=False,
        )
        model.set_matrix_transform_value(latex)
        bounds = grid.get("bounds")
        if topic_id in _CHAPTER_SEVEN_MATRIX_TOOL_TOPICS:
            # 第七章矩阵案例沿用矩阵工具默认网格数量 5；之后用户仍可
            # 通过同一个设置入口修改。
            model.set_matrix_transform_grid_range(5)
        elif isinstance(bounds, (list, tuple)) and bounds:
            try:
                extent = max(abs(float(value)) for value in bounds)
            except (TypeError, ValueError):
                extent = 5.0
            model.set_matrix_transform_grid_range(extent)

    def _sync_determinant_matrix_transform_tool(
        self,
        pane_id: str,
        selection: StoryboardVisibility,
    ) -> None:
        """Pass one 3.2 matrix to the existing toolbar matrix workflow.

        Pane materialization is called from a native VTK callback.  Defer the
        WebEngine/tool-plan work until that callback has returned; doing it
        synchronously can re-enter rendering and terminate the process without
        a Python traceback on Windows.
        """

        # ``_apply_matrix_transform_from_tab`` rebuilds the 2-D scene.  That
        # rebuild normally calls storyboard visibility again, so do not start
        # a second matrix-tool synchronization while the first one is active.
        if (
            getattr(self, "_determinant_matrix_sync_in_progress", False)
            or getattr(self, "_matrix_transform_apply_in_progress", False)
        ):
            return

        if getattr(self, "_teaching_case_materializing", False):
            pending = getattr(self, "_pending_determinant_matrix_sync", None)
            if pending is None:
                pending = self._pending_determinant_matrix_sync = set()
            if pane_id in pending:
                return
            pending.add(pane_id)

            def sync_later() -> None:
                pending.discard(pane_id)
                manager = getattr(self, "pane_manager", None)
                if (
                    manager is None
                    or pane_id not in manager.panes
                    or str(getattr(self, "_active_linear_algebra_topic_id", ""))
                    not in _DETERMINANT_MATRIX_TOOL_TOPICS
                ):
                    return
                self._sync_determinant_matrix_transform_tool_now(pane_id, selection)

            # Let all case panes finish their native renderer/layout callbacks
            # before touching the shared WebEngine algebra surface or drawing
            # the toolbar-owned VTK overlay.
            QTimer.singleShot(150, sync_later)
            return

        self._sync_determinant_matrix_transform_tool_now(pane_id, selection)

    def _sync_determinant_matrix_transform_tool_now(
        self,
        pane_id: str,
        selection: StoryboardVisibility,
    ) -> None:
        """Execute the deferred 3.2 matrix-toolbar synchronization."""

        panel = self.algebra_panel
        pane = self.pane_manager.pane(pane_id)
        if pane.scene_2d.get("matrix_transform_grid_deleted"):
            return
        compiled = self._active_linear_algebra_compiled
        visible = set(selection.visible_aliases)
        matrix_value = next(
            (
                operation.get("matrix")
                for operation in compiled.plan.operations
                if operation.get("op") == "geometry.transformed_grid"
                and operation.get("alias") in visible
            ),
            None,
        )
        matrix_latex = self._basis_matrix_latex(matrix_value)
        if matrix_latex is None:
            return
        latex = f"A={matrix_latex}"
        model = panel.add_matrix_transform_tab(
            pane_id,
            pane.name,
            editable=False,
            activate=False,
        )
        runtime = pane.runtime
        if runtime is None:
            return
        tool_grid = next(
            (
                operation
                for alias, operation in getattr(runtime, "_agent_teaching_2d", {}).items()
                if str(alias).startswith("la_tool_transform")
                and isinstance(operation, dict)
                and operation.get("op") == "geometry.transformed_grid"
            ),
            None,
        )
        if tool_grid is not None and tool_grid.get("matrix") == matrix_value:
            model.set_matrix_transform_value(latex)
            model.set_matrix_transform_grid_range(runtime._matrix_transform_grid_range)
            return
        model.set_matrix_transform_grid_range(5)
        self._determinant_matrix_sync_in_progress = True
        try:
            self._apply_matrix_transform_from_tab(pane_id, latex, 5)
        finally:
            self._determinant_matrix_sync_in_progress = False

    def _visible_teaching_matrix_grid(
        self,
        pane_id: str,
        selection: StoryboardVisibility | None = None,
    ) -> tuple[object, str, dict[str, object]] | None:
        """Return the matrix-grid operation selected for one teaching pane."""
        manager = getattr(self, "pane_manager", None)
        if (
            manager is None
            or pane_id not in manager.panes
            or pane_id not in tuple(getattr(self, "_teaching_case_pane_ids", ()))
        ):
            return None
        runtime = getattr(manager.pane(pane_id), "runtime", None)
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if runtime is None or compiled is None:
            return None
        if selection is None:
            refs = tuple(
                str(ref)
                for ref in getattr(self, "_teaching_case_stage_refs", {}).get(pane_id, ())
                if ref
            )
            stage_id = refs[0] if len(refs) == 1 else getattr(
                self, "_active_linear_algebra_stage_id", None
            )
            if not isinstance(stage_id, str) or not stage_id:
                return None
            try:
                selection = StoryboardVisibilityController(compiled).select(stage_id)
            except ValueError:
                return None
        visible = set(selection.visible_aliases)
        operations = getattr(runtime, "_agent_teaching_2d", {})
        for alias, operation in operations.items():
            if (
                alias in visible
                and isinstance(operation, dict)
                and operation.get("op")
                in {"geometry.basis_grid", "geometry.transformed_grid"}
            ):
                return runtime, str(alias), operation
        return None

    def _apply_teaching_matrix_grid_settings(
        self,
        pane_id: str,
        matrix: CoordinateTransform,
        extent: float,
    ) -> bool:
        """Resize a teaching matrix grid without replacing the lesson scene."""
        selected = self._visible_teaching_matrix_grid(pane_id)
        if selected is None:
            return False
        runtime, alias, operation = selected
        try:
            matrix_key = (
                "basis_matrix"
                if operation.get("op") == "geometry.basis_grid"
                else "matrix"
            )
            basis = tuple(
                tuple(float(value) for value in row)
                for row in operation[matrix_key]  # type: ignore[index]
            )
        except (KeyError, TypeError, ValueError):
            return False
        panel = getattr(self, "algebra_panel", None)
        if basis != matrix:
            if panel is not None:
                panel.set_status("教学案例中的矩阵为只读内容", is_error=True)
            return True
        bounds = (-extent, extent, -extent, extent)
        operation["bounds"] = list(bounds)
        runtime._matrix_transform_grid_range = extent
        pane = self.pane_manager.pane(pane_id)
        pane.scene_2d["matrix_transform_grid_range"] = extent
        controller = getattr(runtime, "geometry_controller", None)
        if controller is not None:
            if operation.get("op") == "geometry.basis_grid":
                controller.add_teaching_basis_grid(
                    basis,
                    bounds,
                    alias=alias,
                    color=str(operation.get("color", "#5b8def")),
                )
            else:
                controller.add_teaching_transformed_grid(
                    basis,
                    bounds,
                    step=float(operation.get("step", 1.0)),
                    alias=alias,
                    color=str(operation.get("color", "#2f7ebd")),
                    origin=tuple(float(value) for value in operation.get("origin", (0.0, 0.0))),
                    show_source_grid=bool(operation.get("show_source_grid", False)),
                    show_basis=bool(operation.get("show_basis", True)),
                )
        renderer = pane.renderer_2d
        render = getattr(renderer, "render", None)
        if callable(render):
            render()
        if panel is not None:
            panel.set_status(f"已将当前案例的矩阵网格范围调整为 ±{extent:g}")
        return True

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

    def _render_agent_points3d(self, *, render: bool = True) -> None:
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            return
        if getattr(self._pane_scene(), "_scene_command_active", False):
            self._pane_scene()._agent_points3d_render_pending = True
            return
        import pyvista as pv

        controller = getattr(self._pane_scene(), "geometry3d_controller", None)
        controller_actors = getattr(controller, "actors", None)
        point_visibility: dict[str, bool] = {}
        if isinstance(controller_actors, dict):
            for name, actor in tuple(controller_actors.items()):
                if not name.startswith("agent-point:"):
                    continue
                alias = name.removeprefix("agent-point:")
                getter = getattr(actor, "GetVisibility", None)
                if callable(getter):
                    point_visibility[alias] = bool(getter())
                else:
                    point_visibility[alias] = bool(getattr(actor, "visibility", True))
                self._pane_renderer().remove_actor(name, render=False)
                controller_actors.pop(name, None)
        else:
            for alias in getattr(self._pane_scene(), "_agent_points3d", {}):
                self._pane_renderer().remove_actor(f"agent-point:{alias}", render=False)
        vector_starts = tuple(
            tuple(float(value) for value in operation.get("start", ()))
            for operation in getattr(self._pane_scene(), "_agent_geometry3d", {}).values()
            if isinstance(operation, dict)
            and operation.get("op") == "linear3d.upsert"
            and operation.get("kind") == "vector"
            and len(operation.get("start", ())) == 3
        )
        for alias, coordinates in getattr(self._pane_scene(), "_agent_points3d", {}).items():
            # 向量起点不叠加球体，避免多个原点标记重合。
            is_teaching_point = not str(alias).startswith("manual_")
            if is_teaching_point and any(
                all(abs(float(point) - float(start)) <= 1e-9 for point, start in zip(coordinates, vector_start))
                for vector_start in vector_starts
            ):
                continue
            mesh = pv.Sphere(radius=0.08, center=coordinates, theta_resolution=16, phi_resolution=8)
            name = f"agent-point:{alias}"
            actor = self._pane_renderer().add_mesh(mesh, name=name, color="#d64545", render=False)
            if isinstance(controller_actors, dict) and actor is not None:
                controller_actors[name] = actor
                if point_visibility.get(str(alias)) is False:
                    setter = getattr(actor, "SetVisibility", None)
                    if callable(setter):
                        setter(False)
                    elif hasattr(actor, "visibility"):
                        actor.visibility = False
        if render:
            self._pane_renderer().render()

    def _command_intersection(self, operation: dict[str, object]) -> None:
        first = str(operation["first"])
        second = str(operation["second"])
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            geometry = self._pane_scene()._agent_geometry3d
            first_plane = geometry.get(first, {})
            second_plane = geometry.get(second, {})
            if first_plane.get("op") == second_plane.get("op") == "plane3d.upsert":
                import numpy as np
                normals=np.asarray([first_plane["normal"],second_plane["normal"]],dtype=float)
                direction=np.cross(normals[0],normals[1])
                length=float(np.linalg.norm(direction))
                if length <= 1e-9:
                    raise CommandError("Parallel or coincident planes do not have a unique intersection line.")
                rhs=np.asarray([np.dot(normals[0],first_plane["origin"]),np.dot(normals[1],second_plane["origin"])])
                point=np.linalg.lstsq(normals,rhs,rcond=None)[0]
                direction=direction/length*3.0
                self._command_upsert_linear3d({"op":"linear3d.upsert","alias":str(operation.get("alias","intersection")),"start":(point-direction).tolist(),"end":(point+direction).tolist(),"kind":"segment","role":"result","color":"#d64545"})
                return
        if self._pane_scene().scene_mode is SceneMode.THREE_D and self._pane_scene().layer_controller is not None:
            first_layer = next((item for item in self._pane_scene().layers if item.agent_alias == first or item.id == first), None)
            second_layer = next((item for item in self._pane_scene().layers if item.agent_alias == second or item.id == second), None)
            if first_layer is None or second_layer is None:
                raise CommandError("交集计算需要两个已存在的曲面别名。")
            self._pane_scene().layer_controller.set_manual_intersection_pair(first_layer.id, second_layer.id, True)
            self._render_scene_after_command()
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
        # 命令引用优先使用稳定别名。显示名称只作旧数据的兼容回退，
        # 否则名称 B 会抢先匹配别名 B（例如另一个点名为 B），把向量
        # 的两个端点错误绑定到同一个点。
        point = next(
            (item for item in self._pane_scene().geometry_points if item.agent_alias == alias),
            None,
        )
        if point is None:
            point = next((item for item in self._pane_scene().geometry_points if item.name == alias), None)
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
        constraint = geometry3d.get(alias) or getattr(self._pane_scene(), "_agent_teaching_2d", {}).get(alias)
        if isinstance(constraint, dict) and constraint.get("op") == "geometry.constraint":
            geometry3d.pop(alias, None)
            getattr(self._pane_scene(), "_agent_teaching_2d", {}).pop(alias, None)
            self._remove_constraint_geometry(constraint)
            return
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
                # 教学演员使用稳定前缀。
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

    def _remove_constraint_geometry(self, operation: dict[str, object]) -> None:
        """Remove the concrete drawable generated for a constraint macro."""
        geometry = operation.get("solution_geometry")
        if not isinstance(geometry, dict):
            return
        state_alias = str(operation.get("state_alias", geometry.get("alias", "")))
        if not state_alias:
            return
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            child_aliases = [state_alias]
            if geometry.get("op") == "linear.upsert":
                child_aliases.extend((f"{state_alias}__start", f"{state_alias}__end"))
            for child_alias in child_aliases:
                point = next((item for item in self._pane_scene().geometry_points if item.agent_alias == child_alias), None)
                if point is not None:
                    self._remove_geometry_object(point.id)
                    continue
                linear = next((item for item in self._pane_scene().linear_objects if item.agent_alias == child_alias), None)
                if linear is not None:
                    self._remove_geometry_object(linear.id)
                    continue
                annotation = next((item for item in self._pane_scene().annotations if item.agent_alias == child_alias), None)
                if annotation is not None:
                    self._pane_scene().annotations = [item for item in self._pane_scene().annotations if item.id != annotation.id]
                    self._pane_scene()._two_d_object_order = [item_id for item_id in self._pane_scene()._two_d_object_order if item_id != annotation.id]
                    if self._pane_scene().geometry_controller is not None:
                        self._pane_scene().geometry_controller.remove_object(annotation.id)
            self._pane_renderer().render()
            return
        getattr(self._pane_scene(), "_agent_points3d", {}).pop(state_alias, None)
        geometry3d_controller = self._pane_scene().geometry3d_controller
        if geometry3d_controller is not None:
            geometry3d_controller.remove_alias(state_alias)
        geometry3d = getattr(self._pane_scene(), "_agent_geometry3d", {})
        geometry3d.pop(state_alias, None)
        geometry3d.pop(f"annotation:{state_alias}", None)
        self._pane_renderer().remove_actor(f"geometry3d:annotation:{state_alias}", render=False)
        self._render_agent_points3d()
        self._pane_renderer().render()

    def _fit_2d_to_command_objects(
        self,
        padding: float,
        bounds: object = None,
        *,
        viewport_aspect: float | None = None,
    ) -> None:
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            self._pane_renderer().reset_camera() # 把预设的相机位置覆盖掉
            self._pane_renderer().render()
            return
        explicit = self._explicit_2d_bounds(bounds)
        if explicit is None:
            points = [(point.x, point.y) for point in self._pane_scene().geometry_points]
            if not points:
                return
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
        else:
            min_x, max_x, min_y, max_y = explicit
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        # 按窗格宽高比和图形边界取景，不强制以原点居中。
        aspect = self._pane_viewport_aspect() if viewport_aspect is None else viewport_aspect
        span = max(height, width / aspect if aspect > 0 else width, 1.0) * max(1.0, padding)
        self._pane_renderer().camera.focal_point = ((min_x + max_x) / 2, (min_y + max_y) / 2, 0.0)
        self._pane_renderer().camera.position = (self._pane_renderer().camera.focal_point[0], self._pane_renderer().camera.focal_point[1], 20.0)
        self._pane_renderer().camera.parallel_scale = span / 2
        pane = self._pane()
        if pane.source == "case":
            pane.scene_2d["view_fit"] = {
                "padding": float(padding),
                "bounds": list(explicit) if explicit is not None else None,
            }
        self._refresh_2d_viewport(resample=True, render=False)

    def _pane_viewport_aspect(self) -> float:
        """Return the pane viewport width/height ratio, defaulting to 1.0."""

        renderer = self._pane_renderer(required=False)
        if renderer is None:
            return 1.0
        size: object = None
        window = getattr(renderer, "render_window", None)
        getter = getattr(window, "GetSize", None)
        if callable(getter):
            try:
                size = getter()
            except Exception:  # pragma: no cover - VTK renderer doubles in tests
                size = None
        if not size:
            getter = getattr(renderer, "GetSize", None)
            if callable(getter):
                try:
                    size = getter()
                except Exception:  # pragma: no cover - VTK renderer doubles in tests
                    size = None
        try:
            width = float(size[0])  # type: ignore[index]
            height = float(size[1])  # type: ignore[index]
        except (TypeError, ValueError, IndexError, KeyError):
            return 1.0
        if width <= 0.0 or height <= 0.0:
            return 1.0
        return width / height

    @staticmethod
    def _explicit_2d_bounds(bounds: object) -> tuple[float, float, float, float] | None:
        """Return (min_x, max_x, min_y, max_y) when a plan fixes the 2D view.

        Multi-pane lectures such as the vector-addition flow emit explicit
        bounds so every pane shares one camera scale instead of fitting to its
        own objects, which previously made one pane look larger than another.
        """
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
            return None
        try:
            values = tuple(float(value) for value in bounds)
        except (TypeError, ValueError):
            return None
        min_x, max_x, min_y, max_y = values
        if max_x <= min_x or max_y <= min_y:
            return None
        return values

    def _render_scene(self) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._render_2d_scene()
        else:
            self._render_3d_scene()

    def _annotation_text_color(self) -> str:
        """Use a legible default color for user-created marks in either theme."""
        return "#f3f6fa" if getattr(self, "effective_theme", "light") == "dark" else "#263241"

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
        if self._pane().camera_3d.get("view_angle") is not None:
            self._pane_renderer().camera.view_angle = float(self._pane().camera_3d["view_angle"])
            self._pane_renderer().reset_camera_clipping_range()
        configure_3d_camera_interaction(self._pane_renderer())
        # build_scene 内部会调用 plotter.clear() 清除全部 actor，因此坐标轴需要重新创建。
        self._pane_scene()._three_d_axes = ThreeDAxes(self._pane_renderer())
        # 相机移动时坐标轴仍固定在世界坐标中。
        extent = DEFAULT_3D_AXIS_EXTENT
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
        self._sync_panel_layers(self._three_d_panel_layers())
        self.algebra_panel.set_status("三维场景已准备好")
        for operation in tuple(getattr(self._pane_scene(), "_agent_geometry3d", {}).values()):
            if (
                operation.get("op") == "annotation.formula"
                and str(operation.get("alias", "")).startswith("manual_annotation_")
            ):
                operation["color"] = self._annotation_text_color()
            if operation.get("op") == "linear3d.upsert":
                self._command_upsert_linear3d(operation)
            elif operation.get("op") == "plane3d.upsert":
                self._command_upsert_plane3d(operation)
            elif operation.get("op") in {"geometry.parallelogram3d", "geometry.parallelepiped", "geometry.oriented_volume"}:
                self._command_upsert_solid3d(operation)
            elif operation.get("op") == "annotation.formula":
                self._command_formula_annotation(operation)
            elif operation.get("op") == "geometry.constraint":
                self._command_constraint(operation)
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
        coordinate_transform = self._pane_scene()._two_d_coordinate_transform
        guide_bounds = (
            coordinate_source_bounds(visible, coordinate_transform)
            if coordinate_transform is not None
            else visible
        )
        curve_sampling_bounds = (
            coordinate_source_bounds(sampling_bounds, coordinate_transform)
            if coordinate_transform is not None
            else sampling_bounds
        )
        sampling_domain = self._curve_sampling_domain(curve_sampling_bounds)
        self._pane_scene().curve_domain = sampling_domain
        spacing = tick_spacing(
            guide_bounds.y_span,
            appearance.tick_spacing_mode,
            appearance.tick_spacing,
        )
        # plotter.clear() 会清除全部 actor，因此二维辅助线池也必须重新建立。
        self._pane_scene()._two_d_original_guides = None
        if coordinate_transform is not None:
            self._pane_scene()._two_d_original_guides = TwoDGuides(self._pane_renderer())
            self._pane_scene()._two_d_original_guides.actor_prefix = "original_"
            if self._pane_scene()._two_d_show_original_coordinate_system:
                self._pane_scene()._two_d_original_guides.render(
                    sampling_bounds,
                    appearance,
                    effective_theme=effective_theme,
                    spacing=tick_spacing(
                        visible.y_span,
                        appearance.tick_spacing_mode,
                        appearance.tick_spacing,
                    ),
                    muted=True,
                    z_offset=-0.03,
                )
        self._pane_scene()._two_d_guides = TwoDGuides(self._pane_renderer())
        if self._pane_scene()._two_d_show_transformed_coordinate_system:
            self._pane_scene()._two_d_guides.render(
                sampling_bounds,
                appearance,
                effective_theme=effective_theme,
                spacing=spacing,
                coordinate_transform=coordinate_transform,
            )
        self._pane_scene()._two_d_guide_spacing = spacing
        self._pane_scene()._two_d_guide_bounds = sampling_bounds
        self._pane_scene()._two_d_sample_bounds = sampling_bounds
        self._pane_scene().curve_controller = CurveSceneController(
            self._pane_renderer(), sampling_domain, coordinate_transform
        )
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
        geometry_controller = self._pane_scene().geometry_controller
        batch_update = getattr(geometry_controller, "batch_update", None)
        geometry_batch = batch_update() if callable(batch_update) else nullcontext()
        with geometry_batch:
            for point in self._pane_scene().geometry_points:
                geometry_controller.add_point(point)
            for linear in self._pane_scene().linear_objects:
                geometry_controller.add_linear(linear)
            for annotation in getattr(self._pane_scene(), "annotations", []):
                if annotation.editable:
                    annotation.color = self._annotation_text_color()
                geometry_controller.add_annotation(annotation)
            for operation in tuple(getattr(self._pane_scene(), "_agent_teaching_2d", {}).values()):
                self._command_teaching_geometry(operation)
            for relation in tuple(getattr(self._pane_scene(), "_vector_additions", ())):
                self._refresh_vector_addition(relation, create_missing=True)
        self._render_agent_areas()
        self._sync_panel_layers(self._two_d_panel_layers())
        self._apply_linear_algebra_storyboard_visibility()
        self.algebra_panel.set_status("二维场景已准备好")
        self._pane_renderer().render()

    def _restore_2d_camera(self) -> None:
        # 并行投影比例决定可见世界范围及网格、刻度和采样区域。
        if self._pane_scene()._two_d_camera_position is not None:
            self._pane_renderer().camera_position = self._pane_scene()._two_d_camera_position
        else:
            self._pane_renderer().camera_position = [
                (0.0, 0.0, 20.0),    # 相机位置
                (0.0, 0.0, 0.0),     # 相机焦点
                (0.0, 1.0, 0.0),     # 相机"向上"的方向
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
        # 分辨率随外扩采样域增加，并设上限控制成本。
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
        # 辅助线和曲线采样带滞后，但几何需跟随实际视口。
        geometry_controller = getattr(self._pane_scene(), "geometry_controller", None)
        if geometry_controller is not None:
            geometry_controller.set_bounds(visible)
        appearance = self._pane_scene().scene_appearances[SceneMode.TWO_D]
        effective_theme = getattr(self, "effective_theme", "light")
        coordinate_transform = self._pane_scene()._two_d_coordinate_transform
        guide_bounds = (
            coordinate_source_bounds(visible, coordinate_transform)
            if coordinate_transform is not None
            else visible
        )
        spacing = tick_spacing(
            guide_bounds.y_span,
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
            if self._pane_scene()._two_d_show_transformed_coordinate_system:
                self._pane_scene()._two_d_guides.render(
                    sampling_bounds,
                    appearance,
                    effective_theme=effective_theme,
                    spacing=spacing,
                    coordinate_transform=coordinate_transform,
                )
        original_guides = getattr(self._pane_scene(), "_two_d_original_guides", None)
        if (
            coordinate_transform is not None
            and original_guides is not None
            and self._pane_scene()._two_d_show_original_coordinate_system
        ):
            original_guides.render(
                sampling_bounds,
                appearance,
                effective_theme=effective_theme,
                spacing=tick_spacing(
                    visible.y_span,
                    appearance.tick_spacing_mode,
                    appearance.tick_spacing,
                ),
                muted=True,
                z_offset=-0.03,
            )
        self._pane_scene()._two_d_guide_spacing = spacing
        self._pane_scene()._two_d_guide_bounds = sampling_bounds
        if resample and self._pane_scene().curve_controller is not None:
            # 放大后旧范围虽仍包含视口，但采样已过稀，需按跨度变化重采样。
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
                curve_sampling_bounds = (
                    coordinate_source_bounds(sampling_bounds, coordinate_transform)
                    if coordinate_transform is not None
                    else sampling_bounds
                )
                sampling_domain = self._curve_sampling_domain(curve_sampling_bounds)
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
        """Return the fixed world-space extent used by the 3-D axes.

        This intentionally does not inspect camera distance.  Camera dolly is
        a view operation and must not change the coordinate-system geometry.
        """
        return DEFAULT_3D_AXIS_EXTENT

    def _refresh_3d_arrows_for_camera(self) -> None:
        """Keep 3-D vector heads a constant pixel size during camera motion."""
        controller = getattr(self._pane_scene(), "geometry3d_controller", None)
        refresh = getattr(controller, "refresh_vector_heads", None)
        if not callable(refresh):
            return
        try:
            refresh()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return

    def _refresh_3d_viewport(
        self, *, resample: bool = True, render: bool = True, force: bool = False
    ) -> None:
        """Refresh 3-D settings and remeasure screen-sized vector heads."""
        if force and self._pane_scene()._three_d_axes is not None:
            appearance = self._pane_scene().scene_appearances[SceneMode.THREE_D]
            effective_theme = getattr(self, "effective_theme", "light")
            extent = DEFAULT_3D_AXIS_EXTENT
            self._pane_scene()._three_d_spacing = self._pane_scene()._three_d_axes.render(
                extent,
                axis_color_mode=appearance.axis_color_mode,
                contrast_color=appearance.contrast_axis_color(effective_theme),
                show_ticks=appearance.show_ticks,
                tick_spacing_mode=appearance.tick_spacing_mode,
                custom_tick_spacing=appearance.tick_spacing,
                previous_spacing=None,
            )

        # Qt 缩放不触发 VTK 相机事件，此处只重算箭头锥体。
        self._refresh_3d_arrows_for_camera()

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
        displayed_layers = self._three_d_panel_layers() if self._pane_scene().scene_mode is SceneMode.THREE_D else layers
        self.algebra_panel.set_layers(displayed_layers)
        self._sync_scene_controls()

    def _add_formula_for_scene(self, kind: str, latex: str) -> None:
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            self._add_cas_curve(kind, latex)
        else:
            self._add_cas_surface(kind, latex)

    def _on_3d_annotation_requested(self) -> None:
        """Arm or cancel one 3-D viewport click for a user-owned mark."""
        self.pane_manager.activate_for_tool()
        toolbar = getattr(self, "three_d_geometry_toolbar", None)
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            if toolbar is not None:
                toolbar.set_annotation_active(False)
            return
        active = (
            bool(toolbar.annotation_button.isChecked())
            if toolbar is not None
            else not bool(getattr(self._pane_scene(), "_pending_3d_annotation", False))
        )
        self._pane_scene()._pending_3d_annotation = active
        interactor = getattr(self._pane_renderer(required=False), "interactor", None)
        set_cursor = getattr(interactor, "setCursor", None)
        if callable(set_cursor):
            set_cursor(
                Qt.CursorShape.CrossCursor if active else Qt.CursorShape.ArrowCursor
            )
        if active:
            self.algebra_panel.set_status("标记工具：请在三维场景中单击标记位置")
        else:
            self.algebra_panel.set_status("已取消标记")

    def _create_3d_annotation(self, position: tuple[float, float, float]) -> bool:
        """Create one editable mark at a picked 3-D position."""
        before = self._capture_scene_command_state()
        existing = getattr(self._pane_scene(), "_agent_geometry3d", {})
        index = 1
        while f"annotation:manual_annotation_{index}" in existing:
            index += 1
        alias = f"manual_annotation_{index}"
        operation = {
            "op": "annotation.formula",
            "alias": alias,
            "text": "",
            "latex": "",
            "position": position,
            "visible": True,
            "color": self._annotation_text_color(),
        }
        try:
            self._command_formula_annotation(operation)
        except CommandError as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return False

        after = self._capture_scene_command_state()
        pane_id = self._pane().pane_id
        self.pane_manager.push(
            pane_id,
            lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            "三维标记",
        )
        self._sync_pane_state()
        self.algebra_panel.set_layers(self._three_d_panel_layers())
        begin_edit = getattr(self.algebra_panel, "begin_annotation_edit", None)
        if callable(begin_edit):
            begin_edit(alias)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已新增标记，请直接在代数区输入文字或数学表达式")
        renderer = self._pane_renderer(required=False)
        if renderer is not None and callable(getattr(renderer, "render", None)):
            renderer.render()
        return True

    def _on_3d_vector_requested(self) -> None:
        """Insert an editable vector row in the focused pane's algebra list."""
        self.pane_manager.activate_for_tool()
        if self._pane_scene().scene_mode is not SceneMode.THREE_D:
            return
        self._create_3d_vector()

    def _create_3d_vector(self) -> None:
        """Create a default vector, then focus its existing algebra list row."""
        endpoint = (1.0, 0.0, 0.0)

        before = self._capture_scene_command_state()
        existing = getattr(self._pane_scene(), "_agent_geometry3d", {})
        index = 1
        while f"manual_vector_{index}" in existing:
            index += 1
        alias = f"manual_vector_{index}"
        try:
            self._command_upsert_linear3d({
                "op": "linear3d.upsert",
                "alias": alias,
                "start": (0.0, 0.0, 0.0),
                "end": endpoint,
                "kind": "vector",
                "color": "#2777b6",
                "role": "primary",
            })
        except CommandError as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return

        after = self._capture_scene_command_state()
        pane_id = self._pane().pane_id
        self.pane_manager.push(
            pane_id,
            lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            "三维向量",
        )
        self._sync_pane_state()
        self.algebra_panel.set_layers(self._three_d_panel_layers())
        self.algebra_panel.begin_three_d_vector_edit(alias)
        toolbar = getattr(self, "three_d_geometry_toolbar", None)
        if toolbar is not None:
            toolbar.set_vector_active(True)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已新增向量，请直接在代数区修改其分量")

    def _update_3d_vector_from_algebra(self, pane_id: str, alias: str, latex: str) -> None:
        """Apply edits from a vector's ordinary MathLive algebra row."""
        if pane_id not in self.pane_manager.panes:
            return
        with self._using_pane(pane_id):
            if self._pane_scene().scene_mode is not SceneMode.THREE_D:
                return
            endpoint = parse_3d_vector_endpoint(latex)
            if endpoint is None:
                self.algebra_panel.set_status("向量格式无效，请填写三个数值分量", is_error=True)
                return
            if sum(component * component for component in endpoint) <= 1e-18:
                self.algebra_panel.set_status("向量终点不能是原点", is_error=True)
                return
            operations = getattr(self._pane_scene(), "_agent_geometry3d", {})
            current = operations.get(alias)
            if not isinstance(current, dict) or current.get("op") != "linear3d.upsert":
                return
            before = self._capture_scene_command_state()
            operation = dict(current)
            operation["end"] = endpoint
            try:
                self._command_upsert_linear3d(operation)
            except CommandError as error:
                self.algebra_panel.set_status(str(error), is_error=True)
                return
            after = self._capture_scene_command_state()
            self.pane_manager.push(
                pane_id,
                lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                "编辑三维向量",
            )
            self._sync_pane_state()
            row = self._three_d_vector_row(alias)
            if row is not None:
                self.algebra_panel.sync_layer(alias, row)
            self.algebra_panel.finish_edit()
        toolbar = getattr(self, "three_d_geometry_toolbar", None)
        if toolbar is not None:
            toolbar.set_vector_active(False)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已更新向量")

    def _update_annotation_from_algebra(self, pane_id: str, layer_id: str, latex: str) -> None:
        """Update the text of a user mark without parsing it as a function."""
        if pane_id not in self.pane_manager.panes:
            return
        updated = False
        with self._using_pane(pane_id):
            source = latex.strip()
            if not source:
                return
            if self._pane_scene().scene_mode is SceneMode.TWO_D:
                annotation = next(
                    (
                        item
                        for item in self._pane_scene().annotations
                        if item.id == layer_id and item.editable
                    ),
                    None,
                )
                if annotation is None:
                    return
                before = self._capture_geometry_state()
                annotation.text = _annotation_display_text(source)
                annotation.latex = source
                controller = getattr(self._pane_scene(), "geometry_controller", None)
                if controller is not None:
                    controller.annotations.pop(annotation.id, None)
                    controller.add_annotation(annotation)
                self._record_geometry_change(before)
                self.algebra_panel.sync_layer(annotation.id, annotation)
                self.algebra_panel.finish_edit()
                updated = True
            elif self._pane_scene().scene_mode is SceneMode.THREE_D:
                operations = getattr(self._pane_scene(), "_agent_geometry3d", {})
                current = operations.get(f"annotation:{layer_id}")
                if (
                    not str(layer_id).startswith("manual_annotation_")
                    or not isinstance(current, dict)
                    or current.get("op") != "annotation.formula"
                ):
                    return
                before = self._capture_scene_command_state()
                operation = dict(current)
                operation["text"] = _annotation_display_text(source)
                operation["latex"] = source
                self._command_formula_annotation(operation)
                after = self._capture_scene_command_state()
                self.pane_manager.push(
                    pane_id,
                    lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                    lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                    "编辑三维标记",
                )
                self._sync_pane_state()
                row = self._three_d_annotation_row(layer_id)
                if row is not None:
                    self.algebra_panel.sync_layer(layer_id, row)
                self.algebra_panel.finish_edit()
                updated = True
        if not updated:
            return
        renderer = self._pane_renderer(required=False)
        if renderer is not None and callable(getattr(renderer, "render", None)):
            renderer.render()
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已更新标记")

    def _restore_scene_command_state_for_pane(self, pane_id: str, state: _SceneCommandState) -> None:
        """Replay a shared-history scene state in the pane that created it."""
        with self._using_pane(pane_id):
            self._restore_scene_command_state(state)
            self._sync_pane_state()
        self._update_geometry_history_controls()

    def _reveal_algebra_pane(self, pane_id: str, _count: int) -> None:
        container = getattr(self, "scene_pane_widget", None)
        manager = getattr(self, "pane_manager", None) or getattr(container, "manager", None)
        if manager is not None:
            manager.reveal_pane(pane_id)
        if container is not None:
            container.sync_layout()
        self._sync_layout_buttons()

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
        point.constraint_kind = None
        point.constraint_refs = ()
        point.constraint_owned = False
        point.x, point.y = coordinates
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.move_point(point_id, *coordinates)
        self._update_vector_additions_for_point(point_id)
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
        parameters = dict(entry.parameters)
        try:
            parsed = parse_curve_expression(entry.expression, entry.kind)
            display_latex = format_parameterized_latex(
                kind=parsed.kind,
                simplified=parsed.simplified,
                parameters=parameters,
                source=parsed.source,
                dependent_axis=parsed.dependent_axis,
                parameter_range=parsed.parameter_range,
                fallback=entry.latex,
            )
        except CurveExpressionError:
            display_latex = entry.latex
        layer = CurveLayer(
            name=entry.name,
            kind=entry.kind,
            expression=entry.expression,
            latex=display_latex,
            parameters=parameters,
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

    def _linear_algebra_source_repository(self) -> LectureSourceRepository | None:
        """开发环境存在讲义源时复用索引；发布环境允许没有源文件。"""

        source_path = Path(__file__).resolve().parents[1] / ".agents" / "线性代数讲义.md"
        if not source_path.is_file():
            self._linear_algebra_source_repository_instance = None
            return None
        repository = getattr(self, "_linear_algebra_source_repository_instance", None)
        if repository is None or repository.path != source_path:
            repository = LectureSourceRepository(source_path)
            self._linear_algebra_source_repository_instance = repository
        return repository

    def _load_linear_algebra_topic(self, topic_id: str) -> None:
        # 开始渲染前更新令牌，使新选择可取消排队中的场景创建。
        generation = int(getattr(self, "_linear_algebra_load_generation", 0)) + 1
        self._linear_algebra_load_generation = generation
        self._pending_linear_algebra_scene_request = None
        registry = catalog_registry()
        store = runtime_teaching_store()
        source_repository = self._linear_algebra_source_repository()
        authoring_sync = self._synchronize_linear_algebra_authoring(
            topic_id,
            registry=registry,
            store=store,
            source_repository=source_repository,
        )
        previous = {
            "topic_id": getattr(self, "_active_linear_algebra_topic_id", None),
            "compiled": getattr(self, "_active_linear_algebra_compiled", None),
            "stage_id": getattr(self, "_active_linear_algebra_stage_id", None),
            "hidden": set(getattr(self, "_hidden_linear_algebra_aliases", set())),
            "pane_ids": list(getattr(self, "_teaching_case_pane_ids", ())),
            "stage_refs": dict(getattr(self, "_teaching_case_stage_refs", {})),
            "explanation_case": getattr(self, "_active_linear_algebra_explanation_case", None),
            "category": getattr(self, "_active_linear_algebra_category", None),
            "source_diagnostic": getattr(self, "_active_linear_algebra_source_diagnostic", None),
        }
        previous_scene_snapshot = None
        try:
            previous_scene_snapshot = self._scene_snapshot_from_current_state()
        except Exception as error:
            # 缺少载入前快照时无法回滚，应在修改界面前拒绝载入。
            self.algebra_panel.set_status(
                f"无法建立线性代数场景回滚快照: {error}", is_error=True,
            )
            return
        try:
            bundle = registry.resolve_bundle(
                topic_id,
                artifact_store=store,
                source_repository=source_repository,
            )
            topic = bundle.topic
            before_scene, before_explanation = self.teaching_fingerprints()
            transaction = registry.commit_curriculum_bundle(
                bundle,
                pane_id=getattr(getattr(self, "pane_manager", None), "active_pane_id", None),
                previous_scene_fingerprint=before_scene,
                previous_explanation_fingerprint=before_explanation,
            )
            if transaction.phase is not LoadPhase.STAGED:
                diagnostic = transaction.diagnostic
                detail = diagnostic.message if diagnostic is not None else "主题资源不完整"
                raise CommandError(f"{diagnostic.code if diagnostic else 'bundle_invalid'}: {detail}")
            explanation_case = transaction.explanation
            lesson_plan = transaction.plan
        except (KeyError, CommandError, ValueError) as error:
            self.algebra_panel.set_status(f"未知或无效的线性代数主题 {topic_id}: {error}", is_error=True)
            return
        request = {
            "generation": generation,
            "topic": topic,
            "bundle": bundle,
            "explanation_case": explanation_case,
            "lesson_plan": lesson_plan,
            "transaction": transaction,
            "previous": previous,
            "previous_scene_snapshot": previous_scene_snapshot,
            "authoring_sync": authoring_sync,
        }
        if self._can_defer_linear_algebra_scene_load():
            # QWebEngine 首帧确认后再由 Qt 线程创建 VTK 案例渲染器。
            self._pending_linear_algebra_scene_request = request
            self._publish_linear_algebra_explanation_preview(
                topic, bundle, explanation_case, lesson_plan, preview_token=str(generation),
            )
            self.algebra_panel.set_status(f"正在加载主题: {topic.title}")
            QTimer.singleShot(
                400,
                lambda generation=generation, topic_id=topic.id: self._start_deferred_linear_algebra_scene_load(
                    topic_id, str(generation),
                ),
            )
            return
        self._continue_linear_algebra_topic_load(request)

    def _can_defer_linear_algebra_scene_load(self) -> bool:
        """Use asynchronous scene creation only for the live Qt application."""
        return (
            isinstance(getattr(self, "window", None), QWidget)
            and hasattr(self, "agent_panel")
            and QApplication.instance() is not None
        )

    def _publish_linear_algebra_explanation_preview(
        self,
        topic: object,
        bundle: object,
        explanation_case: object,
        lesson_plan: object,
        *,
        preview_token: str,
    ) -> None:
        """Show source-backed prose while the native scene is being prepared."""
        if not hasattr(self, "agent_panel"):
            return
        if hasattr(self, "agent_sidebar"):
            self._open_agent_panel()
        self.agent_panel.show_math_case(
            explanation_case,
            case_id=topic.id,
            category=topic.source_path[1],
            scene_mode=lesson_plan.scene,
            compiled=bundle.compiled,
            source_diagnostic=bundle.source_diagnostic,
            scene_ready=False,
            preview_token=preview_token,
        )

    def _start_deferred_linear_algebra_scene_load(self, topic_id: str, preview_token: str) -> None:
        """Start only the preview request that is still current."""
        request = getattr(self, "_pending_linear_algebra_scene_request", None)
        if request is None:
            return
        topic = request.get("topic")
        generation = request.get("generation")
        if (
            generation != getattr(self, "_linear_algebra_load_generation", 0)
            or str(getattr(topic, "id", "")) != topic_id
            or str(generation) != preview_token
        ):
            return
        self._pending_linear_algebra_scene_request = None
        self._continue_linear_algebra_topic_load(request)

    def _continue_linear_algebra_topic_load(self, request: dict[str, object]) -> None:
        """Materialize one staged topic after the explanation has had time to paint."""
        if request["generation"] != getattr(self, "_linear_algebra_load_generation", 0):
            return
        topic = request["topic"]
        bundle = request["bundle"]
        explanation_case = request["explanation_case"]
        lesson_plan = request["lesson_plan"]
        transaction = request["transaction"]
        previous = request["previous"]
        previous_scene_snapshot = request["previous_scene_snapshot"]
        authoring_sync = request["authoring_sync"]
        try:
            compiled = bundle.compiled
            if compiled is None:
                from types import SimpleNamespace
                compiled = SimpleNamespace(topic_id=topic.id, plan=lesson_plan, storyboard=())
            extended = getattr(bundle.topic, "chapter_number", 0) >= 4
            # 每次载入重置交接标记，避免新案例误判事务已提交。
            self._pending_curriculum_host_executed = False
            self._pending_curriculum_finalized = False
            if extended:
                self._pending_curriculum_transaction = transaction
                self._pending_curriculum_bundle = bundle
                self._pending_curriculum_explanation = explanation_case
                self._pending_curriculum_plan = lesson_plan
                self._pending_curriculum_previous_scene = previous_scene_snapshot
            text_only = not tuple(getattr(topic, "required_capabilities", ()))
            was_materializing = getattr(self, "_teaching_case_materializing", False)
            self._teaching_case_materializing = True
            try:
                if text_only:
                    # 纯讲义主题不注册案例窗格，也不触发 VTK/矩阵工具链。
                    self._close_teaching_case_panes()
                else:
                    self._open_teaching_case_panes(explanation_case, compiled)
            finally:
                self._teaching_case_materializing = was_materializing
            if extended:
                target_pane = next(iter(getattr(self, "_teaching_case_pane_ids", ())), None)
                if target_pane is None:
                    raise CommandError("renderer_unavailable: no teaching pane was staged")
                transaction.pane_id = target_pane
                if transaction.phase is LoadPhase.STAGED and not getattr(self, "_pending_curriculum_host_executed", False):
                    transaction.commit_host(
                        self.scene_command_service.execute,
                        expected_scene_fingerprint=None,
                        finalize=False,
                    )
                    self._pending_curriculum_host_executed = True
                if transaction.phase is LoadPhase.STAGED and not getattr(self, "_pending_curriculum_finalized", False):
                    self._finalize_linear_algebra_topic_load(topic, bundle, explanation_case, lesson_plan)
                    transaction.advance(LoadPhase.COMMITTED)
                    self._pending_curriculum_finalized = True
                if transaction.phase is LoadPhase.COMMITTED:
                    self._clear_pending_curriculum_plans()
                self._pending_curriculum_transaction = None
                if transaction.phase is not LoadPhase.COMMITTED:
                    diagnostic = transaction.diagnostic
                    raise CommandError(diagnostic.message if diagnostic else "host transaction failed")
            else:
                self._finalize_linear_algebra_topic_load(topic, bundle, explanation_case, lesson_plan)
        except Exception as error:
            # 重建前解除交接令牌，避免旧布局回调重试已拒绝的事务。
            host_executed = bool(getattr(self, "_pending_curriculum_host_executed", False))
            self._pending_curriculum_transaction = None
            self._close_teaching_case_panes()
            if previous_scene_snapshot is not None:
                try:
                    self._restore_agent_scene_snapshot(previous_scene_snapshot)
                except Exception:
                    pass
            self._active_linear_algebra_topic_id = previous["topic_id"]
            self._active_linear_algebra_compiled = previous["compiled"]
            self._active_linear_algebra_explanation_case = previous["explanation_case"]
            self._active_linear_algebra_stage_id = previous["stage_id"]
            self._hidden_linear_algebra_aliases = previous["hidden"]
            self._teaching_case_pane_ids = previous["pane_ids"]
            self._teaching_case_stage_refs = previous["stage_refs"]
            if transaction.phase is LoadPhase.STAGED:
                code = "explanation_publish_failed" if host_executed else "host_failure"
                transaction.reject(code, LoadPhase.STAGED, "explanation" if code == "explanation_publish_failed" else "teaching_case", str(error))
            old_case = previous.get("explanation_case")
            if old_case is not None and hasattr(self, "agent_panel"):
                try:
                    old_compiled = previous.get("compiled")
                    self.agent_panel.show_math_case(
                        old_case,
                        case_id=previous.get("topic_id"),
                        category=previous.get("category"),
                        scene_mode=getattr(getattr(old_compiled, "plan", None), "scene", "2d"),
                        compiled=old_compiled,
                        source_diagnostic=previous.get("source_diagnostic"),
                    )
                except Exception:
                    pass
            self._pending_curriculum_transaction = None
            self._pending_curriculum_bundle = None
            self._pending_curriculum_explanation = None
            self._pending_curriculum_plan = None
            self._pending_curriculum_previous_scene = None
            self._pending_curriculum_host_executed = False
            self._pending_curriculum_finalized = False
            diagnostic = transaction.diagnostic
            if diagnostic is not None:
                detail = f"{diagnostic.code} [{diagnostic.phase.value}/{diagnostic.field}]: {diagnostic.message}"
            else:
                detail = str(error)
            self.algebra_panel.set_status(f"案例面板显示失败: {detail}", is_error=True)
            return
        if authoring_sync is not None and authoring_sync.status == "rejected":
            detail = authoring_sync.issues[0] if authoring_sync.issues else "校验失败"
            self.algebra_panel.set_status(
                f"已加载主题: {topic.title}（本地教学改动未发布: {detail}）",
                is_error=True,
            )
        elif authoring_sync is not None and authoring_sync.status == "published":
            self.algebra_panel.set_status(
                f"已增量发布并加载主题: {topic.title}（r{authoring_sync.revision}）"
            )
        elif bundle.source_diagnostic is not None:
            _, old_hash, current_hash = bundle.source_diagnostic
            self.algebra_panel.set_status(f"已加载主题: {topic.title}（stale_source: {old_hash} → {current_hash}）")
        else:
            self.algebra_panel.set_status(f"已加载主题: {topic.title}")
        self._pending_curriculum_bundle = None
        self._pending_curriculum_explanation = None
        self._pending_curriculum_plan = None
        self._pending_curriculum_previous_scene = None
        self._pending_curriculum_host_executed = False
        self._pending_curriculum_finalized = False

    def _synchronize_linear_algebra_authoring(
        self,
        topic_id: str,
        *,
        registry: CurriculumRegistry,
        store: TeachingArtifactStore,
        source_repository: LectureSourceRepository | None,
    ) -> AuthoringSyncResult | None:
        if not getattr(self, "_teaching_authoring_enabled", False):
            return None
        if source_repository is None:
            return None
        if not workspace_authoring_available(store=store):
            return None
        try:
            topic = registry.get_topic(topic_id)
            return synchronize_topic(
                topic,
                store=store,
                source_repository=source_repository,
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            return AuthoringSyncResult(topic_id, "rejected", issues=(str(error),))

    def _finalize_linear_algebra_topic_load(self, topic: object, bundle: object, explanation_case: object, lesson_plan: object) -> None:
        """Publish explanation and identity only after the scene transaction commits."""

        if getattr(lesson_plan, "scene", None) == "2d":
            self._set_2d_geometry_tool("select")
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool("select", emit_signal=False)
        self._sync_scene_controls()
        if hasattr(self, "agent_panel"):
            if hasattr(self, "agent_sidebar"):
                self._open_agent_panel()
            self.agent_panel.show_math_case(
                explanation_case,
                case_id=topic.id,
                category=topic.source_path[1],
                scene_mode=lesson_plan.scene,
                compiled=bundle.compiled,
                source_diagnostic=bundle.source_diagnostic,
            )
        self._active_linear_algebra_topic_id = topic.id
        self._active_linear_algebra_compiled = bundle.compiled
        self._active_linear_algebra_explanation_case = explanation_case
        self._active_linear_algebra_category = topic.source_path[1]
        self._active_linear_algebra_source_diagnostic = bundle.source_diagnostic
        extended = str(topic.id).startswith(("ch04.", "ch05.", "ch06.", "ch07.", "ch08."))
        if extended and bundle.compiled is not None and bundle.compiled.storyboard:
            initial_stage = bundle.compiled.storyboard[0].id
            all_aliases, visible_aliases = storyboard_visibility(bundle.compiled, initial_stage)
            self._active_linear_algebra_stage_id = initial_stage
            self._hidden_linear_algebra_aliases = set(all_aliases) - set(visible_aliases)
        else:
            self._active_linear_algebra_stage_id = None
            self._hidden_linear_algebra_aliases = set()
        self._register_linear_algebra_case_vector_additions()
        self._apply_linear_algebra_storyboard_visibility()

    def _register_linear_algebra_case_vector_additions(self) -> None:
        """Attach live vector-sum bindings to compiled lecture panes."""
        topic_id = getattr(self, "_active_linear_algebra_topic_id", None)
        if not isinstance(topic_id, str) or not topic_id:
            return
        pane_ids = tuple(getattr(self, "_teaching_case_pane_ids", ()))
        for pane_id in pane_ids:
            if pane_id not in self.pane_manager.panes:
                continue
            with self._using_pane(pane_id):
                runtime = self._pane_scene()
                if getattr(runtime, "_vector_additions", None):
                    continue
                aliases = {
                    str(linear.agent_alias): linear
                    for linear in runtime.linear_objects
                    if isinstance(linear.agent_alias, str)
                }
                if topic_id == "ch01.ops.addition":
                    # 第一步只显示输入向量，不补和向量及平行四边形。
                    if "sem__flow_sum" not in aliases:
                        continue
                    self._command_register_vector_addition(
                        {
                            "op": "geometry.vector_addition",
                            "alias": "dynamic__sem__rel.addition.flow",
                            "vector_a": "sem__flow_a",
                            "vector_b": "sem__flow_b",
                            "result_vector": "sem__flow_sum",
                            "result_start": "sem__flow_sum__origin",
                            "result_end": "sem__flow_sum__end",
                            "translated_vector": "dynamic__sem__addition__translated_b",
                            "construction_aliases": [
                                "dynamic__sem__addition__construction_b",
                                "dynamic__sem__addition__construction_a",
                            ],
                            "polygon_aliases": ["sem__addition_parallelogram"],
                            "annotation_alias": "dynamic__sem__addition__formula",
                        }
                    )
                    continue
                first = next((alias for alias in aliases if "vector_a" in alias), None)
                second = next((alias for alias in aliases if "vector_b" in alias), None)
                result = next((alias for alias in aliases if alias.endswith("__sum") or alias.endswith("__result")), None)
                if first and second and result:
                    self._command_register_vector_addition(
                        {
                            "op": "geometry.vector_addition",
                            "alias": f"dynamic__{topic_id}__addition",
                            "vector_a": first,
                            "vector_b": second,
                            "result_vector": result,
                            "result_start": f"{result}__origin",
                            "result_end": f"{result}__end",
                        }
                    )

    def teaching_fingerprints(self) -> tuple[str, str]:
        """Return scene and explanation fingerprints for atomic-load tests/UI diagnostics."""

        try:
            scene = self._scene_snapshot_from_current_state()
            scene_value = scene.to_dict() if hasattr(scene, "to_dict") else scene
        except Exception:
            scene_value = repr(getattr(self, "pane_manager", None))
        panel = getattr(self, "agent_panel", None)
        capture = getattr(panel, "capture_math_case", None)
        if callable(capture):
            try:
                explanation_value = capture()
            except Exception:
                explanation_value = None
        else:
            explanation_value = getattr(panel, "_pending_math_case", None)
            if explanation_value is None:
                active_case = getattr(self, "_active_linear_algebra_explanation_case", None)
                if active_case is not None:
                    case_value = active_case.to_dict() if hasattr(active_case, "to_dict") else active_case
                    explanation_value = {
                        "topic_id": getattr(self, "_active_linear_algebra_topic_id", None),
                        "case": case_value,
                    }
                else:
                    explanation_value = {
                        "topic_id": getattr(self, "_active_linear_algebra_topic_id", None),
                        "pane_ids": tuple(getattr(self, "_teaching_case_pane_ids", ())),
                        "stage_refs": getattr(self, "_teaching_case_stage_refs", {}),
                    }
        return fingerprint(scene_value), fingerprint(explanation_value)

    def _enter_linear_algebra_workspace(self) -> None:
        """Enter the 2-D lecture workspace before opening the catalog."""
        self._set_scene_mode(SceneMode.TWO_D)
        self.algebra_panel.set_status("已打开线性代数讲义目录")

    def _add_cas_surface(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_surface(latex, kind)
        except (ExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        parameters = {name: 1.0 for name in parsed.parameter_names}
        display_latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters=parameters,
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
            parameter_ranges=parsed.parameter_ranges,
            fallback=formula.latex,
        )
        layer = SurfaceLayer(
            name=f"曲面 {len(self._pane_scene().layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=display_latex,
            parameters=parameters,
        )
        if self._add_layer(layer):
            self.algebra_panel.confirm_formula_saved()

    def _add_cas_curve(self, kind: str, latex: str) -> None:
        try:
            formula, parsed = self._parse_mathlive_curve(latex, kind)
        except (CurveExpressionError, LatexParseError) as error:
            self.algebra_panel.set_status(str(error), is_error=True)
            return
        parameters = {name: 1.0 for name in parsed.parameter_names}
        display_latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters=parameters,
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
            parameter_range=parsed.parameter_range,
            fallback=formula.latex,
        )
        layer = CurveLayer(
            name=f"曲线 {len(self._pane_scene().curve_layers) + 1}",
            kind=parsed.kind,
            expression=parsed.source,
            latex=display_latex,
            parameters=parameters,
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
        self._sync_panel_layers(self._pane_scene().layers)
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
        parameters = {name: current.parameters.get(name, 1.0) for name in parsed.parameter_names}
        display_latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters=parameters,
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
            parameter_ranges=parsed.parameter_ranges,
            fallback=formula.latex,
        )
        updated = replace(
            current,
            kind=parsed.kind,
            expression=parsed.source,
            latex=display_latex,
            parameters=parameters,
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
        parameters = {name: current.parameters.get(name, 1.0) for name in parsed.parameter_names}
        display_latex = format_parameterized_latex(
            kind=parsed.kind,
            simplified=parsed.simplified,
            parameters=parameters,
            source=parsed.source,
            dependent_axis=parsed.dependent_axis,
            parameter_range=parsed.parameter_range,
            fallback=formula.latex,
        )
        updated = replace(
            current,
            kind=parsed.kind,
            expression=parsed.source,
            latex=display_latex,
            parameters=parameters,
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
            elif self._annotation_2d(layer_id) is not None:
                self._remove_annotation(layer_id)
            else:
                self._remove_curve(layer_id)
        else:
            if self._three_d_annotation_row(layer_id) is not None:
                self._remove_3d_annotation(layer_id)
            else:
                self._remove_surface(layer_id)

    def _remove_surface(self, layer_id: str) -> None:
        if self._pane_scene().layer_controller is None:
            return
        self._pane_scene().layer_controller.remove_layer(layer_id)
        self._pane_scene().layers = [layer for layer in self._pane_scene().layers if layer.id != layer_id]
        self._sync_panel_layers(self._pane_scene().layers)
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

    def _remove_annotation(self, annotation_id: str) -> None:
        annotation = self._annotation_2d(annotation_id)
        if annotation is None:
            return
        before = self._capture_geometry_state()
        self._pane_scene().annotations = [
            item for item in self._pane_scene().annotations if item.id != annotation_id
        ]
        self._pane_scene()._two_d_object_order = [
            item_id for item_id in self._pane_scene()._two_d_object_order if item_id != annotation_id
        ]
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.remove_object(annotation_id)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self._record_geometry_change(before)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已删除标记")
        self._pane_renderer().render()

    def _remove_3d_annotation(self, alias: str) -> None:
        operations = getattr(self._pane_scene(), "_agent_geometry3d", {})
        operation = operations.get(f"annotation:{alias}")
        if not isinstance(operation, dict):
            return
        before = self._capture_scene_command_state()
        operations.pop(f"annotation:{alias}", None)
        remove_actor = getattr(self._pane_renderer(), "remove_actor", None)
        if callable(remove_actor):
            remove_actor(f"geometry3d:annotation:{alias}", render=False)
        after = self._capture_scene_command_state()
        pane_id = self._pane().pane_id
        self.pane_manager.push(
            pane_id,
            lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
            "删除三维标记",
        )
        self._sync_pane_state()
        self.algebra_panel.set_layers(self._three_d_panel_layers())
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已删除标记")
        self._pane_renderer().render()

    def _remove_geometry_object(self, object_id: str) -> None:
        geometry = self._geometry_object(object_id)
        if geometry is None:
            return
        before = self._capture_geometry_state()
        removed_ids = {object_id}
        removed_relation_aliases = {object_id}
        if isinstance(geometry, Point2D):
            removed_relation_aliases.update(
                linear.id
                for linear in self._pane_scene().linear_objects
                if object_id in {linear.start_point_id, linear.end_point_id}
            )
        else:
            removed_relation_aliases.add(geometry.id)
        if isinstance(geometry, Point2D):
            removed_ids.update(
                linear.id
                for linear in self._pane_scene().linear_objects
                if object_id in {linear.start_point_id, linear.end_point_id}
            )
        while True:
            removed_linear_ids = {
                linear.id
                for linear in self._pane_scene().linear_objects
                if linear.id in removed_ids
            }
            dependent_point_ids: set[str] = set()
            for point in self._pane_scene().geometry_points:
                if (
                    point.constraint_kind is None
                    or not removed_linear_ids.intersection(point.constraint_refs)
                ):
                    continue
                if point.constraint_owned:
                    dependent_point_ids.add(point.id)
                else:
                    point.constraint_kind = None
                    point.constraint_refs = ()
                    point.constraint_owned = False
            dependent_linear_ids = {
                linear.id
                for linear in self._pane_scene().linear_objects
                if {linear.start_point_id, linear.end_point_id}.intersection(dependent_point_ids)
            }
            expanded = removed_ids | dependent_point_ids | dependent_linear_ids
            if expanded == removed_ids:
                break
            removed_ids = expanded
        removed_relation_aliases.update(removed_ids)
        linear_refs = {
            str(reference): linear.id
            for linear in (*self._pane_scene().linear_objects,)
            for reference in (linear.id, linear.agent_alias, linear.name)
            if reference is not None
        }

        self._pane_scene().geometry_points = [
            point for point in self._pane_scene().geometry_points if point.id not in removed_ids
        ]
        self._pane_scene().linear_objects = [
            linear for linear in self._pane_scene().linear_objects if linear.id not in removed_ids
        ]
        self._pane_scene()._vector_additions = [
            relation for relation in getattr(self._pane_scene(), "_vector_additions", [])
            if not (
                object_id in {relation.get("vector_a"), relation.get("vector_b"), relation.get("result_vector")}
                or any(
                    linear_refs.get(str(relation.get(key))) in removed_relation_aliases
                    for key in ("vector_a", "vector_b", "result_vector")
                )
            )
        ]
        self._pane_scene()._two_d_object_order = [
            item_id for item_id in self._pane_scene()._two_d_object_order if item_id not in removed_ids
        ]
        if self._pane_scene()._pending_geometry_point_id in removed_ids:
            self._set_2d_geometry_tool(self._pane_scene()._active_2d_tool)
        if (
            getattr(self._pane_scene(), "_pending_point_tool_point_id", None) in removed_ids
            or getattr(self._pane_scene(), "_pending_point_tool_linear_id", None) in removed_ids
        ):
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
            elif self._annotation_2d(layer_id) is not None:
                self._set_annotation_visibility(layer_id, visible)
            else:
                self._set_curve_visibility(layer_id, visible)
        else:
            if self._three_d_vector_row(layer_id) is not None:
                self._set_3d_vector_visibility(layer_id, visible)
            elif self._three_d_annotation_row(layer_id) is not None:
                self._set_3d_annotation_visibility(layer_id, visible)
            elif self._three_d_plane_row(layer_id) is not None:
                self._set_3d_plane_visibility(layer_id, visible)
            else:
                self._set_surface_visibility(layer_id, visible)

    def _set_3d_vector_visibility(self, alias: str, visible: bool) -> None:
        operations = getattr(self._pane_scene(), "_agent_geometry3d", {})
        operation = operations.get(alias)
        if not isinstance(operation, dict):
            return
        operation["visible"] = bool(visible)
        controller = getattr(self._pane_scene(), "geometry3d_controller", None)
        setter = getattr(controller, "set_visible", None)
        if callable(setter):
            setter(alias, bool(visible))
        row = self._three_d_vector_row(alias)
        if row is not None:
            self.algebra_panel.sync_layer(alias, row)
        self._pane_renderer().render()

    def _set_3d_annotation_visibility(self, alias: str, visible: bool) -> None:
        operations = getattr(self._pane_scene(), "_agent_geometry3d", {})
        operation = operations.get(f"annotation:{alias}")
        if not isinstance(operation, dict):
            return
        operation["visible"] = bool(visible)
        self._command_formula_annotation(operation)
        row = self._three_d_annotation_row(alias)
        if row is not None:
            self.algebra_panel.sync_layer(alias, row)
        self._pane_renderer().render()

    def _set_3d_plane_visibility(self, alias: str, visible: bool) -> None:
        operation = getattr(self._pane_scene(), "_agent_geometry3d", {}).get(alias)
        if not isinstance(operation, dict):
            return
        operation["visible"] = bool(visible)
        controller = getattr(self._pane_scene(), "geometry3d_controller", None)
        setter = getattr(controller, "set_visible", None)
        if callable(setter):
            setter(alias, bool(visible))
        row = self._three_d_plane_row(alias)
        if row is not None:
            self.algebra_panel.sync_layer(alias, row)
        self._pane_renderer().render()

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

    def _set_annotation_visibility(self, layer_id: str, visible: bool) -> None:
        annotation = self._annotation_2d(layer_id)
        if annotation is None or annotation.visible == visible:
            return
        before = self._capture_geometry_state()
        annotation.visible = visible
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.set_visible(layer_id, visible)
        self.algebra_panel.sync_layer(layer_id, annotation)
        self._record_geometry_change(before)
        self._update_geometry_history_controls()
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

    def _set_layer_parameter(self, layer_id: str, name: str, value: float) -> None:
        """Update one symbolic parameter and its numeric algebra display."""
        if self._pane_scene().scene_mode is SceneMode.TWO_D:
            current = self._curve_layer(layer_id)
            controller = self._pane_scene().curve_controller
            if current is None or controller is None or name not in current.parameters:
                return
            parameters = dict(current.parameters)
            parameters[name] = max(-10.0, min(10.0, round(float(value), 1)))
            try:
                parsed = parse_curve_expression(current.expression, current.kind)
                display_latex = format_parameterized_latex(
                    kind=parsed.kind,
                    simplified=parsed.simplified,
                    parameters=parameters,
                    source=parsed.source,
                    dependent_axis=parsed.dependent_axis,
                    parameter_range=parsed.parameter_range,
                    fallback=current.latex or current.expression,
                )
                updated = replace(current, parameters=parameters, latex=display_latex)
                controller.update_layer(updated)
            except (CurveExpressionError, CurveRenderError, ValueError) as error:
                self.algebra_panel.set_status(f"无法更新参数 {name}: {error}", is_error=True)
                return
            self._pane_scene().curve_layers = [
                updated if layer.id == layer_id else layer
                for layer in self._pane_scene().curve_layers
            ]
        else:
            current = self._layer(layer_id)
            controller = self._pane_scene().layer_controller
            if current is None or controller is None or name not in current.parameters:
                return
            parameters = dict(current.parameters)
            parameters[name] = max(-10.0, min(10.0, round(float(value), 1)))
            try:
                parsed = parse_surface_expression(current.expression, current.kind)
                display_latex = format_parameterized_latex(
                    kind=parsed.kind,
                    simplified=parsed.simplified,
                    parameters=parameters,
                    source=parsed.source,
                    dependent_axis=parsed.dependent_axis,
                    parameter_ranges=parsed.parameter_ranges,
                    fallback=current.latex or current.expression,
                )
                updated = replace(current, parameters=parameters, latex=display_latex)
                controller.update_layer(updated)
            except (ExpressionError, LayerRenderError, ValueError) as error:
                self.algebra_panel.set_status(f"无法更新参数 {name}: {error}", is_error=True)
                return
            self._pane_scene().layers = [
                updated if layer.id == layer_id else layer
                for layer in self._pane_scene().layers
            ]
        self.algebra_panel.sync_layer(layer_id, updated, refresh_settings=False)
        self.algebra_panel.set_status(f"参数 {name} = {parameters[name]:g}")
        self._pane_renderer().render()

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
            self._set_2d_geometry_tool(None)
            if hasattr(self, "two_d_geometry_toolbar"):
                self.two_d_geometry_toolbar.set_active_tool(None, emit_signal=False)
        self._save_current_view_state()
        self._pane_scene().scene_mode = mode
        if hasattr(self, "status_bar"):
            self.status_bar.set_scene_mode(mode)
        self._close_scene_settings(immediate=True)
        self._render_scene()

    _TOOL_LABELS = {
        "line": "直线",
        "segment": "线段",
        "dashed_segment": "虚线段",
        "ray": "射线",
        "vector": "向量",
        "annotation": "标记",
        "midpoint": "中点",
        "intersection": "交点",
        "addition": "向量加法",
    }

    def _set_2d_geometry_tool(self, tool: ToolKind | None) -> None:
        """切换当前二维几何创建工具，并清理未完成的两点操作。"""
        if self._pane_scene().scene_mode is not SceneMode.TWO_D:
            tool = None
        self._pane_scene()._pending_geometry_point_id = None
        self._pane_scene()._pending_point_tool_point_id = None
        self._pane_scene()._pending_point_tool_linear_id = None
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._dragging_annotation_id = None
        self._pane_scene()._selection_start = None
        band = self._pane_scene()._selection_band
        if band is not None:
            band.hide()
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
                "annotation": Qt.CursorShape.CrossCursor,
            }.get(tool, Qt.CursorShape.CrossCursor)
            self._pane_renderer().interactor.setCursor(cursor)
        if tool == "point":
            self.algebra_panel.set_status("点工具：单击画布创建点")
        elif tool == "midpoint":
            self.algebra_panel.set_status("中点工具：单击线段/向量，或先选一个点再选线段/向量")
        elif tool == "intersection":
            self.algebra_panel.set_status("交点工具：依次选择两个对象，或直接单击相交处")

    def _on_unified_2d_tool_selected(self, tool: ToolKind | None) -> None:
        """Route the single toolbar's selection to the active workspace."""
        self.pane_manager.activate_for_tool()
        if tool == "transform":
            self._open_matrix_transform_workspace()
            return
        if tool is not None and self._pane_scene().scene_mode is not SceneMode.TWO_D:
            self._set_scene_mode(SceneMode.TWO_D)
        if tool in {"addition", "angle", "projection", "polygon", "transform", "subspace", "area"}:
            self._on_linear_algebra_tool_selected(str(tool))
            return
        self._set_2d_geometry_tool(tool)

    def _on_linear_algebra_tool_selected(self, tool: str) -> None:
        """Handle linear algebra toolbar tool selection."""
        tool_labels = {
            "addition": "向量加法",
            "angle": "角度测量",
            "projection": "投影",
            "polygon": "多边形",
            "transform": "矩阵变换",
            "subspace": "子空间",
            "area": "有向面积",
        }
        # 基础工具复用现有二维几何设施。
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
            # 清除基础工具后恢复专用选择状态。
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
        elif tool == "midpoint":
            self.algebra_panel.set_status("中点工具：单击线段/向量，或先选一个点再选线段/向量")
        elif tool == "intersection":
            self.algebra_panel.set_status("交点工具：依次选择两个对象，或直接单击相交处")
        elif tool is not None:
            if tool == "polygon":
                self.algebra_panel.set_status("多边形工具：依次单击顶点，双击完成")
            elif tool == "addition":
                self.algebra_panel.set_status("加法工具：依次单击两条向量")
            elif tool == "transform":
                self.algebra_panel.set_status("矩阵变换工具：请在代数区列表中输入矩阵")
            else:
                self.algebra_panel.set_status(f"{tool_labels.get(tool, tool)}工具：单击第一个向量")

    def _open_matrix_transform_workspace(self) -> str | None:
        """Open the matrix editor for the active pane without changing layout."""
        manager = getattr(self, "pane_manager", None)
        panel = getattr(self, "algebra_panel", None)
        if manager is None or panel is None:
            return None

        pane_id = str(getattr(manager, "active_pane_id", ""))
        if not pane_id or pane_id not in manager.panes:
            return None
        pane = manager.pane(pane_id)
        try:
            manager.focus_pane(pane_id)
        except (AttributeError, ValueError):
            return None
        with self._using_pane(pane_id):
            if self._pane_scene().scene_mode is not SceneMode.TWO_D:
                self._set_scene_mode(SceneMode.TWO_D)
            runtime = self._pane_scene()
            if runtime._two_d_coordinate_transform is not None:
                runtime._two_d_coordinate_transform = None
                runtime._two_d_show_original_coordinate_system = True
                runtime._two_d_show_transformed_coordinate_system = True
                self._pane().scene_2d.pop("coordinate_transform", None)
                if self._pane_renderer(required=False) is not None:
                    self._render_2d_scene()

        model = panel.add_matrix_transform_tab(pane_id, pane.name)
        runtime = self._pane_scene(pane_id)
        pane.scene_2d.pop("matrix_transform_grid_deleted", None)
        model.set_matrix_transform_grid_range(runtime._matrix_transform_grid_range)
        model.setFocus()
        panel.set_status("请在代数列表中编辑 2×2 矩阵；网格数量可在行尾设置中调整")
        toolbar = getattr(self, "two_d_geometry_toolbar", None)
        if toolbar is not None:
            toolbar.set_active_tool(None, emit_signal=False)
        self._pane_scene(pane_id)._active_2d_tool = None
        self._pane_scene(pane_id)._active_linear_algebra_tool = None
        return pane_id

    def _apply_matrix_transform_from_tab(
        self, pane_id: str, text: str, grid_range: int | float = 5
    ) -> None:
        """Draw a transformed grid in the current pane's original coordinates."""
        manager = getattr(self, "pane_manager", None)
        panel = getattr(self, "algebra_panel", None)
        if manager is None or panel is None or pane_id not in manager.panes:
            return
        expression = parse_matrix_expression(text)
        if expression is None:
            panel.set_status(
                r"矩阵表达式无效；二维工具仅支持 2×2 的 A=\begin{pmatrix}...\end{pmatrix}，矩阵相乘使用 \cdot",
                is_error=True,
            )
            return
        matrix = expression.result
        try:
            extent = max(1.0, min(float(grid_range), 100.0))
        except (TypeError, ValueError):
            panel.set_status("网格范围必须是 1 到 100 的数值", is_error=True)
            return
        editor_getter = getattr(panel, "matrix_transform_editor", None)
        editor = editor_getter(pane_id) if callable(editor_getter) else None
        if editor is not None and callable(getattr(editor, "set_matrix_transform_value", None)):
            editor.set_matrix_transform_value(
                expression.input_latex,
                expression.result_latex,
            )
        if self._apply_teaching_matrix_grid_settings(pane_id, matrix, extent):
            return
        with self._using_pane(pane_id):
            if self._pane_scene().scene_mode is not SceneMode.TWO_D:
                self._pane_scene().scene_mode = SceneMode.TWO_D
            if self._pane_renderer(required=False) is None:
                panel.set_status("当前二维窗格尚未准备好，请稍后再试", is_error=True)
                return
            self._clear_linear_algebra_tool_overlays()
            runtime = self._pane_scene()
            # The toolbar tool owns an overlay grid.  Clear any state left by
            # the former coordinate-system replacement behavior first.
            runtime._linear_algebra_tool_preclear_state = None
            runtime._two_d_coordinate_transform = None
            runtime._two_d_show_original_coordinate_system = True
            runtime._two_d_show_transformed_coordinate_system = True
            pane = self._pane()
            pane.scene_2d.pop("coordinate_transform", None)
            pane.scene_2d["matrix_transform_grid_range"] = extent
            runtime._matrix_transform_grid_range = extent
            # Rebuild the guides immediately when a pane still carries state
            # from the former coordinate-system replacement behavior.
            render_2d = getattr(self, "_render_2d_scene", None)
            if callable(render_2d):
                self._matrix_transform_apply_in_progress = True
                try:
                    render_2d()
                finally:
                    self._matrix_transform_apply_in_progress = False
            alias = "la_tool_transform"
            plan = build_matrix_grid_tool_plan(matrix, extent, alias)
            if not self._apply_linear_algebra_tool_plan(plan):
                return
            sync_state = getattr(self, "_sync_pane_state", None)
            if callable(sync_state):
                sync_state()
            panel.set_status(f"已在当前窗格绘制矩阵网格，范围 ±{extent:g}（默认值 5）")

    def _delete_matrix_transform_grid(self, pane_id: str) -> None:
        """Delete the matrix tool overlay and its algebra row from one pane."""

        manager = getattr(self, "pane_manager", None)
        panel = getattr(self, "algebra_panel", None)
        if manager is None or panel is None or pane_id not in manager.panes:
            return
        with self._using_pane(pane_id):
            runtime = self._pane_scene()
            controller = getattr(runtime, "geometry_controller", None)
            if controller is not None:
                controller.clear_teaching_prefix("la_tool_transform")
            runtime._agent_teaching_2d = {
                alias: operation
                for alias, operation in getattr(runtime, "_agent_teaching_2d", {}).items()
                if not str(alias).startswith("la_tool_transform")
            }
            runtime._matrix_transform_grid_range = 5.0
            runtime._linear_algebra_tool_preclear_state = None
            pane = self._pane()
            pane.scene_2d["matrix_transform_grid_range"] = 5.0
            pane.scene_2d["matrix_transform_grid_deleted"] = True
            sync_state = getattr(self, "_sync_pane_state", None)
            if callable(sync_state):
                sync_state()
            renderer = self._pane_renderer(required=False)
            render = getattr(renderer, "render", None)
            if callable(render):
                render()
        remove_editor = getattr(panel, "remove_matrix_transform_tab", None)
        if callable(remove_editor):
            remove_editor(pane_id)
        panel.set_status("已删除当前窗格的矩阵变换网格")

    def _set_matrix_coordinate_system_visibility(
        self, pane_id: str, show_original: bool, show_transformed: bool
    ) -> None:
        """Toggle the reference and transformed guide systems for one pane."""
        manager = getattr(self, "pane_manager", None)
        if manager is None or pane_id not in manager.panes:
            return
        with self._using_pane(pane_id):
            runtime = self._pane_scene()
            runtime._two_d_show_original_coordinate_system = bool(show_original)
            runtime._two_d_show_transformed_coordinate_system = bool(show_transformed)
            pane = self._pane()
            pane.scene_2d["show_original_coordinate_system"] = bool(show_original)
            pane.scene_2d["show_transformed_coordinate_system"] = bool(show_transformed)
            if runtime.scene_mode is SceneMode.TWO_D and self._pane_renderer(required=False) is not None:
                self._render_2d_scene()

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
                    # 轻量测试宿主不含完整场景状态。
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

    def _sync_vector_tool_direction_copy(self, operation: dict[str, object]) -> None:
        """Draw the second vector at the first vector's origin when needed.

        As with vector addition, this is a derived dashed copy; the user's
        original vector and its endpoints are never rewritten.
        """
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        alias = str(operation.get("alias", "vector-tool"))
        if controller is None:
            return
        first = self._geometry_linear_ref(operation.get("source_vector_id"))
        second = self._geometry_linear_ref(operation.get("direction_vector_id"))
        if first is None or second is None:
            controller.set_teaching_translated_vector(alias, (0.0, 0.0), (0.0, 0.0), visible=False)
            return
        first_start = self._geometry_point_ref(first.start_point_id)
        second_start = self._geometry_point_ref(second.start_point_id)
        second_end = self._geometry_point_ref(second.end_point_id)
        if first_start is None or second_start is None or second_end is None:
            controller.set_teaching_translated_vector(alias, (0.0, 0.0), (0.0, 0.0), visible=False)
            return
        separated = (
            abs(first_start.x - second_start.x) > 1e-10
            or abs(first_start.y - second_start.y) > 1e-10
        )
        controller.set_teaching_translated_vector(
            alias,
            (first_start.x, first_start.y),
            (second_end.x - second_start.x, second_end.y - second_start.y),
            visible=separated,
            color=str(operation.get("direction_color", second.color)),
        )

    def _geometry_point_ref(self, reference: object) -> Point2D | None:
        if not isinstance(reference, str):
            return None
        return next(
            (
                point
                for point in self._pane_scene().geometry_points
                if point.id == reference or point.agent_alias == reference or point.name == reference
            ),
            None,
        )

    def _geometry_linear_ref(self, reference: object) -> Linear2D | None:
        if not isinstance(reference, str):
            return None
        return next(
            (
                linear
                for linear in self._pane_scene().linear_objects
                if linear.id == reference or linear.agent_alias == reference or linear.name == reference
            ),
            None,
        )

    def _move_addition_point(self, point: Point2D, coordinates: tuple[float, float]) -> None:
        point.x, point.y = float(coordinates[0]), float(coordinates[1])
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.move_point(point.id, point.x, point.y)
        panel = getattr(self, "algebra_panel", None)
        if panel is not None and callable(getattr(panel, "sync_layer", None)):
            panel.sync_layer(point.id, point)

    def _upsert_addition_point(
        self,
        alias: str,
        name: str,
        coordinates: tuple[float, float],
        *,
        visible: bool = True,
    ) -> Point2D:
        point = next(
            (item for item in self._pane_scene().geometry_points if item.agent_alias == alias),
            None,
        )
        if point is None:
            point = Point2D(name, coordinates[0], coordinates[1], visible=visible, agent_alias=alias)
            self._pane_scene().geometry_points.append(point)
            self._pane_scene()._two_d_object_order.append(point.id)
            controller = getattr(self._pane_scene(), "geometry_controller", None)
            if controller is not None:
                controller.add_point(point)
        else:
            point.visible = visible
            self._move_addition_point(point, coordinates)
        return point

    def _set_addition_point_name(self, point: Point2D, preferred_name: str) -> None:
        """Give a generated addition point a label that cannot collide.

        The old result endpoint was always named ``C``.  If the user had
        already drawn a point C, the canvas rendered two indistinguishable C
        labels.  Generated starts are intentionally unnamed; the result end
        gets C only when that name is still free, otherwise it receives one
        available name once and keeps that name during later redraws.
        """
        names_used_by_others = {
            item.name
            for item in self._pane_scene().geometry_points
            if item.id != point.id and item.name
        }
        current_name = point.name.strip()
        # A generated point is refreshed whenever a pane is restored or an
        # input moves.  Reallocating its name here made D become E (and so on)
        # merely because the point's own old name was now part of the scene.
        if current_name and current_name not in names_used_by_others:
            return
        if preferred_name and preferred_name not in names_used_by_others:
            target_name = preferred_name
        elif preferred_name:
            target_name = self._next_point_name()
        else:
            target_name = ""
        if point.name == target_name:
            return
        point.name = target_name
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.add_point(point)

    def _upsert_addition_linear(
        self,
        alias: str,
        start: Point2D,
        end: Point2D,
        *,
        name: str | None = None,
        role: str = "construction",
        color: str = "#6c7b8d",
        style: str = "dashed",
        label: str | None = None,
        visible: bool = True,
    ) -> Linear2D:
        linear = next(
            (item for item in self._pane_scene().linear_objects if item.agent_alias == alias),
            None,
        )
        if linear is None:
            linear = Linear2D(
                name or alias,
                "vector" if label is not None else "segment",
                start.id,
                end.id,
                color=color,
                style=style,
                role=role,  # type: ignore[arg-type]
                label=label,
                visible=visible,
                agent_alias=alias,
            )
            self._pane_scene().linear_objects.append(linear)
            self._pane_scene()._two_d_object_order.append(linear.id)
        else:
            linear.start_point_id = start.id
            linear.end_point_id = end.id
            linear.role = role  # type: ignore[assignment]
            linear.color = color
            linear.style = style  # type: ignore[assignment]
            linear.label = label
            linear.visible = visible
            if label is not None:
                linear.kind = "vector"
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.linears.pop(linear.id, None)
            controller.add_linear(linear)
        return linear

    def _upsert_addition_annotation(
        self,
        alias: str,
        text: str,
        position: tuple[float, float],
        *,
        color: str = "#d64545",
        visible: bool = True,
    ) -> Annotation2D:
        annotation = next(
            (item for item in self._pane_scene().annotations if item.agent_alias == alias),
            None,
        )
        if annotation is None:
            annotation = Annotation2D(
                alias,
                text,
                position[0],
                position[1],
                color=color,
                visible=visible,
                agent_alias=alias,
            )
            self._pane_scene().annotations.append(annotation)
            self._pane_scene()._two_d_object_order.append(annotation.id)
        else:
            annotation.text = text
            annotation.x, annotation.y = position
            annotation.color = color
            annotation.visible = visible
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.annotations.pop(annotation.id, None)
            controller.add_annotation(annotation)
        return annotation

    def _command_register_vector_addition(self, operation: dict[str, object]) -> None:
        """Register a live vector-sum relation emitted by a case or tool."""
        alias = str(operation.get("alias", "vector_addition_relation"))
        relation = dict(operation)
        relation["alias"] = alias
        relation.setdefault("last_selected_vector", relation.get("vector_b"))
        polygon_aliases = relation.get("polygon_aliases")
        if isinstance(polygon_aliases, (list, tuple)):
            polygon_aliases = list(polygon_aliases)
            # 将已有能力多边形绑定到实时关系，避免拖动后残留副本。
            for polygon_alias in getattr(self._pane_scene(), "_agent_teaching_2d", {}):
                if polygon_alias == "cap__polygon" and polygon_alias not in polygon_aliases:
                    polygon_aliases.append(polygon_alias)
            relation["polygon_aliases"] = polygon_aliases
        relations = getattr(self._pane_scene(), "_vector_additions", [])
        replaced = False
        for index, previous in enumerate(relations):
            if str(previous.get("alias", "")) == alias:
                relations[index] = relation
                replaced = True
                break
        if not replaced:
            # 输入向量属于用户已有对象，不能为满足首尾相接而移动其端点。
            # 刷新关系时会建立独立的平移副本来表现三角形法则。
            relations.append(relation)
        self._pane_scene()._vector_additions = relations
        self._refresh_vector_addition(relation, create_missing=True)
        # 工具直接生成关系时，之前只增量更新了画布演员；代数区的完整
        # 列表要等下次重绘（例如最小化后恢复）才会重建。只在当前窗格
        # 同步一次列表，后续拖动则由各对象的 sync_layer 轻量更新。
        active_pane_id = getattr(getattr(self, "pane_manager", None), "active_pane_id", None)
        if self._pane().pane_id == active_pane_id:
            self.algebra_panel.set_layers(self._two_d_panel_layers())

    def _create_vector_addition_relation(self, first: Linear2D, second: Linear2D) -> bool:
        before = self._capture_geometry_state()
        sequence = getattr(self._pane_scene(), "_linear_algebra_tool_sequence", 0) + 1
        self._pane_scene()._linear_algebra_tool_sequence = sequence
        prefix = f"la_addition_{sequence}"
        relation = {
            "op": "geometry.vector_addition",
            "alias": prefix,
            "vector_a": first.id,
            "vector_b": second.id,
            "result_vector": f"{prefix}__result",
            "result_start": f"{prefix}__result__origin",
            "result_end": f"{prefix}__result__end",
            "translated_vector": f"{prefix}__translated_b",
            "construction_aliases": [
                f"{prefix}__construction_b",
                f"{prefix}__construction_a",
            ],
            "polygon_aliases": [f"{prefix}__parallelogram"],
            # The toolbar always teaches the triangle rule: keep the
            # translated copy visible as a dashed vector.  Lesson-authored
            # relations may still opt out explicitly via their own flag.
            "show_triangle_rule": True,
            "annotation_alias": f"{prefix}__formula",
            "last_selected_vector": second.id,
        }
        self._command_register_vector_addition(relation)
        self._record_geometry_change(before)
        self._pane_renderer().render()
        self.algebra_panel.set_status("已创建向量加法：拖动输入端点可联动更新")
        return True

    def _refresh_vector_addition(self, relation: dict[str, object], *, create_missing: bool = False) -> bool:
        if getattr(self._pane_scene(), "_updating_vector_additions", False):
            return False
        first = self._geometry_linear_ref(relation.get("vector_a"))
        second = self._geometry_linear_ref(relation.get("vector_b"))
        if first is None or second is None or first.kind != "vector" or second.kind != "vector":
            return False
        first_start = self._geometry_point_ref(first.start_point_id)
        first_end = self._geometry_point_ref(first.end_point_id)
        second_start = self._geometry_point_ref(second.start_point_id)
        second_end = self._geometry_point_ref(second.end_point_id)
        if any(point is None for point in (first_start, first_end, second_start, second_end)):
            return False
        assert first_start is not None and first_end is not None and second_start is not None and second_end is not None
        anchor = (first_start.x, first_start.y)
        first_vector = (first_end.x - first_start.x, first_end.y - first_start.y)
        second_vector = (second_end.x - second_start.x, second_end.y - second_start.y)
        result_end_coordinates = (
            anchor[0] + first_vector[0] + second_vector[0],
            anchor[1] + first_vector[1] + second_vector[1],
        )
        relation_id = str(relation.get("alias", "vector_addition_relation"))
        hidden_aliases = set(getattr(self, "_hidden_linear_algebra_aliases", ()))
        result_ref_value = relation.get("result_vector")
        derived_visible = not isinstance(result_ref_value, str) or result_ref_value not in hidden_aliases
        show_triangle = relation.get("show_triangle_rule", True) is not False
        show_parallelogram = relation.get("show_parallelogram", True) is not False
        first_label = str(relation.get("vector_a_label") or "a")
        second_label = str(relation.get("vector_b_label") or "b")
        input_point_ids = {
            first.start_point_id,
            first.end_point_id,
            second.start_point_id,
            second.end_point_id,
        }
        controller = getattr(self._pane_scene(), "geometry_controller", None)

        def result_point_reference(field: str, suffix: str) -> str:
            """Normalize a sum endpoint to a relation-owned point alias.

            Lesson data can name an output endpoint after an input point (such
            as ``O`` or ``C``). Reusing that point would make the generated
            vector mutate the source vector, so result endpoints always get
            their own relation-owned identities.
            """
            fallback = f"{relation_id}__result__{suffix}"
            candidate = str(relation.get(field) or fallback)
            existing = self._geometry_point_ref(candidate)
            return fallback if existing is not None and existing.id in input_point_ids else candidate

        result_start_ref = result_point_reference("result_start", "origin")
        result_end_ref = result_point_reference("result_end", "end")
        if result_start_ref == result_end_ref:
            result_end_ref = f"{relation_id}__result__end"
        relation["result_start"] = result_start_ref
        relation["result_end"] = result_end_ref

        def sync_visibility(item: Point2D | Linear2D | Annotation2D, visible: bool) -> None:
            item.visible = visible
            if controller is not None:
                controller.set_visible(item.id, visible)
        result = self._geometry_linear_ref(relation.get("result_vector"))
        if result is None and create_missing:
            result_ref = str(relation.get("result_vector") or f"{relation_id}__result")
            result_start = self._upsert_addition_point(result_start_ref, "", anchor, visible=derived_visible)
            result_end = self._upsert_addition_point(result_end_ref, "C", result_end_coordinates, visible=derived_visible)
            result = self._upsert_addition_linear(
                result_ref,
                result_start,
                result_end,
                name="a+b",
                role="result",
                color="#7B61FF",
                style="solid",
                label="a+b",
                visible=derived_visible,
            )
            relation["result_vector"] = result_ref
        if result is None:
            return False
        if {result.start_point_id, result.end_point_id} & input_point_ids:
            # Older relations may already bind the sum to input points. Detach
            # them once so the result endpoint C remains independently movable.
            result_start = self._upsert_addition_point(result_start_ref, "", anchor, visible=derived_visible)
            result_end = self._upsert_addition_point(result_end_ref, "C", result_end_coordinates, visible=derived_visible)
            result.start_point_id = result_start.id
            result.end_point_id = result_end.id
            if controller is not None:
                controller.linears.pop(result.id, None)
                controller.add_linear(result)
        result_start = self._geometry_point_ref(result.start_point_id)
        result_end = self._geometry_point_ref(result.end_point_id)
        if result_start is None or result_end is None:
            return False
        # 讲义中预先声明的和向量可能带有 transformed_a/primary 角色；
        # 关系刷新后它仍然是学生要读的 a+b 结果，必须走结果向量的代数格式。
        result.role = "result"
        result.label = "a+b"
        self._set_addition_point_name(result_start, "")
        self._set_addition_point_name(result_end, "C")
        result.display_start_name = first_start.name.strip()
        result.display_end_name = result_end.name.strip()
        begin_batch = getattr(controller, "begin_batch_update", None)
        end_batch = getattr(controller, "end_batch_update", None)
        if callable(begin_batch):
            begin_batch()
        self._pane_scene()._updating_vector_additions = True
        try:
            # 选择的两条输入向量和画布、代数区使用同一套 a、b 记号。
            first.label = first_label
            second.label = second_label
            if controller is not None:
                controller.add_linear(first)
                controller.add_linear(second)
            self._move_addition_point(result_start, anchor)
            self._move_addition_point(result_end, result_end_coordinates)
            # 隐藏结果向量时仍保留输入向量共用端点。
            sync_visibility(result_start, derived_visible or result_start.id in input_point_ids)
            sync_visibility(result_end, derived_visible or result_end.id in input_point_ids)
            sync_visibility(result, derived_visible)
            # 图上只标示向量名称；分量计算属于代数区，不把坐标重复压在箭头上。
            if controller is not None:
                controller.add_linear(result)

            translated = self._geometry_linear_ref(relation.get("translated_vector"))
            translated_start_coordinates = (anchor[0] + first_vector[0], anchor[1] + first_vector[1])
            if translated is None and create_missing and show_triangle:
                translated_ref = str(relation.get("translated_vector") or f"{relation_id}__translated_b")
                start_ref = f"{translated_ref}__start"
                end_ref = f"{translated_ref}__end"
                translated_start = self._upsert_addition_point(start_ref, "", translated_start_coordinates, visible=derived_visible)
                translated_end = self._upsert_addition_point(end_ref, "", result_end_coordinates, visible=derived_visible)
                translated = self._upsert_addition_linear(
                    translated_ref,
                    translated_start,
                    translated_end,
                    name="b",
                    role="construction",
                    color="#2f9e5b",
                    style="dashed",
                    label="b",
                    visible=derived_visible,
                )
                relation["translated_vector"] = translated_ref
            if translated is not None and show_triangle:
                translated_start = self._geometry_point_ref(translated.start_point_id)
                translated_end = self._geometry_point_ref(translated.end_point_id)
                if translated_start is not None and translated_end is not None:
                    self._move_addition_point(translated_start, translated_start_coordinates)
                    self._move_addition_point(translated_end, result_end_coordinates)
                    sync_visibility(translated_start, derived_visible)
                    sync_visibility(translated_end, derived_visible)
                    sync_visibility(translated, derived_visible)
                    if controller is not None:
                        controller.add_linear(translated)
            elif translated is not None:
                sync_visibility(translated, False)
                translated_start = self._geometry_point_ref(translated.start_point_id)
                translated_end = self._geometry_point_ref(translated.end_point_id)
                if translated_start is not None:
                    sync_visibility(translated_start, False)
                if translated_end is not None:
                    sync_visibility(translated_end, False)

            raw_construction_aliases = relation.get("construction_aliases", ())
            construction_aliases = (
                list(raw_construction_aliases)
                if isinstance(raw_construction_aliases, (list, tuple))
                else []
            )
            if not construction_aliases and show_parallelogram:
                construction_aliases = [
                    f"{relation_id}__construction_b",
                    f"{relation_id}__construction_a",
                ]
                relation["construction_aliases"] = construction_aliases
            translated_a_start = None
            if show_parallelogram:
                translated_a_start = self._upsert_addition_point(
                    f"{relation_id}__translated_a_start",
                    "",
                    (anchor[0] + second_vector[0], anchor[1] + second_vector[1]),
                    visible=derived_visible,
                )
            for index, construction_alias in enumerate(str(value) for value in construction_aliases):
                construction = self._geometry_linear_ref(construction_alias)
                start_point = first_end if index == 0 else translated_a_start
                if start_point is None:
                    if construction is not None:
                        construction.visible = False
                    continue
                if construction is None and create_missing:
                    construction = self._upsert_addition_linear(
                        construction_alias,
                        start_point,
                        result_end,
                        role="construction",
                        color="#6c7b8d",
                        style="dashed",
                    )
                elif construction is not None:
                    construction.start_point_id = start_point.id
                    construction.end_point_id = result_end.id
                    construction.role = "construction"
                    construction.style = "dashed"
                    construction.visible = derived_visible
                    controller = getattr(self._pane_scene(), "geometry_controller", None)
                    if controller is not None:
                        controller.linears.pop(construction.id, None)
                        controller.add_linear(construction)
            if not show_parallelogram:
                for construction_alias in construction_aliases:
                    construction = self._geometry_linear_ref(construction_alias)
                    if construction is not None:
                        sync_visibility(construction, False)

            polygon_aliases = relation.get("polygon_aliases")
            if not isinstance(polygon_aliases, (list, tuple)) or not polygon_aliases:
                single_polygon = relation.get("polygon_alias")
                polygon_aliases = (
                    [str(single_polygon)] if single_polygon
                    else [f"{relation_id}__parallelogram"] if show_parallelogram
                    else []
                )
                relation["polygon_aliases"] = list(polygon_aliases)
            vertices = [
                [anchor[0], anchor[1]],
                [anchor[0] + first_vector[0], anchor[1] + first_vector[1]],
                [result_end_coordinates[0], result_end_coordinates[1]],
                [anchor[0] + second_vector[0], anchor[1] + second_vector[1]],
            ]
            for polygon_alias in (str(value) for value in polygon_aliases):
                if not show_parallelogram:
                    controller = getattr(self._pane_scene(), "geometry_controller", None)
                    if controller is not None:
                        controller.set_teaching_visible(polygon_alias, False)
                    continue
                polygon = self._pane_scene()._agent_teaching_2d.get(polygon_alias)
                if polygon is None:
                    polygon = {
                        "op": "geometry.polygon",
                        "alias": polygon_alias,
                        "vertices": vertices,
                        "color": "#6B7280",
                        "opacity": 0.14,
                        "outline": True,
                    }
                else:
                    polygon["vertices"] = vertices
                self._pane_scene()._agent_teaching_2d[polygon_alias] = dict(polygon)
                controller = getattr(self._pane_scene(), "geometry_controller", None)
                if controller is not None:
                    controller.add_teaching_polygon(
                        polygon_alias,
                        tuple(tuple(float(value) for value in point) for point in vertices),
                        color=str(polygon.get("color", "#6B7280")),
                        opacity=float(polygon.get("opacity", 0.14)),
                        outline=bool(polygon.get("outline", True)),
                    )
                    controller.set_teaching_visible(polygon_alias, derived_visible)
            annotation_alias = relation.get("annotation_alias")
            show_result_annotation = relation.get(
                "show_result_annotation",
                not relation_id.startswith("la_addition_"),
            ) is not False
            if annotation_alias and show_result_annotation:
                annotation_text = "a+b"
                annotation = self._upsert_addition_annotation(
                    str(annotation_alias),
                    annotation_text,
                    (
                        anchor[0] + (first_vector[0] + second_vector[0]) * 0.62,
                        anchor[1] + (first_vector[1] + second_vector[1]) * 0.62,
                    ),
                    visible=derived_visible,
                )
            elif annotation_alias:
                annotation = next(
                    (
                        item
                        for item in self._pane_scene().annotations
                        if item.agent_alias == str(annotation_alias)
                    ),
                    None,
                )
                if annotation is not None:
                    sync_visibility(annotation, False)
        finally:
            self._pane_scene()._updating_vector_additions = False
            if callable(end_batch):
                end_batch()
        # 结果向量的代数式依赖端点坐标；仅同步端点行不会重新计算
        # ``a+b=(...)``。关系刷新完成后立即重发当前窗格的完整对象列表，
        # 避免必须最小化/恢复窗口才看到最新结果。
        active_pane_id = getattr(getattr(self, "pane_manager", None), "active_pane_id", None)
        panel = getattr(self, "algebra_panel", None)
        if panel is not None and self._pane().pane_id == active_pane_id:
            panel.set_layers(self._two_d_panel_layers())
        return True

    def _update_vector_additions_for_point(self, point_id: str) -> None:
        # Toolbar projections are bound to their input vectors as well as
        # vector-addition relations.  Refresh them before the addition early
        # return so projection-only scenes are handled too.
        self._update_vector_projections_for_point(point_id)
        relations = getattr(self._pane_scene(), "_vector_additions", ())
        if not relations:
            self._refresh_constrained_points()
            return
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        selected_id = controller.selected_id if controller is not None else None
        for relation in relations:
            first = self._geometry_linear_ref(relation.get("vector_a"))
            second = self._geometry_linear_ref(relation.get("vector_b"))
            result = self._geometry_linear_ref(relation.get("result_vector"))
            if first is None or second is None:
                continue
            first_points = {first.start_point_id, first.end_point_id}
            second_points = {second.start_point_id, second.end_point_id}
            result_end_id = result.end_point_id if result is not None else str(relation.get("result_end", ""))
            if point_id == result_end_id:
                selected_vector = selected_id if selected_id in {first.id, second.id} else relation.get("last_selected_vector")
                if selected_vector not in {first.id, second.id}:
                    selected_vector = first.id
                chosen = first if selected_vector == first.id else second
                moved_input_point_id: str | None = None
                chosen_start = self._geometry_point_ref(chosen.start_point_id)
                other = second if chosen is first else first
                other_start = self._geometry_point_ref(other.start_point_id)
                other_end = self._geometry_point_ref(other.end_point_id)
                target = self._geometry_point_ref(point_id)
                first_start = self._geometry_point_ref(first.start_point_id)
                if not any(value is None for value in (chosen_start, other_start, other_end, target, first_start)):
                    assert chosen_start is not None and other_start is not None and other_end is not None and target is not None and first_start is not None
                    other_vector = (other_end.x - other_start.x, other_end.y - other_start.y)
                    desired = (target.x - first_start.x - other_vector[0], target.y - first_start.y - other_vector[1])
                    begin_batch = getattr(controller, "begin_batch_update", None)
                    end_batch = getattr(controller, "end_batch_update", None)
                    if callable(begin_batch):
                        begin_batch()
                    try:
                        self._move_addition_point(chosen_start, (chosen_start.x, chosen_start.y))
                        chosen_end = self._geometry_point_ref(chosen.end_point_id)
                        if chosen_end is not None:
                            self._move_addition_point(chosen_end, (chosen_start.x + desired[0], chosen_start.y + desired[1]))
                            # Moving the result endpoint changes one of the
                            # original vectors.  Its live angle/projection
                            # overlays must be refreshed after that endpoint
                            # has received the new coordinates, not before.
                            moved_input_point_id = chosen_end.id
                    finally:
                        if callable(end_batch):
                            end_batch()
                if moved_input_point_id is not None:
                    self._update_vector_projections_for_point(moved_input_point_id)
            if point_id in first_points or point_id in second_points or point_id == result_end_id:
                self._refresh_vector_addition(relation, create_missing=True)
        self._refresh_constrained_points()

    def _update_vector_projections_for_point(self, point_id: str) -> None:
        """Recompute live angle/projection overlays after an endpoint moves.

        Toolbar drawings are teaching overlays rather than editable vectors.
        Their operation records retain both source vector ids so each overlay
        can be rebuilt from current point coordinates.
        """
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is None:
            return
        teaching = getattr(self._pane_scene(), "_agent_teaching_2d", {})
        for alias, raw_operation in tuple(teaching.items()):
            if (
                not isinstance(raw_operation, dict)
                or raw_operation.get("op") not in {"geometry.angle_arc", "geometry.projection"}
            ):
                continue
            source_ref = raw_operation.get("source_vector_id")
            direction_ref = raw_operation.get("direction_vector_id")
            if source_ref is None or direction_ref is None:
                # Lecture-provided projections are static unless they opt into
                # the toolbar's live source-vector binding.
                continue
            source = self._geometry_linear_ref(source_ref)
            direction = self._geometry_linear_ref(direction_ref)
            if (
                source is None
                or direction is None
                or source.kind != "vector"
                or direction.kind != "vector"
            ):
                continue
            source_points = {source.start_point_id, source.end_point_id}
            direction_points = {direction.start_point_id, direction.end_point_id}
            if point_id not in source_points | direction_points:
                continue
            source_start = self._geometry_point_ref(source.start_point_id)
            source_end = self._geometry_point_ref(source.end_point_id)
            direction_start = self._geometry_point_ref(direction.start_point_id)
            direction_end = self._geometry_point_ref(direction.end_point_id)
            if any(point is None for point in (source_start, source_end, direction_start, direction_end)):
                continue
            assert source_start is not None and source_end is not None
            assert direction_start is not None and direction_end is not None
            vector = (source_end.x - source_start.x, source_end.y - source_start.y)
            direction_vector = (
                direction_end.x - direction_start.x,
                direction_end.y - direction_start.y,
            )
            source_length = hypot(*vector)
            direction_length = hypot(*direction_vector)
            if source_length <= 1e-12 or direction_length <= 1e-12:
                # Angle and projection both require two non-zero vectors. Keep
                # the last valid overlay until the user restores them.
                continue
            operation = dict(raw_operation)
            annotation_alias = str(operation.get("annotation_alias", f"{alias}_label"))
            annotation = next(
                (item for item in self._pane_scene().annotations if item.agent_alias == annotation_alias),
                None,
            )
            if operation["op"] == "geometry.angle_arc":
                cosine = (
                    vector[0] * direction_vector[0]
                    + vector[1] * direction_vector[1]
                ) / (source_length * direction_length)
                angle = degrees(acos(max(-1.0, min(1.0, cosine))))
                radius = max(0.25, min(0.8, min(source_length, direction_length) * 0.22))
                vertex = (source_start.x, source_start.y)
                operation.update(
                    {
                        "vertex": [*vertex],
                        "first": [vertex[0] + vector[0], vertex[1] + vector[1]],
                        "second": [
                            vertex[0] + direction_vector[0],
                            vertex[1] + direction_vector[1],
                        ],
                        "radius": radius,
                    }
                )
                teaching[str(alias)] = operation
                controller.add_teaching_angle_arc(
                    str(operation.get("alias", alias)),
                    tuple(operation["vertex"]),  # type: ignore[arg-type]
                    tuple(operation["first"]),  # type: ignore[arg-type]
                    tuple(operation["second"]),  # type: ignore[arg-type]
                    radius=radius,
                    color=str(operation.get("color", "#d97845")),
                )
                if annotation is not None:
                    bisector = (
                        vector[0] / source_length + direction_vector[0] / direction_length,
                        vector[1] / source_length + direction_vector[1] / direction_length,
                    )
                    bisector_length = hypot(*bisector)
                    if bisector_length <= 1e-12:
                        bisector = (-vector[1] / source_length, vector[0] / source_length)
                    else:
                        bisector = (
                            bisector[0] / bisector_length,
                            bisector[1] / bisector_length,
                        )
                    annotation.text = f"θ={angle:.1f}°"
                    annotation.latex = annotation.text
                    annotation.x = vertex[0] + bisector[0] * (radius + 0.28)
                    annotation.y = vertex[1] + bisector[1] * (radius + 0.28)
            else:
                denominator = direction_length * direction_length
                scale = (
                    vector[0] * direction_vector[0]
                    + vector[1] * direction_vector[1]
                ) / denominator
                projection = (
                    scale * direction_vector[0],
                    scale * direction_vector[1],
                )
                operation.update(
                    {
                        "vector": [vector[0], vector[1]],
                        "direction": [direction_vector[0], direction_vector[1]],
                        "origin": [source_start.x, source_start.y],
                        "style": "dashed",
                    }
                )
                teaching[str(alias)] = operation
                controller.add_teaching_projection(
                    vector,
                    direction_vector,
                    result_alias=str(operation.get("result_alias", f"{alias}_result")),
                    foot_alias=str(operation.get("foot_alias", f"{alias}_foot")),
                    residual_alias=str(operation.get("residual_alias", f"{alias}_residual")),
                    alias=str(operation.get("alias", alias)),
                    origin=(source_start.x, source_start.y),
                    color=str(operation.get("color", "#2777b6")),
                    style="dashed",
                )
                if annotation is not None:
                    projection_x = format_number(projection[0])
                    projection_y = format_number(projection[1])
                    annotation.text = f"proj_b(a)=({projection_x}, {projection_y})"
                    annotation.latex = (
                        r"\operatorname{proj}_{b}(a)="
                        rf"\left({projection_x},{projection_y}\right)"
                    )
                    annotation.x = source_start.x + 0.5 * projection[0]
                    annotation.y = source_start.y + 0.5 * projection[1]
            self._sync_vector_tool_direction_copy(operation)
            if annotation is not None:
                controller.annotations.pop(annotation.id, None)
                controller.add_annotation(annotation)

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
            # 撤销项应指向替换交互层前的场景。
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
        if self._pane_scene()._active_linear_algebra_tool == "addition":
            self._create_vector_addition_relation(first, second)
            self._select_geometry_object(None)
            return True
        active_tool = self._pane_scene()._active_linear_algebra_tool or ""
        self._clear_linear_algebra_tool_overlays()
        plan = self._build_linear_algebra_tool_plan(active_tool, (first, second))
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
        panel = getattr(self, "algebra_panel", None)
        if callable(getattr(panel, "add_matrix_transform_tab", None)):
            # 兼容恢复的旧工具状态；正式界面由代数输入区接收矩阵。
            pane_id = getattr(self.pane_manager, "active_pane_id", None)
            has_editor = (
                pane_id is not None
                and callable(getattr(panel, "matrix_transform_editor", None))
                and panel.matrix_transform_editor(pane_id) is not None
            )
            if not has_editor:
                self._open_matrix_transform_workspace()
            else:
                panel.set_status("矩阵变换工具：请在代数区列表中输入矩阵")
            return True
        self.algebra_panel.set_status("矩阵变换需要在代数区列表中输入矩阵", is_error=True)
        return True

    def _set_snap_to_grid(self, enabled: bool) -> None:
        self._pane_scene()._snap_to_grid = bool(enabled)
        self.algebra_panel.set_status("已开启网格吸附" if enabled else "已关闭网格吸附")

    def _linear_midpoint(self, linear: Linear2D) -> tuple[float, float] | None:
        if linear.kind not in {"segment", "vector"}:
            return None
        start = self._geometry_point_ref(linear.start_point_id)
        end = self._geometry_point_ref(linear.end_point_id)
        if start is None or end is None:
            return None
        return ((start.x + end.x) * 0.5, (start.y + end.y) * 0.5)

    @staticmethod
    def _linear_parameter_is_valid(kind: str, parameter: float) -> bool:
        tolerance = 1e-10
        if kind in {"segment", "vector"}:
            return -tolerance <= parameter <= 1.0 + tolerance
        if kind == "ray":
            return parameter >= -tolerance
        return True

    def _linear_intersection(
        self,
        first: Linear2D,
        second: Linear2D,
    ) -> tuple[float, float] | None:
        """Return the unique intersection within both primitives' domains."""
        first_start = self._geometry_point_ref(first.start_point_id)
        first_end = self._geometry_point_ref(first.end_point_id)
        second_start = self._geometry_point_ref(second.start_point_id)
        second_end = self._geometry_point_ref(second.end_point_id)
        if any(value is None for value in (first_start, first_end, second_start, second_end)):
            return None
        assert first_start is not None and first_end is not None
        assert second_start is not None and second_end is not None
        first_direction = (first_end.x - first_start.x, first_end.y - first_start.y)
        second_direction = (second_end.x - second_start.x, second_end.y - second_start.y)
        denominator = (
            first_direction[0] * second_direction[1]
            - first_direction[1] * second_direction[0]
        )
        scale = max(
            1.0,
            hypot(*first_direction) * hypot(*second_direction),
        )
        if abs(denominator) <= 1e-12 * scale:
            return None
        offset = (second_start.x - first_start.x, second_start.y - first_start.y)
        first_parameter = (
            offset[0] * second_direction[1]
            - offset[1] * second_direction[0]
        ) / denominator
        second_parameter = (
            offset[0] * first_direction[1]
            - offset[1] * first_direction[0]
        ) / denominator
        if not self._linear_parameter_is_valid(first.kind, first_parameter):
            return None
        if not self._linear_parameter_is_valid(second.kind, second_parameter):
            return None
        return (
            first_start.x + first_parameter * first_direction[0],
            first_start.y + first_parameter * first_direction[1],
        )

    def _intersection_pair_near(
        self,
        x: float,
        y: float,
    ) -> tuple[Linear2D, Linear2D] | None:
        best: tuple[float, Linear2D, Linear2D] | None = None
        visible = [linear for linear in self._pane_scene().linear_objects if linear.visible]
        tolerance_squared = (self._hit_tolerance() * 1.25) ** 2
        for index, first in enumerate(visible):
            for second in visible[index + 1:]:
                intersection = self._linear_intersection(first, second)
                if intersection is None:
                    continue
                distance_squared = (intersection[0] - x) ** 2 + (intersection[1] - y) ** 2
                if distance_squared <= tolerance_squared and (
                    best is None or distance_squared < best[0]
                ):
                    best = (distance_squared, first, second)
        return (best[1], best[2]) if best is not None else None

    def _set_point_constraint(
        self,
        point: Point2D,
        kind: str,
        references: tuple[str, ...],
        coordinates: tuple[float, float],
        *,
        owned: bool,
    ) -> None:
        point.constraint_kind = kind  # type: ignore[assignment]
        point.constraint_refs = references
        point.constraint_owned = owned
        point.visible = True
        point.x, point.y = coordinates
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.set_visible(point.id, True)
            controller.move_point(point.id, *coordinates)
        self.algebra_panel.sync_layer(point.id, point)

    def _create_constrained_point(
        self,
        kind: str,
        references: tuple[str, ...],
        coordinates: tuple[float, float],
        *,
        point: Point2D | None = None,
    ) -> Point2D:
        owned = False
        if point is None:
            point, owned = self._get_or_create_geometry_point(
                *coordinates,
                record_history=False,
            )
        self._set_point_constraint(
            point,
            kind,
            references,
            coordinates,
            owned=owned,
        )
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self._select_geometry_object(point.id)
        return point

    def _handle_midpoint_tool_click(self, x: float, y: float) -> bool:
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is None:
            return False
        pending_id = getattr(self._pane_scene(), "_pending_point_tool_point_id", None)
        linear_id = controller.hit_test_linear(
            x,
            y,
            self._hit_tolerance(),
            kinds={"segment", "vector"},
        )
        if pending_id is not None and linear_id is not None:
            point = self._point_2d(pending_id)
            linear = self._geometry_linear_ref(linear_id)
            if point is None or linear is None:
                self._pane_scene()._pending_point_tool_point_id = None
                return False
            if point.id in {linear.start_point_id, linear.end_point_id}:
                self.algebra_panel.set_status("不能把对象自身的端点附着到其中点", is_error=True)
                return True
            coordinates = self._linear_midpoint(linear)
            if coordinates is None:
                return False
            before = self._capture_geometry_state()
            self._create_constrained_point(
                "midpoint",
                (linear.id,),
                coordinates,
                point=point,
            )
            self._pane_scene()._pending_point_tool_point_id = None
            self._update_vector_additions_for_point(point.id)
            self._record_geometry_change(before)
            self.algebra_panel.set_status(f"已将点 {point.name} 附着到{self._TOOL_LABELS[linear.kind]} {linear.name} 的中点")
            self._pane_renderer().render()
            return True

        hit_id = controller.hit_test(x, y, self._hit_tolerance())
        hit_point = self._point_2d(hit_id)
        if hit_point is not None:
            self._pane_scene()._pending_point_tool_point_id = hit_point.id
            self._select_geometry_object(hit_point.id)
            self.algebra_panel.set_status(f"已选择点 {hit_point.name}，请再选择线段或向量")
            self._pane_renderer().render()
            return True
        if linear_id is None:
            self.algebra_panel.set_status("中点工具需要选择线段或向量", is_error=True)
            return True
        linear = self._geometry_linear_ref(linear_id)
        coordinates = self._linear_midpoint(linear) if linear is not None else None
        if linear is None or coordinates is None:
            return False
        before = self._capture_geometry_state()
        point = self._create_constrained_point("midpoint", (linear.id,), coordinates)
        self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已创建中点 {point.name}")
        self._pane_renderer().render()
        return True

    def _handle_intersection_tool_click(self, x: float, y: float) -> bool:
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is None:
            return False
        pair = self._intersection_pair_near(x, y)
        pending_id = getattr(self._pane_scene(), "_pending_point_tool_linear_id", None)
        if pair is None:
            linear_id = controller.hit_test_linear(
                x,
                y,
                self._hit_tolerance(),
                exclude={pending_id} if pending_id is not None else None,
            )
            if pending_id is None:
                if linear_id is None:
                    self.algebra_panel.set_status("请单击相交处，或依次选择两个直线类对象", is_error=True)
                    return True
                self._pane_scene()._pending_point_tool_linear_id = linear_id
                selected = self._geometry_linear_ref(linear_id)
                self._select_geometry_object(linear_id)
                self.algebra_panel.set_status(
                    f"已选择{self._TOOL_LABELS.get(selected.kind, '对象')} {selected.name}，请再选择一个对象"
                    if selected is not None
                    else "已选择第一个对象，请再选择一个对象"
                )
                self._pane_renderer().render()
                return True
            first = self._geometry_linear_ref(pending_id)
            second = self._geometry_linear_ref(linear_id) if linear_id is not None else None
            if first is None or second is None:
                self.algebra_panel.set_status("请选择与第一个对象相交的另一个对象", is_error=True)
                return True
            pair = (first, second)

        intersection = self._linear_intersection(*pair)
        if intersection is None:
            self.algebra_panel.set_status("所选对象没有唯一的有效交点", is_error=True)
            return True
        before = self._capture_geometry_state()
        point = self._create_constrained_point(
            "intersection",
            (pair[0].id, pair[1].id),
            intersection,
        )
        self._pane_scene()._pending_point_tool_linear_id = None
        self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已创建交点 {point.name}")
        self._pane_renderer().render()
        return True

    def _refresh_constrained_points(self) -> None:
        """Recompute midpoint/intersection points after source endpoints move."""
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        changed_ids: set[str] = set()
        for _pass in range(max(1, len(self._pane_scene().geometry_points))):
            changed_this_pass = False
            for point in self._pane_scene().geometry_points:
                coordinates: tuple[float, float] | None = None
                if point.constraint_kind == "midpoint" and len(point.constraint_refs) == 1:
                    linear = self._geometry_linear_ref(point.constraint_refs[0])
                    coordinates = self._linear_midpoint(linear) if linear is not None else None
                elif point.constraint_kind == "intersection" and len(point.constraint_refs) == 2:
                    first = self._geometry_linear_ref(point.constraint_refs[0])
                    second = self._geometry_linear_ref(point.constraint_refs[1])
                    if first is not None and second is not None:
                        coordinates = self._linear_intersection(first, second)
                if point.constraint_kind is None:
                    continue
                visible = coordinates is not None
                if point.visible != visible:
                    point.visible = visible
                    if controller is not None:
                        controller.set_visible(point.id, visible)
                    changed_this_pass = True
                if coordinates is None:
                    continue
                if abs(point.x - coordinates[0]) <= 1e-10 and abs(point.y - coordinates[1]) <= 1e-10:
                    continue
                point.x, point.y = coordinates
                if controller is not None:
                    controller.move_point(point.id, *coordinates)
                self.algebra_panel.sync_layer(point.id, point)
                changed_ids.add(point.id)
                changed_this_pass = True
            if not changed_this_pass:
                break
        for point_id in changed_ids:
            self._update_vector_projections_for_point(point_id)

    def _capture_geometry_state(self) -> _GeometryHistoryState:
        """复制当前几何状态，避免后续点移动修改历史快照。"""
        return _GeometryHistoryState(
            points=tuple(replace(point) for point in self._pane_scene().geometry_points),
            linears=tuple(replace(linear) for linear in self._pane_scene().linear_objects),
            object_order=tuple(self._pane_scene()._two_d_object_order),
            annotations=tuple(replace(a) for a in getattr(self._pane_scene(), "annotations", [])),
            curves=tuple(replace(c) for c in getattr(self._pane_scene(), "curve_layers", [])),
            teaching_2d=tuple(
                (alias, dict(operation))
                for alias, operation in getattr(self._pane_scene(), "_agent_teaching_2d", {}).items()
            ),
            vector_additions=tuple(
                dict(relation) for relation in getattr(self._pane_scene(), "_vector_additions", ())
            ),
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
        can_undo = bool(getattr(self.pane_manager, "can_undo", False)) or bool(
            getattr(self._pane_scene(), "_geometry_undo_stack", [])
        ) or bool(
            getattr(self._pane_scene(), "_scene_command_undo_stack", [])
        )
        can_redo = bool(getattr(self.pane_manager, "can_redo", False)) or bool(
            getattr(self._pane_scene(), "_geometry_redo_stack", [])
        ) or bool(
            getattr(self._pane_scene(), "_scene_command_redo_stack", [])
        )
        for toolbar in (
            getattr(self, "two_d_geometry_toolbar", None),
            getattr(self, "three_d_geometry_toolbar", None),
        ):
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
        self._pane_scene()._agent_teaching_2d = {alias: dict(operation) for alias, operation in state.teaching_2d}
        self._pane_scene()._vector_additions = [dict(relation) for relation in state.vector_additions]
        self._pane_scene()._two_d_object_order = list(state.object_order)
        self._pane_scene()._pending_geometry_point_id = None
        self._pane_scene()._pending_point_tool_point_id = None
        self._pane_scene()._pending_point_tool_linear_id = None
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._dragging_annotation_id = None
        self._pane_scene()._drag_moved = False
        self._pane_scene()._drag_start_geometry_state = None

        renderer = self._pane_renderer(required=False)
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if renderer is not None and controller is not None:
            controller.clear_draft()
            controller.clear_teaching()
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
            for operation in tuple(getattr(self._pane_scene(), "_agent_teaching_2d", {}).values()):
                self._command_teaching_geometry(operation)
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
        commit_annotation = getattr(self.algebra_panel, "commit_annotation_edit", None)
        if callable(commit_annotation):
            commit_annotation()
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            return self._handle_3d_annotation_mouse_press(event)
        tool = self._pane_scene()._active_2d_tool
        linear_algebra_tool = getattr(self._pane_scene(), "_active_linear_algebra_tool", None)
        if (
            self._pane_scene().scene_mode is not SceneMode.TWO_D
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return False
        if tool is None and linear_algebra_tool is None:
            coordinates = self._viewport_to_world(event.position().x(), event.position().y())
            if coordinates is not None and self._begin_annotation_drag(*coordinates):
                event.accept()
                return True
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
            if linear_algebra_tool in {"addition", "angle", "projection", "subspace", "area"}:
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
        if tool == "annotation":
            if self._begin_annotation_drag(*coordinates):
                event.accept()
                return True
            self._create_2d_annotation(*coordinates)
            self._set_2d_geometry_tool(None)
            event.accept()
            return True
        coordinates = self._maybe_snap(*coordinates)
        if tool == "midpoint":
            handled = self._handle_midpoint_tool_click(*coordinates)
            if handled:
                event.accept()
            return handled
        if tool == "intersection":
            handled = self._handle_intersection_tool_click(*coordinates)
            if handled:
                event.accept()
            return handled
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
        linear = self._create_linear_geometry(
            self._linear_geometry_kind(tool),
            first,
            point,
            style=self._linear_geometry_style(tool),
            record_history=False,
        )
        self._pane_scene()._pending_geometry_point_id = None
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.clear_draft()
        if not getattr(self._pane_scene(), "_scene_command_active", False):
            self._record_geometry_change(before)
        self.algebra_panel.set_status(f"已创建{self._TOOL_LABELS[tool]} {linear.name}")
        self._pane_renderer().render()
        event.accept()
        return True

    def _handle_3d_annotation_mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        annotation_alias = self._three_d_annotation_at(event)
        if annotation_alias is not None:
            scene = self._pane_scene()
            scene._dragging_3d_annotation_alias = annotation_alias
            scene._dragging_3d_annotation_moved = False
            scene._drag_start_3d_annotation_state = self._capture_scene_command_state()
            select_layer = getattr(self.algebra_panel, "set_selected_layer", None)
            if callable(select_layer):
                select_layer(annotation_alias)
            self._set_3d_annotation_hover(annotation_alias)
            self._set_3d_annotation_cursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return True
        if not getattr(self._pane_scene(), "_pending_3d_annotation", False):
            return False
        position = self._three_d_annotation_position(event)
        if position is None:
            self.algebra_panel.set_status("无法确定标记位置，请在三维视口内单击", is_error=True)
            event.accept()
            return True
        if self._create_3d_annotation(position):
            self._pane_scene()._pending_3d_annotation = False
            toolbar = getattr(self, "three_d_geometry_toolbar", None)
            if toolbar is not None:
                toolbar.set_annotation_active(False)
            self._set_3d_annotation_cursor(Qt.CursorShape.ArrowCursor)
        event.accept()
        return True

    def _handle_3d_annotation_mouse_move(self, event: QMouseEvent) -> bool:
        scene = self._pane_scene()
        alias = getattr(scene, "_dragging_3d_annotation_alias", None)
        if alias is not None:
            position = self._three_d_annotation_position(event)
            operation = getattr(scene, "_agent_geometry3d", {}).get(f"annotation:{alias}")
            if position is None or not isinstance(operation, dict):
                return True
            updated = dict(operation)
            updated["position"] = position
            self._command_formula_annotation(updated)
            scene._dragging_3d_annotation_moved = True
            row = self._three_d_annotation_row(alias)
            if row is not None:
                self.algebra_panel.sync_layer(alias, row)
            renderer = self._pane_renderer(required=False)
            if renderer is not None and callable(getattr(renderer, "render", None)):
                renderer.render()
            event.accept()
            return True

        annotation_alias = self._three_d_annotation_at(event)
        self._set_3d_annotation_hover(annotation_alias)
        cursor = (
            Qt.CursorShape.OpenHandCursor
            if annotation_alias is not None
            else Qt.CursorShape.CrossCursor
            if getattr(scene, "_pending_3d_annotation", False)
            else Qt.CursorShape.ArrowCursor
        )
        self._set_3d_annotation_cursor(cursor)
        return False

    def _handle_3d_annotation_mouse_release(self, event: QMouseEvent) -> bool:
        scene = self._pane_scene()
        alias = getattr(scene, "_dragging_3d_annotation_alias", None)
        if alias is None:
            return False
        if scene._dragging_3d_annotation_moved:
            before = scene._drag_start_3d_annotation_state
            after = self._capture_scene_command_state()
            if before is not None and before != after:
                pane_id = self._pane().pane_id
                self.pane_manager.push(
                    pane_id,
                    lambda state=before, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                    lambda state=after, target=pane_id: self._restore_scene_command_state_for_pane(target, state),
                    "移动三维标记",
                )
                self._sync_pane_state()
                row = self._three_d_annotation_row(alias)
                if row is not None:
                    self.algebra_panel.sync_layer(alias, row)
                self.algebra_panel.set_status(f"已移动标记 {row.name if row is not None else alias}")
                self._update_geometry_history_controls()
        scene._dragging_3d_annotation_alias = None
        scene._dragging_3d_annotation_moved = False
        scene._drag_start_3d_annotation_state = None
        hovered_alias = self._three_d_annotation_at(event)
        self._set_3d_annotation_hover(hovered_alias)
        self._set_3d_annotation_cursor(
            Qt.CursorShape.OpenHandCursor
            if hovered_alias is not None
            else Qt.CursorShape.CrossCursor
            if getattr(scene, "_pending_3d_annotation", False)
            else Qt.CursorShape.ArrowCursor
        )
        event.accept()
        return True

    def _set_3d_annotation_cursor(self, cursor: Qt.CursorShape) -> None:
        interactor = getattr(self._pane_renderer(required=False), "interactor", None)
        set_cursor = getattr(interactor, "setCursor", None)
        if callable(set_cursor):
            set_cursor(cursor)

    def _set_3d_annotation_hover(self, alias: str | None) -> None:
        """Redraw the previous and current 3-D mark when hover changes."""
        scene = self._pane_scene()
        previous = getattr(scene, "_hovered_3d_annotation_alias", None)
        if alias == previous:
            return
        scene._hovered_3d_annotation_alias = alias
        operations = getattr(scene, "_agent_geometry3d", {})
        for candidate in (previous, alias):
            if candidate is None:
                continue
            operation = operations.get(f"annotation:{candidate}")
            if isinstance(operation, dict):
                self._command_formula_annotation(dict(operation))
        renderer = self._pane_renderer(required=False)
        if renderer is not None and callable(getattr(renderer, "render", None)):
            renderer.render()

    def _three_d_annotation_at(self, event: QMouseEvent) -> str | None:
        """Pick a toolbar-created 3-D mark by its projected label anchor."""
        plotter = self._pane_renderer(required=False)
        interactor = getattr(plotter, "interactor", None)
        vtk_interactor = getattr(plotter, "iren", None)
        if interactor is None or vtk_interactor is None:
            return None
        try:
            width = max(1, int(interactor.width()))
            height = max(1, int(interactor.height()))
            screen_x = float(event.position().x())
            screen_y = float(event.position().y())
            if not 0.0 <= screen_x <= width or not 0.0 <= screen_y <= height:
                return None
            renderer = vtk_interactor.get_poked_renderer(int(screen_x), int(height - screen_y))
            if renderer is None:
                return None
            best: tuple[float, str] | None = None
            for key, operation in getattr(self._pane_scene(), "_agent_geometry3d", {}).items():
                if not str(key).startswith("annotation:") or not isinstance(operation, dict):
                    continue
                alias = str(key).removeprefix("annotation:")
                if (
                    not alias.startswith("manual_annotation_")
                    or operation.get("op") != "annotation.formula"
                    or operation.get("visible") is False
                ):
                    continue
                position = tuple(float(value) for value in operation["position"])
                if len(position) != 3:
                    continue
                renderer.SetWorldPoint(*position, 1.0)
                renderer.WorldToDisplay()
                display = renderer.GetDisplayPoint()
                distance_sq = (float(display[0]) - screen_x) ** 2 + (height - float(display[1]) - screen_y) ** 2
                if distance_sq <= 18.0**2 and (best is None or distance_sq < best[0]):
                    best = (distance_sq, alias)
            return best[1] if best is not None else None
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
            return None

    def _begin_select_or_drag(self, x: float, y: float) -> bool:
        """选择工具左键按下：命中对象则选中，可编辑点和标记可拖动。"""
        if self._pane_scene().geometry_controller is None:
            return False
        hit_id = self._pane_scene().geometry_controller.hit_test(x, y, self._hit_tolerance())
        curve_controller = getattr(self._pane_scene(), "curve_controller", None)
        if hit_id is None and curve_controller is not None:
            hit_id = curve_controller.hit_test(x, y, self._hit_tolerance())
        self._select_geometry_object(hit_id)
        controller = self._pane_scene().geometry_controller
        self._pane_scene()._dragging_point_id = hit_id if hit_id in controller.points else None
        self._pane_scene()._dragging_annotation_id = (
            hit_id
            if hit_id in controller.annotations and controller.annotations[hit_id].editable
            else None
        )
        self._pane_scene()._drag_start_geometry_state = (
            self._capture_geometry_state()
            if self._pane_scene()._dragging_point_id is not None
            or self._pane_scene()._dragging_annotation_id is not None
            else None
        )
        self._pane_scene()._drag_moved = False
        if (
            self._pane_scene()._dragging_point_id is not None
            or self._pane_scene()._dragging_annotation_id is not None
        ):
            self._pane_renderer().interactor.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._pane_renderer().render()
        # 命中对象时拦截事件，避免触发相机平移；未命中则放行以便平移画布。
        return hit_id is not None

    def _begin_annotation_drag(self, x: float, y: float) -> bool:
        """Start moving an editable mark while the mark tool is active."""
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is None:
            return False
        annotation_id = controller.hit_test_annotation(
            x, y, self._hit_tolerance(), editable_only=True
        )
        if annotation_id is None:
            return False
        self._select_geometry_object(annotation_id)
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._dragging_annotation_id = annotation_id
        self._pane_scene()._drag_start_geometry_state = self._capture_geometry_state()
        self._pane_scene()._drag_moved = False
        self._pane_renderer().interactor.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._pane_renderer().render()
        return True

    def _handle_geometry_mouse_move(self, event: QMouseEvent) -> bool:
        if self._pane_scene().scene_mode is SceneMode.THREE_D:
            return self._handle_3d_annotation_mouse_move(event)
        if self._pane_scene().scene_mode is not SceneMode.TWO_D or self._pane_scene().geometry_controller is None:
            return False
        tool = self._pane_scene()._active_2d_tool
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        if coordinates is None:
            if self._pane_scene()._dragging_annotation_id is None:
                if self._pane_scene().geometry_controller.set_hover(None):
                    self._pane_renderer().render()
                self._pane_renderer().interactor.setCursor(
                    Qt.CursorShape.CrossCursor
                    if tool == "annotation"
                    else Qt.CursorShape.ArrowCursor
                )
            return False
        if self._pane_scene()._dragging_annotation_id is not None:
            annotation_id = self._pane_scene()._dragging_annotation_id
            self._pane_scene().geometry_controller.move_annotation(
                annotation_id, *coordinates
            )
            annotation = self._annotation_2d(annotation_id)
            if annotation is not None:
                self.algebra_panel.sync_layer(annotation.id, annotation)
            self._pane_scene()._drag_moved = True
            self._pane_renderer().render()
            event.accept()
            return True
        if tool in {None, "annotation"}:
            annotation_id = self._pane_scene().geometry_controller.hit_test_annotation(
                *coordinates, self._hit_tolerance(), editable_only=True
            )
            if self._pane_scene().geometry_controller.set_hover(annotation_id):
                self._pane_renderer().render()
            self._pane_renderer().interactor.setCursor(
                Qt.CursorShape.OpenHandCursor
                if annotation_id is not None
                else Qt.CursorShape.CrossCursor
                if tool == "annotation"
                else Qt.CursorShape.ArrowCursor
            )
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
                dragged_point = self._point_2d(self._pane_scene()._dragging_point_id)
                if dragged_point is not None and dragged_point.constraint_kind is not None:
                    # A deliberate free drag releases a previously attached
                    # midpoint/intersection from its source objects.
                    dragged_point.constraint_kind = None
                    dragged_point.constraint_refs = ()
                    dragged_point.constraint_owned = False
                self._pane_scene().geometry_controller.move_point(self._pane_scene()._dragging_point_id, *snapped)
                point = dragged_point
                if point is not None:
                    point.x, point.y = snapped
                    self.algebra_panel.sync_layer(point.id, point)
                    self._update_vector_additions_for_point(point.id)
                self._pane_scene()._drag_moved = True
                self._pane_renderer().render()
                return True
            # 悬浮高亮：命中变化时才重绘。
            hit_id = self._pane_scene().geometry_controller.hit_test(*coordinates, self._hit_tolerance())
            if self._pane_scene().geometry_controller.set_hover(hit_id):
                cursor = (
                    Qt.CursorShape.OpenHandCursor
                    if hit_id in self._pane_scene().geometry_controller.points
                    or (
                        hit_id in self._pane_scene().geometry_controller.annotations
                        and self._pane_scene().geometry_controller.annotations[hit_id].editable
                    )
                    else Qt.CursorShape.PointingHandCursor
                    if hit_id is not None
                    else Qt.CursorShape.ArrowCursor
                )
                self._pane_renderer().interactor.setCursor(cursor)
                self._pane_renderer().render()
            return False
        if tool in {"midpoint", "intersection"}:
            controller = self._pane_scene().geometry_controller
            if tool == "midpoint":
                hit_id = controller.hit_test(*coordinates, self._hit_tolerance())
                if hit_id not in controller.points:
                    hit_id = controller.hit_test_linear(
                        *coordinates,
                        self._hit_tolerance(),
                        kinds={"segment", "vector"},
                    )
            else:
                pair = self._intersection_pair_near(*coordinates)
                hit_id = (
                    pair[0].id
                    if pair is not None
                    else controller.hit_test_linear(*coordinates, self._hit_tolerance())
                )
            if controller.set_hover(hit_id):
                self._pane_renderer().render()
            self._pane_renderer().interactor.setCursor(
                Qt.CursorShape.PointingHandCursor
                if hit_id is not None
                else Qt.CursorShape.CrossCursor
            )
            return False
        if (
            tool in {"line", "segment", "dashed_segment", "ray", "vector"}
            and self._pane_scene()._pending_geometry_point_id is not None
        ):
            first = self._point_2d(self._pane_scene()._pending_geometry_point_id)
            if first is not None:
                self._pane_scene().geometry_controller.set_draft(
                    self._linear_geometry_kind(tool),
                    first,
                    self._maybe_snap(*coordinates),
                    style=self._linear_geometry_style(tool),
                )
                self._pane_renderer().render()
        return False

    def _handle_geometry_mouse_leave(self) -> bool:
        """Clear marker hover feedback as soon as the pointer exits a viewport."""
        scene = self._pane_scene()
        if scene.scene_mode is SceneMode.THREE_D:
            if getattr(scene, "_dragging_3d_annotation_alias", None) is None:
                self._set_3d_annotation_hover(None)
                self._set_3d_annotation_cursor(Qt.CursorShape.ArrowCursor)
            return False
        controller = getattr(scene, "geometry_controller", None)
        if controller is not None and getattr(scene, "_dragging_annotation_id", None) is None:
            if controller.set_hover(None):
                self._pane_renderer().render()
            self._pane_renderer().interactor.setCursor(Qt.CursorShape.ArrowCursor)
        return False

    def _handle_geometry_mouse_release(self, event: QMouseEvent) -> bool:
        scene = self._pane_scene()
        if scene.scene_mode is SceneMode.THREE_D:
            return self._handle_3d_annotation_mouse_release(event)
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
        if (
            self._pane_scene()._dragging_point_id is None
            and self._pane_scene()._dragging_annotation_id is None
        ):
            return False
        point = self._point_2d(self._pane_scene()._dragging_point_id)
        annotation = self._annotation_2d(self._pane_scene()._dragging_annotation_id)
        if point is not None and self._pane_scene()._drag_moved:
            if self._pane_scene()._drag_start_geometry_state is not None:
                self._record_geometry_change(self._pane_scene()._drag_start_geometry_state)
            self.algebra_panel.set_status(f"已移动点 {point.name}")
        elif annotation is not None and self._pane_scene()._drag_moved:
            if self._pane_scene()._drag_start_geometry_state is not None:
                self._record_geometry_change(self._pane_scene()._drag_start_geometry_state)
            self.algebra_panel.set_status(f"已移动标记 {annotation.name}")
        self._pane_scene()._dragging_point_id = None
        self._pane_scene()._dragging_annotation_id = None
        self._pane_scene()._drag_moved = False
        self._pane_scene()._drag_start_geometry_state = None
        coordinates = self._viewport_to_world(event.position().x(), event.position().y())
        remaining_annotation = (
            self._pane_scene().geometry_controller.hit_test_annotation(
                *coordinates, self._hit_tolerance(), editable_only=True
            )
            if coordinates is not None and self._pane_scene().geometry_controller is not None
            else None
        )
        self._pane_renderer().interactor.setCursor(
            Qt.CursorShape.OpenHandCursor
            if remaining_annotation is not None
            else Qt.CursorShape.CrossCursor
            if self._pane_scene()._active_2d_tool == "annotation"
            else Qt.CursorShape.ArrowCursor
        )
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
        curve_controller = getattr(self._pane_scene(), "curve_controller", None)
        if curve_controller is not None:
            curve_controller.set_selected(
                object_id if self._curve_layer(object_id or "") is not None else None
            )
        if self._pane_scene().geometry_controller is not None:
            geometry_id = (
                object_id
                if object_id is not None and self._geometry_object(object_id) is not None
                else None
            )
            self._pane_scene().geometry_controller.set_selected(geometry_id)
            selected = self._geometry_object(object_id) if object_id is not None else None
            if isinstance(selected, Linear2D) and selected.kind == "vector":
                for relation in getattr(self._pane_scene(), "_vector_additions", ()):
                    if selected.id in {relation.get("vector_a"), relation.get("vector_b")}:
                        relation["last_selected_vector"] = selected.id
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

    def _three_d_annotation_position(self, event: QMouseEvent) -> tuple[float, float, float] | None:
        """Map a viewport click to the plane through the current camera focus.

        A focal-plane projection keeps marks placeable over empty space instead
        of requiring a mesh pick, while still following the visible 3-D view.
        """
        plotter = self._pane_renderer(required=False)
        interactor = getattr(plotter, "interactor", None)
        vtk_interactor = getattr(plotter, "iren", None)
        if interactor is None or vtk_interactor is None:
            return None
        try:
            width = max(1, int(interactor.width()))
            height = max(1, int(interactor.height()))
            screen_x = int(event.position().x())
            screen_y = int(height - event.position().y())
            if not 0 <= screen_x <= width or not 0 <= screen_y <= height:
                return None
            renderer = vtk_interactor.get_poked_renderer(screen_x, screen_y)
            if renderer is None:
                return None
            focal = renderer.GetActiveCamera().GetFocalPoint()
            renderer.SetWorldPoint(*focal, 1.0)
            renderer.WorldToDisplay()
            depth = renderer.GetDisplayPoint()[2]
            renderer.SetDisplayPoint(screen_x, screen_y, depth)
            renderer.DisplayToWorld()
            world = renderer.GetWorldPoint()
            if len(world) != 4 or abs(float(world[3])) <= 1e-12:
                return None
            position = tuple(float(value) / float(world[3]) for value in world[:3])
            return position if all(isfinite(value) for value in position) else None
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return None

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

    def _create_2d_annotation(self, x: float, y: float) -> Annotation2D:
        """Place one editable mark and focus its existing algebra-list row."""
        before = self._capture_geometry_state()
        index = 1 + sum(
            1 for annotation in self._pane_scene().annotations if annotation.editable
        )
        annotation = Annotation2D(
            name=f"标记 {index}",
            text="",
            x=x,
            y=y,
            latex="",
            color=self._annotation_text_color(),
            editable=True,
        )
        self._pane_scene().annotations.append(annotation)
        self._pane_scene()._two_d_object_order.append(annotation.id)
        controller = getattr(self._pane_scene(), "geometry_controller", None)
        if controller is not None:
            controller.add_annotation(annotation)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        self._record_geometry_change(before)
        begin_edit = getattr(self.algebra_panel, "begin_annotation_edit", None)
        if callable(begin_edit):
            begin_edit(annotation.id)
        self._update_geometry_history_controls()
        self.algebra_panel.set_status("已新增标记，请直接在代数区输入文字或数学表达式")
        self._pane_renderer().render()
        return annotation

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
        style: str = "solid",
        record_history: bool = True,
    ) -> Linear2D:
        before = self._capture_geometry_state()
        linear = Linear2D(
            name=self._next_linear_name(kind),
            kind=kind,
            start_point_id=start.id,
            end_point_id=end.id,
            style=style,  # type: ignore[arg-type]
        )
        self._pane_scene().linear_objects.append(linear)
        self._pane_scene()._two_d_object_order.append(linear.id)
        if self._pane_scene().geometry_controller is not None:
            self._pane_scene().geometry_controller.add_linear(linear)
        self.algebra_panel.set_layers(self._two_d_panel_layers())
        if record_history:
            self._record_geometry_change(before)
        return linear

    @staticmethod
    def _linear_geometry_kind(tool: str) -> LinearKind:
        """Map toolbar variants to the persisted geometric kind."""
        return "segment" if tool == "dashed_segment" else tool  # type: ignore[return-value]

    @staticmethod
    def _linear_geometry_style(tool: str) -> str:
        return "dashed" if tool == "dashed_segment" else "solid"

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
            camera = getattr(self._pane_renderer(), "camera", None)
            self._pane().camera_3d = {
                "position": self._pane_scene()._three_d_camera_position,
                "view_angle": float(getattr(camera, "view_angle", 30.0)) if camera is not None else 30.0,
            }

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
        agent_button = getattr(self, "agent_button", None)
        if agent_button is not None:
            agent_button.setChecked(True)
        title_bar = getattr(self, "title_bar", None)
        if title_bar is not None:
            title_bar.set_right_panel_expanded(True)
        self.agent_sidebar.show()
        self.agent_resize_handle.show()
        self.agent_sidebar.expand()
        self.agent_sidebar.select_tab("agent")
        self._root_layout.activate()
        self.agent_panel.view.setFocus()

    def _close_agent_panel(self, immediate: bool = False) -> None:
        agent_button = getattr(self, "agent_button", None)
        if agent_button is not None:
            agent_button.setChecked(False)
        title_bar = getattr(self, "title_bar", None)
        if title_bar is not None:
            title_bar.set_right_panel_expanded(False)
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
            command_service=SceneCommandService(self._scene_command_host_proxy),
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
            self.two_d_geometry_toolbar.set_linear_algebra_mode(True)
            self.two_d_geometry_toolbar.setVisible(is_2d)
            if not is_2d:
                self.two_d_geometry_toolbar.line_flyout.hide()
                point_flyout = getattr(self.two_d_geometry_toolbar, "point_flyout", None)
                if point_flyout is not None:
                    point_flyout.hide()
        if hasattr(self, "three_d_geometry_toolbar"):
            is_3d = self._pane_scene().scene_mode is SceneMode.THREE_D
            self.three_d_geometry_toolbar.setVisible(is_3d)
            if not is_3d:
                self.three_d_geometry_toolbar.set_vector_active(False)
                clear_annotation = getattr(self.three_d_geometry_toolbar, "set_annotation_active", None)
                if callable(clear_annotation):
                    clear_annotation(False)
                self._pane_scene()._pending_3d_annotation = False
        self._position_viewport_overlays()
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
        alias_filter = self._teaching_case_alias_filter()
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        toolbar_matrix_label_aliases: set[str] = set()
        topic_id = str(getattr(compiled, "topic_id", ""))
        chapter_seven_case = topic_id in _CHAPTER_SEVEN_MATRIX_TOOL_TOPICS
        if str(getattr(compiled, "topic_id", "")) in (
            _CHAPTER_TWO_MATRIX_TOOL_TOPICS
            | _CHAPTER_SEVEN_MATRIX_TOOL_TOPICS
            | _CHAPTER_FOUR_MATRIX_TOOL_TOPICS
        ):
            toolbar_matrix_label_aliases = {
                f"{alias}__label"
                for operation in compiled.plan.operations
                if operation.get("op") == "geometry.transformed_grid"
                and isinstance(alias := operation.get("alias"), str)
            }
        addition_helper_aliases: set[str] = set()
        for relation in getattr(self._pane_scene(), "_vector_additions", ()):
            if not isinstance(relation, dict):
                continue
            translated = relation.get("translated_vector")
            if isinstance(translated, str):
                addition_helper_aliases.add(translated)
            construction_aliases = relation.get("construction_aliases", ())
            if isinstance(construction_aliases, (list, tuple)):
                addition_helper_aliases.update(
                    str(alias) for alias in construction_aliases if isinstance(alias, str)
                )

        def include(item: CurveLayer | GeometryObject | Annotation2D) -> bool:
            # 向量加法创建的无名锚点和虚线辅助边仅用于作图。将它们列入
            # 代数区会出现 ``=(x,y)`` 和内部别名，既不对应学生看到的
            # 向量，也无法说明数学含义。
            if isinstance(item, Point2D) and not item.name.strip():
                return False
            # 几何证明中的无名向量仍需在代数区以端点形式显示
            # ``\overrightarrow{AB}``；无名线段/射线只是内部构造，不能
            # 退化成 ``=\overline{O?}`` 这样的占位公式。
            if (
                isinstance(item, Linear2D)
                and item.kind != "vector"
                and not item.name.strip()
                and not (item.label or "").strip()
            ):
                return False
            if isinstance(item, Linear2D) and item.agent_alias in addition_helper_aliases:
                return False
            if chapter_seven_case and isinstance(item, Point2D):
                # 矩阵案例代数区以矩阵与向量公式为主。向量端点只负责画图，
                # 列成 O、v1、Av1 等点坐标会和公式重复并制造无关标签。
                return False
            if (
                isinstance(item, Annotation2D)
                and item.agent_alias in toolbar_matrix_label_aliases
            ):
                return False
            if alias_filter is None:
                return True
            alias = getattr(item, "agent_alias", None)
            if not isinstance(alias, str):
                return True
            controlled, visible = alias_filter
            return alias not in controlled or alias in visible

        objects: dict[str, CurveLayer | GeometryObject | Annotation2D] = {
            layer.id: layer for layer in self._pane_scene().curve_layers
        }
        objects.update({point.id: point for point in self._pane_scene().geometry_points})
        objects.update({linear.id: linear for linear in self._pane_scene().linear_objects})
        objects.update({annotation.id: annotation for annotation in self._pane_scene().annotations})
        for object_id in objects:
            if object_id not in self._pane_scene()._two_d_object_order:
                self._pane_scene()._two_d_object_order.append(object_id)
        result: list[CurveLayer | GeometryObject | Annotation2D] = []
        point_keys: set[tuple[str, float, float]] = set()
        for object_id in self._pane_scene()._two_d_object_order:
            if object_id not in objects or not include(objects[object_id]):
                continue
            item = objects[object_id]
            if isinstance(item, Point2D):
                key = (item.name.strip(), round(item.x, 10), round(item.y, 10))
                if key in point_keys:
                    continue
                point_keys.add(key)
            result.append(item)
        return result

    def _three_d_vector_row(self, alias: str) -> AlgebraVector3D | None:
        operation = getattr(self._pane_scene(), "_agent_geometry3d", {}).get(alias)
        if (
            not isinstance(operation, dict)
            or operation.get("op") != "linear3d.upsert"
            or operation.get("kind") != "vector"
            or operation.get("algebra_visible") is False
        ):
            return None
        try:
            end = tuple(float(value) for value in operation["end"])
        except (KeyError, TypeError, ValueError):
            return None
        if len(end) != 3:
            return None
        symbol = operation.get("algebra_symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            symbol = self._three_d_vector_symbol(alias)
        return AlgebraVector3D(
            alias=alias,
            end=end,
            visible=operation.get("visible") is not False,
            color=str(operation.get("color", "#2777b6")),
            symbol=symbol,
        )

    @staticmethod
    def _three_d_vector_symbol(alias: str) -> str | None:
        """Use the same textbook symbols as the 4.1 scene labels."""
        prefix = "ch04__entity__input_vector_"
        if alias.startswith(prefix):
            index = {"a": "1", "b": "2", "c": "3"}.get(alias.removeprefix(prefix))
            return rf"x_{{{index}}}" if index is not None else None
        prefix = "ch04__entity__output_vector_"
        if alias.startswith(prefix):
            index = {"a": "1", "b": "2", "c": "3"}.get(alias.removeprefix(prefix))
            return rf"Ax_{{{index}}}" if index is not None else None
        if alias == "ch04__entity__kernel_vector":
            return r"k"
        return None

    def _three_d_plane_row(self, alias: str) -> AlgebraPlane3D | None:
        operation = getattr(self._pane_scene(), "_agent_geometry3d", {}).get(alias)
        if (
            not isinstance(operation, dict)
            or operation.get("op") != "plane3d.upsert"
            or operation.get("algebra_visible") is not True
        ):
            return None
        try:
            origin = tuple(float(value) for value in operation["origin"])
            normal = tuple(float(value) for value in operation["normal"])
        except (KeyError, TypeError, ValueError):
            return None
        if len(origin) != 3 or len(normal) != 3:
            return None
        return AlgebraPlane3D(
            alias=alias,
            origin=origin,
            normal=normal,
            label=str(operation.get("algebra_label") or alias),
            visible=operation.get("visible") is not False,
            color=str(operation.get("color", "#5b8def")),
        )

    def _three_d_annotation_row(self, alias: str) -> AlgebraAnnotation3D | None:
        operation = getattr(self._pane_scene(), "_agent_geometry3d", {}).get(f"annotation:{alias}")
        if (
            not str(alias).startswith("manual_annotation_")
            or not isinstance(operation, dict)
            or operation.get("op") != "annotation.formula"
        ):
            return None
        try:
            position = tuple(float(value) for value in operation["position"])
        except (KeyError, TypeError, ValueError):
            return None
        if len(position) != 3:
            return None
        text = str(operation.get("text", ""))
        return AlgebraAnnotation3D(
            alias=alias,
            position=position,
            text=text,
            source=str(operation.get("latex", text)),
            visible=operation.get("visible") is not False,
            color=str(operation.get("color", "#263241")),
        )

    def _teaching_case_alias_filter(self) -> tuple[set[str], set[str]] | None:
        """返回当前教学案例窗格受阶段控制及实际可见的别名。"""
        pane_id = self._pane().pane_id
        if pane_id not in tuple(getattr(self, "_teaching_case_pane_ids", ())):
            return None
        compiled = getattr(self, "_active_linear_algebra_compiled", None)
        if compiled is None:
            return None
        refs = tuple(
            str(ref)
            for ref in getattr(self, "_teaching_case_stage_refs", {}).get(pane_id, ())
            if ref
        )
        stage_id = refs[0] if len(refs) == 1 else getattr(self, "_active_linear_algebra_stage_id", None)
        if not isinstance(stage_id, str) or not stage_id:
            return None
        try:
            controlled, visible = storyboard_visibility(compiled, stage_id)
        except ValueError:
            return None
        return set(controlled), set(visible)

    def _three_d_panel_layers(self) -> list[SurfaceLayer | AlgebraVector3D | AlgebraPlane3D | AlgebraAnnotation3D]:
        alias_filter = self._teaching_case_alias_filter()

        def include(alias: str) -> bool:
            if alias_filter is None:
                return True
            controlled, visible = alias_filter
            return alias not in controlled or alias in visible

        vector_rows = [
            row
            for alias in getattr(self._pane_scene(), "_agent_geometry3d", {})
            if include(str(alias))
            if (row := self._three_d_vector_row(alias)) is not None
        ]
        plane_rows = [
            row
            for alias in getattr(self._pane_scene(), "_agent_geometry3d", {})
            if include(str(alias))
            if (row := self._three_d_plane_row(alias)) is not None
        ]
        annotation_rows = [
            row
            for alias in getattr(self._pane_scene(), "_agent_geometry3d", {})
            if include(str(alias))
            if str(alias).startswith("annotation:")
            and (row := self._three_d_annotation_row(str(alias).removeprefix("annotation:"))) is not None
        ]
        return [*self._pane_scene().layers, *plane_rows, *vector_rows, *annotation_rows]

    def _layer(self, layer_id: str) -> SurfaceLayer | None:
        return next((layer for layer in self._pane_scene().layers if layer.id == layer_id), None)

    def _curve_layer(self, layer_id: str) -> CurveLayer | None:
        return next((layer for layer in self._pane_scene().curve_layers if layer.id == layer_id), None)

    def _point_2d(self, point_id: str | None) -> Point2D | None:
        if point_id is None:
            return None
        return next((point for point in self._pane_scene().geometry_points if point.id == point_id), None)

    def _geometry_object(self, object_id: str) -> GeometryObject | Annotation2D | None:
        point = self._point_2d(object_id)
        if point is not None:
            return point
        linear = next((linear for linear in self._pane_scene().linear_objects if linear.id == object_id), None)
        return linear if linear is not None else self._annotation_2d(object_id)

    def _annotation_2d(self, annotation_id: str) -> Annotation2D | None:
        return next(
            (annotation for annotation in self._pane_scene().annotations if annotation.id == annotation_id),
            None,
        )

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
            getattr(self, "three_d_geometry_toolbar", None),
            getattr(getattr(self, "two_d_geometry_toolbar", None), "line_flyout", None),
            getattr(self, "scene_settings_panel", None),
        ):
            if widget is not None:
                apply_drop_shadow(widget, "overlay", effective_theme)
                # QSS 无法重绘 QIcon，主题切换时需显式刷新。
                retint_icons(widget, effective_theme)
        status_bar = getattr(self, "status_bar", None)
        if status_bar is not None and hasattr(status_bar, "set_theme"):
            status_bar.set_theme(effective_theme)
        two_d_toolbar = getattr(self, "two_d_geometry_toolbar", None)
        if two_d_toolbar is not None and hasattr(two_d_toolbar, "set_theme"):
            two_d_toolbar.set_theme(effective_theme)
        three_d_toolbar = getattr(self, "three_d_geometry_toolbar", None)
        if three_d_toolbar is not None and hasattr(three_d_toolbar, "set_theme"):
            three_d_toolbar.set_theme(effective_theme)
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
        # 主题表面可选，以兼容测试替身和旧嵌入宿主。
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
