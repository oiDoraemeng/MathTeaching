"""AI 设置对话框的字段、掩码和 QSettings 键测试。"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from services.agent_provider import AgentSettings
from services.scene_commands import RuleBasedAgentProvider
from ui.agent_settings import AgentSettingsDialog
from ui.designer_window import MainWindow


class AgentSettingsTests(unittest.TestCase):
    _settings_keys = (
        "agent/base_url", "agent/api_key", "agent/model",
        "agent/timeout_seconds", "agent/enabled", "agent/provider",
        "agent/protocol",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.qsettings = QSettings("Math3DTeaching", "Math3DTeaching")
        self.original = {
            key: self.qsettings.value(key)
            for key in self._settings_keys
            if self.qsettings.contains(key)
        }
        for key in self._settings_keys:
            self.qsettings.remove(key)
        self.qsettings.sync()

    def tearDown(self) -> None:
        for key in self._settings_keys:
            self.qsettings.remove(key)
        for key, value in self.original.items():
            self.qsettings.setValue(key, value)
        self.qsettings.sync()

    def test_save_and_load_uses_fixed_fields(self) -> None:
        value = AgentSettings("https://example.test/v1", "secret", "model-x", 15.5)
        AgentSettingsDialog.save_settings(value)
        loaded = AgentSettingsDialog.load_settings()
        self.assertEqual(loaded, value)
        self.assertTrue(AgentSettingsDialog.is_enabled())

    def test_api_key_editor_is_password_mode(self) -> None:
        dialog = AgentSettingsDialog()
        self.assertEqual(dialog.api_key_edit.echoMode(), dialog.api_key_edit.EchoMode.Password)
        dialog.reveal_key_button.setChecked(True)
        self.assertEqual(dialog.api_key_edit.echoMode(), dialog.api_key_edit.EchoMode.Normal)
        dialog.reveal_key_button.setChecked(False)
        self.assertEqual(dialog.api_key_edit.echoMode(), dialog.api_key_edit.EchoMode.Password)
        dialog.deleteLater()

    def test_api_key_visibility_uses_circle_icons(self) -> None:
        dialog = AgentSettingsDialog(effective_theme="light")
        self.assertEqual(dialog.reveal_key_button.text(), "")
        self.assertEqual(dialog.reveal_key_button.property("_kiro_icon_state")[0], "circle-outline")
        dialog.reveal_key_button.setChecked(True)
        self.assertEqual(dialog.reveal_key_button.property("_kiro_icon_state")[0], "circle-filled")
        dialog.set_effective_theme("dark")
        self.assertEqual(dialog.reveal_key_button.property("_kiro_icon_state")[0], "circle-filled")
        dialog.deleteLater()

    def test_form_values_are_trimmed_and_base_url_loses_trailing_slash(self) -> None:
        dialog = AgentSettingsDialog()
        dialog.base_url_edit.setText("  https://example.test/v1/  ")
        dialog.api_key_edit.setText("  secret  ")
        dialog.model_edit.setText("  model-x  ")
        dialog.timeout_spin.setValue(20.0)

        self.assertEqual(
            dialog.current_settings(),
            AgentSettings("https://example.test/v1", "secret", "model-x", 20.0, protocol="responses"),
        )
        dialog.deleteLater()

    def test_enabling_without_complete_fields_is_refused(self) -> None:
        # 确保从干净状态开始
        for key in ("agent/base_url", "agent/api_key", "agent/model", "agent/enabled"):
            self.qsettings.remove(key)
        self.qsettings.sync()

        dialog = AgentSettingsDialog()
        saved: list[object] = []
        dialog.settings_saved.connect(saved.append)
        dialog.base_url_edit.setText("https://example.test/v1")
        dialog.model_edit.setText("model-x")
        dialog.api_key_edit.clear()
        dialog.enabled_check.setChecked(True)

        dialog._save()
        self.assertEqual(saved, [])
        self.assertFalse(self.qsettings.value("agent/enabled", False, type=bool))
        self.assertIn("完整", dialog.status_label.text())
        dialog.deleteLater()

    def test_demo_mode_only_disables_and_keeps_credentials(self) -> None:
        AgentSettingsDialog.save_settings(
            AgentSettings("https://example.test/v1", "secret", "model-x", 15.0)
        )
        dialog = AgentSettingsDialog()
        requested: list[bool] = []
        dialog.demo_requested.connect(lambda: requested.append(True))

        dialog._restore_demo()

        self.assertEqual(requested, [True])
        self.assertFalse(AgentSettingsDialog.is_enabled())
        self.assertEqual(
            AgentSettingsDialog.load_settings(),
            AgentSettings("https://example.test/v1", "secret", "model-x", 15.0),
        )
        dialog.deleteLater()

    def test_disabled_remote_configuration_uses_local_demo_provider(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window._agent_settings = AgentSettings(provider="openai")

        provider = window._create_agent_provider()

        self.assertIsInstance(provider, RuleBasedAgentProvider)


if __name__ == "__main__":
    unittest.main()
