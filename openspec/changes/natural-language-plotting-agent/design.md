## Context

The repository already contains `ToolRegistry`, `SceneCommandService`, `AgentRuntime`, mathematical Skills, serializable scene snapshots, and a JSON-only Web UI bridge. Existing tools are useful but are primarily flat helper names, and model responses currently center on a single `CommandPlan`. The new behavior must preserve the current validation and transaction boundary while allowing a model to discover and combine capabilities.

## Goals / Non-Goals

**Goals:**

- Make capabilities discoverable through stable names, descriptions, schemas, permissions, and scene scope.
- Separate read-only context tools from mutating plan-producing tools.
- Support multi-step natural-language requests while keeping one complete-plan approval boundary.
- Keep all scene mutation behind `CommandPlan -> SceneCommandService`.
- Provide serializable audit events and deterministic limits for tool use.
- Keep old tool names and structured JSON plan responses working.

**Non-Goals:**

- Executing model-generated Python or arbitrary shell commands.
- Exposing Qt, PyVista, filesystem handles, credentials, or renderer objects to a model or Web UI.
- Building a general-purpose coding Agent or connecting to external MCP servers.
- Replacing the existing renderer, persistence format, or visible Agent/Ask/Plan semantics.

## Decisions

### 1. Use a registry-backed capability contract

Each capability is registered with a namespaced name, category, description, JSON-compatible input schema, output kind, mutation flag, and supported scene modes. A registry is preferred over keyword parsing because providers can discover the same contract, the UI can group it, and tests can validate it independently. The registry remains a local Python boundary; it does not become an arbitrary plugin execution surface.

### 2. Keep mutation plan-only

Read tools return detached JSON data. Mutating tools return a `CommandPlan` (or a structured validation error) and never call a renderer. The runtime combines operations from one turn, validates the complete plan, and applies it exactly once through `SceneCommandService`. This preserves transaction, undo, approval, and snapshot behavior. Direct host callbacks and ad-hoc per-tool execution are rejected.

### 3. Namespace the first-party tools

The initial catalog uses `scene.inspect`, `scene.find`, `scene.edit`, `scene.clear`, `math.calculate`, `math.derive`, `view.control`, `result.export`, and `teaching.explain`. Existing names such as `create_curve` and `create_tangent` remain aliases that normalize into the namespaced contract. Namespaces are preferred over a flat list because they communicate responsibility and prevent collisions as the catalog grows.

### 4. Compose calls before approval

The model may make bounded read calls, then produce multiple mutating calls. The runtime normalizes those results into one `CommandPlan`, emits one preview/approval event, and uses the existing mode mapping: Agent executes automatically, Ask asks once, and Plan waits. A maximum tool-call count and operation count are enforced per turn; exceeding either produces a serializable error and no scene mutation.

### 5. Support native calls with a JSON fallback

Providers that support native tool calling receive the registry schemas and return structured calls. Providers without that feature continue to return pure JSON or a fenced JSON `CommandPlan`, which passes through the same validator. No provider is allowed to bypass local mathematical validation.

### 6. Treat events as the UI contract

Tool start, tool result, plan composition, validation, approval, execution, and error events contain only JSON-safe summaries. The Web UI renders categories and event cards from these events; it cannot invoke a tool handler directly. Sensitive values, full attachment contents, credentials, and renderer objects are excluded.

## Risks / Trade-offs

- [Model loops or tool spam] -> Enforce per-turn call and operation limits, detect repeated identical calls, and stop with an error event.
- [A malformed tool result could mutate the scene] -> Normalize and validate every operation again through `SceneCommandService` before execution.
- [Provider feature differences] -> Keep the structured JSON fallback and contract tests for both native and fallback paths.
- [A large scene may exceed context limits] -> Return bounded summaries and stable object identifiers from read tools.
- [Legacy Skills depend on flat names] -> Keep aliases and test that aliases produce the same plans as namespaced tools.

## Migration Plan

1. Add the capability registry and contract tests without changing existing tool behavior.
2. Add runtime orchestration, provider catalog injection, plan composition, limits, and lifecycle events.
3. Add Web UI grouping and event projection; keep the existing bridge and mode controls.
4. Migrate built-in Skills and prompts to namespaced names while retaining aliases.
5. Roll back by disabling catalog injection and UI projection; the existing single-plan JSON path remains usable.

## Open Questions

None. The capability categories, first-party tool names, execution semantics, and security boundary were approved during design review.

## Detailed Implementation Design

### Module boundaries

The existing `agent/tool_registry.py` becomes a compatibility facade rather than the place that owns every tool implementation. The capability system is split by responsibility:

| Module | Responsibility | Prohibited dependency |
|---|---|---|
| `agent/capabilities/contracts.py` | Versioned catalog records, invocation/result envelopes, normalized errors, and output-size limiting | Qt, PyVista, provider HTTP |
| `agent/capabilities/registry.py` | First-party registration, alias resolution, strict schema validation, and handler dispatch | Qt, PyVista |
| `agent/capabilities/scene_index.py` | Convert a `SceneSnapshot` into a detached object index and apply validated staged operations to that index | Renderer and persistence |
| `agent/capabilities/scene_tools.py` | `scene.*`, `view.control`, and `result.export` handlers | Direct host access |
| `agent/capabilities/math_tools.py` | `math.calculate`, `math.derive`, and `teaching.explain` handlers | Direct host access |
| `agent/capabilities/orchestrator.py` | Native tool-call loop, deterministic limits, plan composition, and lifecycle events | Qt and WebView objects |
| `agent/tool_registry.py` | Existing public imports and legacy flat-name aliases | New independent behavior |

`agent/runtime.py` owns one registry and one orchestrator per runtime. `agent/agent.py` chooses the native-tool path for a capable remote provider and keeps the deterministic Skill path only for local/rule-based fallback. `services/agent_provider.py` owns protocol-specific request and response conversion. `services/scene_commands.py` remains the only validator/executor of renderer operations. `ui/designer_window.py` supplies immutable snapshots and performs GUI-thread scene-fingerprint checks through the existing host proxy. The React application receives only catalog and event projections.

### Capability and result contracts

Catalog version 1 exposes exactly these canonical names: `scene.inspect`, `scene.find`, `scene.edit`, `scene.clear`, `math.calculate`, `math.derive`, `view.control`, `result.export`, and `teaching.explain`. Legacy aliases are accepted by local dispatch but are not advertised to remote models.

Each catalog entry serializes the following fields:

```json
{
  "catalog_version": 1,
  "name": "scene.edit",
  "category": "scene_edit",
  "description": "Create, update, or delete a supported mathematical object.",
  "scene_scope": "both",
  "mutating": true,
  "input_schema": {"type": "object", "additionalProperties": false},
  "result_kind": "plan"
}
```

The catalog is provider documentation, not a security boundary. Dispatch validates the same schema locally with `jsonschema` Draft 2020-12. All first-party schemas set `additionalProperties: false`, have bounded strings and arrays, and reject non-finite JSON numbers before a handler runs. The implementation adds `jsonschema>=4.23,<5` as a runtime dependency rather than hand-implementing a partial JSON Schema validator.

Each native invocation is normalized to `{call_id, name, arguments}`. A successful result is exactly one of `data`, `plan`, or `explanation`; an unsuccessful result is `{code, message, field?}` and has no plan. Internal exception text, stack traces, credentials, absolute attachment paths, and renderer values are never included. Event and model-visible values are recursively detached, string fields are capped at 512 characters, and collections are capped before serialization.

The concrete version-1 input boundary is:

- `scene.inspect` has no arguments. It returns a bounded scene summary, counts, camera summary, optional selected aliases, `truncated`, and `omitted_count`.
- `scene.find` accepts literal `alias`, `object_types`, and/or `expression_contains` filters. It does not accept regular expressions and returns at most 20 ordered summaries.
- `scene.edit` accepts one high-level `action` (`upsert`, `update`, or `delete`) and one supported object type (`point`, `point3d`, `vector`, `line`, `curve`, `surface`, or `annotation`). It converts those fields to existing white-listed operations; callers cannot submit a raw operation object.
- `scene.clear` accepts only `all`, `curves`, `surfaces`, `geometry`, or `annotations`. Scoped clear expands against the staged scene index; clearing an already empty scope returns an explicit no-op result.
- `math.calculate` accepts a scalar expression with no free symbols. It reuses a controlled algebra parser and never calls `sympy.sympify` directly on arbitrary tool input.
- `math.derive` accepts `derivative`, `tangent`, `integral_area`, or supported 3D `intersection`, plus an explicit `presentation` of `data` or `draw`. The drawing form produces a plan; the data form produces detached values. Two-dimensional intersection drawing is not in version 1.
- `view.control` supports only `set_mode` and `fit` in version 1. Arbitrary camera rotation, zoom, and visibility toggles are rejected as unsupported instead of being approximated.
- `result.export` supports only a PNG basename. The GUI resolves it below the application-managed `.math/exports/` directory; a path, absolute filename, non-PNG extension, reserved device name, or traversal segment is rejected.
- `teaching.explain` accepts a question plus bounded JSON-safe references to prior tool results and returns text only.

Machine aliases are ASCII identifiers (`[A-Za-z][A-Za-z0-9_-]{0,63}`) and are distinct from user-visible labels, which may contain Chinese text. Aliases are case-sensitive. An upsert of the same alias and type is normalized to the corresponding update operation; an alias already owned by a different type fails with `alias_conflict` rather than replacing or deleting another object.

### Snapshot, staged state, and plan composition

At turn creation the GUI captures one `SceneSnapshot`, serializes it canonically with `SceneSnapshot.to_json()`, and computes a SHA-256 scene fingerprint. The worker receives this immutable snapshot, not a live Qt or PyVista object. The capability context contains the snapshot, a selection list (empty when the host cannot provide selection), the fingerprint, and a `SceneIndex` created from snapshot curves, geometry, layers, annotations, 3D points, and metadata.

After each successful mutating tool result, the orchestrator validates its plan through `SceneCommandService.preview` and applies the returned `expanded_operations` to the detached `SceneIndex`. Later `scene.inspect` and `scene.find` calls see the staged index, marked as staged, while the rendered scene remains unchanged. Failed and no-op calls do not change staged state. This provides deterministic alias lookup and prevents a second call in the same turn from creating a conflicting object without requiring a renderer simulation.

`compose_command_plans()` accepts only version-1 plans with the same target scene. It flattens operations in tool-call order, rejects mixed 2D/3D mutation requests with `scene_conflict`, caps the raw count at 32 and expanded count at 128, and writes a concise deterministic summary. A composed plan has exactly one target scene. The command validator injects one leading `scene.set_mode` operation when the plan does not already begin with the target mode, for both 2D and 3D; it never inserts a duplicate. A request that genuinely needs a 2D mutation and a 3D mutation is split into separate turns.

The fingerprint is stored in the persisted turn validation record as `base_scene_fingerprint`; it is deliberately not a renderer operation or a model-controlled `CommandPlan` field. `SceneCommandService.execute()` gains an optional expected fingerprint parameter. When supplied, the scene host proxy synchronously asks the GUI thread to hash its current snapshot before beginning the transaction. A mismatch raises `scene_changed_since_plan`, records an error event, invalidates the approval ticket, and starts no transaction. This guard applies to automatic Agent execution and later Ask/Plan approval.

### Provider integration and tool-loop state machine

The provider boundary gains a structured `ProviderToolCall` result and tool-aware conversation items. `AgentMessage` is extended to represent an assistant tool-call message and a tool-result message without changing existing plain text callers. `OpenAICompatibleProvider` converts those items into the selected API protocol:

- Chat Completions uses function tool definitions, assistant `tool_calls`, and `tool` result messages carrying the matching call ID.
- Responses uses function definitions, `function_call` output items, and matching `function_call_output` input items.

Both request shapes set `parallel_tool_calls` to false. If a provider still returns several calls, the orchestrator dispatches them sequentially in response order, so each mutation observes the preceding staged state. The official Responses API documents function-call items with `call_id` and matching `function_call_output` items, and exposes `parallel_tool_calls`; this design follows that relationship. [OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)

The state machine is:

```text
captured -> requesting_model -> dispatching_tool -> requesting_model
         -> composing -> validating -> awaiting_approval -> executing -> completed
                                      \-> scene_conflict | rejected | stopped | failed
```

The initial and every continuation request include the same catalog. A recoverable tool error is sent back as a structured tool result so the model can correct it. The loop stops before dispatch, after every provider event, before composition, and before execution when the turn has been cancelled. The limits are fixed for catalog version 1: eight total calls, four mutating calls, 16 KiB arguments per call, 32 KiB serialized result per call, 32 raw operations, 128 expanded operations, 50 scene summaries from inspect, and 20 find results. A third identical normalized invocation fails with `tool_loop_detected`; limit and cancellation errors are terminal.

Providers that do not support native tools retain the existing single `CommandPlan` JSON/fenced-JSON fallback. The fallback uses the bounded legacy `SceneContext`, has the same final validation and fingerprint guard, and does not claim staged multi-tool read/modify behavior. A native-tool request rejected as unsupported is retried once through this JSON fallback with the same provider and emits a visible capability-fallback event; the runtime never switches model providers.

### Execution, persistence, and event projection

Read-only calls run in all three visible modes. When a turn has no mutating plan, it finishes as `answered` without a plan card. For a composed plan, Agent validates and executes with the fingerprint guard; Ask emits one approval request; Plan emits one pending preview. Only one persisted approval ticket exists per `(session_id, turn_id)`, and any stop, scene conflict, validation failure, or completed execution invalidates it.

The event order for a native turn is `session_started`, visible message deltas, zero or more `tool_started`/`tool_finished`, optional `plan_composed`, `plan_ready`, `validation_result`, then the mode-specific preview/approval/execution event, and exactly one `turn_finished`. Tool lifecycle payloads contain call ID, canonical capability name, category, mutation flag, sanitized argument summary, result kind, and structured error code when applicable. They do not contain hidden chain-of-thought, raw attachments, API keys, full model prompts, or renderer data.

The session snapshot adds a `capability_catalog` projection. `open_skills` returns that projection, and the React Skills popover groups the six approved categories without creating a manual tool-selection flow. The reducer treats a catalog replacement as a snapshot-style update and preserves existing session/timeline state. Tool events use distinct timeline cards with an expandable sanitized detail view; event sequencing, duplicate suppression, and offline local assets remain unchanged.

### Security and compatibility boundaries

The capability system is not an external MCP client and does not start a network listener. The existing `Math3DMCPServer` remains a local compatibility adapter, but Agent orchestration calls the registry directly and never calls its `execute=True` path. Existing Skill handlers and flat tool names remain supported through aliases while built-in prompts are migrated to canonical names.

The renderer-facing command validator stays authoritative. Capability handlers additionally perform semantic expression checks using the same controlled curve and surface parsers used by rendering, so an unsafe or malformed curve/surface is rejected before a plan is shown. Partial-scope clears and exports are resolved from the detached index and managed export root, respectively. Generic save, restore, arbitrary file reads/writes, camera manipulation, code execution, and external MCP access remain out of scope.
