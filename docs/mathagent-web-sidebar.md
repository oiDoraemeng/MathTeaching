# MathAgent Web Sidebar

The right-side MathAgent workspace is a local React document hosted by PySide6 `QWebEngineView`. It loads packaged assets through the read-only `mathagent://app/` scheme and communicates with Python through a narrow `QWebChannel` JSON bridge.

## Development Build

From `ui/agent_web`:

```text
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

The production `dist/` directory is committed so installed Math3D Teaching builds do not require Node.js or pnpm at runtime. The application never starts a web server and does not fetch a CDN.

## Runtime Boundary

The browser sends JSON intents through `send_json`. Python emits serializable runtime events through `event_json`. The browser cannot access Qt widgets, PyVista objects, Python callables, API keys, or `SceneCommandService` directly. Scene changes continue through:

```text
Agent Runtime -> CommandPlan -> Validator -> SceneCommandService -> renderer
```

The Python `SessionStore` remains the source of truth for conversations, preferences, attachments, and scene snapshots. The browser keeps only a display projection.

## Backup Branch

The pre-migration Qt Agent panel is preserved on the Git branch `math-qt`. The main branch has no runtime feature flag or old-panel fallback. A source rollback uses Git branch or commit operations; it does not change `.math` data.

The Agent sidebar remains hidden at startup and opens from the viewport Agent button. The Web UI provides session tabs, streaming timeline cards, Agent/Ask/Plan modes, model selection, context usage, attachments, stop, restore, undo, and branch intents.

The local `.math` store keeps one durable session row per tab, one turn row per prompt, event rows for the streamed timeline, and attachment metadata. Switching tabs requests a fresh projection only; it never restores or mutates the drawing scene. Restore and undo explicitly apply the selected `SceneSnapshot` through the host adapter, while branch creates a new session with a copied history prefix.
