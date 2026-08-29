Task 8 review fix completed.

Changed:
- Added `IntersectionPopup` to the shared overlay family in `ui/styles/base.qss.in`.
- Set `IntersectionPopup`'s `objectName` to `intersectionPopup`.
- Included `IntersectionPopup` in `AlgebraPanel.sync_overlay_theme(theme)` so it receives the token-backed overlay shadow with the other AlgebraPanel popups.
- Expanded `tests/test_ui_tokens.py` to assert the new selector, object name, and shadow/theme sync.
- Refreshed `tests/snapshots/base-light.qss` and `tests/snapshots/base-dark.qss`.

Verification:
- `PYTHONPATH=. uv run pytest tests/test_ui_tokens.py tests/test_algebra_panel.py -q`
- Result: 44 passed, 2 warnings.
