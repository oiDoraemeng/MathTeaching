## ADDED Requirements

### Requirement: Dynamic native tool loop

For providers that support native function tools, the runtime SHALL send only the four core tools on the first request and rebuild each continuation catalog as core plus the current turn's active names. Each request SHALL contain at most four core and eight active definitions.

#### Scenario: Search enables the next request
- **WHEN** the model searches and the session atomically activates existing capabilities
- **THEN** the next provider request contains their full schemas plus the four core tools

#### Scenario: Active tools do not leak across turns
- **WHEN** a new user turn starts after a previous search
- **THEN** its first request contains core tools only

### Requirement: Offered schema snapshot

Before every provider request, the runtime SHALL freeze the offered-name set and registry metadata revision. Provider calls in that response SHALL be accepted only for names in that snapshot. Search changes SHALL affect only the next request.

#### Scenario: Same-batch stale call
- **WHEN** a response searches for a capability and also calls a capability whose schema was not offered in that request
- **THEN** the latter call returns `tool_not_activated` without invoking its handler

#### Scenario: Registry change is deferred
- **WHEN** a capability is registered or its schema changes during a turn
- **THEN** the frozen snapshot remains internally consistent and the change takes effect on a later turn, subject to real-time disable/cancel checks

### Requirement: Discovery-aware limits and termination

The runtime SHALL enforce at most eight total capability calls per turn (including search and describe), with sublimits of three searches and four mutation calls, and at most nine provider rounds, in addition to existing result, raw-operation, expanded-operation, duplicate-call and cancellation limits. Terminal limit, cancellation, timeout, scene-conflict and protocol errors SHALL discard staged operations and prevent final execution.

#### Scenario: Search loop is bounded
- **WHEN** the model repeats searches beyond the search budget
- **THEN** the runtime emits a serializable terminal limit error and makes no composed scene mutation

#### Scenario: Cancellation is transactional
- **WHEN** cancellation arrives after a successful staged capability call but before final execution
- **THEN** the staged operations are discarded and the renderer is not invoked

### Requirement: Provider compatibility

Only native function-tools providers SHALL use dynamic discovery. JSON/fenced `CommandPlan` providers SHALL retain their existing request/response protocol and SHALL not receive a fake `tool.search` interface. Existing provider transport fallback SHALL remain available.

#### Scenario: Legacy fallback remains unchanged
- **WHEN** a provider rejects native tools
- **THEN** the runtime follows the existing one-time structured plan fallback and records the sanitized fallback event

### Requirement: Discovery lifecycle events

The runtime SHALL reuse the existing lifecycle event envelope for discovery, description, invocation and rejection. Optional fields MAY include `phase`, `search_revision`, `activated_names`, offered count and bounded result metadata. Events SHALL not contain full schemas, internal paths, credentials, renderer objects, hidden reasoning or unsanitized long arguments.

#### Scenario: Ordered discovery trace
- **WHEN** a turn searches, activates and invokes an existing capability
- **THEN** the bridge receives ordered bounded events before the final plan event, while old consumers can still parse required fields
