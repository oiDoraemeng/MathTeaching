"""AI provider 配置对话框与本地 QSettings 存储。"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from agent.instruction import InstructionStore
from agent.memory import MemoryProfile, MemoryStore
from agent.providers import ModelProvider
from services.agent_provider import AgentSettings
from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import ThemeName, apply_drop_shadow


def _resolve_effective_theme(parent, effective_theme: ThemeName | None) -> ThemeName:
    if effective_theme in ("light", "dark"):
        return effective_theme
    window = getattr(parent, "window", None)
    if callable(window):
        window = window()
    resolved = getattr(window, "effective_theme", None)
    return resolved if resolved in ("light", "dark") else "light"


class _ConnectionTestWorker(QObject):
    """在工作线程里做一次连接测试，避免阻塞界面。"""

    succeeded = Signal()
    failed = Signal(str)
    finished = Signal()

    def __init__(self, settings: AgentSettings) -> None:
        super().__init__()
        self._settings = settings

    @Slot()
    def run(self) -> None:
        try:
            ModelProvider.create(self._settings.provider, self._settings).test_connection()
        except Exception as error:  # provider 已负责掩码 API Key
            self.failed.emit(str(error))
        else:
            self.succeeded.emit()
        finally:
            self.finished.emit()


class AgentSettingsDialog(QDialog):
    settings_saved = Signal(object)
    demo_requested = Signal()
    instructions_requested = Signal()

    _ORGANIZATION = "Math3DTeaching"
    _APPLICATION = "Math3DTeaching"

    def __init__(self, parent=None, *, effective_theme: ThemeName | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 教学助手设置")
        self.setModal(False)
        self.setMinimumWidth(430)
        self.effective_theme = _resolve_effective_theme(parent, effective_theme)
        self.set_effective_theme(self.effective_theme)
        self._settings = self.load_settings()
        self._test_thread: QThread | None = None
        self._test_worker: _ConnectionTestWorker | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.provider_combo = QComboBox(self)
        self.provider_combo.addItem("OpenAI - Responses", "openai")
        self.provider_combo.addItem("DeepSeek", "deepseek")
        self.provider_combo.addItem("本地演示模型", "local")
        self.protocol_combo = QComboBox(self)
        self.protocol_combo.addItem("Responses", "responses")
        self.protocol_combo.addItem("Chat Completions", "chat_completions")
        self.base_url_edit = QLineEdit(self)
        self.base_url_edit.setPlaceholderText("https://example.com/v1")
        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("API Key")
        self.reveal_key_button = QToolButton(self)
        self.reveal_key_button.setCheckable(True)
        self.reveal_key_button.setToolTip("临时显示 API Key")
        self._sync_reveal_key_icon(False)
        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.addWidget(self.api_key_edit, 1)
        key_row.addWidget(self.reveal_key_button, 0)
        self.model_edit = QLineEdit(self)
        self.model_edit.setPlaceholderText("例如 gpt-4o-mini")
        self.timeout_spin = QDoubleSpinBox(self)
        self.timeout_spin.setRange(1.0, 600.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSuffix(" 秒")
        form.addRow("模型 Provider", self.provider_combo)
        form.addRow("API protocol", self.protocol_combo)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("API Key", key_row)
        form.addRow("Model name", self.model_edit)
        form.addRow("请求超时", self.timeout_spin)
        layout.addLayout(form)

        self.enabled_check = QCheckBox("启用远程模型（取消勾选则使用本地演示模式）", self)
        layout.addWidget(self.enabled_check)

        action_row = QHBoxLayout()
        self.test_button = QPushButton("测试连接", self)
        self.demo_button = QPushButton("切换到本地演示模式", self)
        self.demo_button.setToolTip("仅停用远程模型，不会清空已保存的连接信息")
        action_row.addWidget(self.test_button)
        action_row.addWidget(self.demo_button)
        self.instructions_button = QPushButton("编辑 Instructions", self)
        self.instructions_button.setToolTip("编辑 Math Teacher Agent 的用户规则")
        action_row.addWidget(self.instructions_button)
        layout.addLayout(action_row)
        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        layout.addWidget(buttons)

        self._set_form_values(self._settings)
        self.enabled_check.setChecked(self.is_enabled() and (self._settings.provider == "local" or self._settings.is_complete))
        self.reveal_key_button.toggled.connect(self._toggle_key_echo)
        self.test_button.clicked.connect(self._test_connection)
        self.demo_button.clicked.connect(self._restore_demo)
        self.instructions_button.clicked.connect(self._edit_instructions)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

    def set_effective_theme(self, effective_theme: ThemeName) -> None:
        self.effective_theme = effective_theme
        apply_drop_shadow(self, "modal", effective_theme)
        if hasattr(self, "reveal_key_button"):
            retint_icons(self, effective_theme)

    @classmethod
    def _qsettings(cls) -> QSettings:
        return QSettings(cls._ORGANIZATION, cls._APPLICATION)

    @classmethod
    def load_settings(cls) -> AgentSettings:
        settings = cls._qsettings()
        try:
            timeout = float(settings.value("agent/timeout_seconds", 60.0))
        except (TypeError, ValueError):
            timeout = 60.0
        return AgentSettings(
            base_url=str(settings.value("agent/base_url", "") or ""),
            api_key=str(settings.value("agent/api_key", "") or ""),
            model=str(settings.value("agent/model", "") or ""),
            timeout_seconds=max(1.0, min(600.0, timeout)),
            provider=str(settings.value("agent/provider", "openai") or "openai"),
            protocol=str(settings.value("agent/protocol", "responses") or "responses"),
        )

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(cls._qsettings().value("agent/enabled", False, type=bool))

    @classmethod
    def save_settings(cls, settings_value: AgentSettings, *, enabled: bool | None = None) -> None:
        settings = cls._qsettings()
        settings.setValue("agent/base_url", settings_value.base_url.strip())
        settings.setValue("agent/api_key", settings_value.api_key)
        settings.setValue("agent/model", settings_value.model.strip())
        settings.setValue("agent/timeout_seconds", float(settings_value.timeout_seconds))
        settings.setValue("agent/provider", settings_value.provider or "openai")
        settings.setValue("agent/protocol", settings_value.normalized_protocol)
        settings.setValue(
            "agent/enabled",
            settings_value.is_complete if enabled is None else bool(enabled),
        )
        settings.sync()

    def current_settings(self) -> AgentSettings:
        return AgentSettings(
            base_url=self._normalized_base_url(),
            api_key=self.api_key_edit.text().strip(),
            model=self.model_edit.text().strip(),
            timeout_seconds=float(self.timeout_spin.value()),
            provider=str(self.provider_combo.currentData() or "openai"),
            protocol=str(self.protocol_combo.currentData() or "responses"),
        )

    def _normalized_base_url(self) -> str:
        return self.base_url_edit.text().strip().rstrip("/")

    def _set_form_values(self, settings: AgentSettings) -> None:
        index = self.provider_combo.findData(settings.provider)
        self.provider_combo.setCurrentIndex(index if index >= 0 else 0)
        protocol_index = self.protocol_combo.findData(settings.normalized_protocol)
        self.protocol_combo.setCurrentIndex(protocol_index if protocol_index >= 0 else 0)
        self.base_url_edit.setText(settings.base_url)
        self.api_key_edit.setText(settings.api_key)
        self.model_edit.setText(settings.model)
        self.timeout_spin.setValue(settings.timeout_seconds)

    def _toggle_key_echo(self, revealed: bool) -> None:
        self.api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if revealed else QLineEdit.EchoMode.Password
        )
        self._sync_reveal_key_icon(revealed)

    def _sync_reveal_key_icon(self, revealed: bool) -> None:
        apply_icon(
            self.reveal_key_button,
            "circle-filled" if revealed else "circle-outline",
            icon_color(self.effective_theme),
            icon_size=16,
            hit_size=28,
        )

    def _save(self) -> None:
        settings = self.current_settings()
        enabled = self.enabled_check.isChecked()
        if enabled and settings.provider != "local" and not settings.is_complete:
            self.status_label.setText("启用远程模型前需要填写完整的 Base URL、API Key 和模型名。")
            return
        self.base_url_edit.setText(settings.base_url)
        self.save_settings(settings, enabled=enabled)
        self.settings_saved.emit(settings)
        self.accept()

    def _restore_demo(self) -> None:
        """只停用远程模型；已保存的连接信息保持不变，便于随时切回。"""
        self.enabled_check.setChecked(False)
        self.save_settings(self.current_settings(), enabled=False)
        self.demo_requested.emit()
        self.status_label.setText("已切回本地演示模式，连接信息仍然保留。")

    def _edit_instructions(self) -> None:
        dialog = InstructionsDialog(self, effective_theme=self.effective_theme)
        dialog.open()
        self._instructions_dialog = dialog

    def _test_connection(self) -> None:
        if self._test_thread is not None:
            return
        settings = self.current_settings()
        if settings.provider == "local":
            self.status_label.setText("本地演示模型无需连接测试。")
            return
        if not settings.is_complete:
            self.status_label.setText("请填写完整的 Base URL、API Key 和模型名。")
            return
        self.test_button.setEnabled(False)
        self.status_label.setText("正在测试连接…")
        thread = QThread(self)
        worker = _ConnectionTestWorker(settings)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_test_succeeded)
        worker.failed.connect(self._on_test_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_test_thread_finished)
        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _on_test_succeeded(self) -> None:
        self.status_label.setText("连接成功。")

    def _on_test_failed(self, message: str) -> None:
        detail = message.strip()
        self.status_label.setText(
            f"连接失败：{detail}" if detail else "连接失败，请检查地址、凭据和网络。"
        )

    def _on_test_thread_finished(self) -> None:
        thread = self._test_thread
        self._test_thread = None
        self._test_worker = None
        if thread is not None:
            thread.deleteLater()
        self.test_button.setEnabled(True)

    def _wait_for_test_thread(self) -> None:
        thread = self._test_thread
        if thread is None:
            return
        # 阻塞的 HTTP 请求最多持续测试超时（10 秒），这里只等待有限时间。
        thread.quit()
        thread.wait(11000)

    def done(self, result: int) -> None:
        self._wait_for_test_thread()
        super().done(result)


class InstructionsDialog(QDialog):
    """Instructions 编辑器，内容写入 QSettings 而不是覆盖默认文件。"""

    saved = Signal(str)

    def __init__(
        self,
        parent=None,
        store: InstructionStore | None = None,
        *,
        effective_theme: ThemeName | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑 Math Teacher Agent Instructions")
        self.setMinimumSize(520, 420)
        self.effective_theme = _resolve_effective_theme(parent, effective_theme)
        self.set_effective_theme(self.effective_theme)
        self.store = store or InstructionStore()
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit(self)
        self.editor.setPlainText(self.store.load())
        self.editor.setPlaceholderText("写入适用于数学教学的规则…")
        layout.addWidget(self.editor, 1)
        row = QHBoxLayout()
        save = QPushButton("保存", self)
        reset = QPushButton("恢复默认", self)
        close = QPushButton("关闭", self)
        row.addWidget(save)
        row.addWidget(reset)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        save.clicked.connect(self._save)
        reset.clicked.connect(lambda: self.editor.setPlainText(self.store.default_text))
        close.clicked.connect(self.close)

    def set_effective_theme(self, effective_theme: ThemeName) -> None:
        self.effective_theme = effective_theme
        apply_drop_shadow(self, "modal", effective_theme)

    def _save(self) -> None:
        text = self.store.save(self.editor.toPlainText())
        self.saved.emit(text)
        self.accept()


class MemorySettingsDialog(QDialog):
    """学习偏好编辑器，保存少量 JSON 记忆。"""

    saved = Signal(object)

    def __init__(
        self,
        parent=None,
        store: MemoryStore | None = None,
        *,
        effective_theme: ThemeName | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 学习记忆")
        self.effective_theme = _resolve_effective_theme(parent, effective_theme)
        self.set_effective_theme(self.effective_theme)
        self.store = store or MemoryStore()
        profile = self.store.load()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.level_combo = QComboBox(self)
        self.level_combo.addItems(["middle_school", "high_school", "university", "competition"])
        self.level_combo.setCurrentText(profile.level)
        self.visual_check = QCheckBox("优先使用图形解释", self)
        self.visual_check.setChecked(profile.prefer_visual)
        self.language_edit = QLineEdit(profile.language, self)
        form.addRow("数学水平", self.level_combo)
        form.addRow("教学偏好", self.visual_check)
        form.addRow("语言", self.language_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, parent=self)
        layout.addWidget(buttons)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

    def set_effective_theme(self, effective_theme: ThemeName) -> None:
        self.effective_theme = effective_theme
        apply_drop_shadow(self, "modal", effective_theme)

    def _save(self) -> None:
        current = self.store.load()
        profile = self.store.save(
            MemoryProfile(
                self.level_combo.currentText(),
                self.visual_check.isChecked(),
                self.language_edit.text().strip() or "zh-CN",
                list(current.recent_topics),
            )
        )
        self.saved.emit(profile)
        self.accept()
