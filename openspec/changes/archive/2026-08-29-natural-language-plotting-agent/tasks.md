## 1. Capability Contract

- [x] 1.1 Add capability contracts, catalog version 1, canonical names, categories, scene scopes, result envelopes, and bounded error codes in `agent/capabilities/contracts.py`; verify serialization and JSON-safe output tests pass
- [x] 1.2 Add strict Draft 2020-12 schema validation with bounded first-party argument schemas and dependency metadata; verify unknown fields, non-finite values, and oversized payloads fail before dispatch
- [x] 1.3 Implement canonical registry entries for scene inspection, lookup, editing, clearing, calculation, analysis, view control, export, and teaching explanation; verify every approved category is discoverable from the catalog
- [x] 1.4 Preserve legacy flat-name aliases in `agent/tool_registry.py` without advertising them to models; verify every supported alias produces the canonical plan or result

## 2. Tool Dispatch and Safety

- [x] 2.1 Build a snapshot-backed staged `SceneIndex` with alias/type lookup, bounded inspection/find results, and no selection fallback; verify reads never import or access renderer objects
- [x] 2.2 Implement high-level scene edit, scoped clear, view, and managed PNG export handlers; verify alias conflicts, empty scopes, unsafe filenames, unsupported views, and 2D/3D scope errors do not mutate the scene
- [x] 2.3 Implement calculation and derivation handlers using controlled existing curve/surface parsers instead of unrestricted SymPy input; verify unsafe expressions and unsupported two-dimensional intersections are rejected before a plan exists
- [x] 2.4 Normalize valid mutating results into plans, apply preview-expanded operations only to the staged index, and compose one target-scene plan; verify ordering, mixed-scene rejection, raw/expanded operation caps, and no renderer access
- [x] 2.5 Add per-turn call, mutation, argument/result-size, and repeated-invocation limits; verify every terminal limit failure leaves both staged commit and rendered scene unchanged

## 3. Runtime and Provider Integration

- [x] 3.1 Extend provider conversation records and OpenAI-compatible serializers for Chat Completions and Responses function calls plus matching results; verify call IDs, sequential call processing, and `parallel_tool_calls=false` payloads
- [x] 3.2 Inject the capability catalog into native provider requests, run the bounded continuation loop, and preserve the JSON/fenced-plan parsing on a streaming retry; verify unsupported-native-tool retry uses the same provider, streams incremental deltas, and emits a fallback event carrying the sanitized provider reason
- [x] 3.3 Carry the immutable start snapshot and SHA-256 fingerprint through workers, validation persistence, automatic execution, and approval; verify `scene_changed_since_plan` starts no transaction and invalidates the ticket
- [x] 3.4 Preserve Agent/Ask/Plan behavior for one combined plan, including no-plan answers, duplicate approval rejection, cancellation at every loop boundary, and rollback; verify runtime integration tests pass
- [x] 3.5 Emit and persist ordered, bounded, JSON-safe tool lifecycle and plan-composition events; verify one terminal event, credential redaction, and renderer-object rejection

## 4. Web UI Projection

- [x] 4.1 Project the versioned capability catalog in session snapshots and `open_skills` events, then group it in the Skills popover without manual selection; verify all six categories and canonical names render locally
- [x] 4.2 Add tool lifecycle, capability fallback, composed-plan, and scene-conflict cards to the timeline while retaining existing event ordering and hover actions; verify frontend reducer/component tests pass
- [x] 4.3 Extend bridge event validation and TypeScript event types for the new JSON-only event contract; verify invalid payloads, duplicate sequences, and offline production build behavior

## 5. Verification and Migration

- [x] 5.1 Migrate built-in prompts and local Skill fallback metadata to canonical capability names while retaining aliases; verify existing math Skill tests and natural-language scenarios pass
- [x] 5.2 Add end-to-end fixtures for inspect-then-edit, derivative/tangent, surface creation, scoped clear, export path rejection, provider fallback, stale plan, cancellation, and 2D/3D conflict scenarios
- [x] 5.3 Run the complete Python and frontend test suites plus strict OpenSpec validation; verify no existing runtime, persistence, renderer, bridge, or sidebar regressions
