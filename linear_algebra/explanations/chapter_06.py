from .model import ExplanationContent

_IDS = ("basis-change.motivation", "basis-change.coordinates", "similarity-transform")


def _content(topic: str) -> ExplanationContent:
    subject = topic.replace(".", " ").replace("-", " ")
    formula = r"[x]_B=P_{B\leftarrow C}[x]_C,\quad [T]_C=P^{-1}[T]_B P"
    summary = f"{subject} 解释同一向量或变换在不同基下的坐标表示。"
    return ExplanationContent(
        id=f"explain.ch06.{topic}", title=f"第6章 {subject}", summary=summary, formula=formula,
        steps=("列出新旧基向量并组成换基矩阵。", "用矩阵乘法转换坐标。", "用逆变换核对回到原表示。"),
        geometric_meaning="几何对象不变，变化的是描述它的坐标网格；相似矩阵是同一变换的两种坐标记录。",
        conclusion="换基改变坐标和矩阵外观，但保持线性变换本身及其不变量。",
        searchable_text=(f"第6章 {subject}", summary, formula, "换基", "坐标", "相似变换"),
        numeric_example="若新基矩阵 P=[[1,1],[0,1]]，则坐标转换由 P 或 P^{-1} 完成。",
        pitfalls=("不要把换基误当成对几何向量施加变换。", "矩阵乘法顺序必须固定。"),
        read_guide=("先区分对象与坐标，再确定换基方向，最后检查逆矩阵。",),
        analogy_boundary="网格图只展示二维情形；换基公式对任意有限维基成立。",
    )


EXPLANATIONS = {f"ch06.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
