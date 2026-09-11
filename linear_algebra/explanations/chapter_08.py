from .model import ExplanationContent

_IDS = ("quadratic.matrix-form", "quadratic.level-sets", "principal-axis", "definiteness", "completing-square", "congruence-inertia")


def _content(topic: str) -> ExplanationContent:
    subject = topic.replace(".", " ").replace("-", " ")
    formula = r"q(x)=x^T A x,\quad A=A^T,\quad q(x)=\sum_i \lambda_i y_i^2"
    summary = f"{subject} 用对称矩阵和二次型描述曲线曲面及其主轴。"
    return ExplanationContent(
        id=f"explain.ch08.{topic}", title=f"第8章 {subject}", summary=summary, formula=formula,
        steps=("写出二次型的对称矩阵。", "求特征方向或配方消去交叉项。", "依据符号和等值集核对分类。"),
        geometric_meaning="二次型的等值集是椭圆、双曲线、抛物线或其高维对应物，主轴沿特征方向。",
        conclusion="对称矩阵的谱和惯性决定二次型的几何类型及正定性。",
        searchable_text=(f"第8章 {subject}", summary, formula, "二次型", "主轴", "正定性"),
        numeric_example="q(x,y)=4x^2+9y^2 的等值集 q=1 是半轴 1/2、1/3 的椭圆。",
        pitfalls=("不要把相似变换和合同变换混用。", "交叉项系数要注意二次型中的 2。"),
        read_guide=("先看矩阵对称性，再看特征值符号和等值集形状。",),
        analogy_boundary="二维圆锥曲线是可视化示例；主轴、惯性和正定性可推广到 n 维。",
    )


EXPLANATIONS = {f"ch08.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
