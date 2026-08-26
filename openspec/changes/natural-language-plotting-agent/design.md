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
