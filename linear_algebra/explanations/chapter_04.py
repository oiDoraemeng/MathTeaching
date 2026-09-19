from .model import ExplanationContent

_IDS = (
    "subspace.col-null",
    "dependence.redundancy",
    "basis.definition", "linear-map.definition",
    "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity",
)


def _content(topic: str) -> ExplanationContent:
    subject = topic.replace(".", " ").replace("-", " ")
    formula = r"x=\sum_i c_i v_i,\quad T(x+y)=T(x)+T(y)"
    summary = f"{subject} 用闭性、线性组合和维数描述线性空间中的结构。"
    return ExplanationContent(
        id=f"explain.ch04.{topic}", title=f"第4章 {subject}", summary=summary,
        formula=formula, steps=("先识别对象及其所在空间。", "代入线性组合并检查闭性、独立性或维数。", "用秩、核和像核对结论。"),
        geometric_meaning="向量集合在加法和数乘下保持封闭，几何上表现为直线、平面或其高维对应物。",
        conclusion="结构条件成立时，代数表示与几何子空间描述一致。",
        searchable_text=(f"第4章 {subject}", summary, formula, "线性空间", "子空间", "秩与零空间"),
        numeric_example="例如 v1=(1,0), v2=(0,1), x=(2,3)=2v1+3v2。",
        pitfalls=("不要把任意点集误判为过原点的子空间。", "坐标表示依赖所选基。"),
        read_guide=("先看对象和运算，再看公式，最后核对维数和几何形状。",),
        analogy_boundary="二维图形只是低维示意；闭性、秩和维数的结论可推广到有限维空间。",
    )


EXPLANATIONS = {f"ch04.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
