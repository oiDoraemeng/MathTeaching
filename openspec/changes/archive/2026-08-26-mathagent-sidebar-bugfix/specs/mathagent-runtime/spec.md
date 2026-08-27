## MODIFIED Requirements

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
