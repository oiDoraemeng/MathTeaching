## Purpose

Provide a focused right-side MathAgent workspace for mathematical explanation and visualization, with modern conversation ergonomics while keeping the main viewport available and preserving safe command execution.

## ADDED Requirements

### Requirement: Hidden-by-default sidebar

The application SHALL keep the MathAgent sidebar hidden at startup and SHALL provide an Agent icon in the main viewport toolbar that opens it. Closing the sidebar SHALL remove its layout space so the viewport returns to its previous width.

#### Scenario: Open and close the sidebar
- **WHEN** the user clicks the viewport Agent icon
- **THEN** a fixed right-side MathAgent sidebar is shown without rebuilding or clearing the current scene
- **WHEN** the user closes the sidebar
- **THEN** the sidebar is hidden and the viewport occupies the released space

### Requirement: Conversation workspace layout

The sidebar SHALL show a `MathAgent` title bar with new-chat, history, and settings icon actions, a horizontal multi-session tab strip, a conversation timeline, and a bottom composer with the placeholder `提问或输入 "/"快捷命令`.

#### Scenario: New empty conversation
- **WHEN** the user opens a new session
- **THEN** the timeline shows a title, subtitle, and math-focused feature cards instead of an empty message bubble

#### Scenario: Switch sessions
- **WHEN** the user selects another session tab
- **THEN** the sidebar displays that session's messages, mode, execution strategy, and model without changing the current scene

### Requirement: Agent mode selector

The composer SHALL provide Agent, Ask, and Plan modes. Agent SHALL be the default for a new session; Ask SHALL answer without silently changing the scene; Plan SHALL present an actionable plan without applying scene changes until the user confirms.

#### Scenario: Ask mode protects the scene
- **WHEN** a user requests a scene modification in Ask mode
- **THEN** the assistant asks for confirmation or explains the proposed operation and the current scene remains unchanged

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

Each turn SHALL render distinct cards for the user message, mathematical explanation, scene context, calculations, CommandPlan, preview, execution result, and errors or cancellation. Raw JSON SHALL be available only under technical details.

#### Scenario: Successful turn timeline
- **WHEN** an Agent turn completes successfully
- **THEN** the timeline contains the user request, explanation, plan, preview, and execution result as readable cards

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

The composer SHALL provide attachment, image, document, menu, and tool actions; a model selector; a send action that becomes stop while a request is running; and a read-only circular context-usage indicator whose percentage is shown on hover. The first release SHALL accept images, PDFs, and plain text with at most five attachments per turn.

#### Scenario: Attachment limit
- **WHEN** a user adds a sixth attachment or an attachment over its allowed size
- **THEN** the composer shows a validation error and does not send a model request

#### Scenario: Unsupported image input
- **WHEN** the selected model does not support image input
- **THEN** the composer reports that capability clearly and does not silently switch models
