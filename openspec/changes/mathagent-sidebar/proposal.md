## Why

Math3D Teaching currently exposes an AI chat area, but it does not provide the session continuity, execution control, visual feedback, and scene recovery users expect from a modern agent workspace. The result is difficult to use for iterative mathematical exploration, especially when a user wants to compare or restore previous drawings. This change defines a math-specific MathAgent workspace without turning the product into a code IDE.

## What Changes

- Replace the permanent/low-fidelity assistant area with a right-side MathAgent workspace that is hidden by default and opened from the viewport Agent button.
- Add persistent multi-session tabs, in-panel history, per-turn event cards, and hover-only restore, undo, and branch actions.
- Add Agent, Ask, and Plan modes, plus per-session confirmation or continuous execution strategies, model selection, stop, and undo.
- Persist sessions, turns, events, attachments, scene snapshots, and startup state in an application-managed SQLite `.math` directory.
- Add a Context Broker, attachment limits, context-usage ring, and local WebView rendering for Markdown and LaTeX.
- Add math-specific Skills, local MCP tools, editable Instructions/Memory, and teach/visualize/prove prompt templates without permitting direct rendering or arbitrary code execution.
- Preserve the safety pipeline: Agent understands and plans; validators and mathematical tools produce safe CommandPlans; SceneCommandService remains the only scene mutation entry point.
- Keep the existing PySide6, PyVista, SymPy, OpenAI-compatible provider, 2D/3D, and layer-management behavior compatible.

## Capabilities

### New Capabilities

- `mathagent-sidebar`: right-side workspace layout, composer, modes, session tabs, timeline cards, history view, and user actions.
- `mathagent-conversations`: persistent sessions, per-turn records, scene snapshots, restore/undo/branch semantics, attachments, and startup recovery.
- `mathagent-runtime`: event-driven context-aware execution with Agent/Ask/Plan behavior, confirmation/continuous strategies, cancellation, validated math tools, Skills, local MCP tools, prompt templates, and provider streaming.

### Modified Capabilities

- None. The repository has no existing OpenSpec capability specs; this change establishes the first requirements for the MathAgent surface.

## Impact

- UI: `ui/agent_panel.py`, `ui/agent_sidebar.py`, main-window Agent toggle, and a local `QWebEngineView` timeline.
- Runtime and services: `agent/`, `agent/skills/`, local math MCP tools, `services/agent_provider.py`, `services/agent_worker.py`, and `services/scene_commands.py` integration points.
- Persistence: new SQLite storage and application data directories; API keys remain in QSettings or system credential storage.
- Dependencies: existing PySide6/PyVista/SymPy remain; streaming provider, structured validation, Markdown/KaTeX, and PDF text extraction may be added.
- Tests: unit, protocol, UI, runtime, persistence, and end-to-end acceptance coverage, while preserving existing 2D/3D regression tests.
