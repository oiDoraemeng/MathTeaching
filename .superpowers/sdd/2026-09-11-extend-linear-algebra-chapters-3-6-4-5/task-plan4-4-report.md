# Plan4 Task4 report: single toolbar and legacy chapter compatibility

## Scope

Task4 protects the existing `TwoDGeometryToolbar` as the only geometry/
linear-algebra toolbar. It is created during viewport initialization, remains
visible independently of the selected lecture chapter, and is now anchored
horizontally at `(12, 12)` in the viewport's top-left corner. Chapter 4--8
selection only changes the teaching bundle/pane; it does not create, move,
retint, or replace the toolbar controls or their window-level shortcuts.

## Delivered

- Restored the established top-left horizontal toolbar layout in
  `ui/two_d_tools.py`; `set_linear_algebra_mode()` is retained as a no-op
  compatibility hook and cannot create a second toolbar.
- Added a frozen Chapter 1--3 regression fixture containing all 54 legacy
  topic IDs and their published plan digests. Each legacy plan still begins
  with `scene.clear`, ends with `view.fit`, and validates through the command
  service.
- Added an integration regression that loads representative Chapter 4 and
  Chapter 8 topics and compares the toolbar instance, position, layout,
  button identity/action metadata, and undo/redo/copy/paste shortcut contract
  before and after each load.
- Updated the existing toolbar/overlay tests to assert the top-left horizontal
  anchor and the single-toolbar contract.

## Verification

```text
pytest tests/test_2d_geometry_toolbar.py tests/test_overlay_corners.py \
  tests/test_linear_algebra_loading.py tests/test_designer_window_toolbar.py \
  tests/test_linear_algebra_chapters_1_3_regression.py -q
→ 86 passed, 2 warnings
```

The warnings are the existing Paramiko TripleDES deprecation notices. The
viewport tests also exercise the offscreen VTK setup; no test failure or
toolbar mutation is associated with those renderer warnings.

## Out of scope

The working tree contains unrelated `ui/designer_window.py` changes from the
storyboard/runtime tasks. They were intentionally not staged by this task.
