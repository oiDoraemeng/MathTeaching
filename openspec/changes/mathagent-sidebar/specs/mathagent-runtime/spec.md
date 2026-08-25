## Purpose

Provide a cancellable, context-aware mathematical Agent runtime that can explain concepts, generate validated CommandPlans, and execute safe scene changes through the existing command service while supporting compatible hosted and local models.

## ADDED Requirements

### Requirement: Safe command pipeline

All scene-changing requests SHALL follow `Agent -> mathematical tools/skills -> CommandPlan -> validator -> SceneCommandService -> renderer`. The Agent SHALL NOT execute arbitrary Python, call Qt or PyVista directly, or bypass validation.

#### Scenario: Valid visualization request
- **WHEN** a user asks the Agent to draw a mathematical object
- **THEN** the Agent returns a validated CommandPlan and only the SceneCommandService applies it

#### Scenario: Invalid plan
- **WHEN** validation rejects a generated plan
- **THEN** the runtime reports the validation error and does not mutate the scene

### Requirement: Context Broker

Before each model request, the runtime SHALL package the current scene and selected-object summaries, recent messages, bounded summaries of older messages, and attachment context. It SHALL expose only used tokens, maximum tokens, and percentage to the UI context indicator.

#### Scenario: Context usage
- **WHEN** a request is prepared
- **THEN** the runtime emits a context-usage value based on provider usage when available or a documented local estimate

### Requirement: Streaming provider compatibility

The runtime SHALL support OpenAI-compatible streaming responses and structured tool calls, including DeepSeek and local endpoints, while preserving the existing plan-generation compatibility entry point.

#### Scenario: Incremental response
- **WHEN** a provider streams a response
- **THEN** the UI receives incremental text/tool events and a completed result without exposing hidden reasoning content

### Requirement: Runtime state and cancellation

The runtime SHALL expose observable states for analyzing context, planning, validating, previewing, waiting for approval, applying, verifying, stopped, and error. A stop request SHALL cancel the provider and prevent later tool calls or scene mutations for that turn.

#### Scenario: Stop an active turn
- **WHEN** the user presses the composer stop action during planning
- **THEN** the turn ends as stopped, pending tool calls are discarded, and the current scene is unchanged

### Requirement: Mathematical tools and skills

The runtime SHALL expose parameter-validated math tools for scene inspection, expression calculation, geometry, calculus, and linear algebra. Mutating tools SHALL produce CommandPlans; skills SHALL not render directly.

#### Scenario: Create a curve
- **WHEN** the Agent calls the curve tool with a valid expression and range
- **THEN** the tool returns a validated CommandPlan suitable for preview and later approval

### Requirement: Execution modes

Agent mode SHALL support confirmation and continuous execution; Ask mode SHALL refuse silent scene mutation; Plan mode SHALL never execute a scene-changing plan until an explicit confirmation transitions it to an execution mode.

#### Scenario: Mode-specific behavior
- **WHEN** an identical visualization request is submitted in Agent, Ask, and Plan modes
- **THEN** Agent follows its execution strategy, Ask requests permission, and Plan returns a non-executed plan

### Requirement: Observable event protocol

The runtime SHALL emit JSON-serializable events for session start, message deltas, tool lifecycle, calculations, plans, validation, approval, previews, execution, undo availability, branches, stops, and errors. UI messages SHALL express intents only and SHALL NOT carry renderer or Qt objects.

#### Scenario: UI intent boundary
- **WHEN** the WebView requests `approve_plan`, `stop_session`, `undo_turn`, or `branch_from_turn`
- **THEN** the Python runtime handles the intent and the WebView receives serializable result events only
