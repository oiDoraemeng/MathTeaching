## Purpose

Provide a discoverable and safe capability system through which the Math Teacher Agent can read, analyze, edit, view, export, and explain 2D or 3D mathematical scenes using natural language.

## ADDED Requirements

### Requirement: Categorized capability registry

The Agent SHALL expose a versioned local registry of mathematical capabilities grouped into scene reading, scene editing, mathematical analysis, view control, result export, and teaching explanation. Each entry SHALL include a stable namespaced name, description, input schema, output kind, mutation flag, and supported scene scope.

#### Scenario: Discover capabilities
- **WHEN** the runtime requests the available capability catalog
- **THEN** it returns all first-party entries with their category, schema, mutation flag, and 2D/3D scope as JSON-safe data

#### Scenario: Capability metadata is stable
- **WHEN** a provider or Web UI receives the catalog
- **THEN** the entries use the same names and schema fields for the lifetime of protocol version 1

#### Scenario: Reject unknown arguments
- **WHEN** a capability invocation includes an argument not declared by that capability schema, a value of the wrong type, a non-finite number, or an argument payload above the configured limit
- **THEN** local dispatch returns a structured `invalid_arguments` error identifying the field when available
- **AND** no handler, renderer, or scene transaction is invoked

#### Scenario: Legacy alias is not advertised
- **WHEN** a remote model or Web UI requests the capability catalog
- **THEN** it receives only canonical namespaced capability names
- **AND** a legacy local caller can still resolve its documented flat-name alias to the same canonical capability

### Requirement: Read-only scene and math tools

The registry SHALL provide read-only tools for inspecting the current scene, finding objects, calculating safe expressions, and generating teaching explanations. Read-only tools SHALL return detached JSON-compatible data and SHALL NOT mutate the scene.

#### Scenario: Inspect current scene
- **WHEN** the Agent calls `scene.inspect`
- **THEN** it receives the current 2D/3D mode, bounded object summaries, annotations, view state, and selection without renderer objects

#### Scenario: Calculate safely
- **WHEN** the Agent calls `math.calculate` with a supported expression
- **THEN** it receives a structured result, and expressions containing imports, evaluation primitives, or unsupported code are rejected without a model retry causing scene mutation

#### Scenario: Explain from results
- **WHEN** the Agent calls `teaching.explain` with a question and JSON-safe scene or calculation context
- **THEN** it receives a mathematical explanation and no scene command is executed

#### Scenario: Bounded scene inspection
- **WHEN** the scene contains more objects than an inspection result is allowed to expose
- **THEN** `scene.inspect` returns stable object summaries up to its limit plus `truncated` and `omitted_count`
- **AND** it does not serialize renderer handles, full attachment content, or unbounded scene payloads

#### Scenario: No current selection
- **WHEN** the host has no serializable selected object
- **THEN** scene inspection returns an empty selection list rather than inventing a selected object or failing the request

#### Scenario: Literal object lookup
- **WHEN** the Agent calls `scene.find` with an alias, object-type, or expression substring filter
- **THEN** matching uses bounded literal comparisons and returns at most the configured number of summaries
- **AND** regular expressions, executable filter expressions, and raw renderer queries are not accepted

### Requirement: Mutating tools produce validated plans

Scene editing, clearing, view control, and result export tools SHALL be marked mutating and SHALL return a complete `CommandPlan` or a structured validation error. They SHALL NOT call Qt, PyVista, or a renderer directly.

#### Scenario: Create a 2D curve
- **WHEN** the Agent calls `scene.edit` with a valid explicit curve expression and alias in a 2D scene
- **THEN** the tool returns a plan accepted by the existing command validator and the scene remains unchanged until runtime execution

#### Scenario: Create a 3D surface
- **WHEN** the Agent calls `scene.edit` with a valid surface operation in a 3D scene
- **THEN** the tool returns a plan scoped to 3D and no 2D-only operation is included

#### Scenario: Reject invalid scope
- **WHEN** a mutating tool requests a 3D-only object in a 2D plan, or vice versa
- **THEN** it returns a structured error identifying the scope mismatch and the scene is unchanged

#### Scenario: Semantic expression validation
- **WHEN** a curve or surface edit contains an expression that the renderer's controlled mathematical parser cannot accept
- **THEN** the capability returns a structured validation error before showing a plan
- **AND** the renderer is not asked to parse or partially draw the expression

#### Scenario: Alias type conflict
- **WHEN** an edit uses an alias currently owned by a different object type in the captured or staged scene
- **THEN** the capability returns `alias_conflict` and leaves the staged and rendered scenes unchanged

#### Scenario: Idempotent empty scoped clear
- **WHEN** the Agent clears a supported object scope that is already empty
- **THEN** the tool returns a serializable no-op result without an empty CommandPlan
- **AND** the runtime does not show an approval request or start a scene transaction

#### Scenario: Bounded export destination
- **WHEN** the Agent requests `result.export` with a valid PNG basename
- **THEN** the completed export is written below the application-managed export directory and reports only a safe relative result path
- **WHEN** the filename contains a path separator, traversal segment, absolute path, reserved device name, or non-PNG extension
- **THEN** the request is rejected before execution and no file is written

#### Scenario: Unsupported view operation
- **WHEN** the Agent requests camera rotation, arbitrary zoom, or a visibility operation not supported by the version-1 view contract
- **THEN** `view.control` returns `unsupported_operation` and does not approximate a different scene change

### Requirement: Multi-tool plan composition

The runtime SHALL allow bounded read calls followed by multiple mutating capability calls in one turn and SHALL combine their operations into one complete `CommandPlan` before validation, preview, approval, or execution.

#### Scenario: Compose a natural-language request
- **WHEN** a user asks to draw a parabola, compute its vertex, add an annotation, and fit the view
- **THEN** the runtime may call analysis, editing, and view tools, emits one combined plan, and applies one approval boundary for all scene changes

#### Scenario: Tool limit exceeded
- **WHEN** a model exceeds the configured per-turn tool-call or operation limit, or repeats an identical call beyond the limit
- **THEN** the runtime stops the turn with a serializable error and performs no scene mutation

#### Scenario: Staged reads see prior planned changes
- **WHEN** one successful mutating capability creates or updates an object and a later read capability runs in the same turn
- **THEN** the later read reports the validated staged object as pending rather than reading a renderer or missing the object
- **AND** the rendered scene remains unchanged until the complete plan is executed

#### Scenario: Cross-dimensional mutation request
- **WHEN** one turn attempts to compose a 2D mutation and a 3D mutation into the same plan
- **THEN** composition returns `scene_conflict`, creates no approval ticket, and executes no operation

#### Scenario: Deterministic tool ordering
- **WHEN** a provider returns more than one tool call in a response
- **THEN** the runtime validates and dispatches them in provider response order against one staged scene index
- **AND** it does not run mutating calls concurrently

### Requirement: Mode-aware execution boundary

The capability layer SHALL preserve the public Agent, Ask, and Plan semantics. Agent SHALL execute a valid combined plan automatically, Ask SHALL request one confirmation for the complete plan, and Plan SHALL return the plan without execution until explicitly approved.

#### Scenario: Ask protects a multi-operation plan
- **WHEN** a composed plan contains multiple scene edits in Ask mode
- **THEN** the timeline shows one plan and one approval request, and the scene remains unchanged before approval

#### Scenario: Duplicate approval is idempotent
- **WHEN** the same composed plan approval is submitted twice
- **THEN** only the first valid approval can execute and the second returns a stale-approval error without additional scene mutation

#### Scenario: Scene changes while a plan is pending
- **WHEN** the current scene differs from the turn's captured scene fingerprint before automatic execution or approval
- **THEN** execution returns `scene_changed_since_plan`, invalidates the approval ticket, and starts no scene transaction

#### Scenario: Stop during a capability loop
- **WHEN** the user stops a turn while a model response or tool loop is in progress
- **THEN** the runtime discards all later tool calls, plan composition, and execution for that turn
- **AND** a provider response that arrives after the stop cannot mutate the scene

### Requirement: Serializable tool lifecycle events

The runtime SHALL emit JSON-serializable events for capability start, capability result, plan composition, validation, preview, approval, execution, and capability errors. Events SHALL include the session and turn identifiers where required and SHALL exclude credentials, renderer objects, callables, and full sensitive attachment contents.

#### Scenario: Render tool events
- **WHEN** the Agent performs a read call followed by a scene edit
- **THEN** the Web UI receives ordered tool lifecycle events and a separate plan/execution sequence using only JSON data

#### Scenario: Invalid capability request
- **WHEN** the runtime receives an unknown capability, malformed arguments, or an unsupported protocol version
- **THEN** it emits a structured error event and does not invoke a handler or mutate the scene

#### Scenario: Ordered terminal event
- **WHEN** a capability-enabled turn ends in success, rejection, scene conflict, stop, or failure
- **THEN** events are emitted in turn order and exactly one `turn_finished` event records the terminal status

#### Scenario: Sanitized event details
- **WHEN** a tool result, argument, or provider error contains a long string, credential-like value, attachment content, renderer value, or internal exception detail
- **THEN** the lifecycle event contains only a bounded sanitized summary and structured error code
- **AND** the complete unsafe value is not persisted to the conversation event timeline

### Requirement: Compatibility and local-only boundary

Legacy helper names SHALL remain callable as aliases that normalize into the namespaced capability contract. Providers without native tool calling SHALL be able to return a pure JSON or fenced JSON `CommandPlan`. The capability layer SHALL not connect to external MCP servers or execute arbitrary code.

#### Scenario: Legacy alias
- **WHEN** an existing Skill calls `create_curve` or `create_tangent`
- **THEN** the alias produces the same validated namespaced plan and existing callers continue to work

#### Scenario: JSON fallback
- **WHEN** a provider cannot perform native tool calls but returns a valid structured plan
- **THEN** the runtime validates and executes it through the same capability and command pipeline

#### Scenario: Native tool protocol fallback
- **WHEN** a configured provider rejects native function tools as unsupported
- **THEN** the runtime retries once with the same provider's JSON CommandPlan path and records a visible fallback event
- **AND** it does not switch models, connect to an external MCP server, or claim multi-tool staged behavior for that fallback turn

#### Scenario: No external or direct MCP execution
- **WHEN** the Agent needs a capability during a natural-language turn
- **THEN** it dispatches the local registry directly and does not open a network listener, connect to an external MCP server, or use a local MCP adapter's direct execution path
