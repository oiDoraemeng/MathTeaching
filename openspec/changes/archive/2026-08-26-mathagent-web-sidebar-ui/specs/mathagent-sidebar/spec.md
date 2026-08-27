## MODIFIED Requirements

### Requirement: Conversation workspace layout

The sidebar SHALL render its conversation workspace from a packaged local Web UI hosted by `QWebEngineView`, while retaining the existing hidden-by-default visibility, fixed right-side width, title bar, session tabs, timeline, and composer behavior. The Web UI SHALL provide the MathAgent title bar, multi-session tabs, an event timeline, and the composer placeholder `提问或输入 "/"快捷命令`.

#### Scenario: Local Web UI startup
- **WHEN** the user opens the viewport Agent icon
- **THEN** a local packaged document loads into the sidebar without starting a web server or fetching remote assets
- **AND** the active session snapshot is rendered without changing the current scene

#### Scenario: Web UI close
- **WHEN** the user closes the sidebar
- **THEN** the WebView is hidden and its layout space is released while the current session and scene remain unchanged

#### Scenario: New empty conversation
- **WHEN** the user opens a new session
- **THEN** the timeline shows a title, subtitle, and math-focused feature cards instead of an empty message bubble

#### Scenario: Switch sessions
- **WHEN** the user selects another session tab
- **THEN** the sidebar displays that session's messages, mode, execution strategy, and model without changing the current scene

### Requirement: Timeline event cards

Each turn SHALL render readable, role-specific cards in the local Web UI for user input, streamed explanation, scene context, calculations, CommandPlan, preview, execution, stop, and error events. The UI SHALL update the active assistant card incrementally when `message_delta` events arrive. Raw JSON SHALL remain behind an explicit technical-details disclosure.

#### Scenario: Streaming turn
- **WHEN** the runtime emits multiple message deltas followed by a plan event
- **THEN** the Web UI updates one explanation card in order and appends a separate CommandPlan card without replacing earlier user-visible content

#### Scenario: Successful turn timeline
- **WHEN** an Agent turn completes successfully
- **THEN** the timeline contains the user request, explanation, plan, preview, and execution result as readable cards

## ADDED Requirements

### Requirement: JSON-only UI bridge

The Web UI SHALL communicate with Python through a versioned JSON message bridge. The bridge SHALL validate message type, protocol version, session ID, turn ID when required, and payload size before forwarding an intent. The bridge SHALL never expose Qt objects, PyVista objects, Python callables, credentials, or direct `SceneCommandService` access to JavaScript.

#### Scenario: Invalid UI message
- **WHEN** the Web UI sends an unknown message type or an intent without its required session or turn ID
- **THEN** the bridge rejects it and returns a serializable error event without invoking the Agent Runtime or scene service

#### Scenario: Approved scene action
- **WHEN** the Web UI sends `approve_plan` for a valid turn
- **THEN** Python handles the intent through the existing Runtime validation and SceneCommandService pipeline and returns only serializable result events

### Requirement: Local frontend assets

The sidebar SHALL load React, Markdown, LaTeX, icon, script, and style assets from the packaged application resources. It SHALL not require a runtime Node process, remote CDN, external page navigation, or external MCP server.

#### Scenario: Offline rendering
- **WHEN** the application runs without network access
- **THEN** the Agent sidebar still renders existing conversation events, Markdown, and LaTeX using local assets

### Requirement: Modern composer interaction

The Web UI composer SHALL provide multiline input, slash-command affordance, attachment actions, Agent/Ask/Plan selection, per-session model selection, read-only context usage, send/stop state, and keyboard-friendly focus behavior. Hover-only restore, undo, and branch actions SHALL not change event-card layout dimensions.

#### Scenario: Stop while streaming
- **WHEN** the user presses the composer stop action during an active turn
- **THEN** the bridge sends a `stop_turn` intent, the runtime emits a stopped event, and the composer returns to send state without allowing a later tool call for that turn
