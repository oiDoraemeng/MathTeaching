"""右侧 AI 教学助手抽屉内容。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTextBrowser,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QTabBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import html
import re
from uuid import uuid4

from services.agent_provider import AgentResponse
from services.scene_commands import CommandPlan


class _PromptEdit(QPlainTextEdit):
    submitted = Signal(str)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            text = self.toPlainText().strip()
            if text:
                # 由面板决定是否真的发送；忙碌时输入必须留在框里。
                self.submitted.emit(text)
            event.accept()
            return
        super().keyPressEvent(event)


class _EscapeFilter(QObject):
    def __init__(self, panel: "AgentPanel") -> None:
        super().__init__(panel)
        self.panel = panel

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                self.panel.close_requested.emit()
                event.accept()
                return True
        return False


class _MarkdownBrowser(QTextBrowser):
    """轻量 Markdown/LaTeX 消息视图，不引入网络渲染器。"""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setOpenExternalLinks(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setReadOnly(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setStyleSheet("QTextBrowser { background: transparent; border: 0; padding: 0; }")
        self.setHtml(_markdown_to_html(text))
        self.document().contentsChanged.connect(self._fit_height)
        self._fit_height()

    def _fit_height(self) -> None:
        self.setFixedHeight(max(26, int(self.document().size().height()) + 8))


def _markdown_to_html(text: str) -> str:
    value = html.escape(str(text))
    value = re.sub(r"```(?:json|text)?\s*(.*?)```", r"<pre>\1</pre>", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    # Qt 富文本没有 TeX 排版引擎；保留公式内容并用数学字体突出显示。复杂公式
    # 仍可以在现有 MathLive 输入控件中查看和编辑。
    value = re.sub(
        r"(?:\$([^$]+)\$|\\\((.*?)\\\)|\\\[(.*?)\\\])",
        lambda match: "<span style='color:#805ad5; font-family:serif; font-size:15px;'>"
        + _latex_to_html(next(group for group in match.groups() if group is not None))
        + "</span>",
        value,
    )
    return value.replace("\n", "<br>")


def _latex_to_html(formula: str) -> str:
    """把常用教学公式转换为 Qt 富文本可显示的安全片段。"""
    value = html.escape(formula)
    value = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"<sup>\1</sup>&frasl;<sub>\2</sub>", value)
    value = re.sub(r"\\sqrt\{([^{}]+)\}", r"&radic;(<i>\1</i>)", value)
    commands = {
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
        r"\pi": "π", r"\theta": "θ", r"\infty": "∞", r"\cdot": "·",
        r"\le": "≤", r"\ge": "≥", r"\neq": "≠", r"\times": "×",
    }
    for command, replacement in commands.items():
        value = value.replace(command, replacement)
    value = re.sub(r"\^\{([^{}]+)\}", r"<sup>\1</sup>", value)
    value = re.sub(r"_\{([^{}]+)\}", r"<sub>\1</sub>", value)
    value = re.sub(r"\^([A-Za-z0-9])", r"<sup>\1</sup>", value)
    value = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", value)
    return value


class AgentPanel(QWidget):
    """聊天式 Agent 面板；它只负责显示和发出确认信号。"""

    message_requested = Signal(str)
    prompt_requested = Signal(str)
    execute_requested = Signal()
    settings_requested = Signal()
    history_requested = Signal()
    new_chat_requested = Signal(str)
    session_changed = Signal(str)
    close_requested = Signal()

    _DEMO_STATUS = "本地演示模式"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("agentPanel")
        self.setMinimumWidth(320)
        self._plan: CommandPlan | None = None
        self._plan_card: QFrame | None = None
        self._plan_toggle: QToolButton | None = None
        self._plan_messages: tuple[str, ...] = ()
        self._busy = False
        self._is_2d = True
        self._idle_status = self._DEMO_STATUS
        self._pending_scroll = False
        self._session_ids: list[str] = []
        self._session_titles: dict[str, str] = {}
        self._session_modes: dict[str, str] = {}
        self._session_execution_modes: dict[str, str] = {}
        self._session_models: dict[str, str] = {}
        self._active_session_id = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("MathAgent", self)
        title.setObjectName("agentTitle")
        header.addWidget(title)
        header.addStretch()
        self.new_chat_button = QToolButton(self)
        self.new_chat_button.setText("＋")
        self.new_chat_button.setToolTip("新建对话")
        self.new_chat_button.setFixedSize(30, 30)
        header.addWidget(self.new_chat_button)
        self.history_button = QToolButton(self)
        self.history_button.setText("◷")
        self.history_button.setToolTip("历史记录")
        self.history_button.setFixedSize(30, 30)
        header.addWidget(self.history_button)
        self.settings_button = QToolButton(self)
        self.settings_button.setText("⚙")
        self.settings_button.setToolTip("配置模型连接")
        self.settings_button.setFixedSize(30, 30)
        header.addWidget(self.settings_button)
        self.close_button = QToolButton(self)
        self.close_button.setText("×")
        self.close_button.setToolTip("关闭 AI 教学助手")
        self.close_button.setFixedSize(30, 30)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.session_tabs = QTabBar(self)
        self.session_tabs.setObjectName("agentSessionTabs")
        self.session_tabs.setExpanding(False)
        self.session_tabs.setMovable(True)
        self.session_tabs.setTabsClosable(True)
        layout.addWidget(self.session_tabs)
        self._add_session_tab("New Chat", select=True, emit=False)

        # 状态独占一行，长错误信息不再把标题挤出面板。
        self.status_label = QLabel(self._DEMO_STATUS, self)
        self.status_label.setObjectName("agentStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.status_label)

        self.mode_hint = QLabel("", self)
        self.mode_hint.setObjectName("agentModeHint")
        self.mode_hint.setWordWrap(True)
        self.mode_hint.hide()
        layout.addWidget(self.mode_hint)

        self.message_scroll = QScrollArea(self)
        self.message_scroll.setObjectName("agentMessageScroll")
        self.message_scroll.setWidgetResizable(True)
        self.message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_container = QWidget(self.message_scroll)
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(2, 2, 2, 2)
        self.message_layout.setSpacing(8)
        self.message_layout.addStretch()
        self.message_scroll.setWidget(self.message_container)
        layout.addWidget(self.message_scroll, 1)

        input_row = QHBoxLayout()
        self.prompt_edit = _PromptEdit(self)
        self.prompt_edit.setObjectName("agentPromptEdit")
        self.prompt_edit.setPlaceholderText('提问或输入 "/"快捷命令')
        self.prompt_edit.setMinimumHeight(58)
        self.prompt_edit.setMaximumHeight(110)
        input_row.addWidget(self.prompt_edit, 1)
        self.send_button = QPushButton("发送", self)
        self.send_button.setObjectName("agentSendButton")
        self.send_button.setFixedWidth(62)
        input_row.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignBottom)
        self.preview_button = self.send_button
        layout.addLayout(input_row)

        composer_tools = QHBoxLayout()
        self.attachment_button = QToolButton(self)
        self.attachment_button.setText("＋")
        self.attachment_button.setToolTip("添加附件或图片")
        composer_tools.addWidget(self.attachment_button)
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(("Agent", "Ask", "Plan", "配置自定义智能体…"))
        self.mode_combo.setToolTip("Agent 模式")
        composer_tools.addWidget(self.mode_combo)
        self.execution_combo = QComboBox(self)
        self.execution_combo.addItems(("确认执行", "连续自动执行"))
        self.execution_combo.setToolTip("Agent 执行策略")
        composer_tools.addWidget(self.execution_combo)
        composer_tools.addStretch(1)
        self.model_button = QToolButton(self)
        self.model_button.setText("模型")
        self.model_button.setToolTip("切换当前会话模型")
        composer_tools.addWidget(self.model_button)
        self.context_ring = QLabel("◯", self)
        self.context_ring.setObjectName("agentContextRing")
        self.context_ring.setToolTip("上下文用量：0%")
        composer_tools.addWidget(self.context_ring)
        layout.addLayout(composer_tools)

        # 计划卡片尚未创建时的兼容占位；显示计划时会被卡片内的控件替换。
        self.plan_view = QPlainTextEdit(self)
        self.plan_view.hide()
        self.execute_button = QPushButton(self)
        self.execute_button.setEnabled(False)
        self.execute_button.hide()

        self._escape_filter = _EscapeFilter(self)
        self._escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape_shortcut.activated.connect(self.close_requested)
        for child in (
            self,
            self.prompt_edit,
            self.message_scroll,
            self.message_container,
            self.settings_button,
            self.close_button,
            self.send_button,
        ):
            child.installEventFilter(self._escape_filter)
        self.prompt_edit.submitted.connect(self._submit_message)
        self.send_button.clicked.connect(self._submit_from_button)
        self.settings_button.clicked.connect(self.settings_requested)
        self.history_button.clicked.connect(self.history_requested)
        self.new_chat_button.clicked.connect(self.new_chat)
        self.close_button.clicked.connect(self.close_requested)
        self.session_tabs.tabCloseRequested.connect(self.close_chat)
        self.session_tabs.currentChanged.connect(self._session_changed)
        self.mode_combo.currentTextChanged.connect(self._mode_changed)
        self.execution_combo.currentTextChanged.connect(self._execution_mode_changed)
        self._update_send_enabled()
        self.prompt_edit.textChanged.connect(self._update_send_enabled)
        self.message_scroll.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)

    @property
    def plan(self) -> CommandPlan | None:
        return self._plan

    @property
    def active_session_id(self) -> str:
        return self._active_session_id

    def _add_session_tab(self, title: str, *, select: bool, emit: bool) -> str:
        session_id = uuid4().hex
        self._session_ids.append(session_id)
        self._session_titles[session_id] = title
        self._session_modes[session_id] = "Agent"
        self._session_execution_modes[session_id] = "确认执行"
        self._session_models[session_id] = ""
        index = self.session_tabs.addTab(title)
        self.session_tabs.setTabData(index, session_id)
        if select:
            self.session_tabs.setCurrentIndex(index)
            self._active_session_id = session_id
        if emit:
            self.new_chat_requested.emit(session_id)
        return session_id

    def new_chat(self) -> str:
        self._clear_timeline()
        return self._add_session_tab("New Chat", select=True, emit=True)

    def close_chat(self, index: int) -> None:
        if self.session_tabs.count() <= 1:
            return
        session_id = self.session_tabs.tabData(index)
        self.session_tabs.removeTab(index)
        if session_id in self._session_ids:
            self._session_ids.remove(session_id)
        self._session_titles.pop(session_id, None)
        self._session_modes.pop(session_id, None)
        self._session_execution_modes.pop(session_id, None)
        self._session_models.pop(session_id, None)

    def _session_changed(self, index: int) -> None:
        if index < 0:
            return
        session_id = self.session_tabs.tabData(index)
        self._active_session_id = str(session_id)
        if hasattr(self, "mode_combo"):
            self.mode_combo.blockSignals(True)
            self.execution_combo.blockSignals(True)
            self.mode_combo.setCurrentText(self._session_modes.get(self._active_session_id, "Agent"))
            self.execution_combo.setCurrentText(self._session_execution_modes.get(self._active_session_id, "确认执行"))
            self.mode_combo.blockSignals(False)
            self.execution_combo.blockSignals(False)
        self.session_changed.emit(self._active_session_id)

    def _mode_changed(self, value: str) -> None:
        if self._active_session_id:
            self._session_modes[self._active_session_id] = value

    def _execution_mode_changed(self, value: str) -> None:
        if self._active_session_id:
            self._session_execution_modes[self._active_session_id] = value

    def set_context_usage(self, used_tokens: int, max_tokens: int) -> None:
        percentage = 0.0 if max_tokens <= 0 else min(100.0, used_tokens / max_tokens * 100.0)
        self.context_ring.setText("◉" if percentage >= 80 else "◯")
        self.context_ring.setToolTip(f"上下文用量：{percentage:.1f}%")

    def _clear_timeline(self) -> None:
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.clear_plan()

    def set_model_status(self, model: str, *, enabled: bool) -> None:
        self._idle_status = f"{model} · 已连接" if enabled and model else self._DEMO_STATUS
        if not self._busy:
            self._set_status(self._idle_status)

    def set_scene_mode(self, is_2d: bool) -> None:
        self._is_2d = is_2d
        if is_2d:
            self.mode_hint.hide()
        else:
            self.mode_hint.setText("当前为三维场景；只可执行 scene=3d 的命令计划。")
            self.mode_hint.show()
        self._refresh_execute_enabled()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.prompt_edit.setReadOnly(busy)
        self.settings_button.setEnabled(not busy)
        self._update_send_enabled()
        self._refresh_execute_enabled()
        if busy:
            self._set_status("正在请求…")
        else:
            self._set_status(self._idle_status)

    def add_user_message(self, text: str) -> None:
        self._add_message(text, user=True)

    def add_assistant_message(self, text: str) -> None:
        if text.strip():
            self._add_message(text, user=False)

    def show_response(self, response: AgentResponse, messages: tuple[str, ...] = ()) -> None:
        self.add_assistant_message(response.text)
        if response.plan is not None:
            self.show_plan(response.plan, messages)
        elif messages:
            self.show_error("；".join(messages), keep_plan=False)

    def show_plan(self, plan: CommandPlan, messages: tuple[str, ...] = ()) -> None:
        self._remove_plan_card()
        self._plan = plan
        self._plan_messages = tuple(messages)
        card = QFrame(self.message_container)
        card.setObjectName("agentPlanCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 8)
        top = QHBoxLayout()
        toggle = QToolButton(card)
        toggle.setText("命令计划")
        toggle.setCheckable(True)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        summary = QLabel(plan.summary or "已生成可验证的场景计划", card)
        summary.setWordWrap(True)
        top.addWidget(toggle)
        top.addWidget(summary, 1)
        card_layout.addLayout(top)
        self.plan_view = QPlainTextEdit(card)
        self.plan_view.setReadOnly(True)
        self.plan_view.setPlainText(plan.to_json())
        self.plan_view.setMinimumHeight(120)
        self.plan_view.setMaximumHeight(220)
        self.plan_view.hide()
        card_layout.addWidget(self.plan_view)
        if messages:
            problems = QLabel("；".join(messages), card)
            problems.setObjectName("agentPlanProblems")
            problems.setWordWrap(True)
            card_layout.addWidget(problems)
        self.execute_button = QPushButton("执行计划", card)
        self.execute_button.setToolTip("确认后应用当前命令计划")
        card_layout.addWidget(self.execute_button, 0, Qt.AlignmentFlag.AlignRight)
        for child in (card, toggle, self.plan_view, self.execute_button):
            child.installEventFilter(self._escape_filter)
        toggle.toggled.connect(self._toggle_plan_details)
        self.execute_button.clicked.connect(self.execute_requested)
        self._plan_card = card
        self._plan_toggle = toggle
        self.message_layout.insertWidget(self.message_layout.count() - 1, card)
        self._refresh_execute_enabled()
        self._idle_status = "计划已通过校验" if not messages else "；".join(messages)
        if not self._busy:
            self._set_status(self._idle_status)
        self._scroll_to_bottom()

    def _toggle_plan_details(self, expanded: bool) -> None:
        if self._plan_card is None:
            return
        if self._plan_toggle is not None:
            self._plan_toggle.setArrowType(
                Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
            )
        self.plan_view.setVisible(expanded)
        if expanded:
            self._scroll_to_bottom()

    def show_error(self, message: str, *, keep_plan: bool = False) -> None:
        if not keep_plan:
            self.clear_plan()
        self.add_assistant_message(f"错误：{message}")
        self._set_status(message)

    def clear_plan(self) -> None:
        self._remove_plan_card()
        self._plan = None
        self._plan_messages = ()
        self._refresh_execute_enabled()

    def _remove_plan_card(self) -> None:
        if self._plan_card is not None:
            self.message_layout.removeWidget(self._plan_card)
            self._plan_card.setParent(None)
            self._plan_card.deleteLater()
            self._plan_card = None
        self._plan_toggle = None
        # 卡片内的控件随卡片销毁，换回不属于卡片的占位控件。
        self.plan_view = QPlainTextEdit(self)
        self.plan_view.hide()
        self.execute_button = QPushButton(self)
        self.execute_button.setEnabled(False)
        self.execute_button.hide()

    def _refresh_execute_enabled(self) -> None:
        runnable = (
            self._plan is not None
            and self._plan_card is not None
            and not self._plan_messages
            and self._plan.scene == ("2d" if self._is_2d else "3d")
            and not self._busy
        )
        self.execute_button.setEnabled(runnable)
        if self._plan_card is not None and not runnable:
            if self._plan is not None and self._plan.scene != ("2d" if self._is_2d else "3d"):
                self.execute_button.setToolTip("切换到计划对应的场景模式后才能执行。")
            elif self._plan_messages:
                self.execute_button.setToolTip("计划未通过校验，无法执行。")
            else:
                self.execute_button.setToolTip("正在请求模型，请稍候。")
        elif self._plan_card is not None:
            self.execute_button.setToolTip("确认后应用当前命令计划")

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)
        # 状态被截断时仍可通过悬停读到完整文本。
        self.status_label.setToolTip(text)

    def _add_message(self, text: str, *, user: bool) -> None:
        bubble = QFrame(self.message_container)
        bubble.setObjectName("agentUserBubble" if user else "agentAssistantBubble")
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(max(200, int(self.message_scroll.viewport().width() * 0.86)))
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(9, 7, 9, 7)
        message_view = _MarkdownBrowser(text, bubble)
        message_view.setMinimumWidth(80)
        bubble_layout.addWidget(message_view)
        self.message_layout.insertWidget(
            self.message_layout.count() - 1,
            bubble,
            Qt.AlignmentFlag.AlignRight if user else Qt.AlignmentFlag.AlignLeft,
        )
        self._scroll_to_bottom()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        limit = max(200, int(self.message_scroll.viewport().width() * 0.86))
        for name in ("agentUserBubble", "agentAssistantBubble"):
            for bubble in self.message_container.findChildren(QFrame, name):
                bubble.setMaximumWidth(limit)

    def _scroll_to_bottom(self) -> None:
        # 新气泡的高度要等下一次布局才确定；先尝试一次，随后的 rangeChanged 再补一次。
        self._pending_scroll = True
        QTimer.singleShot(0, self._apply_scroll_to_bottom)

    def _on_scroll_range_changed(self) -> None:
        if self._pending_scroll:
            self._apply_scroll_to_bottom()
            self._pending_scroll = False

    def _apply_scroll_to_bottom(self) -> None:
        scrollbar = self.message_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_send_enabled(self) -> None:
        self.send_button.setEnabled(not self._busy and bool(self.prompt_edit.toPlainText().strip()))

    def _submit_from_button(self) -> None:
        self._submit_message(self.prompt_edit.toPlainText())

    def _submit_message(self, text: str) -> None:
        if self._busy or not text.strip():
            return
        prompt = text.strip()
        self.prompt_edit.clear()
        self.message_requested.emit(prompt)
        self.prompt_requested.emit(prompt)
