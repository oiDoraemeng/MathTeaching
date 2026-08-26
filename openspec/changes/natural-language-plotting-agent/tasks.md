## 1. Capability Contract

- [ ] 1.1 Define versioned capability metadata, categories, schemas, mutation flags, and 2D/3D scope; verify catalog serialization contract tests pass
- [ ] 1.2 Implement namespaced registry entries for scene inspection, lookup, editing, clearing, calculation, analysis, view control, export, and teaching explanation; verify every category is discoverable
- [ ] 1.3 Add legacy aliases for existing flat tool names and verify aliases produce equivalent validated plans

## 2. Tool Dispatch and Safety

- [ ] 2.1 Implement JSON-only argument validation and detached read results; verify malformed fields and unsafe expressions are rejected without scene mutation
- [ ] 2.2 Normalize mutating tool results into `CommandPlan` and route all execution through `SceneCommandService`; verify Qt/PyVista objects are never returned or called by tools
- [ ] 2.3 Add bounded multi-tool composition with repeated-call detection and per-turn call/operation limits; verify limit failures leave the scene unchanged

## 3. Runtime and Provider Integration

- [ ] 3.1 Inject the capability catalog into provider requests and parse native tool calls while preserving the JSON/fenced-plan fallback; verify both paths produce the same plan
- [ ] 3.2 Preserve Agent/Ask/Plan behavior for one combined plan, including approval tickets, duplicate approval rejection, stop invalidation, and transaction rollback; verify runtime integration tests pass
- [ ] 3.3 Emit ordered JSON-safe capability lifecycle events and persist only serializable summaries; verify event protocol tests reject credentials and renderer objects

## 4. Web UI Projection

- [ ] 4.1 Group registered capabilities in the Skills popover without requiring manual tool selection; verify all six categories render from the runtime catalog
- [ ] 4.2 Add tool lifecycle and composed-plan event cards to the timeline while retaining existing event ordering and hover actions; verify frontend reducer/component tests pass
- [ ] 4.3 Keep the bridge JSON-only and offline-compatible; verify build and bridge regression tests pass

## 5. Verification and Migration

- [ ] 5.1 Migrate built-in prompts and Skills to namespaced capability names while retaining aliases; verify existing math Skill tests and natural-language scenarios pass
- [ ] 5.2 Run the complete Python and frontend test suites plus OpenSpec validation; verify no existing runtime, persistence, renderer, or sidebar regressions
