## MODIFIED Requirements

### Requirement: Timeline event cards

User messages SHALL render as right-aligned message bubbles without visible `你` or `用户` labels. Assistant event cards SHALL remain readable and distinguishable, while accessible semantic labels may remain hidden from visual presentation. The conversation timeline SHALL use a compact reading density: assistant body text and event card text at the body token size with line height no greater than 1.5, and vertical paddings and margins (timeline padding, event card padding, spacing between turns) sized so identical content occupies fewer lines than the previous relaxed density.

#### Scenario: Render a user message
- **WHEN** a user turn is added to the timeline
- **THEN** the message is shown as a right-aligned bubble without a visible role word

#### Scenario: Streaming turn
- **WHEN** the runtime emits multiple message deltas followed by a plan event
- **THEN** the Web UI updates one explanation card in order and appends a separate CommandPlan card without replacing earlier user-visible content

#### Scenario: Successful turn timeline
- **WHEN** an Agent turn completes successfully
- **THEN** the timeline contains the user request, explanation, plan, preview, and execution result as readable cards

#### Scenario: Compact reading density
- **WHEN** the same assistant reply renders in the timeline
- **THEN** its body text uses the 12px body token size with at most 1.5 line height
- **AND** event card padding and inter-turn spacing use the compact density values defined by the token-derived stylesheet
- **AND** the reply occupies no more lines than it would with the previous 13px/1.55 relaxed density

#### Scenario: Streaming scroll sticks to bottom only when pinned
- **WHEN** a streaming turn appends tokens while the user has scrolled up to read earlier content
- **THEN** the timeline does not force-scroll back to the bottom
- **AND** when the user is at the bottom of the timeline, streaming output keeps the latest content in view

#### Scenario: Background events in secondary views
- **WHEN** a runtime event arrives while history or settings is open
- **THEN** the event is retained for the session timeline and is visible when the user returns to conversation

### Requirement: In-panel history

The history icon SHALL switch the same sidebar to a history view grouped by session and turn, with a back action returning to the current timeline. Closing a session tab SHALL not delete its stored history. Renaming a session inline SHALL commit on Enter or blur, and pressing Escape SHALL cancel the rename without saving the edited text.

#### Scenario: Reopen closed session
- **WHEN** the user closes a session tab and later selects it from history
- **THEN** the session reopens with its prior turns and can be selected as an active tab

#### Scenario: Escape cancels rename
- **WHEN** the user edits a session title in the history view and presses Escape
- **THEN** the rename is cancelled, the original title is kept, and no save occurs

### Requirement: Model catalog

The model picker SHALL show an `内置模型` group with fixed DeepSeek presets and a separate `自定义模型` group. The first built-in preset SHALL be selected by default. The Deepseek-V4-Pro preset SHALL expose a hover detail card with its context, image, reasoning, thinking-mode, and thinking-strength metadata. The list SHALL provide `+ 配置自定义模型` at the end of the custom group. The picker popover SHALL close on Escape and on outside pointer interaction, and its trigger button SHALL expose an `aria-expanded` state.

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

#### Scenario: Popover dismissal
- **WHEN** the model picker popover is open and the user presses Escape or clicks outside it
- **THEN** the popover closes without changing the selected model
- **AND** the trigger button's `aria-expanded` state reflects the popover visibility

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

### Requirement: Resizable sidebar layout integrity

The Agent sidebar SHALL remain usable across its 360–720px width range: session tabs scroll horizontally, the composer controls do not overflow, model popovers stay within the sidebar bounds, and the conversation column keeps its maximum readable width centered. The existing narrow-width (≤359px) fallback rules SHALL remain for undersized rendering contexts.

#### Scenario: Narrow bound
- **WHEN** the user drags the sidebar to its 360px minimum
- **THEN** header actions, session tabs, composer toolbar, and send controls remain visible and functional

#### Scenario: Wide bound
- **WHEN** the user drags the sidebar to its 720px maximum
- **THEN** event cards do not stretch full width and the timeline stays centered with readable measure
