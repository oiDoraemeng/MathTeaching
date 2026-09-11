from .model import ExplanationContent

_IDS = ("eigen.direction", "characteristic-polynomial", "eigenspace", "diagonalization", "gram-schmidt", "orthogonal-transform")


def _content(topic: str) -> ExplanationContent:
    subject = topic.replace(".", " ").replace("-", " ")
    formula = r"Av=\lambda v,\quad \det(A-\lambda I)=0"
    summary = f"{subject} 研究变换保持方向、谱值和正交结构的方式。"
    return ExplanationContent(
        id=f"explain.ch07.{topic}", title=f"第7章 {subject}", summary=summary, formula=formula,
        steps=("从特征方程或内积条件识别候选对象。", "求解向量、特征空间或正交基。", "代回矩阵关系验证不变量。"),
        geometric_meaning="特征向量方向在变换后不偏转，只发生尺度变化；正交变换保持长度和角度。",
        conclusion="谱结构和正交结构把复杂矩阵作用分解为可读的方向与尺度。",
        searchable_text=(f"第7章 {subject}", summary, formula, "特征值", "特征空间", "正交"),
        numeric_example="矩阵 diag(2,3) 的特征值为 2、3，坐标轴分别是特征方向。",
        pitfalls=("特征值重数不自动保证可对角化。", "Gram-Schmidt 需跳过零向量。"),
        read_guide=("先看方向关系，再看谱值或内积，最后检查正交和维数。",),
        analogy_boundary="箭头图展示低维方向；谱定理和特征空间定义适用于有限维内积空间。",
    )


EXPLANATIONS = {f"ch07.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
