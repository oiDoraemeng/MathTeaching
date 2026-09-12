from .model import ExplanationContent

_IDS = ("quadratic.matrix-form", "quadratic.level-sets", "principal-axis", "definiteness", "completing-square", "congruence-inertia")


def _content(topic: str) -> ExplanationContent:
    from linear_algebra.chapter_08_semantics import spec_for
    spec=spec_for(topic)
    subject = {'quadratic.matrix-form':'矩阵表示与交叉项','quadratic.level-sets':'对齐与倾斜等值线','principal-axis':'正交主轴标准化','definiteness':'正定、不定与半正定','completing-square':'可逆配方替换','congruence-inertia':'合同与惯性指数'}[topic]
    formula = spec.formula
    summary = f"{subject} 用对称矩阵和二次型描述曲线曲面及其主轴。"
    return ExplanationContent(
        id=f"explain.ch08.{topic}", title=f"第8章 {subject}", summary=summary, formula=formula,
        steps=tuple(stage.title for stage in spec.stages),
        geometric_meaning="齐次二次型的单位等值集可为椭圆、双曲线、平行直线或空集；主轴由对称矩阵的特征方向决定。",
        conclusion="对称矩阵的谱和惯性决定二次型的几何类型及正定性。",
        searchable_text=(f"第8章 {subject}", summary, formula, "二次型", "主轴", "正定性"),
        numeric_example=spec.formula,
        pitfalls=("不要把相似变换和合同变换混用。", "交叉项系数要注意二次型中的 2。"),
        read_guide=("先看矩阵对称性，再看特征值符号和等值集形状。",),
        analogy_boundary="二维圆锥曲线是可视化示例；主轴、惯性和正定性可推广到 n 维。",
    )


EXPLANATIONS = {f"ch08.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
