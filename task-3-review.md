# Task 3 review

Commit reviewed: `92ef86c` (`feat: connect extended linear algebra plan replay`)

## Spec Compliance

**Needs fixes.** The commit adds all currently listed extended operation names to `SceneCommandService.allowed_operations` and adds validation branches for the new operation families (`services/scene_commands.py:92-147`, `services/scene_commands.py:530-762`). It also adds a transaction rollback regression test (`tests/test_linear_algebra_extended_plan_replay.py:21-33`).

However, the required replay adapter/registry contract is not implemented. `replay_extended_plan` merely constructs a new service and calls `execute`; it does not provide or consult a replay registry (`services/scene_commands.py:791-793`). The coverage test intended to prove replay coverage instead repeats the same allowed-operation assertion twice and never checks an adapter (`tests/test_linear_algebra_extended_plan_replay.py:6-12`). Thus operation registration is covered, but validator/replay parity is not.

The requested exact schema behavior is also not demonstrated by the added tests: there are no assertions for unknown fields, unknown roles, non-finite values, bounds/count limits, or scene mismatch. The implementation contains partial family validation, but this review cannot mark the contract complete without executable coverage.

## Strengths

- Extended operation names are present in the service allow-list, including the quadratic level-set operation (`services/scene_commands.py:127-146`).
- New operation validation checks finite numeric data and dimensional/budget constraints in several families, including quadratic geometry (`services/scene_commands.py:734-762`).
- The regression test confirms that an exception during a later operation does not commit earlier pending operations (`tests/test_linear_algebra_extended_plan_replay.py:21-33`).
- Focused test command executed: `python -m pytest tests/test_linear_algebra_extended_plan_replay.py -q` → **2 passed**. This is not the requested **19 passed** verification.

## Issues

1. **P1 — Replay parity is unimplemented/unverified.** The plan calls for `replay_registry.has(op)` and deterministic offline/host parity, but no registry exists and `replay_extended_plan` is only an alias for normal execution (`services/scene_commands.py:791-793`). Add explicit adapters/registry coverage for every primitive operation and test that each registered op can replay.
2. **P1 — The coverage test has a duplicated assertion.** `assert op in service.allowed_operations` appears twice and provides no replay assertion (`tests/test_linear_algebra_extended_plan_replay.py:8-10`). Replace the duplicate with the required registry check.
3. **P1 — Required 19-test evidence is absent.** The committed test module contains only two tests and the focused run reports 2 passed, not 19. Add the missing schema, replay, host-dispatch, parity, and rollback cases and record the 19-test run.
4. **P2 — Strict schema contract lacks regression coverage.** Unknown keys/roles, NaN/Inf, excessive samples/entities, and scene/dimension mismatch need explicit failure tests before claiming compliance with task 3.8.

## Assessment

**Needs fixes.** The commit is a useful partial integration: allow-list coverage and one rollback path are present, but the central replay-registry/parity requirement and the requested 19-passed verification are not satisfied. Re-review after adding the registry/adapters, replacing the duplicated assertion, and supplying the complete focused test evidence.
