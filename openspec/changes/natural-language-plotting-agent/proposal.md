## Why

Math3D Teaching already has a safe `CommandPlan` pipeline and several mathematical tools, but the Agent does not present them as a coherent, discoverable capability system. Users should be able to describe a task naturally and have the Agent select and combine scene reading, editing, analysis, view control, result export, and teaching capabilities like an IDE Agent selects tools.

## What Changes

- Add a versioned, registry-backed capability catalog grouped by mathematical responsibility.
- Add read-only scene inspection and object lookup capabilities that return JSON-safe context.
- Add unified scene editing, clearing, view control, and result export capabilities that return validated `CommandPlan` objects.
- Add mathematical analysis capabilities for safe calculation, derivatives, tangents, integral areas, intersections, and related teaching demonstrations.
- Add teaching explanation capability that can consume scene and calculation results without mutating the scene.
- Allow the Agent to compose multiple tool calls into one complete plan with one approval boundary.
- Emit serializable tool lifecycle events for the Web UI and expose grouped capabilities in the Skills popover.
- Preserve legacy tool names as compatibility aliases and retain the JSON plan fallback for providers without native tool calling.
- Reject arbitrary code execution, direct renderer access, external MCP calls, and unbounded tool loops.

## Capabilities

### New Capabilities

- `mathagent-capabilities`: Registry-backed, categorized tools for natural-language scene interaction and mathematical teaching.

### Modified Capabilities

None. Existing runtime and sidebar requirements remain authoritative; this change adds a capability contract consumed by them.

## Impact

- Python Agent layer: capability metadata, dispatch, validation, plan composition, and compatibility aliases.
- Runtime/provider boundary: tool catalog injection, native tool-call parsing, JSON fallback, loop limits, and tool lifecycle events.
- Scene integration: reuse `SceneCommandService`, `SceneSnapshot`, and existing renderer host adapters without exposing Qt/PyVista.
- Web UI: grouped Skills/tool presentation and rendering of tool lifecycle events.
- Tests: registry contracts, safe dispatch, plan composition, mode semantics, event serialization, and UI projection regression coverage.
