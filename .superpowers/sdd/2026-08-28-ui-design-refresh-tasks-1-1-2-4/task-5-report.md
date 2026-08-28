# Task 5 Report: Token and QSS Regression Coverage

## Implemented

- Added malformed-token validation coverage for missing theme leaves, mismatched theme leaf sets, zero font sizes, negative durations, and invalid colors.
- Added explicit QSS assertions requiring `#sceneSettingsPanel` and rejecting retired selectors and legacy colors.
- Added normalized light and dark QSS snapshot comparison (trailing whitespace stripped, exactly one final newline).
- Added reviewed baseline snapshots at `tests/snapshots/base-light.qss` and `tests/snapshots/base-dark.qss`.

## Verification

`uv run pytest tests/test_ui_tokens.py -q` could not collect because the current environment does not expose the repository package on `PYTHONPATH` (`ModuleNotFoundError: No module named 'ui'`).

The retired-selector assertions are intentionally strict; they will fail until the corresponding stylesheet cleanup from the upstream UI tasks is present.

## Review follow-up

- Replaced literal `\\n` sequences in both snapshots with actual line breaks matching `build_qss` output.
- Tightened malformed-theme assertions to exact invalid JSON paths, including the specific missing or extra leaf.
- Updated validation to report the precise counterpart path for theme leaf-set mismatches.

Focused verification remains blocked by the existing `ModuleNotFoundError: No module named 'ui'` collection issue.
