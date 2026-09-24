# Agent Tool Discovery: Deep Technical Design

## Goal

Let the Agent work with a capability registry that may grow to hundreds of entries without sending the entire registry to the model. Discovery must be explicit, bounded, deterministic, auditable, and compatible with the existing scene command transaction boundary.

This design is Stage 1 only. Stage 2 adds semantic `draw.2d.*` and `draw.3d.*` capabilities. Stage 3 unifies Agent-callable toolbar actions through a `ToolIntent` contract and may add a Skills explorer. Neither later stage is part of this change.

## Current System

- `CapabilitySpec` already describes canonical name, category, description, input schema, result kind, scene scope, mutation behavior, aliases, catalog version, and dependencies.
- `CapabilityRegistry` validates and dispatches the current nine canonical capabilities.
- `CapabilitySession` owns the staged `SceneIndex`, tool results, composed operations, scene scope, and existing budgets.
- `AgentRuntime._native_turn` currently obtains the full registry catalog and sends it on each native provider request.
- `SceneCommandService.preview` and the final command execution path are the authoritative validation and mutation boundary.
- A non-native provider can use the existing JSON/fenced `CommandPlan` path; that path does not support iterative native tool discovery.

## Architecture

```text
CapabilitySpec registry
    | immutable per-turn metadata/schema snapshot
    v
tool.search (core) -- pure retrieval --> candidates
    | session validates and atomically replaces active set
    v
next provider request: four core tools + active full schemas
    | only names in this request's frozen offered snapshot are callable
    v
existing capability handler -> preview -> staged SceneIndex
    | normal session finish only
    v
one CommandPlan -> existing approval/execution boundary
```

The registry remains the source of truth. Search is not a second registry, and there is no generic `tool.invoke(name, arguments)` escape hatch. The model decides when to search and which returned capability to call; Python does not pre-retrieve a guessed tool before the provider request.

## Metadata Contract

Extend `CapabilitySpec` with:

| Field | Type / values | Default |
|---|---|---|
| `family` | bounded stable string; initial families: scene, math, view, export, teaching, general | `general` |
| `title` | short display title | canonical name |
| `tags` | tuple of bounded search tokens | empty |
| `examples` | tuple of short natural-language phrases | empty |
| `exposure` | `core`, `discoverable`, `internal` | `discoverable` |
| `status` | `stable`, `experimental`, `deprecated`, `disabled` | `stable` |
| `schema_version` | positive integer | `1` |

Existing canonical name, aliases, category, input schema, result kind, mutation flag, scene scope, and catalog version remain compatible. Catalog version remains 1 for this additive metadata. Metadata is not added to provider function arguments: provider adapters continue to receive only name, description, and input schema.

Stage 1 classification:

| Exposure | Capabilities |
|---|---|
| Core, always offered | `tool.search`, `tool.describe`, `scene.inspect`, `scene.find` |
| Discoverable, offered only after search | `scene.edit`, `scene.clear`, `math.calculate`, `math.derive`, `view.control`, `result.export`, `teaching.explain` |
| Internal, never offered | renderer operations and implementation-only handlers |

There are no `draw.*` entries in Stage 1. In particular, `scene.edit` remains an existing bounded capability, not permission to expose renderer operations or invent unsupported semantic tools.

## Search API

`tool.search` accepts a strict object:

```json
{
  "query": "求导并标出切线",
  "scene": "2d",
  "family": "math",
  "tags": ["derivative"],
  "limit": 6,
  "include_experimental": false
}
```

Constraints:

- `query` is required, trimmed, 1-512 characters.
- `scene` is optional and is one of `2d` or `3d`.
- `family` is optional and at most 32 characters.
- `tags` is optional, with at most 8 entries and at most 32 characters per entry.
- `limit` defaults to 6 and is clamped/rejected above the hard maximum of 8. Invalid values are errors, not silently rewritten.
- `include_experimental` defaults to false. It must be explicitly true to return experimental capabilities.
- If `scene` is omitted, current session scene scope is used. An explicitly incompatible scene returns `scene_scope_mismatch`.

A match is compact and does not carry schema:

```json
{
  "name": "math.derive",
  "title": "求导与切线",
  "score": 0.93,
  "reasons": ["同义词匹配：切线", "场景匹配：2D"],
  "scene_scope": "2d",
  "status": "stable"
}
```

The result contains `status` (`ok` or `no_match`), `matches`, `near_misses` (at most 3, never activated), `activated_names`, `search_revision`, and a short `limitation` when needed. A valid no-match is a normal bounded tool result with `status=no_match`; it clears the previous active set. `no_capability_match` is a stable domain code for the limitation, not a transport/handler exception. Invalid requests use `CapabilityResult.error` and preserve the previous active set.

Search errors use stable codes: `invalid_search_query`, `scene_scope_mismatch`, `experimental_capability_unavailable`, and `search_limit_exceeded`. No results must never trigger a fallback to guessed renderer operations or a universal `scene.edit` call.

## Retrieval Algorithm

The first implementation uses deterministic local lexical retrieval. It does not call an embedding API, network service, or external database.

An immutable index snapshot is built lazily from name, title, aliases, family, tags, description, examples, scene scope, and status. Registering a capability marks the index dirty; rebuilding swaps the complete index atomically. A simple O(N) candidate scan is acceptable for a 500-entry catalog and avoids premature indexing complexity.

Chinese synonym expansion lives in `agent/capabilities/search_terms.py`, independent of individual handlers. Initial synonym groups cover curve/function, tangent/derivative, projection, surface/intersection, view/fit, export, and explain/teaching. Canonical English names and aliases remain searchable.

Deterministic base weights:

| Match source | Weight |
|---|---:|
| Canonical name | 100 |
| Alias | 80 |
| Tag or synonym | 60 |
| Title | 40 |
| Description | 20 |
| Example | 10 |
| Exact scene scope | +15 |
| `both` scene scope | +5 |

Tie-break by canonical name. Scores may be normalized for presentation within one result set, but ranking uses the stable unnormalized score. Return at most three short reasons per candidate, each at most 64 characters. Stable tools are eligible by default; experimental tools only when explicitly opted in; deprecated and disabled tools are never returned as callable matches. A near miss is explanatory only and does not enter the active set.

## Session State and Atomic Activation

`CapabilitySession` gains:

- `active_names: tuple[str, ...]`, initially empty and capped at 8.
- `search_revision`, incremented only when a valid search commits a replacement.
- `search_count`, capped at 3 per turn.
- An immutable capability metadata/schema snapshot captured at turn start.
- The frozen `offered_names` and offered schema revision for the most recent provider request.

The search handler is pure: it reads the session's registry snapshot and returns candidates. After the handler returns, the session validates each candidate against the snapshot, exposure, lifecycle status, scene scope, and activation cap. Only then does it atomically replace the active set and advance the revision.

| Search outcome | Active set | Revision |
|---|---|---|
| Valid search with matches | Replace with eligible match names | Increment |
| Valid search with no matches | Clear | Increment |
| Invalid arguments / limit / index failure | Preserve | Unchanged |
| Candidate validation failure | Preserve; return error | Unchanged |

The newest search replaces rather than accumulates. If the model needs a previously active capability, it searches again. `tool.describe` is read-only, can describe only a current active name, and cannot enumerate or activate capabilities. It returns name, title, description, family, scene scope, status, schema version, input schema, and examples; it never returns handler paths, dependencies, raw atomic operations, credentials, or internal exceptions.

Active names are ephemeral and never persisted across user turns. The requested scene defaults to the current session scene. A scene switch requires an activated `view.control`; following a successful switch, the model must search again under the new scope.

## Provider Request Consistency

At turn start, capture an immutable registry metadata/schema snapshot. For each provider request, construct and freeze:

```text
offered_names = core_names + active_names
offered_schemas = schemas resolved from the turn snapshot
offered_registry_revision = turn snapshot revision
```

All calls returned in a provider response are checked against that request's `offered_names` before dispatch. A `tool.search` call may replace the session active set, but the change affects only the next provider request. Therefore, a response batch that searches and also calls a newly discovered tool is rejected with `tool_not_activated`: the model had not yet seen that tool's schema.

Registration, removal, or schema changes during a turn take effect next turn, avoiding mismatches between search metadata, descriptions, and schemas. Execution still performs live safety gates for emergency disable, scene scope, execution mode, and cancellation. A capability that fails a live gate is rejected before its handler, and no newer schema is guessed or substituted.

## Runtime Loop and Budgets

Only native function-tools providers use discovery:

1. First provider request receives exactly four core definitions.
2. The model may search; the session validates and atomically commits activation.
3. The next request receives four core definitions plus up to eight active schemas.
4. Activated existing tools are dispatched sequentially through the current capability handlers and staged scene.
5. A normal finish composes at most one `CommandPlan` through the existing Agent/Ask/Plan boundary.

The runtime freezes the offer snapshot before every request and preserves current provider call/result serialization. The system prompt must stop enumerating low-level renderer operation names and state only that the model may call tools supplied in the current request.

Budget contract: at most 8 total capability calls per turn (including search and describe); search is further capped at 3; mutation calls are capped at 4; provider requests are capped at 9. Existing argument/result size, raw operation, expanded operation, duplicate-call, scene conflict, and cancellation limits remain in force. At most 4 core plus 8 active schemas are sent in one request.

For non-native providers, preserve the existing JSON/fenced `CommandPlan` fallback. Do not advertise a synthetic `tool.search`, do not claim iterative discovery, and do not change provider/model selection. Native transport rejection follows only the existing sanitized fallback path.

## Safety, Failure, and Commit Semantics

- Unknown, inactive, disabled, deprecated, experimental without opt-in, schema-changed, invalid-argument, and out-of-scope calls return stable bounded errors before handler execution.
- Recoverable tool errors return as tool results if budget remains. Search no-match is not a guessed invocation; the model asks a clarification or provides an explanation.
- Every mutating plan passes `SceneCommandService.preview` before entering staged `SceneIndex`. A failed preview stages nothing.
- Mutating operations from multiple successful calls remain staged until normal session finish; only one final plan is produced.
- Limit, cancellation, timeout, cross-scene conflict, and protocol errors are terminal. They discard staged operations and do not invoke final `finish()` or renderer execution.
- Only a normally completed, validated session reaches the existing execution/approval boundary. Existing scene fingerprint checks, undo, and rollback remain authoritative.

Search and event bounds: query at most 512 characters; matches at most 6 by default and 8 hard maximum; near misses at most 3; reasons at most 3 per candidate and 64 characters each. Events contain only canonical names, phase, revision, activated names, bounded summaries, status, stable error code, and offered count. Never include full schemas in lifecycle events, raw long arguments, file paths, credentials, renderer objects, stack traces, attachments, or hidden reasoning.

## Data and Event Changes

Keep the existing event envelope and required fields. Optional additions:

- `phase`: `discover | describe | invoke`
- `search_revision`
- `activated_names`
- `offered_tool_count`
- `result_kind`: allow `search` and `description` in addition to existing kinds

The validator must continue accepting older events without these optional fields. Search query summaries are truncated and sanitized. `build_session_snapshot()` may continue to project a serializable complete local catalog for a future Skills UI, but it must not be reused as the provider catalog.

Per-turn telemetry records offered tool count, search count, active count, bounded result size, and terminal reason. It must not persist original query or arguments beyond the existing ephemeral tool transcript policy.

## Rejected Designs

- Pre-retrieval in Python before the model request hides intent selection in heuristics and prevents in-turn query refinement.
- Generic `tool.invoke(name, arguments)` removes per-tool schemas and weakens provider validation.
- Full-catalog requests scale token use and selection ambiguity with registry size.
- Paged catalogs force the model to manage directory state and can make it choose a page rather than a capability.
- Semantic drawing, toolbar migration, and Skills UI in this first change would couple discovery infrastructure to several independent regression surfaces.
- Remote vector search is not justified until deterministic local retrieval fixtures show a measurable recall gap.

## Verification Plan

### Retrieval

- Canonical name, alias, Chinese synonyms, tag/family filters, exact/both scene boosts, deterministic ties, stable-only defaults, experimental opt-in, deprecated/disabled filtering.
- Query boundaries 0/1/512/513; result limits 1/6/8/9; near-miss and reason truncation.
- Fixtures for function, tangent, 3D view switch, PNG export, projection explanation, and an unsupported 3D surface request in Stage 1.
- A synthetic 500-capability registry remains local and bounded; record latency without introducing a brittle microbenchmark threshold initially.

### Protocol and Session

- Strict search and describe schemas; output bounds; search revision behavior.
- Match replacement, valid no-match clearing, invalid search preservation, and active cap.
- Describe active succeeds; describe inactive cannot enumerate or activate.
- Same-batch newly discovered call is rejected; subsequent request can call it.
- Registry snapshot stays stable through the turn; emergency disable and cancellation still gate execution.

### Runtime and Safety

- Fake native provider sees four initial tools and only core-plus-active thereafter.
- Eight total calls, three searches, four mutations, nine requests, and per-result/per-plan limits stop at exact boundaries.
- `scene.edit` and `math.derive` search-activate-call succeed through preview/staging; invalid plan never partially stages.
- Cancellation, timeout, scene conflict, terminal protocol error, and budget exhaustion discard staged operations.
- Search no-match never guesses a universal edit tool or low-level renderer operation.

### Compatibility

- JSON/fenced non-native path receives no search tool and remains unchanged.
- Existing Agent/Ask/Plan approval/execution semantics and legacy aliases remain intact.
- Existing bridge validators accept events with and without optional discovery fields.
- Run focused Agent/capability/scene/bridge tests, full Python tests, compile checks, and strict OpenSpec validation.
