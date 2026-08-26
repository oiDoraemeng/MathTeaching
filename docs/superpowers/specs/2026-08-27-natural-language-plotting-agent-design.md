# Natural-Language Plotting Agent Design

## Decision

Math3D Teaching will use a registry-backed capability layer, similar to an IDE Agent tool catalog. The Math Teacher Agent will select capabilities from six groups: scene reading, scene editing, mathematical analysis, view control, result export, and teaching explanation.

## Contract

Read-only capabilities return detached JSON. Mutating capabilities return validated `CommandPlan` data and never access Qt or PyVista. The runtime combines multiple calls into one plan, validates it once, and preserves Agent/Ask/Plan execution semantics. Legacy flat tool names remain aliases.

## User-visible behavior

A natural-language request can combine operations such as inspecting the current scene, calculating a vertex, drawing a curve, adding an annotation, and fitting the view. The timeline shows capability lifecycle events, one combined plan, and the resulting approval or execution state. The Skills popover groups capabilities but does not require manual selection.

## Boundaries

The first release is local and math-only. It excludes arbitrary code, shell commands, external MCP servers, direct renderer handles, credentials, and unbounded tool loops. Providers without native tool calling continue to use the existing structured JSON plan fallback.

## Validation

The implementation must cover registry contracts, safe dispatch, 2D/3D scope checks, multi-tool composition, mode-specific approval, event serialization, aliases, JSON fallback, Web UI projection, and full regression suites.
