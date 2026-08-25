## Why

The current MathAgent sidebar is assembled from Qt Widgets and renders assistant content through a lightweight `QTextBrowser` conversion. It is functional, but it does not provide the visual hierarchy, streaming feedback, dense event cards, hover actions, and composer ergonomics users associate with modern agent workspaces such as VS Code. The problem is concentrated in the presentation layer; the existing mathematical runtime and safe scene-command pipeline should remain stable.

## What Changes

- Replace the Qt-built conversation surface inside the right sidebar with a local `QWebEngineView` host.
- Build the local sidebar document with React, TypeScript, Vite, CSS variables, and local Markdown/KaTeX assets.
- Add a narrow JSON-only Python/JavaScript bridge for session snapshots, streaming runtime events, approval, stop, restore, undo, branch, settings, and attachment intents.
- Render a VS Code-inspired MathAgent workspace: title bar, session tabs, event timeline, readable math cards, CommandPlan cards, hover-only turn actions, and a multi-row composer.
- Keep all scene mutation behind `Agent Runtime -> CommandPlan -> Validator -> SceneCommandService`; JavaScript must never receive Qt, PyVista, or Python execution handles.
- Package the frontend as local static assets with a restrictive Content Security Policy; no CDN, remote page, or external MCP tool is introduced.
- Preserve the existing `.math` session database, QSettings credentials, provider interfaces, 2D/3D scene behavior, and current sidebar open/close affordance.

## Non-Goals

- Rewriting `agent/runtime.py`, `services/scene_commands.py`, or the mathematical engines.
- Adding Electron, Tauri, a web server, cloud persistence, or browser-based application deployment.
- Adding code editing, terminal commands, arbitrary Python execution, multi-agent orchestration, hooks, or a plugin marketplace.

## Impact

- UI: new `ui/agent_sidebar_web.py`, `ui/agent_bridge.py`, and `ui/agent_web/` frontend source; existing `AgentSidebar` remains the Qt container.
- Runtime integration: event serialization and intent routing are added without changing the CommandPlan safety contract.
- Build: a small Node-based frontend build (`npm`/`pnpm`) produces local assets consumed by the PySide6 application; the Python test suite remains the primary runtime test.
- Dependencies: use the already available PySide6 `QtWebEngineWidgets` and `QtWebChannel`; add frontend dependencies only to the web workspace manifest.
- Verification: add bridge protocol, frontend rendering/state, packaging, and sidebar integration tests while retaining the existing 2D/3D regression suite.
