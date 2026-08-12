# MathInputWidget

`MathInputWidget` is a reusable PySide6 component for MathLive formula entry.
It hosts a local MathLive Web Component in `QWebEngineView` and exposes LaTeX to
Python without coupling callers to the application window or rendering layer.

```python
from MathInputWidget import LatexParser, MathInputWidget
from MathInputWidget.api import FormulaVisualizer

editor = MathInputWidget()
editor.set_latex(r"\frac{x^2}{a^2}+y^2=1")
editor.latexChanged.connect(print)

formula = LatexParser().parse(editor.get_latex(), "implicit")
mesh = FormulaVisualizer().build_mesh(formula.expression, plot_domain)
```

`get_latex()` returns a cached value so it remains synchronous despite the
asynchronous browser bridge. Renderable formulas currently support explicit and
implicit surfaces plus parameterized coordinate triples with `u`/`v` ranges.
Integrals, sums, limits and matrices are rejected with a clear error before
reaching the mesh builder.

MathLive 0.110.0 and required fonts are bundled locally under this package so
desktop use does not depend on a network connection. MathLive is distributed
under its own license; see the upstream package for details.
