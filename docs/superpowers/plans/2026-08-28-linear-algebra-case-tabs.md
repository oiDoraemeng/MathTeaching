# Linear Algebra Case Tabs Implementation Plan

Implement the approved OpenSpec change `linear-algebra-case-tabs` in the existing PySide6/React application. Preserve the Qt/WebView JSON-only boundary and use the existing `SceneCommandService` for all scene mutations.

## Global constraints

- Do not alter the existing Agent session persistence or provider protocol.
- Case loading must validate and execute one 2D `CommandPlan` transaction; failures must leave the scene unchanged.
- Case ids are stable ASCII identifiers and case labels are deduplicated by id in the Web reducer.
- Keep tab strip horizontal, fixed-width per tab, and hide the scrollbar.

<!-- openspec-task: 1.1 -->
### Task 1: Create the case catalog

Files: create `models/linear_algebra_cases.py`, create `tests/test_linear_algebra_cases.py`.

1. Define a frozen `LinearAlgebraCase` dataclass with `id`, `category`, `name`, `formula`, `steps`, `conclusion`, `summary`, and `plan` fields.
2. Add five vector cases with deterministic 2D data and plans using only operations accepted by `SceneCommandService`: addition via `teach.vector_addition`; subtraction, scalar multiplication, dot product, and cross product via points/vectors/segments/annotations plus `view.fit`.
3. Expose `linear_algebra_cases()` and `linear_algebra_case(case_id)` returning immutable records.
4. Test unique ids, required explanation fields, 2D scene plans, and successful `SceneCommandService.validate` for every plan.

<!-- openspec-task: 1.2 -->
### Task 2: Add the AlgebraPanel entry and popup

Files: modify `ui/algebra_panel.py`, create or extend `tests/test_algebra_panel.py`.

1. Add `linear_algebra_requested = Signal(str)` and a `QToolButton` named `linear_algebra_button` immediately after `function_catalog_button` with text `线性代数`.
2. Add a small popup/list widget parallel to `FunctionCatalogPopup`, grouping entries by category and emitting the selected case id.
3. Close the popup when scene mode changes or another popup opens; retain existing function APIs and signals.
4. Test button order/object names and that selecting a vector row emits the stable case id.

<!-- openspec-task: 1.3 -->
### Task 3: Load cases atomically in DesignerWindow

Files: modify `ui/designer_window.py`, create or extend `tests/test_linear_algebra_case_loading.py`.

1. Connect `AlgebraPanel.linear_algebra_requested` in `_bind_algebra_panel`.
2. Implement `_load_linear_algebra_case(case_id)` that looks up the catalog record, creates a plan containing `scene.clear(all)` followed by the case operations, and validates it before execution.
3. Execute through `self.scene_command_service.execute` with the existing transaction/fingerprint path. On `CommandError`, show an AlgebraPanel error and do not emit a case event.
4. On success, update the 2D panel state, render, set a concise status message, and call `self.agent_panel.show_math_case(case)` (or equivalent) with only JSON-safe case fields.
5. Test successful loading clears/replaces the scene and failed validation preserves the prior state using a fake host or isolated service.

<!-- openspec-task: 2.1 -->
### Task 4: Add the `math_case` bridge event

Files: modify `agent/web_protocol.py`, `ui/agent_sidebar_web.py`, create or extend `tests/test_agent_web_protocol.py`.

1. Add `math_case` to event message types and validate bounded string/list/object fields.
2. Implement `AgentSidebarWeb.show_math_case(case)` to emit a version-1 event with case id, category, name, formula, steps, conclusion, summary, and scene mode.
3. Ensure bridge normalization strips unsupported values and never exposes Python objects or callables.
4. Test parsing and serialization of a valid event plus rejection of malformed payloads.

<!-- openspec-task: 2.2 -->
### Task 5: Model and render case tabs in React

Files: modify `ui/agent_web/src/types.ts`, `ui/agent_web/src/state/reducer.ts`, `ui/agent_web/src/App.tsx`, create `ui/agent_web/src/components/MathCaseView.tsx`, create/extend tests.

1. Add `CaseProjection`, `AppState.cases`, and `activeTab` (`session:<id>` or `case:<id>`); initialize with the existing local session tab.
2. Handle `math_case` events by upserting on `case.id`, preserving insertion order, and setting `activeTab` to the case namespace. Repeated events update the existing case without duplicating it.
3. Extend `SessionTabs` props to render session and case tabs, with case tabs using a distinct class and a close button that returns to the active session.
4. Render `MathCaseView` when the active tab is a case. Show name, formula, numbered explanation steps, conclusion, and summary; keep Agent composer/timeline mounted only for session tabs.
5. Add reducer, component, and App tests for creation, deduplication, switching back to Agent, and independent case content.

<!-- openspec-task: 2.3 -->
### Task 6: Stabilize horizontal tab layout

Files: modify `ui/agent_web/src/components/SessionTabs.tsx`, `ui/agent_web/src/styles/layout.css`, create/extend tests.

1. Give each `.session-tab` natural title-based sizing with a 104px minimum and 240px maximum; preserve the close-button slot and ellipsize titles at the cap.
2. Keep the tab nav `overflow-x: auto`, `scrollbar-width: none`, and WebKit scrollbar hidden; preserve keyboard focus and accessible labels.
3. Add case-specific styling without nested cards or visible scrollbars.
4. Verify the frontend test suite and production build pass.

<!-- openspec-task: 3.1 -->
### Task 7: Run regression verification and sync OpenSpec

Files: modify `openspec/changes/linear-algebra-case-tabs/tasks.md` only for checkbox sync.

1. Run focused Python tests for cases, algebra panel, scene commands, bridge, and sidebar integration.
2. Run `pnpm test` and `pnpm build` from `ui/agent_web`.
3. Run `openspec validate --change linear-algebra-case-tabs` and fix any artifact errors.
4. Mark completed OpenSpec task labels in `tasks.md` only after all corresponding checks pass.
