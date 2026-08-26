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

### Requirement: Multi-tool plan composition

The runtime SHALL allow bounded read calls followed by multiple mutating capability calls in one turn and SHALL combine their operations into one complete `CommandPlan` before validation, preview, approval, or execution.

#### Scenario: Compose a natural-language request
- **WHEN** a user asks to draw a parabola, compute its vertex, add an annotation, and fit the view
- **THEN** the runtime may call analysis, editing, and view tools, emits one combined plan, and applies one approval boundary for all scene changes

#### Scenario: Tool limit exceeded
- **WHEN** a model exceeds the configured per-turn tool-call or operation limit, or repeats an identical call beyond the limit
- **THEN** the runtime stops the turn with a serializable error and performs no scene mutation

### Requirement: Mode-aware execution boundary

The capability layer SHALL preserve the public Agent, Ask, and Plan semantics. Agent SHALL execute a valid combined plan automatically, Ask SHALL request one confirmation for the complete plan, and Plan SHALL return the plan without execution until explicitly approved.

#### Scenario: Ask protects a multi-operation plan
- **WHEN** a composed plan contains multiple scene edits in Ask mode
- **THEN** the timeline shows one plan and one approval request, and the scene remains unchanged before approval

#### Scenario: Duplicate approval is idempotent
- **WHEN** the same composed plan approval is submitted twice
- **THEN** only the first valid approval can execute and the second returns a stale-approval error without additional scene mutation

### Requirement: Serializable tool lifecycle events

The runtime SHALL emit JSON-serializable events for capability start, capability result, plan composition, validation, preview, approval, execution, and capability errors. Events SHALL include the session and turn identifiers where required and SHALL exclude credentials, renderer objects, callables, and full sensitive attachment contents.

#### Scenario: Render tool events
- **WHEN** the Agent performs a read call followed by a scene edit
- **THEN** the Web UI receives ordered tool lifecycle events and a separate plan/execution sequence using only JSON data

#### Scenario: Invalid capability request
- **WHEN** the runtime receives an unknown capability, malformed arguments, or an unsupported protocol version
- **THEN** it emits a structured error event and does not invoke a handler or mutate the scene

### Requirement: Compatibility and local-only boundary

Legacy helper names SHALL remain callable as aliases that normalize into the namespaced capability contract. Providers without native tool calling SHALL be able to return a pure JSON or fenced JSON `CommandPlan`. The capability layer SHALL not connect to external MCP servers or execute arbitrary code.

#### Scenario: Legacy alias
- **WHEN** an existing Skill calls `create_curve` or `create_tangent`
- **THEN** the alias produces the same validated namespaced plan and existing callers continue to work

#### Scenario: JSON fallback
- **WHEN** a provider cannot perform native tool calls but returns a valid structured plan
- **THEN** the runtime validates and executes it through the same capability and command pipeline
