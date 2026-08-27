## MODIFIED Requirements

### Requirement: Conversation workspace layout

The sidebar SHALL provide conversation, history, and settings views inside the same packaged local Web UI. The title-bar history action SHALL open a session history list, and the settings action SHALL open the in-panel settings view instead of silently emitting an unsupported snapshot request.

#### Scenario: Open history
- **WHEN** the user clicks the title-bar history icon
- **THEN** the sidebar switches to a history list showing visible sessions with title, recent activity, and turn count
- **AND** the current scene remains unchanged

#### Scenario: Open settings
- **WHEN** the user clicks the title-bar settings icon
- **THEN** the sidebar switches to the settings view with Agent/model, Skills, Memory, and Rules sections
- **AND** the view provides an explicit return action to the conversation

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

### Requirement: In-panel history

The history view SHALL show one item per visible session with an editable title and a hide action. Hiding a session SHALL remove it from the history list and session tabs without deleting its turns, scene snapshots, attachments, or database record.

#### Scenario: Rename a session
- **WHEN** the user edits and saves a session title
- **THEN** the new title is persisted locally and appears in the history list and session tab

#### Scenario: Hide a session
- **WHEN** the user hides a session
- **THEN** the session is excluded from visible history and tabs
- **AND** its stored turns, snapshots, attachments, and database record remain recoverable by the application

#### Scenario: Hide the active session
- **WHEN** the user hides the active session
- **THEN** the UI first selects another visible session or creates a new visible session
- **AND** the hidden session is not deleted

#### Scenario: Reopen closed session
- **WHEN** the user closes a session tab and later selects it from history
- **THEN** the session reopens with its prior turns and can be selected as an active tab

#### Scenario: Restore hidden session
- **WHEN** the user chooses a hidden session in the history recovery section
- **THEN** the session becomes visible again without deleting or changing any turn, snapshot, or attachment

#### Scenario: Duplicate and invalid titles
- **WHEN** the user saves a duplicate title
- **THEN** the title is accepted
- **WHEN** the user saves an empty title
- **THEN** it becomes `New Chat`
- **WHEN** the title exceeds 80 Unicode code points
- **THEN** the save is rejected and the draft remains editable

### Requirement: MathAgent settings surface

The settings view SHALL expose local model/provider configuration, Skills, Memory, and Rules. The provider configuration SHALL be labeled `OpenAI - Responses` and SHALL persist credentials locally through the existing QSettings boundary.

#### Scenario: Save a provider key
- **WHEN** the user saves a DeepSeek/OpenAI Responses API key and endpoint
- **THEN** the values are persisted locally
- **AND** the Web UI receives only configured/masked status, never the raw key

#### Scenario: Unconfigured DeepSeek request
- **WHEN** the user sends a message while the selected DeepSeek provider has no key
- **THEN** the request is still sent
- **AND** the provider error is rendered as an assistant error card without automatic Local fallback

#### Scenario: Edit instructions and memory
- **WHEN** the user edits a rule or learning preference and saves it
- **THEN** the value is persisted locally, visible after restarting the application, and included in the next runtime context

## ADDED Requirements

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

## MODIFIED Requirements

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
