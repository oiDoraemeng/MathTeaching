## ADDED Requirements

### Requirement: Capability metadata and exposure

Every registered capability SHALL expose stable `name`, `family`, `title`, `tags`, `examples`, `scene_scope`, `status`, `exposure`, `schema_version`, input schema, result kind, mutation flag and catalog version. Only `core` and eligible `discoverable` capabilities SHALL appear in model-facing catalogs; `internal` renderer operations SHALL never appear.

#### Scenario: Existing capability receives defaults
- **WHEN** a legacy capability is registered without the new optional metadata
- **THEN** the registry assigns deterministic defaults (`family=general`, `status=stable`, `exposure=discoverable`, `schema_version=1`) without changing its canonical name or input schema

#### Scenario: Internal operation is hidden
- **WHEN** a low-level renderer operation is registered for command execution
- **THEN** it is absent from every provider catalog and can only be produced by a validated handler/plan

### Requirement: Fixed core catalog

The registry SHALL classify exactly `tool.search`, `tool.describe`, `scene.inspect` and `scene.find` as core for the Stage 1 native discovery protocol. Existing user-facing capabilities SHALL remain discoverable unless their lifecycle status or scope excludes them.

#### Scenario: Large registry remains bounded
- **WHEN** a native turn starts with hundreds of registered capabilities
- **THEN** the initial provider catalog contains only the four core capabilities

### Requirement: Deterministic capability search

`tool.search` SHALL accept a bounded natural-language query and optional scene, family, tags, limit and experimental opt-in. It SHALL return at most eight compact ranked matches (default six), at most three near misses, stable relevance reasons, and a search revision. Search SHALL use deterministic local metadata and synonym matching, not require a network service, and SHALL not return full schemas.

#### Scenario: Search ranks a known existing capability
- **WHEN** the Agent searches for derivative or tangent work in a 2D scene
- **THEN** `math.derive` is returned with a stable score/reason and an activation name

#### Scenario: No match is explicit
- **WHEN** no eligible capability matches the query
- **THEN** the result has no matches, may include bounded near misses, includes a limitation, and does not activate a guessed tool

#### Scenario: Experimental tools require opt-in
- **WHEN** a matching capability is experimental and `include_experimental` is false
- **THEN** it is omitted or reported as unavailable and is not activated

### Requirement: Search is atomic activation

A successful search SHALL atomically replace the session active set with validated eligible match names. A valid no-match SHALL clear the active set. Invalid search input, index failure or activation validation failure SHALL preserve the previous active set. The active set SHALL be turn-scoped and capped at eight names.

#### Scenario: Latest search replaces old tools
- **WHEN** the Agent searches for export after previously activating derivative tools
- **THEN** the active set contains only the eligible export matches; derivative tools require a new search

#### Scenario: Failed search preserves state
- **WHEN** a search request violates a query or limit constraint
- **THEN** the previous active set and search revision remain unchanged

### Requirement: Description permission

`tool.describe` SHALL return full schema/examples only for a name in the current active set. It SHALL not enumerate arbitrary registry entries, activate a capability, reveal internal handler data or return raw renderer operations.

#### Scenario: Description of active capability
- **WHEN** the Agent describes an activated capability
- **THEN** it receives name, title, description, family, scene scope, lifecycle status, schema version, input schema and examples

#### Scenario: Description bypass is rejected
- **WHEN** the Agent describes a discoverable name that is not active
- **THEN** it receives `tool_not_activated` and the active set is unchanged

### Requirement: Discovery-aware dispatch

The dispatcher SHALL reject calls to unactivated, disabled, deprecated, experimental-without-opt-in, unknown or scene-incompatible capabilities before invoking a handler. Rejections SHALL use bounded stable errors and SHALL not stage plans or mutate the scene.

#### Scenario: Direct guessed call
- **WHEN** a model calls a discoverable capability before searching
- **THEN** dispatch returns `tool_not_activated` and invokes no handler

#### Scenario: Scope mismatch
- **WHEN** a 2D session calls an eligible 3D-only capability
- **THEN** dispatch returns `scene_scope_mismatch` and leaves staged state unchanged

### Requirement: Existing plan boundary remains authoritative

Existing capability handlers SHALL continue to return data, explanation, no-op or validated `CommandPlan` results. Mutating plans SHALL pass `SceneCommandService.preview` before entering `SceneIndex`; low-level command names SHALL not become model tools.

#### Scenario: Existing capability remains usable
- **WHEN** an activated `scene.edit` or `math.derive` call has valid arguments
- **THEN** the result follows the existing plan/data contract and later staged reads observe only the validated staged representation
