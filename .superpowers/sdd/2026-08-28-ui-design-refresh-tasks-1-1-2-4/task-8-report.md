Task 8 completed.

Changed:
- Unified overlay chrome in `ui/styles/base.qss.in` for `#viewportToolbar`, `#twoDGeometryToolbar`, `#twoDLineFlyout`, `#sceneSettingsPanel`, and `#linearAlgebraCasePopup`.
- Added `QDialog` chrome radius token styling.
- Added `ui.tokens.apply_drop_shadow(widget, level, theme)` and applied token-backed shadow effects to floating toolbars, flyouts, the scene settings panel, and `LightingDialog`.
- Added construction and token-mapping assertions in `tests/test_ui_tokens.py`.
- Refreshed QSS snapshots in `tests/snapshots/base-light.qss` and `tests/snapshots/base-dark.qss`.

Verification:
- `PYTHONPATH=. uv run pytest tests/test_ui_tokens.py tests/test_2d_geometry_toolbar.py tests/test_scene_settings.py tests/test_lighting_dialog.py -q`
- `PYTHONPATH=. uv run pytest tests/test_2d_geometry_toolbar.py tests/test_scene_settings.py tests/test_main_window_layout.py -q`

Note:
- The targeted assertions passed. `test_main_window_layout.py` still shows a QtWebEngine/GPU teardown crash in some runs after pytest exits; the test body itself passes.
