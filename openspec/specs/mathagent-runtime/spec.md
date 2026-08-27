# mathagent-runtime Specification

## Purpose
Provide a cancellable, context-aware mathematical Agent runtime that can explain concepts, generate validated CommandPlans, and execute safe scene changes through the existing command service while supporting compatible hosted and local models.

## Requirements

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

The runtime SHALL keep the OpenAI-compatible provider boundary for DeepSeek and custom models, including an `OpenAI - Responses` configuration label. Provider credentials SHALL remain in local QSettings and SHALL not be included in session snapshots, runtime events, logs, or WebView state.

#### Scenario: Provider error without fallback
- **WHEN** a selected DeepSeek provider has no API key or returns an API error
- **THEN** the runtime emits a serializable error event for the current turn
- **AND** it does not silently switch to the Local provider

#### Scenario: Incremental response
- **WHEN** a provider streams a response
- **THEN** the UI receives incremental text/tool events and a completed result without exposing hidden reasoning content

#### Scenario: Provider test isolation
- **WHEN** the user clicks `Test connection`
- **THEN** the runtime performs a bounded provider request without changing saved settings, session history, or scene state

### Requirement: Runtime state and cancellation

The runtime SHALL expose observable states for analyzing context, planning, validating, previewing, waiting for approval, applying, verifying, stopped, and error. A stop request SHALL cancel the provider and prevent later tool calls or scene mutations for that turn.

#### Scenario: Stop an active turn
- **WHEN** the user presses the composer stop action during planning
- **THEN** the turn ends as stopped, pending tool calls are discarded, and the current scene is unchanged

### Requirement: Mathematical tools and skills

The runtime SHALL expose parameter-validated math tools for scene inspection, expression calculation, geometry, calculus, and linear algebra. Skills SHALL be discoverable from the local math skill registry and SHALL produce CommandPlans only; skills SHALL not render directly.

#### Scenario: Create a curve
- **WHEN** the Agent calls the curve tool with a valid expression and range
- **THEN** the tool returns a validated CommandPlan suitable for preview and later approval

### Requirement: Local MCP tool boundary

The local Math3D MCP layer SHALL expose math-only tools for creating points, vectors, curves, surfaces, annotations, image exports, and intersections. Each mutating MCP tool SHALL delegate to the same validated CommandPlan and SceneCommandService pipeline; it SHALL not call PyVista or Qt directly and SHALL not connect to an external MCP server.

#### Scenario: MCP tool invocation
- **WHEN** the Agent invokes a local `create_curve` or `create_surface` tool
- **THEN** the tool returns a validated plan or a structured validation error and no renderer is called before approval

### Requirement: Prompt and instruction composition

The runtime SHALL support local `teach`, `visualize`, and `prove` prompt templates and SHALL select or combine them according to the user's intent. It SHALL load the editable math-teacher Instructions and lightweight Memory preferences for each request, while keeping the Math Teacher Agent as the only active agent role in this release.

#### Scenario: Explain and visualize a concept
- **WHEN** a user asks why a determinant represents area and requests a drawing
- **THEN** the runtime composes teaching and visualization guidance, explains the concept first, and then produces a validated visualization plan

#### Scenario: No arbitrary agent role
- **WHEN** the user requests a code-editing or terminal-style agent
- **THEN** the runtime refuses that capability and keeps the Math Teacher Agent role and math-only tools active

### Requirement: Execution modes

The runtime SHALL map the three visible composer modes to fixed execution semantics: Agent continuously executes validated plans, Ask requests one confirmation per complete CommandPlan, and Plan does not execute until explicit confirmation. The deprecated confirmation/continuous selector SHALL not be required by the Web UI.

#### Scenario: Fixed mode mapping
- **WHEN** an identical visualization request is submitted in Agent, Ask, and Plan modes
- **THEN** Agent executes after validation, Ask waits for one complete-plan confirmation, and Plan remains unexecuted until confirmation

#### Scenario: Mode-specific behavior
- **WHEN** an identical visualization request is submitted in Agent, Ask, and Plan modes
- **THEN** Agent follows its continuous execution strategy, Ask requests permission, and Plan returns a non-executed plan

#### Scenario: Duplicate approval
- **WHEN** the same Ask or Plan approval is submitted twice
- **THEN** only the first valid approval can execute the CommandPlan
- **AND** the second request returns an idempotent stale-approval error without scene mutation

#### Scenario: Stop invalidates approval
- **WHEN** the user stops a turn with a pending Ask or Plan approval
- **THEN** the pending approval is invalidated and cannot later mutate the scene

### Requirement: Observable event protocol

The runtime SHALL emit JSON-serializable events for session start, message deltas, tool lifecycle, calculations, plans, validation, approval, previews, execution, undo availability, branches, stops, and errors. UI messages SHALL express intents only and SHALL NOT carry renderer or Qt objects.

#### Scenario: UI intent boundary
- **WHEN** the WebView requests `approve_plan`, `stop_session`, `undo_turn`, or `branch_from_turn`
- **THEN** the Python runtime handles the intent and the WebView receives serializable result events only
