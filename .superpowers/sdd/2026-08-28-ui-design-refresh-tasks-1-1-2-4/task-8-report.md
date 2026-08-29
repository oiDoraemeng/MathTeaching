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

Review fix:
- Applied token-backed overlay drop shadows to AlgebraPanel-owned popups: `#layerSettingsPopup`, `#geometrySettingsPopup`, `#functionCatalogPopup`, `#formulaEditorPopup`, and `#linearAlgebraCasePopup`.
- Added `AlgebraPanel.sync_overlay_theme(theme)` and wired `MainWindow._apply_style()` to refresh those popup shadows during theme changes, so shadow colors and metrics do not go stale.
- Expanded overlay chrome tests to include all overlay family selectors and added AlgebraPanel popup shadow synchronization coverage.

Verification:
- `PYTHONPATH=. uv run pytest tests/test_ui_tokens.py tests/test_algebra_panel.py -q` (PowerShell equivalent: `$env:PYTHONPATH='.'; uv run pytest tests/test_ui_tokens.py tests/test_algebra_panel.py -q`)
- Result: 44 passed, 2 warnings.
