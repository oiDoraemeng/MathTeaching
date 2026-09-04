"""右侧 MathAgent 侧边栏，默认隐藏，打开时占用固定宽度。"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from agent.instruction import InstructionStore
from agent.memory import MemoryStore
from agent.skill_manager import SkillManager
from agent.session_store import SessionStore
from ui.icons import apply_icon
from ui.agent_sidebar_web import AgentSidebarWeb


class AgentSidebarState(Enum):
    """侧边栏状态"""
    COLLAPSED = "collapsed"  # 折叠态：36px 工具条
    EXPANDED = "expanded"    # 展开态：380px 完整面板


class AgentSidebar(QWidget):
    """AI 助手侧边栏容器：关闭时隐藏并释放主视口布局空间。"""

    state_changed = Signal(AgentSidebarState)
    MIN_WIDTH = 360
    DEFAULT_WIDTH = 440
    MAX_WIDTH = 560

    def __init__(self, parent: QWidget | None = None, dispatcher: Callable[[object], object] | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("agentSidebar")
        self._state = AgentSidebarState.COLLAPSED
        self._model_name = ""
        self._model_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.navigation_bar = QWidget(self)
        nav_layout = QVBoxLayout(self.navigation_bar)
        nav_layout.setContentsMargins(8, 8, 8, 4)
        nav_layout.setSpacing(4)
        self.navigation_buttons: dict[str, QToolButton] = {}
        for key, label in (("agent", "Agent"), ("skills", "Skills"), ("memory", "Memory"), ("rules", "Rules")):
            button = QToolButton(self.navigation_bar)
            button.setText(label)
            button.setObjectName(f"sidebarNav{key.title()}")
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.clicked.connect(lambda checked=False, name=key: self.select_tab(name))
            nav_layout.addWidget(button)
            self.navigation_buttons[key] = button
        self.navigation_bar.hide()
        layout.addWidget(self.navigation_bar)

        # 展开态完整面板由本地 React/WebEngine 文档渲染。
        self.expanded_panel = AgentSidebarWeb(dispatcher or (lambda _message: None), parent=self)
        self.expanded_panel.hide()
        layout.addWidget(self.expanded_panel)

        self.tool_pages = QStackedWidget(self)
        self.skills_page = self._build_skills_page()
        self.memory_page = self._build_memory_page()
        self.rules_page = self._build_rules_page()
        self.history_page = self._build_history_page()
        self.tool_pages.addWidget(self.skills_page)
        self.tool_pages.addWidget(self.memory_page)
        self.tool_pages.addWidget(self.rules_page)
        self.tool_pages.addWidget(self.history_page)
        self.tool_pages.hide()
        layout.addWidget(self.tool_pages, 1)

        # 初始状态：整个侧边栏隐藏，不留下 40px 占位。
        self.set_panel_width(self.DEFAULT_WIDTH)
        self.hide()

        # 连接信号
        self.expanded_panel.bridge.event_json.connect(self._handle_web_event)
        self.select_tab("agent")

    def _handle_web_event(self, raw: str) -> None:
        # UI intents are dispatched by the host owner; this hook is reserved for
        # sidebar-level navigation events emitted by the local document.
        return None

    def _build_history_page(self) -> QWidget:
        page = QWidget(self)
        column = QVBoxLayout(page)
        self.history_back_button = QPushButton("返回当前对话", page)
        self.history_back_button.clicked.connect(lambda: self.select_tab("agent"))
        column.addWidget(self.history_back_button)
        title = QLabel("历史记录", page)
        title.setObjectName("sectionHeader")
        column.addWidget(title)
        self.history_list = QListWidget(page)
        column.addWidget(self.history_list, 1)
        self._refresh_history()
        return page

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_list"):
            return
        self.history_list.clear()
        try:
            sessions = SessionStore().list_sessions(include_closed=True)
        except Exception:
            sessions = []
        for session in sessions:
            state = "已关闭" if session.closed_at else "进行中"
            self.history_list.addItem(f"{session.title} · {state}")

    def show_history(self) -> None:
        self._refresh_history()
        self.navigation_bar.show()
        self.expanded_panel.hide()
        self.tool_pages.setCurrentWidget(self.history_page)
        self.tool_pages.show()

    def _build_skills_page(self) -> QWidget:
        page = QWidget(self)
        column = QVBoxLayout(page)
        title = QLabel("已注册数学 Skills", page)
        title.setObjectName("sectionHeader")
        column.addWidget(title)
        self.skills_list = QListWidget(page)
        for manifest in SkillManager().list_skills():
            self.skills_list.addItem(f"{manifest.name}  ·  {manifest.description}")
        column.addWidget(self.skills_list, 1)
        return page

    def _build_memory_page(self) -> QWidget:
        page = QWidget(self)
        column = QVBoxLayout(page)
        title = QLabel("学习记忆", page)
        title.setObjectName("sectionHeader")
        column.addWidget(title)
        self.memory_label = QLabel(page)
        self.memory_label.setWordWrap(True)
        column.addWidget(self.memory_label)
        clear = QPushButton("清空本地记忆", page)
        clear.clicked.connect(self._clear_memory)
        column.addWidget(clear)
        edit = QPushButton("编辑学习偏好", page)
        edit.clicked.connect(self._edit_memory)
        column.addWidget(edit)
        column.addStretch(1)
        self._refresh_memory_label()
        return page

    def _build_rules_page(self) -> QWidget:
        page = QWidget(self)
        column = QVBoxLayout(page)
        title = QLabel("Math Teacher Agent 规则", page)
        title.setObjectName("sectionHeader")
        column.addWidget(title)
        self.rules_edit = QPlainTextEdit(page)
        self.rules_edit.setPlainText(InstructionStore().load())
        column.addWidget(self.rules_edit, 1)
        actions = QFormLayout()
        save = QPushButton("保存规则", page)
        reset = QPushButton("恢复默认", page)
        save.clicked.connect(lambda: InstructionStore().save(self.rules_edit.toPlainText()))
        reset.clicked.connect(lambda: self.rules_edit.setPlainText(InstructionStore().default_text))
        actions.addRow(save, reset)
        column.addLayout(actions)
        return page

    def _refresh_memory_label(self) -> None:
        profile = MemoryStore().load()
        topics = "、".join(profile.recent_topics[:5]) or "暂无"
        self.memory_label.setText(
            f"水平：{profile.level}\n偏好图形：{'是' if profile.prefer_visual else '否'}\n"
            f"语言：{profile.language}\n最近主题：{topics}"
        )

    def _clear_memory(self) -> None:
        MemoryStore().clear()
        self._refresh_memory_label()

    def _edit_memory(self) -> None:
        from ui.agent_settings import MemorySettingsDialog

        effective_theme = getattr(self.window(), "effective_theme", "light")
        dialog = MemorySettingsDialog(self, effective_theme=effective_theme)
        dialog.saved.connect(lambda _profile: self._refresh_memory_label())
        dialog.open()
        self._memory_dialog = dialog

    def select_tab(self, name: str) -> None:
        name = name if name in self.navigation_buttons else "agent"
        for key, button in self.navigation_buttons.items():
            button.setChecked(key == name)
        if name == "agent":
            self.expanded_panel.show()
            self.navigation_bar.hide()
            self.tool_pages.hide()
        else:
            self.expanded_panel.hide()
            self.tool_pages.setCurrentWidget({"skills": self.skills_page, "memory": self.memory_page, "rules": self.rules_page}[name])
            if name == "memory":
                self._refresh_memory_label()
            self.tool_pages.show()

    @property
    def state(self) -> AgentSidebarState:
        return self._state

    def toggle(self) -> None:
        """切换折叠/展开状态。"""
        if self._state == AgentSidebarState.COLLAPSED:
            self.expand()
        else:
            self.collapse()

    def expand(self) -> None:
        """展开到完整面板。"""
        if self._state == AgentSidebarState.EXPANDED:
            return
        self.show()
        self.navigation_bar.hide()
        self.expanded_panel.show()
        self.tool_pages.hide()
        self.set_panel_width(self.width())
        self._state = AgentSidebarState.EXPANDED
        self.state_changed.emit(self._state)

    def collapse(self) -> None:
        """折叠到工具条。"""
        if self._state == AgentSidebarState.COLLAPSED:
            return
        self.expanded_panel.hide()
        self.navigation_bar.hide()
        self.tool_pages.hide()
        self.set_panel_width(self.width())
        self.hide()
        self._state = AgentSidebarState.COLLAPSED
        self.state_changed.emit(self._state)

    def set_model_status(self, model: str, *, enabled: bool) -> None:
        """更新模型状态显示。"""
        self._model_name = model
        self._model_enabled = enabled
        self.expanded_panel.set_model_status(model, enabled=enabled)
        _ = (model, enabled)

    def set_panel_width(self, width: int) -> int:
        value = max(self.MIN_WIDTH, min(self.MAX_WIDTH, int(width)))
        self.setFixedWidth(value)
        return value

    def set_busy(self, busy: bool) -> None:
        """设置忙碌状态。"""
        self.expanded_panel.set_busy(busy)
        if not busy:
            self.set_model_status(self._model_name, enabled=self._model_enabled)
