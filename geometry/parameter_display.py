"""Render parameterized CAS expressions with their current numeric values."""

from __future__ import annotations

from collections.abc import Mapping
import math

import sympy as sp
from sympy.core.sympify import SympifyError


_FUNCTIONS = {
    "abs": sp.Abs,
    "cos": sp.cos,
    "exp": sp.exp,
    "log": sp.log,
    "sin": sp.sin,
    "sqrt": sp.sqrt,
    "tan": sp.tan,
}


def _numeric(value: float) -> sp.Expr:
    """Keep slider values readable (``1`` instead of ``1.0``)."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("parameter values must be finite")
    if math.isclose(number, round(number), rel_tol=0.0, abs_tol=1e-12):
        return sp.Integer(round(number))
    return sp.Float(f"{number:.12g}")


def _substitutions(parameters: Mapping[str, float]) -> dict[sp.Symbol, sp.Expr]:
    return {
        sp.Symbol(str(name), real=True): _numeric(float(value))
        for name, value in parameters.items()
    }


def _equation_sides(
    source: str | None,
    simplified: sp.Expr,
    substitutions: Mapping[sp.Symbol, sp.Expr],
) -> tuple[sp.Expr, sp.Expr] | None:
    """Recover a validated implicit equation's original left/right layout."""
    if source is None or source.count("=") != 1:
        return None
    left_source, right_source = (part.strip() for part in source.split("=", 1))
    symbols = {
        symbol.name: symbol
        for symbol in (*simplified.free_symbols, *substitutions.keys())
    }
    local_dict = {
        **symbols,
        **_FUNCTIONS,
        "E": sp.E,
        "pi": sp.pi,
    }
    try:
        left = sp.sympify(left_source.replace("^", "**"), locals=local_dict, evaluate=True)
        right = sp.sympify(right_source.replace("^", "**"), locals=local_dict, evaluate=True)
    except (SyntaxError, TypeError, ValueError, SympifyError):
        return None
    return left, right


def format_parameterized_latex(
    *,
    kind: str,
    simplified: sp.Expr | tuple[sp.Expr, ...],
    parameters: Mapping[str, float],
    source: str | None = None,
    dependent_axis: str | None = None,
    parameter_range: tuple[sp.Expr, sp.Expr] | None = None,
    parameter_ranges: tuple[tuple[sp.Expr, sp.Expr], ...] = (),
    fallback: str = "",
) -> str:
    """Return a display-only formula with parameter symbols substituted."""
    if not parameters:
        return fallback
    substitutions = _substitutions(parameters)
    if kind == "explicit":
        if dependent_axis is None or not isinstance(simplified, sp.Expr):
            return fallback
        value = sp.simplify(simplified.subs(substitutions))
        return f"{dependent_axis}={sp.latex(value)}"
    if kind == "implicit":
        if not isinstance(simplified, sp.Expr):
            return fallback
        sides = _equation_sides(source, simplified, substitutions)
        if sides is not None:
            left, right = sides
            left = sp.simplify(left.subs(substitutions))
            right = sp.simplify(right.subs(substitutions))
            return f"{sp.latex(left)}={sp.latex(right)}"
        value = sp.simplify(simplified.subs(substitutions))
        return f"{sp.latex(value)}=0"
    if not isinstance(simplified, tuple):
        return fallback
    components = ",".join(sp.latex(sp.simplify(item.subs(substitutions))) for item in simplified)
    result = rf"\left({components}\right)"
    if parameter_range is not None:
        result += f";t=[{sp.latex(parameter_range[0])},{sp.latex(parameter_range[1])}]"
    elif parameter_ranges:
        names = ("u", "v")
        ranges = ",".join(
            f"{name}=[{sp.latex(lower)},{sp.latex(upper)}]"
            for name, (lower, upper) in zip(names, parameter_ranges)
        )
        result += f";{ranges}"
    return result
