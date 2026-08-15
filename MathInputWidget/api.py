"""供 MathInputWidget 调用的独立 SymPy 到 PyVista 转换桥接层。"""

from __future__ import annotations

import sympy as sp


class FormulaVisualizer:
    """复用 CAS 采样逻辑，将 SymPy 表达式转换为 PyVista 网格。"""

    def build_mesh(
        self,
        formula: sp.Expr | sp.Equality,
        domain,
        parameters: dict[str, float] | None = None,
    ):
        from geometry.cas_surface import build_surface_mesh

        expression = self._surface_expression(formula)
        resolved_parameters = {name: 1.0 for name in expression.parameter_names}
        resolved_parameters.update(parameters or {})
        return build_surface_mesh(expression, resolved_parameters, domain)

    @staticmethod
    def _surface_expression(formula: sp.Expr | sp.Equality):
        from geometry.cas_surface import SurfaceExpression

        formula = FormulaVisualizer._real_coordinates(formula)
        if isinstance(formula, sp.Equality):
            left, right = sp.simplify(formula.lhs), sp.simplify(formula.rhs)
            if isinstance(left, sp.Symbol) and left.name in {"x", "y", "z"}:
                return FormulaVisualizer._explicit(left.name, right)
            if isinstance(right, sp.Symbol) and right.name in {"x", "y", "z"}:
                return FormulaVisualizer._explicit(right.name, left)
            formula = left - right
        expression = sp.simplify(formula)
        parameters = FormulaVisualizer._parameter_names(expression)
        return SurfaceExpression("implicit", sp.sstr(expression), expression, parameters)

    @staticmethod
    def _explicit(dependent_axis: str, expression: sp.Expr):
        from geometry.cas_surface import SurfaceExpression

        expression = sp.simplify(expression)
        return SurfaceExpression(
            "explicit",
            f"{dependent_axis} = {sp.sstr(expression)}",
            expression,
            FormulaVisualizer._parameter_names(expression),
            dependent_axis,
        )

    @staticmethod
    def _parameter_names(expression: sp.Expr) -> tuple[str, ...]:
        return tuple(sorted(str(symbol) for symbol in expression.free_symbols if str(symbol) not in {"x", "y", "z"}))

    @staticmethod
    def _real_coordinates(formula: sp.Expr | sp.Equality) -> sp.Expr | sp.Equality:
        """将普通 SymPy 的 x/y/z 符号统一为渲染器使用的实数符号。"""
        replacements = {
            symbol: sp.Symbol(symbol.name, real=True)
            for symbol in formula.free_symbols
            if symbol.name in {"x", "y", "z"}
        }
        return formula.xreplace(replacements)
