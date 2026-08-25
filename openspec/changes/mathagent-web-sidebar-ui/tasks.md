## 1. Web UI workspace and build

- [ ] 1.1 Add a local `ui/agent_web` React + TypeScript + Vite workspace with pinned Markdown, KaTeX, and Lucide dependencies and a production build that emits self-contained static assets.
- [ ] 1.2 Implement the MathAgent shell: header actions, session tabs, empty state, timeline container, theme tokens, fixed-width layout, and responsive composer skeleton.
- [ ] 1.3 Implement event-card components for user, explanation, context, calculation, CommandPlan, preview, execution, stop, and error states with streaming updates and technical-details disclosure.
- [ ] 1.4 Implement composer interactions: slash affordance, attachment actions, Agent/Ask/Plan, model selection, context ring, send/stop, keyboard behavior, and hover-only restore/undo/branch actions.

## 2. JSON bridge and Qt host

- [ ] 2.1 Add versioned JSON protocol models and validation for UI intents and runtime events, including required IDs, unknown types, payload limits, and serializable errors.
- [ ] 2.2 Add `AgentBridge(QObject)` and a `QWebEngineView` host that loads only packaged local assets and publishes the narrow bridge to the page.
- [ ] 2.3 Connect the bridge to the existing Runtime, SessionStore, and sidebar signals while preserving CommandPlan validation and SceneCommandService as the only scene mutation path.
- [ ] 2.4 Enforce local asset security: restrictive CSP, blocked remote navigation, no credential exposure, and no arbitrary JavaScript-to-Python method surface.

## 3. Session and runtime projection

- [ ] 3.1 Define `session_snapshot`, `turn_event`, `context_usage`, `model_status`, and `settings_state` projection payloads from existing domain objects without duplicating SQLite state in the browser.
- [ ] 3.2 Stream provider/runtime events into the Web UI reducer and preserve confirmation, Ask, Plan, continuous, stop, restore, undo, and branch behavior.
- [ ] 3.3 Persist per-session UI selections and attachments through existing stores and restore the active projection when the sidebar opens or a tab changes.

## 4. Integration and migration

- [ ] 4.1 Add the WebView-backed sidebar to `DesignerWindow` with hidden startup, viewport Agent toggle, fixed width, and close behavior; before migration, preserve the old Qt panel on the `math-qt` branch and do not add a runtime rollback flag on the main branch.
- [ ] 4.2 Replace the old Qt timeline/composer wiring after the Web UI projection is connected, then remove the old Qt panel imports, compatibility methods, and execution wiring from the main branch.
- [ ] 4.3 Update packaging and development commands so Python tests can run without Node while release builds verify the frontend asset manifest.

## 5. Verification and documentation

- [ ] 5.1 Add Python protocol and bridge tests for valid intents, invalid messages, missing IDs, payload limits, and renderer isolation.
- [ ] 5.2 Add frontend reducer/component tests for streaming, tabs, cards, composer states, context ring, and hover actions.
- [ ] 5.3 Add Qt integration tests for WebView loading, offline local assets, hidden/open/close behavior, and no implicit scene mutation on tab switching.
- [ ] 5.4 Run focused tests, the full Python suite, compile checks, frontend production build, and OpenSpec strict validation.
- [ ] 5.5 Document the WebView/React `pnpm` build workflow, committed local assets, bridge protocol, and `math-qt` source-control rollback path without documenting arbitrary code execution.
