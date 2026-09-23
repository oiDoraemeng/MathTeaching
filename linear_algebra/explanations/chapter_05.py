from .model import ExplanationContent

_IDS = ("homogeneous.solution-space", "affine.solution-set", "consistency.geometry", "gaussian-elimination", "least-squares.projection")


def _content(topic: str) -> ExplanationContent:
    subject = topic.replace(".", " ").replace("-", " ")
    formula = r"Ax=b,\quad x=x_p+x_h,\quad Ax_h=0"
    summary = f"{subject} 通过消元、核和投影描述线性方程组的解。"
    return ExplanationContent(
        id=f"explain.ch05.{topic}", title=f"第5章 {subject}", summary=summary, formula=formula,
        steps=("写出增广矩阵并检查约束。", "用初等行变换得到主元和自由变量。", "代回原方程核对残差。"),
        geometric_meaning="齐次解形成过原点的子空间，非齐次解是它的平移；无解对应不相交的约束。",
        conclusion="主元决定一致性和自由度，所有解可由特解加零空间表示。",
        searchable_text=(f"第5章 {subject}", summary, formula, "高斯消元", "零空间", "最小二乘"),
        numeric_example="例如 x+y=3, x-y=1 的解为 (2,1)。",
        pitfalls=("不能把特解误当成全部解。", "最小二乘解不等于精确解。"),
        read_guide=("先判断是否一致，再读主元、自由变量和几何位置。",),
        analogy_boundary="二维直线交点是示意；消元和仿射解集结论适用于有限维方程组。",
    )


EXPLANATIONS = {f"ch05.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
