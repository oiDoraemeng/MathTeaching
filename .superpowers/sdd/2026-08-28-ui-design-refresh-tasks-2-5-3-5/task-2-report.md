# Task 2.6 repair note

- Added `set_effective_theme()` hooks to `AgentSettingsDialog`, `InstructionsDialog`, `MemorySettingsDialog`, and `LightingDialog` so modal shadows can be reapplied when `effective_theme` changes.
- Dialog constructors now resolve or accept the current effective theme, and `MainWindow._apply_style()` refreshes already-open Agent Settings, Instructions, Memory, and Lighting dialogs.
- Updated the Memory dialog creation path in `ui/agent_sidebar.py` to pass the current effective theme through.
- Extended `tests/test_dialog_theming.py` to cover themed construction and live theme reapplication.

Verification: `PYTHONPATH=. uv run pytest tests/test_dialog_theming.py tests/test_ui_typography.py tests/test_scene_settings.py -q` PASS.
