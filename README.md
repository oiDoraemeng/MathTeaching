# Math3D Teaching

An interactive PySide6 and PyVista teaching application for a two-sheet hyperboloid.

## Run

```powershell
uv sync
uv run python main.py
```

The left panel changes `a`, `b`, and `c` in real time. The 3D viewport supports rotation, zoom, and pan.

## Edit the UI

The interface layout is stored in `ui/main_window.ui`. Open that file with Qt Designer,
save it, then run the application again. `ui/designer_window.py` loads the Designer form
at runtime and contains only scene wiring and interaction behavior.
