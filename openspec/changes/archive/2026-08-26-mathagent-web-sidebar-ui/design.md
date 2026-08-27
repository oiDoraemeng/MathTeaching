## Context

Math3D Teaching is a PySide6 desktop application with a PyVista viewport, SymPy-backed calculations, and a Python Agent Runtime. The existing right sidebar is a QWidget tree. It must become easier to scan and operate like a modern agent workspace without turning the product into a code IDE or weakening the scene-command boundary.

## Goals / Non-Goals

**Goals:**

- Make the right panel feel like a polished, focused MathAgent workspace rather than a form made from Qt controls.
- Support incremental streaming, event-specific cards, Markdown/LaTeX, session tabs, hover actions, and a dense composer.
- Keep the Python runtime authoritative for model calls, persistence, validation, and scene changes.
- Make the UI transport independently testable with versioned JSON messages.
- Keep the panel local, offline-capable for its assets, and safe to package with the desktop application.

**Non-Goals:**

- Replacing the main Qt shell, PyVista viewport, or existing settings storage.
- Moving Agent state or scene state into browser Local Storage.
- Exposing a general JavaScript-to-Python RPC surface.

## Decisions

### 1. Hybrid desktop architecture

Keep `AgentSidebar` as a QWidget container that controls visibility, fixed width, and the viewport layout. Put one `QWebEngineView` inside it and render a bundled React document. Use an `AgentBridge(QObject)` published through `QWebChannel` or an equivalent `runJavaScript` adapter. The bridge accepts and emits JSON payloads only.

This isolates rich layout concerns from Qt while preserving the current main-window and rendering integration. A pure QWidget implementation is rejected because dense chat layouts, KaTeX, streaming cards, and hover actions become difficult to maintain. QML is deferred because the application is already QWidget-based and the Agent timeline benefits from the Web ecosystem.

### 2. React/TypeScript frontend

Use React with TypeScript and Vite for the local document. Use `pnpm` with a committed `pnpm-lock.yaml`, CSS variables for light/dark theme tokens, CSS layout primitives for the fixed sidebar, `lucide-react` for familiar controls, `markdown-it` plus DOMPurify for safe Markdown parsing, and a pinned local KaTeX build for formulas. The build outputs static assets; no runtime Node process is started. Commit the production `dist/` output so installed desktop builds do not require Node.js or pnpm.

The browser-side state is a projection of Python state, not a second source of truth. A reducer/store owns the active session, timeline events, composer state, model status, and context usage. A page reload requests a fresh `session.snapshot` from Python.

### 3. Versioned JSON bridge

All messages use an envelope with `protocol_version`, `type`, `request_id`, `session_id`, optional `turn_id`, and a JSON payload. UI intents include `send_message`, `approve_plan`, `stop_turn`, `restore_turn`, `undo_turn`, `branch_turn`, `open_history`, `open_settings`, and `attach_files`. Runtime events include `session_snapshot`, `message_delta`, `explanation`, `scene_context`, `calculation`, `plan_ready`, `validation`, `preview`, `execution`, `context_usage`, `stopped`, `error`, and `turn_finished`.

Unknown message types, missing required IDs, invalid protocol versions, non-JSON values, and oversized payloads are rejected before they reach application code. The bridge emits an error event instead of raising a Python object into JavaScript.

### 4. MathAgent visual system

The sidebar uses a compact IDE-like layout: a 36px header, 30px session tabs, a scrollable timeline, and a composer with a multiline input and tool rows. The palette uses neutral surfaces and one accent color, with tokens for both themes. Timeline cards are differentiated by role rather than decorative gradients. Restore, undo, and branch actions are absolutely positioned and hidden until the pointer enters a successful turn card, so hover does not change layout height.

The empty state contains a math-specific title, subtitle, and four starter cards. Streaming text updates one assistant card; tool and plan events append structured cards. Technical JSON is available only inside an explicit details disclosure.

### 5. Asset and security boundary

The document is loaded from packaged local assets with a restrictive CSP: scripts and styles are local, inline execution is disabled where practical, and network navigation is blocked. No remote CDN assets are required. If a custom local URL scheme is used, it is registered with a narrow read-only handler; otherwise the page uses a local base URL for relative assets. The WebEngine page must not expose arbitrary navigation or JavaScript-to-Python method discovery.

### 6. Integration and migration

Before implementation, create the `math-qt` branch from the pre-migration baseline to preserve the old Qt Agent panel. Apply the migration directly on the main branch. Add the WebView host, mirror the existing session snapshot and message methods, then switch `DesignerWindow` connections to the bridge. The main branch SHALL not retain a feature flag, compatibility panel, or runtime fallback to the old Qt conversation widgets; remove their imports and execution wiring after the bridge projection is connected. If a later rollback is needed, use the `math-qt` branch or a Git commit, not an in-application switch.

### 7. Testing strategy

- Python protocol tests validate envelopes, required IDs, unknown messages, and safe payload limits.
- Bridge tests use a fake Runtime and assert that intents become runtime calls without renderer access.
- Frontend tests cover reducer transitions, event-card rendering, composer send/stop state, hover-action visibility, and session switching.
- Packaging tests verify the built asset manifest exists and contains only local references.
- Qt integration tests verify hidden startup, open/close behavior, fixed width, and no scene change when switching tabs.
- The complete existing suite remains a release gate.

## Data Flow

```text
React interaction
  -> JSON intent
  -> AgentBridge validation
  -> Agent Runtime / SessionStore
  -> serializable event
  -> QWebChannel signal
  -> reducer/store
  -> React timeline update
```

An approval, restore, undo, or branch intent is handled by Python and returns a result event. The browser never invokes `SceneCommandService` directly.

## Acceptance Criteria

- Opening the viewport Agent icon displays the WebView-backed sidebar without changing the scene; closing it releases the layout width.
- A streamed turn visibly updates its explanation and appends plan, preview, and execution cards.
- Switching tabs restores the selected session projection without an implicit scene restore.
- Confirmation, Ask, and Plan behavior remains identical to the existing runtime contract.
- Restore, undo, branch, stop, and attachment intents pass through the JSON bridge and are persisted by the existing services.
- The built document works without network access and contains no Python, Qt, PyVista, or API credential data.
- Existing 2D, 3D, SymPy, PyVista, layer, and Agent runtime tests remain green.

## Rollback

The old Qt panel is preserved only on the `math-qt` Git branch. The main branch has no runtime rollback flag or compatibility implementation. A rollback is a source-control operation and must not alter `.math` data or the Runtime/SceneCommandService contract.
