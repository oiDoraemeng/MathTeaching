# Plan4 Task2 report: Qt/Web structured teaching payload

## Scope

Task2 extends the Qt explanation view and Web `math_case` bridge without exposing
compiled command plans, scene operation names, renderer objects, or unrestricted
expressions. The public payload remains JSON-safe and is built from the
published teaching artifact/explanation fields.

## Delivered

- `AgentSidebarWeb.show_math_case()` now publishes `topic_id`, `revision`, a
  bounded `source` object (`source_path`, `heading_path`, hash and anchor
  metadata), and a concise `source_diagnostic` object.
- A semantic `explanation` envelope exposes claims, formula, derivation,
  numeric examples, symbol roles, geometric meaning, misconception/pitfall
  notes, read guide and analogy boundary. Existing legacy fields remain for
  reducer compatibility.
- The Qt content view can render artifact provenance and stale-source
  diagnostics through `set_artifact()` / `set_source_context()`.
- Web `CaseProjection` and reducer parsing preserve the same topic/revision,
  source path/hash and diagnostic identity; `MathCaseView` renders the source
  path and diagnostic status.

## Verification

- `pytest tests/test_linear_algebra_dialog.py tests/test_agent_bridge.py -q`
  → **25 passed**.
- `npm --prefix ui/agent_web test -- --run MathCaseView.structured.test.tsx`
  → **6 passed**.
- `python -m py_compile ui/agent_sidebar_web.py ui/linear_algebra_content_view.py`
  → passed.
- Payload secrecy test asserts serialized payload contains no `operations`,
  `geometry.` operation names, or `renderer` data.

## Follow-up wiring

The existing `MainWindow` caller currently invokes `show_math_case()` without
passing `bundle.source_diagnostic`. The bridge API accepts the diagnostic and
the UI renders it; Task1/runtime wiring should pass
`source_diagnostic=bundle.source_diagnostic` when the bundle is committed.
