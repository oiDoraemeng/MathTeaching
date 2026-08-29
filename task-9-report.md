# Task 9 Report: Typography Hierarchy Normalization

## Summary

- Moved AlgebraPanel title and section-label typography responsibility into global QSS.
- Added `sectionHeader` object names to settings popup labels.
- Reduced AlgebraPanel color swatch inline styles to the dynamic background only.
- Updated `LightRotationWidget` painted text fonts to copy `self.font()` and set only pixel size/weight.
- Added `tests/test_ui_typography.py` to guard typography source ownership and local override regressions.
- Updated QSS snapshots for the new `algebraTitle` and `sectionHeader` rules.

## Verification

Command run:

```powershell
$env:PYTHONPATH='.'; uv run pytest tests/test_ui_typography.py tests/test_algebra_panel.py tests/test_ui_tokens.py tests/test_main_window_layout.py -q
```

Observed pytest result:

```text
53 passed, 2 warnings in 2.54s
```

The command completed with exit code 0. QtWebEngine may still emit offscreen GPU context messages, but they no longer affect test-process teardown.

## Scope Notes

- Did not modify OpenSpec files or Superpowers plan files.
- Existing OpenSpec/plan working-tree changes were left untouched.
