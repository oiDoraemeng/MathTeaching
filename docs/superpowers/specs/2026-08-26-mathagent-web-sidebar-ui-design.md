# MathAgent Web Sidebar UI Design

## Scope

This design implements the already-approved OpenSpec change `mathagent-web-sidebar-ui`. It changes the right-side presentation layer only. The existing Agent Runtime, CommandPlan validation, SceneCommandService, SymPy calculations, PyVista rendering, `.math` persistence, and QSettings credential storage remain authoritative.

The old Qt Agent panel is preserved on the `math-qt` Git branch before migration. The main branch directly adopts the WebView-backed UI and does not retain a runtime feature flag, compatibility panel, or old-panel imports.

## Architecture

```text
DesignerWindow
  └── AgentSidebar(QWidget)
        └── AgentSidebarWeb(QWidget)
              └── QWebEngineView
                    └── local React MathAgent document
                          └── narrow QWebChannel JSON bridge
                                └── Agent Runtime / SessionStore
                                      └── CommandPlan -> Validator -> SceneCommandService
                                            └── SymPy / PyVista scene
```

`AgentSidebar` continues to own hidden startup, fixed width, opening from the viewport Agent button, closing, and layout-space release. `AgentSidebarWeb` owns WebEngine setup and local document loading. `AgentBridge` validates messages and forwards only approved intents. No browser code receives a Qt object, PyVista object, Python callable, credential, or renderer handle.

## Bridge Contract

The bridge exposes exactly one callable slot and one event signal:

```python
class AgentBridge(QObject):
    event_json = Signal(str)

    @Slot(str)
    def send_json(self, raw: str) -> None:
        ...
```

The JavaScript page calls `send_json(JSON.stringify(envelope))`. Python emits `event_json` with JSON text. Business operations are not exposed as separate Qt slots.

Every envelope contains:

```json
{
  "protocol_version": 1,
  "type": "message_delta",
  "request_id": "req-1",
  "session_id": "session-1",
  "turn_id": "turn-1",
  "sequence": 14,
  "payload": {}
}
```

Required IDs depend on the message type. The validator rejects unknown types, unsupported protocol versions, missing IDs, non-JSON values, malformed payloads, and payloads above the configured limit before runtime dispatch. Rejections become serializable `error` events.

The page requests a complete `session_snapshot` on load or sequence recovery. Runtime updates then arrive as ordered events. The reducer applies `sequence == last + 1`, drops duplicate sequences, buffers a small out-of-order window, and requests a snapshot when a gap cannot be repaired. `session_id` and `turn_id` mismatches are ignored.

## Local Web Document

The frontend is a React + TypeScript + Vite workspace under `ui/agent_web/`. `pnpm-lock.yaml` is committed. Dependencies are local and pinned: `markdown-it`, DOMPurify, KaTeX, and `lucide-react`. The reducer is implemented with React `useReducer`; React is a projection of Python state and does not use Local Storage.

The production build is committed under `ui/agent_web/dist/` so desktop users do not need Node.js or pnpm at runtime. Development and release commands are:

```text
pnpm install --frozen-lockfile
pnpm build
```

The component tree is:

```text
App
├── AgentHeader
├── SessionTabs
├── EmptyState
├── Timeline
│   ├── UserCard
│   ├── ExplanationCard
│   ├── SceneContextCard
│   ├── CalculationCard
│   ├── PlanCard
│   ├── PreviewCard
│   ├── ExecutionCard
│   ├── StoppedCard
│   └── ErrorCard
├── HistoryView
└── Composer
    ├── AttachmentActions
    ├── ModeSelector
    ├── ModelSelector
    ├── ContextRing
    └── SendStopButton
```

The visual system uses CSS variables for light and dark themes, neutral IDE-like surfaces, one accent color, compact header and tabs, and role-specific event cards. Markdown is sanitized before rendering; KaTeX assets are local. Technical JSON is behind a details disclosure. Restore, undo, and branch controls are absolutely positioned and appear only when hovering a successful turn card, so the card height does not shift.

## Resource and Security Boundary

Register a read-only `mathagent://app/` URL scheme. The handler serves only packaged `index.html`, JavaScript, CSS, fonts, KaTeX, and icon assets from an allowlist. The page cannot navigate to `http`, `https`, or arbitrary `file` URLs. A restrictive CSP allows only the local scheme, `data:` images where required, and no network connections. Production WebEngine developer tools are disabled.

Attachments are selected and validated by Python. JavaScript sends an intent, never a filesystem path that Python blindly trusts. Python performs type and size checks, SHA-256 calculation, `.math/attachments/` copying, and SessionStore persistence.

## Runtime Projection

The flow remains:

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

`send_message`, `approve_plan`, `stop_turn`, `restore_turn`, `undo_turn`, `branch_turn`, `open_history`, `open_settings`, `attach_files`, mode changes, model changes, and snapshot requests all use the same intent boundary. Confirmation, Ask, Plan, continuous execution, stop, restore, undo, and branch behavior are not reimplemented in JavaScript.

## Migration and Git Strategy

Before editing the main branch, create `math-qt` from the pre-migration baseline and verify that the old Qt panel files and focused tests remain available there. Implement the WebView host and bridge on the main branch. Once the new projection and integration tests pass, remove `AgentPanel` imports, compatibility methods, and old timeline/composer wiring from the main branch. No `mathagent.web_ui_enabled` setting is introduced. A later rollback uses Git branch/commit operations and does not touch `.math` data or runtime safety boundaries.

## Test Strategy

Python tests cover protocol envelopes, unknown types, required IDs, version checks, payload limits, serializable errors, bridge dispatch, renderer isolation, restore-without-model, and stop cancellation. Frontend tests use Vitest and React Testing Library for snapshots, ordered and duplicate events, gap recovery, tab switching, event cards, streaming merge, modes, send/stop, context usage, and hover actions. Qt integration tests cover hidden startup, Agent toggle, close layout release, custom-scheme loading, offline assets, and no scene mutation on tab switches. The release gate runs the frontend build, the complete Python suite, compileall, diff checks, and strict OpenSpec validation.

## Risks and Mitigations

- WebEngine or asset load failure: validate the dist manifest at startup and show an actionable error.
- Event gaps or provider bursts: sequence-aware reducer, bounded buffering, and snapshot recovery.
- WebView privilege escalation: one JSON slot, strict schemas, CSP, URL allowlist, and no renderer exposure.
- Import breakage after old-panel removal: create and verify `math-qt` before deleting main-branch dependencies, then run a repository-wide import scan.
- Stale build assets: require `pnpm build` and manifest checks in release verification; commit `dist/` with source changes.
- Memory growth: one QWebEngineView per sidebar and no WebView per session tab.
