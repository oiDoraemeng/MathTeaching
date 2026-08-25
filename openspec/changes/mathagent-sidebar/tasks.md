## 1. Scene and persistence foundation

- [ ] 1.1 Add a versioned, Qt/PyVista-free scene snapshot type and round-trip tests; verify unknown versions are rejected and `pytest tests/test_scene_snapshot.py -q` passes.
- [ ] 1.2 Add the application-data resolver and SQLite WAL session store with sessions, turns, events, attachments, and app state; verify temporary-root creation, WAL mode, CRUD, and reopen tests pass.
- [ ] 1.3 Add snapshot capture/restore adapters to the existing scene host; verify 2D, 3D, layers, annotations, and camera state survive a snapshot restore without serializing PyVista objects.
- [ ] 1.4 Implement immutable turn pointers, restore, undo, and explicit branch persistence; verify restoring a turn makes no provider call and branching leaves the source session unchanged.
- [ ] 1.5 Implement startup recovery of tabs, active session, and final scene while keeping the sidebar hidden; verify an end-to-end restart test passes.

## 2. Context and attachments

- [ ] 2.1 Implement the Context Broker with structured scene context, selected-object context, recent verbatim messages, bounded older summaries, and token usage; verify deterministic packing and usage percentage tests pass.
- [ ] 2.2 Add image/PDF/plain-text attachment validation, SHA-256 metadata, and `.math/attachments/` copying; verify five-file, 10 MB image, 20 MB document, and unsupported-image-model cases.
- [ ] 2.3 Keep credentials out of SQLite and expose only context usage numbers to the UI; verify database inspection and protocol tests contain no API key or hidden reasoning content.

## 3. Provider and mathematical tools

- [ ] 3.1 Extend the OpenAI-compatible provider contract for streaming text and structured tool-call deltas while preserving the existing plan-generation entry point; verify fake-stream compatibility tests pass.
- [ ] 3.2 Add DeepSeek, OpenAI-compatible, and local provider adapters with capability metadata and masked errors; verify provider regression tests pass with mocked responses.
- [ ] 3.3 Add typed geometry, calculus, linear-algebra, scene-inspection, and expression tools; verify mutating tools return CommandPlans, reject invalid arguments, and import no Qt/PyVista modules.
- [ ] 3.4 Ensure preview revalidates plans and only an approved runtime action can call `SceneCommandService.execute()`; verify direct tool execution cannot mutate a scene.

## 4. Runtime and execution modes

- [ ] 4.1 Implement the event-driven runtime state machine and JSON event protocol; verify state transition and event serialization tests cover planning, validation, preview, apply, stop, and error.
- [ ] 4.2 Add per-session Agent/Ask/Plan behavior and confirmation/continuous execution strategies; verify confirmation waits, continuous applies after validation, Ask requests permission, and Plan never applies.
- [ ] 4.3 Add cancellation tokens, bounded repair/tool-call loops, and worker signals for event, finish, error, and stop; verify stop prevents later tool calls and scene mutation.
- [ ] 4.4 Persist completed, rejected, stopped, and failed turns with before/after snapshots and event timelines; verify runtime persistence tests pass.

## 5. Sidebar shell and session tabs

- [ ] 5.1 Replace the permanent collapsed assistant strip with a hidden-by-default fixed-width sidebar opened by the viewport Agent icon; verify open/close layout tests pass.
- [ ] 5.2 Add the MathAgent header icons, multi-session tab strip, new/close behavior, and per-session model/mode restoration; verify tabs never change the scene implicitly and at least one input session remains.
- [ ] 5.3 Add the empty state, timeline event-card model, exact composer placeholder, tool buttons, Agent/Ask/Plan selector, and confirmation/continuous control; verify UI behavior tests pass.
- [ ] 5.4 Add the read-only circular context indicator with hover percentage plus send/stop state; verify it is not clickable and reflects the latest usage event.

## 6. Rich local timeline and history

- [ ] 6.1 Add the local WebView document, Markdown/LaTeX rendering assets, and strict JSON message bridge; verify protocol tests reject unknown messages and missing session/turn IDs.
- [ ] 6.2 Render readable cards for user, explanation, context, calculations, plans, previews, execution, stop, and errors; verify raw JSON is only available in technical details.
- [ ] 6.3 Add hover-only restore, undo, and branch actions without layout shifts; verify successful turns expose actions only on hover and failed turns do not.
- [ ] 6.4 Add in-panel history grouped by session and turn with back navigation and thumbnail metadata; verify closed tabs remain reopenable and no separate history window is created.

## 7. Settings and integration

- [ ] 7.1 Connect existing Instructions, Memory, Skills, and model settings to new runtime requests while retaining QSettings credential storage; verify edits affect subsequent turns and are not written to the database.
- [ ] 7.2 Connect the sidebar to the existing designer window, scene command service, layer management, 2D/3D rendering, and PyVista refresh path; verify existing scene regression tests pass.
- [ ] 7.3 Update user documentation for hidden-panel toggle, session modes, `.math` storage, history restore, undo, and branch behavior; verify documented commands and paths match the implementation.

## 8. Verification and rollout

- [ ] 8.1 Add focused tests for snapshots, storage, context, providers, tools, runtime, WebView protocol, sidebar, history, and settings; verify each focused test group passes.
- [ ] 8.2 Run the complete suite with `pytest -q`, `python -m compileall agent services ui tests`, and `git diff --check`; verify no existing 2D/3D, SymPy, PyVista, or layer tests regress.
- [ ] 8.3 Run `openspec validate --change mathagent-sidebar` and verify all proposal, specs, design, and task artifacts are recognized as complete before implementation begins.
