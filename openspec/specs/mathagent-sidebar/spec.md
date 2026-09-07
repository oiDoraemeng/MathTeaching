# mathagent-sidebar Specification

## Purpose
Provide a focused right-side MathAgent workspace for mathematical explanation and visualization, with modern conversation ergonomics while keeping the main viewport available and preserving safe command execution.

## Requirements

### Requirement: Hidden-by-default sidebar

The application SHALL keep the MathAgent sidebar hidden at startup and SHALL provide an Agent icon in the main viewport toolbar that opens it. Closing the sidebar SHALL remove its layout space so the viewport returns to its previous width.

#### Scenario: Open and close the sidebar
- **WHEN** the user clicks the viewport Agent icon
- **THEN** a fixed right-side MathAgent sidebar is shown without rebuilding or clearing the current scene
- **WHEN** the user closes the sidebar
- **THEN** the sidebar is hidden and the viewport occupies the released space

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

### Requirement: Agent mode selector

The composer SHALL expose Agent, Ask, and Plan modes without a separate confirmation/continuous execution selector. Agent SHALL continuously execute validated plans, Ask SHALL request one confirmation per complete CommandPlan, and Plan SHALL never execute until the user confirms the plan.

#### Scenario: Mode-specific visualization
- **WHEN** an identical visualization request is submitted in Agent, Ask, and Plan modes
- **THEN** Agent executes after validation, Ask asks once for the complete plan, and Plan displays a non-executed plan

#### Scenario: Ask mode protects the scene
- **WHEN** a user requests a scene modification in Ask mode
- **THEN** the assistant asks for confirmation or explains the proposed operation and the current scene remains unchanged until confirmation

#### Scenario: Plan mode waits for confirmation
- **WHEN** a user submits a visualization request in Plan mode
- **THEN** the assistant displays the explanation and CommandPlan without executing it

### Requirement: Per-session execution strategy

Agent mode SHALL support confirmation execution and continuous automatic execution. The selected mode, execution strategy, and model SHALL be stored per session and restored when the user switches tabs.

#### Scenario: Confirmation execution
- **WHEN** a plan is valid in confirmation execution
- **THEN** the timeline shows the plan and preview and waits for an explicit apply action before changing the scene

#### Scenario: Continuous execution
- **WHEN** a plan is valid in continuous execution
- **THEN** the plan is applied automatically after validation and the timeline exposes stop and undo actions

### Requirement: Timeline event cards

User messages SHALL render as right-aligned message bubbles without visible `你` or `用户` labels. Assistant event cards SHALL remain readable and distinguishable, while accessible semantic labels may remain hidden from visual presentation.

#### Scenario: Render a user message
- **WHEN** a user turn is added to the timeline
- **THEN** the message is shown as a right-aligned bubble without a visible role word

#### Scenario: Streaming turn
- **WHEN** the runtime emits multiple message deltas followed by a plan event
- **THEN** the Web UI updates one explanation card in order and appends a separate CommandPlan card without replacing earlier user-visible content

#### Scenario: Successful turn timeline
- **WHEN** an Agent turn completes successfully
- **THEN** the timeline contains the user request, explanation, plan, preview, and execution result as readable cards

#### Scenario: Background events in secondary views
- **WHEN** a runtime event arrives while history or settings is open
- **THEN** the event is retained for the session timeline and is visible when the user returns to conversation

### Requirement: Hover-only turn actions

For a successfully executed turn, the UI SHALL show `恢复场景`, `撤销绘图`, and `分支到新聊天记录` only while the pointer is over that turn card. The buttons SHALL NOT change the card's layout height.

#### Scenario: Restore and undo actions
- **WHEN** the user hovers a successful turn and clicks `恢复场景`
- **THEN** the turn's post-execution snapshot replaces the current scene without a model request
- **WHEN** the user clicks `撤销绘图`
- **THEN** the turn's pre-execution snapshot replaces the current scene without a model request

### Requirement: In-panel history

The history icon SHALL switch the same sidebar to a history view grouped by session and turn, with a back action returning to the current timeline. Closing a session tab SHALL not delete its stored history.

#### Scenario: Reopen closed session
- **WHEN** the user closes a session tab and later selects it from history
- **THEN** the session reopens with its prior turns and can be selected as an active tab

### Requirement: Branch from a turn

The sidebar SHALL support creating a new session from a historical turn. The new session SHALL copy the selected scene snapshot, relevant context, and necessary messages; the source session SHALL remain unchanged.

#### Scenario: Continue after restoring an old turn
- **WHEN** the user restores an earlier turn and sends a new prompt in the same session
- **THEN** the new turn records the restored turn as its parent and the earlier records remain intact

#### Scenario: Explicit branch
- **WHEN** the user clicks `分支到新聊天记录`
- **THEN** a new session tab is created from that turn and the source session is not modified

### Requirement: Composer controls and attachments

The composer SHALL provide only a Skills tool action and a `+` attachment action on the left side. The Skills action SHALL show registered math capabilities without requiring manual skill selection. The plus action SHALL open the existing image/PDF/plain-text attachment flow.

#### Scenario: Open Skills
- **WHEN** the user clicks the Skills tool action
- **THEN** the available registered Skills are shown without changing the current scene or forcing a skill choice

#### Scenario: Add attachment
- **WHEN** the user clicks the plus action
- **THEN** the attachment/image picker opens and selected files use the existing ContextBroker validation path

#### Scenario: Attachment limit
- **WHEN** a user adds a sixth attachment or an attachment over its allowed size
- **THEN** the composer shows a validation error and does not send a model request

#### Scenario: Unsupported image input
- **WHEN** the selected model does not support image input
- **THEN** the composer reports that capability clearly and does not silently switch models

#### Scenario: Skills popover
- **WHEN** the user clicks `工具`
- **THEN** an anchored Skills popover lists registered math Skills without requiring a manual selection
- **AND** clicking outside or pressing Escape closes it without changing the scene

#### Scenario: Attachment multi-select
- **WHEN** the user selects multiple attachments through `+`
- **THEN** the existing ContextBroker validates the batch and rejects a sixth item or an oversized item before any model request

### Requirement: MathAgent settings surface

The settings action SHALL open an in-panel settings view with sections for Agent, Skills, Memory, and Rules. Rules SHALL expose the editable math-teacher Instructions document; Memory SHALL expose the lightweight learning preferences and recent topics; changes SHALL be saved locally and applied to subsequent turns without altering historical turn records.

#### Scenario: Edit instructions and memory
- **WHEN** the user edits a rule or learning preference and saves it
- **THEN** the value is persisted locally, visible after restarting the application, and included in the next runtime context

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

### Requirement: Model catalog

The model picker SHALL show an `内置模型` group with fixed DeepSeek presets and a separate `自定义模型` group. The first built-in preset SHALL be selected by default. The Deepseek-V4-Pro preset SHALL expose a hover detail card with its context, image, reasoning, thinking-mode, and thinking-strength metadata. The list SHALL provide `+ 配置自定义模型` at the end of the custom group.

#### Scenario: Select a built-in model
- **WHEN** the user selects a DeepSeek preset
- **THEN** the selected row is highlighted and the model preference is stored for the current session

#### Scenario: Save a custom model
- **WHEN** the user saves a valid OpenAI-compatible custom model
- **THEN** it appears in the separate custom group and can be selected without changing built-in presets

#### Scenario: Configure model protocol
- **WHEN** the user opens provider configuration
- **THEN** `OpenAI - Responses` is selected by default and `Responses` and `Chat Completions` are available
- **AND** saving does not run a connection test unless the user explicitly clicks `Test connection`

#### Scenario: Configure Pro thinking preferences
- **WHEN** the user changes the Pro model thinking switch or strength
- **THEN** the preference is stored for the active session and restored when switching back to that session
- **AND** disabling thinking hides and disables the strength controls while retaining the last selected strength

#### Scenario: Delete a custom model
- **WHEN** the user permanently deletes a custom model configuration
- **THEN** it is removed from the custom catalog only and built-in models and conversation records remain unchanged

### Requirement: Host-synchronized theming

The Agent Web UI SHALL render with the theme provided by the host application and SHALL NOT follow the OS `prefers-color-scheme`. The host SHALL guarantee a correct first paint by loading the document with the effective theme as a URL parameter applied by a document-creation user script, and SHALL communicate runtime theme changes through a `theme_state` bridge event carrying only the effective mode. If no theme information is available, the Web UI SHALL render with built-in light tokens.

#### Scenario: Initial theme match
- **WHEN** the Agent document loads while the host is in dark mode
- **THEN** the document root carries `data-theme="dark"` before any stylesheet is evaluated, producing a correct first paint without a visible light-to-dark flash

#### Scenario: Theme change while loaded
- **WHEN** the host switches its effective theme while the sidebar document is loaded
- **THEN** the sidebar applies the new theme from the `theme_state` event without reloading the document or losing conversation state

#### Scenario: Theme change while hidden
- **WHEN** the host theme changes while the sidebar widget is hidden
- **THEN** the sidebar renders the new theme on its next open without an intermediate wrong-theme frame

#### Scenario: Mode fallback
- **WHEN** a `theme_state` event is missing, malformed, or carries an unknown mode value
- **THEN** the sidebar keeps its current theme and renders light when no theme has ever been applied, recovering when a valid event arrives

### Requirement: Theme-consistent sidebar surfaces

All Agent sidebar surfaces — conversation timeline, event cards, plan cards, composer, history, settings views, and the teaching case reader — SHALL use only semantic CSS custom properties from the token-generated theme, with text contrast meeting WCAG AA in both light and dark themes. Hardcoded literal colors SHALL not remain in sidebar stylesheets, and the native `color-scheme` property SHALL follow the applied theme so scrollbars and form controls match.

#### Scenario: Both themes pass contrast
- **WHEN** the sidebar renders in light or dark mode
- **THEN** body text, muted text, and status-colored event card accents meet the AA contrast threshold against their backgrounds

#### Scenario: No system theme following
- **WHEN** the OS color scheme differs from the host application theme
- **THEN** the sidebar still renders the host-provided theme

### Requirement: Resizable sidebar layout integrity

The Agent sidebar SHALL remain usable across its 360–720px width range: session tabs scroll horizontally, the composer controls do not overflow, model popovers stay within the sidebar bounds, and the conversation column keeps its maximum readable width centered. The existing narrow-width (≤359px) fallback rules SHALL remain for undersized rendering contexts.

#### Scenario: Narrow bound
- **WHEN** the user drags the sidebar to its 360px minimum
- **THEN** header actions, session tabs, composer toolbar, and send controls remain visible and functional

#### Scenario: Wide bound
- **WHEN** the user drags the sidebar to its 720px maximum
- **THEN** event cards do not stretch full width and the timeline stays centered with readable measure

### Requirement: Teaching case tabs

The sidebar tab strip SHALL support two tab kinds — conversation tabs and teaching case tabs — distinguished by a small leading icon on case tabs. Case tabs SHALL always show a close action; closing a case tab SHALL return activation to the current conversation tab. Case tabs are transient: they live only in the sidebar document memory, are rebuilt when the host re-publishes a `math_case` event, and are never persisted to the session store.

#### Scenario: Case tab identity
- **WHEN** both conversation tabs and case tabs are open
- **THEN** case tabs display a leading book icon so the user can tell teaching content from conversations at a glance
- **AND** the icon uses muted color, switching to the accent color when the case tab is active

#### Scenario: Receive a case
- **WHEN** the host publishes a `math_case` event
- **THEN** the sidebar upserts the case by id and activates its tab
- **AND** re-publishing the same case id reuses the existing tab

#### Scenario: Close a case tab
- **WHEN** the user closes the active case tab
- **THEN** the sidebar removes the case tab and reactivates the current conversation tab
- **AND** no conversation state is affected

#### Scenario: Case tabs survive conversation work
- **WHEN** a model turn is running in a conversation and the user opens or closes case tabs
- **THEN** the running turn and its streaming events are unaffected

### Requirement: Teaching case reader

The teaching case view SHALL present the case as a reading page: a category eyebrow, the case name as a document title, the summary, a centered KaTeX formula card, numbered steps rendered as Markdown, and a conclusion card. Reading cards SHALL follow the card visual spec (elevated background, medium radius, no default border), and document typography (reading title at 20px) is independent of panel chrome typography (15px).

#### Scenario: Reading layout
- **WHEN** a case tab is active
- **THEN** the case renders in a centered reading column with the eyebrow, title, summary, formula card, numbered steps, and conclusion card in reading order
- **AND** formulas render through KaTeX and steps render inline Markdown

#### Scenario: Card styling
- **WHEN** the formula card and conclusion card render in either theme
- **THEN** they use the elevated background with medium radius and no default border
- **AND** step markers use the accent color and steps keep comfortable reading line height

#### Scenario: Case pending before document load
- **WHEN** the host publishes a case before the sidebar document finishes loading
- **THEN** the case is delivered after load and opens without loss

### Requirement: Web UI typography and interaction floor

Text in the sidebar SHALL not render below the 11px caption token size except where the token system defines a smaller size, and interactive click targets SHALL be at least 28px in both dimensions. User-facing sidebar copy SHALL be in Chinese, consistent with the rest of the application UI.

#### Scenario: Small text floor
- **WHEN** the sidebar renders status, capability, model metadata, or turn action labels
- **THEN** no text renders below 11px

#### Scenario: Click target floor
- **WHEN** the sidebar renders attachment buttons, tab close buttons, or turn action buttons
- **THEN** each interactive target is at least 28 by 28 pixels

#### Scenario: Chinese copy
- **WHEN** the user opens the history or settings views or hovers formula list controls
- **THEN** headings, empty states, tooltips, and aria labels are in Chinese instead of mixed English
