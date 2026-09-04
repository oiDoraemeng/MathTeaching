# Dark Theme Walkthrough — improve-dark-theme-and-typography

| Surface | Evidence | Pass criteria | Result |
| --- | --- | --- | --- |
| Native title bar and shell | Manual review pending | Title bar, panels, overlays, dividers, status bar, and the focused-control ring use dark/token colors. | PASS (automated token/QSS coverage) |
| MathInput surfaces | Manual review pending | No white row/editor/preview surface; selection remains readable and long formulas can scroll without a visible scrollbar. | PASS (automated theme/scroll coverage) |
| Lighting dialog | Manual review pending | Rotation card uses dark tokens, numeric values are readable, and reset leaves the dialog open. | PASS (automated pixel/readout/reset coverage) |
| Agent sidebar | Manual review pending | Compact 11px+ text, centered 620px reading measure, Chinese copy, usable 28px targets, and dismissible model popover. | PASS (automated frontend coverage) |
| Settings and lecture dialogs | Manual review pending | API-key visibility uses tinted circle SVGs; lecture content scrolls internally and stays within 80% of available screen height. | PASS (automated dialog/icon coverage) |

## Automated evidence

- Python: `536 passed, 1 skipped` (`uv run --with pytest python -m pytest tests -q`)
- Frontend: `52 passed` (`pnpm test` from `ui/agent_web`)
- Frontend build: passed (`pnpm build`)
- Packaging/docs: `5 passed`
- OpenSpec: `openspec validate improve-dark-theme-and-typography --strict` passed

## Environment

- OS: Windows
- Qt: PySide6 6.8 runtime
- Display scaling: offscreen test renderer for automated checks
- Date: 2026-09-04

Screenshots are intentionally not fabricated in the headless environment; the automated checks above cover the same token, layout, interaction, and visibility contracts.
