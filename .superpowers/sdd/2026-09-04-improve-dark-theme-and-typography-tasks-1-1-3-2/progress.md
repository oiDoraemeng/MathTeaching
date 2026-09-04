# SDD ledger — plan: docs/superpowers/plans/2026-09-04-improve-dark-theme-and-typography-tasks-1-1-3-2.md

Worktree: D:/github/Math3DTeaching/.worktrees/improve-dark-theme-and-typography
Branch: codex/improve-dark-theme-and-typography
Starting snapshot: 82db9fa chore: snapshot prerequisite work for theme plan

## Baseline

- Agent Web: `pnpm test` — 39 passed.
- Python: `uv run --with pytest python -m pytest tests -q` — 478 passed, 1 skipped, 1 pre-existing collection warning.
- The ignored lecture source `.agents/线性代数讲义.md` was copied into the isolated worktree because one repository validation test reads it at runtime.

## Rulings

- Ruling: Use the isolated feature-branch snapshot commit as the execution base because the active OpenSpec change, plans, and prerequisite archived change existed only as user working-tree state. The original `master` checkout remains untouched. Cost if wrong: the feature branch includes prerequisite user work in its ancestry and may need rebase/cherry-pick cleanup before integration.
- Ruling: Translate every plan command of the form `uv run pytest ...` to `uv run --with pytest python -m pytest ...` in this worktree. The project does not declare pytest in its environment, so the literal command resolves to Anaconda's global runner and cannot import the repository. Cost if wrong: the ephemeral current pytest release could differ from the developer's intended version.
- Ruling: For Task 3, implement selector-scoped assertions rather than relying only on the sample's global `"font-size" in qss` checks. This follows the task's stated exact-selector contract and avoids false positives. Cost if wrong: tests will be slightly stricter than the illustrative snippet.
- Ruling: Treat Task 9's direct-browser inspection as a smoke check supplementary to its automated fallback/variable contracts; do not alter bridge behavior to facilitate the check. Cost if wrong: a browser-specific visual issue not represented by the CSS contracts could escape automation.
- Ruling: The first review dispatched for Plan 1 Task 5 used Plan 2's same-numbered compact-timeline brief by mistake; that verdict is out of scope. The implementation was rechecked against Plan 1 Task 5's font-stack brief and its reported generator/Vitest/build/package evidence.

## Preflight scan

### Task self-consistency

| Task | Tests vs implementation | Files/interfaces continuity | Result |
|---|---|---|---|
| 1 | Malformed-list tests directly exercise `_validate`; accessor test checks exact order. | Adds `font.family_stack` while explicitly keeping scalar flattening compatible. | Consistent. |
| 2 | Tests distinguish pixel size from point size and verify QApplication acceptance. | Consumes Task 1 accessor; applies before MainWindow construction. | Consistent. |
| 3 | Tests name every Qt chrome category and snapshot outputs. | QSS template and both generated snapshots are all listed. | Consistent, with stricter selector-scoped test ruling above. |
| 4 | Source contract detects all four legacy 14px declarations and four shared object names. | Both edited source and typography test are listed. | Consistent. |
| 5 | Generator and committed-CSS tests check the exact quoted stack twice. | Generated source CSS and production dist are both listed; build chain is preserved. | Consistent. |
| 6 | Tests cover DWM values, all no-throw fallbacks, idempotence/lifecycle. | New module is installed from `main.py` immediately after QApplication creation. | Consistent. |
| 7 | Tests cover current top-level windows and repeated light/dark cycles. | Consumes Task 6 adapter and updates the shared application property in `_apply_style()`. | Consistent. |
| 8 | Tests cover complete identical variable sets, token parity, deterministic script behavior, and invalid themes. | New generator module and its tests are both listed. | Consistent. |
| 9 | Tests require fallbacks, reject raw authored colors, and compare referenced/generated variables. | Shares Task 8 tests and consumes its full `--mi-*` interface without bridge changes. | Consistent; browser smoke ruling above. |

### Shared-file and interface pairs

| Tasks | Producer / shared surface / consumer | Finding |
|---|---|---|
| 1 → 2 | `font_family_stack()` and token body size → `build_application_font()`. | Compatible; Task 2 follows Task 1. |
| 1 ↔ 3 | `tests/test_ui_tokens.py`, scalar flattening, and generated QSS snapshots. | Compatible; Task 1 must keep list values out of QSS substitution so Task 3 snapshots remain scalar. |
| 1 → 5 | `font.family_stack` → Agent Web `webFontStack()`. | Compatible; Web intentionally uses first three UI families plus one generic fallback. |
| 1 → 8 | Validated design tokens and `flatten_theme()` → MathInput CSS generator. | Compatible; Task 8 consumes theme leaves and is unaffected by the excluded list token. |
| 2 ↔ 3 | `tests/test_ui_typography.py`. | Compatible sequential extensions; no contradictory assertions. |
| 2 ↔ 4 | `tests/test_ui_typography.py`. | Compatible; Task 4 removes the remaining authored 14px heading declarations. |
| 2 ↔ 6 | `main.py`. | Compatible; application font setup and titlebar-tracker installation occur before MainWindow construction. |
| 3 ↔ 4 | `tests/test_ui_typography.py` and shared `#sectionHeader` QSS behavior. | Compatible; Task 3 preserves the existing section rule that Task 4 reuses. |
| 6 → 7 | `apply_native_titlebar_theme`, application property, and `tests/test_native_chrome.py`. | Compatible; Task 6 handles future window lifecycle, Task 7 handles existing windows during each style pass. |
| 8 → 9 | `math_input_theme_css()`, the `--mi-*` set, and `tests/test_math_input_theme.py`. | Compatible; Task 9 references the exact variable set emitted by Task 8 and retains literal fallbacks. |

No task contradiction or plan-mandated review-rubric defect remains unresolved.

## Tasks

- Task 1: complete — implementation 83eccd2; review approved
- Task 2: implementation committed at e7b7df9; task review pending
- Task 2: complete — implementation e7b7df9; review approved
- Task 2: pending
- Task 3: fix round 1/5 (1 addressed, 0 open — selector-scoped QSS assertions; commits 1f8d4e0..35861d6)
- Task 3: complete (commits 1f8d4e0..35861d6, review clean)
- Task 4: complete (commits 9390886..ca4fdcf, review clean)
- Task 5: complete (commit ef93ae0, review clean against the correct Plan 1 brief)
- Task 6: pending
- Task 7: pending
- Task 8: pending
- Task 9: pending
