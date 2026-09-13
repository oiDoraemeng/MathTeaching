# Task 7 current review

## Verdict

**Approved** for the requested Task 7 final-fix checks.

## Revision and evidence

- Reviewed revision: `2e1c16e3c076271c6aa7489228334869f5fd3381` (`fix: gate constraint scene commands with shared budgets`).
- Exact command run from `D:\github\Math3DTeaching`:

  `pytest tests/test_linear_algebra_constraint_family.py tests/test_geometry_2d.py tests/test_geometry_3d_scene.py tests/test_agent_runtime.py -q`

- Result: **32 passed, 2 warnings** (both the existing Paramiko/TripleDES deprecation warnings).

## Code/evidence review

- `SceneCommandService.validate` is the shared validation entry point and invokes `_validate_operation` for every operation and expanded operation ([services/scene_commands.py:204](services/scene_commands.py:204), [services/scene_commands.py:213](services/scene_commands.py:221)).
- `geometry.constraint` validates matrix/rhs shape, solution state, rank evidence, and bounds before budget evaluation ([services/scene_commands.py:491](services/scene_commands.py:509)).
- It calls the shared `validate_budget("lecture-v1", ...)` and returns an explicit `constraint render_budget` error when over budget ([services/scene_commands.py:510](services/scene_commands.py:517)). This covers the valid 3D over-budget branch, exercised by `test_scene_command_service_3d_constraint_budget_reports_budget_error` ([tests/test_linear_algebra_constraint_family.py:46](tests/test_linear_algebra_constraint_family.py:50)).

`task-7-report.md` describes the algebra-pane label work and is not evidence for these constraint-budget checks. `task-7-review-fix3-package.md` was not present in the current workspace, so no claims are made about that missing artifact.
