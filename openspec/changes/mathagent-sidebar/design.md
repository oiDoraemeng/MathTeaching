## Context

See `proposal.md` for the motivation and user-visible scope. The existing application already has PySide6, PyVista, SymPy, an OpenAI-compatible provider, `CommandPlan`, and `SceneCommandService`. The design must preserve those boundaries while adding durable conversations and a richer right-side workspace.

## Goals / Non-Goals

**Goals:**

- Keep the viewport and existing 2D/3D rendering paths stable while making the Agent panel a first-class, hidden-by-default workspace.
- Make every scene-changing turn inspectable, cancellable, recoverable, and branchable.
- Keep provider, context, tools, persistence, and UI transport independently testable.
- Make the local user experience feel like a mathematical teaching workspace rather than a code editor.

**Non-Goals:**

- Code editing, terminal access, arbitrary Python execution, or general-purpose IDE tools.
- Multi-agent orchestration, hooks, a plugin marketplace, vector databases, or external MCP dependencies.

## Decisions

### 1. Local WebView for the timeline, Qt for orchestration

Use a local `QWebEngineView` for Markdown/LaTeX rendering, event cards, hover actions, and composer micro-interactions. Keep Python/Qt responsible for session state, model calls, persistence, and scene operations. A narrow JSON message bridge carries UI intents and serializable events.

This gives reliable rich text and layout behavior without allowing JavaScript to access Qt widgets, PyVista objects, or command-service methods. A pure Qt widget tree was considered, but would make Markdown/KaTeX and dense timeline interactions harder to maintain.

### 2. Event-driven runtime with a bounded state machine

Represent one user turn as a state machine: context analysis, planning, validation, optional repair, preview/approval, apply, verify, stop, or error. Emit typed JSON events through the worker boundary. Keep `create_plan()` as a compatibility wrapper around the streaming runtime so older callers are not broken.

This is preferable to a single blocking request because the UI needs incremental output, stop, confirmation, and progress cards. Repair attempts and tool calls are bounded to avoid model loops.

### 3. SQLite WAL under application-managed `.math`

Use SQLite in WAL mode with `sessions`, `turns`, `events`, `attachments`, and `app_state` tables. Store snapshots and plans as versioned JSON text, and keep attachment files below `.math/attachments/`. Resolve the OS application-data root through a single storage helper; allow a temporary root injection in tests.

SQLite keeps this single-user desktop workflow simple and recoverable. A cloud database or project-folder workflow would add setup and lifecycle complexity that the product does not need.

### 4. Immutable turn snapshots and explicit branches

Capture `scene_before` before planning and `scene_after` only after successful execution. Restoring or undoing a turn applies a stored snapshot through the existing scene refresh adapter and never calls the model. New input after a restore records a parent turn; the explicit branch action creates a new session with copied context and snapshot.

This makes history deterministic and prevents a model response from changing while a user is trying to reproduce an earlier drawing.

### 5. Context Broker instead of vector retrieval in the first release

Build each request from a structured scene summary, selected-object summary, recent verbatim messages, bounded summaries of older messages, and validated attachment context. Prefer provider token usage and fall back to a deterministic local estimate. The UI receives only usage numbers.

This is enough for a single-user math teaching workflow and avoids introducing an opaque retrieval layer before there is evidence it is needed.

### 6. Typed mathematical tools remain the only mutating interface

Skills and tools validate parameters with typed schemas and return CommandPlans. Preview revalidates a plan; only an approved runtime action calls `SceneCommandService.execute()`. Geometry, calculus, and linear algebra handlers remain renderer-agnostic.

The alternative of allowing the model to emit raw scene JSON was rejected because it weakens validation and makes provider-specific prompt behavior part of the execution contract.

### 7. Per-session settings with safe defaults

Store Agent/Ask/Plan mode, confirmation/continuous strategy, and model on each session. New sessions use Agent plus confirmation and the current configured model. Credentials remain in QSettings or system credential storage, never in SQLite.

This matches tab behavior users expect and prevents changing one conversation from unexpectedly changing another.

## Risks / Trade-offs

- [QWebEngine is unavailable in a minimal PySide6 install] -> Detect the import during startup and report an actionable dependency error; do not silently revert to the old low-fidelity panel.
- [Provider tool-call streaming differs across compatible APIs] -> Isolate provider adapters, validate all tool arguments, and test DeepSeek/OpenAI-compatible streams with fixtures.
- [Snapshot schema evolves] -> Include a version and reject unsupported versions before mutating the scene.
- [SQLite writes contend with the UI] -> Use WAL, short transactions, and batch event inserts; keep UI-facing methods domain-object based.
- [Large attachments or conversations exhaust context] -> Enforce file/turn limits, summarize older messages, and expose usage percentage before submission.
- [Restore creates an unexpected visual change] -> Capture an in-memory pre-restore guard and provide the existing undo path.
- [WebView bridge becomes a safety bypass] -> Expose only JSON intent signals; never expose Python objects or direct renderer calls.

## Migration Plan

1. Add the storage and snapshot schema behind new services without changing the existing panel entry point.
2. Add runtime events, provider streaming, and tool validation while retaining compatibility methods.
3. Replace the sidebar shell and connect startup recovery, history, restore, undo, and branch actions.
4. Enable the new panel by default only after focused and full regression tests pass; on startup, recover data while keeping the panel hidden.
5. If rollout must be reverted, disable the new sidebar entry point; stored `.math` data remains local and can be read by the next build.

## Open Questions

- Which bundled Markdown and KaTeX versions should be pinned after the runtime dependency check? This does not change the user-facing contract and can be decided during implementation.
