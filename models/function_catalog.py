"""二维与三维工作区共用的运行时函数目录。"""

from __future__ import annotations

from dataclasses import dataclass

from models.scene_mode import SceneMode


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    category: str
    name: str
    kind: str
    expression: str
    latex: str
    parameters: dict[str, float]
    color: str
    mode: SceneMode
    builtin_id: str | None = None


TWO_D_CATALOG = (
    CatalogEntry("sin", "基本初等函数", "正弦", "explicit", "y = sin(x)", r"y=\sin(x)", {}, "#2777b6", SceneMode.TWO_D),
    CatalogEntry("cos", "基本初等函数", "余弦", "explicit", "y = cos(x)", r"y=\cos(x)", {}, "#d1664a", SceneMode.TWO_D),
    CatalogEntry("tan", "基本初等函数", "正切", "explicit", "y = tan(x)", r"y=\tan(x)", {}, "#6b56a5", SceneMode.TWO_D),
    CatalogEntry("exp", "基本初等函数", "指数", "explicit", "y = exp(x)", r"y=e^{x}", {}, "#2f8f83", SceneMode.TWO_D),
    CatalogEntry("log", "基本初等函数", "对数", "explicit", "y = log(x)", r"y=\ln(x)", {}, "#b97920", SceneMode.TWO_D),
    CatalogEntry("sqrt", "基本初等函数", "平方根", "explicit", "y = sqrt(x)", r"y=\sqrt{x}", {}, "#2777b6", SceneMode.TWO_D),
    CatalogEntry("abs", "基本初等函数", "绝对值", "explicit", "y = abs(x)", r"y=|x|", {}, "#bf5b78", SceneMode.TWO_D),
    CatalogEntry("line", "代数函数", "一次函数", "explicit", "y = a*x + b", r"y=ax+b", {"a": 1.0, "b": 0.0}, "#2777b6", SceneMode.TWO_D),
    CatalogEntry("quadratic", "代数函数", "二次函数", "explicit", "y = a*x^2 + b*x + c", r"y=ax^{2}+bx+c", {"a": 1.0, "b": 0.0, "c": 0.0}, "#d1664a", SceneMode.TWO_D),
    CatalogEntry("cubic", "代数函数", "三次函数", "explicit", "y = a*x^3 + b*x^2 + c*x + d", r"y=ax^{3}+bx^{2}+cx+d", {"a": 1.0, "b": 0.0, "c": 0.0, "d": 0.0}, "#6b56a5", SceneMode.TWO_D),
    CatalogEntry("reciprocal", "代数函数", "反比例", "explicit", "y = a/x", r"y=\frac{a}{x}", {"a": 1.0}, "#2f8f83", SceneMode.TWO_D),
    CatalogEntry("reciprocal_square", "代数函数", "反比例平方", "explicit", "y = a/x^2", r"y=\frac{a}{x^{2}}", {"a": 1.0}, "#b97920", SceneMode.TWO_D),
    CatalogEntry("circle", "圆锥曲线", "圆", "implicit", "x^2/a^2 + y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}}+\frac{y^{2}}{b^{2}}=1", {"a": 3.0, "b": 3.0}, "#2777b6", SceneMode.TWO_D),
    CatalogEntry("ellipse", "圆锥曲线", "椭圆", "implicit", "x^2/a^2 + y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}}+\frac{y^{2}}{b^{2}}=1", {"a": 5.0, "b": 3.0}, "#d1664a", SceneMode.TWO_D),
    CatalogEntry("hyperbola", "圆锥曲线", "双曲线", "implicit", "x^2/a^2 - y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}}-\frac{y^{2}}{b^{2}}=1", {"a": 3.0, "b": 2.0}, "#6b56a5", SceneMode.TWO_D),
    CatalogEntry("parabola", "圆锥曲线", "抛物线", "implicit", "y^2 = 4*a*x", r"y^{2}=4ax", {"a": 1.0}, "#2f8f83", SceneMode.TWO_D),
)


def catalog_entries(mode: SceneMode) -> tuple[CatalogEntry, ...]:
    """返回指定场景的目录项，不向调用方暴露可变的内部状态。"""
    if mode is SceneMode.TWO_D:
        return TWO_D_CATALOG

    # 延迟导入可避免模型目录与几何目录在模块初始化时形成循环依赖。
    from geometry.standard_surfaces import BUILTIN_SURFACES

    return tuple(
        CatalogEntry(
            id=surface.id,
            category="圆锥曲面",
            name=surface.name,
            kind=surface.kind,
            expression=surface.expression,
            latex=surface.latex,
            parameters=dict(surface.parameters),
            color=surface.color,
            mode=SceneMode.THREE_D,
            builtin_id=surface.id,
        )
        for surface in BUILTIN_SURFACES
    )


def catalog_entry(entry_id: str, mode: SceneMode) -> CatalogEntry | None:
    return next((entry for entry in catalog_entries(mode) if entry.id == entry_id), None)
