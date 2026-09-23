from .model import ExplanationContent


def _content(topic_id: str, title: str, summary: str, formula: str, meaning: str, conclusion: str, *steps: str, aliases: tuple[str, ...] = ()) -> ExplanationContent:
    return ExplanationContent(
        id=f"explain.{topic_id}",
        title=title,
        summary=summary,
        formula=formula,
        steps=tuple(steps),
        geometric_meaning=meaning,
        conclusion=conclusion,
        searchable_text=(title, summary, formula, *aliases),
    )


CONTENT = {
"ch03.det.oriented-area": _content("ch03.det.oriented-area", "行列式的几何定义", "行列式等于以矩阵两列为邻边的平行四边形的有向面积，按 ad-bc 计算。", r"\det(\begin{pmatrix}a&b\\c&d\end{pmatrix})=ad-bc", "面积的绝对值记录缩放倍数，符号记录从第一列到第二列的方向是否翻转。", "行列式的几何定义把面积缩放、代数公式与方向符号统一在一起。", "显示单位正方形与矩阵两列。", "填充两列张成的平行四边形并读出面积。"),
"ch03.det.basic-properties": _content("ch03.det.basic-properties", "行列式的基本性质", "交换、数乘和行叠分别改变有向面积的方向、比例或形状。", r"\det(\boldsymbol A')=\pm k\det(\boldsymbol A)", "同一平行四边形经过三种行变换时，可以直接观察有向面积的变号、缩放与守恒。", "行列式的基本性质把行变换与面积变化对应起来。", "比较同一矩阵经过三种行变换后的有向面积。", "再检查零行导致的退化。"),
"ch03.det.multiplicativity": _content("ch03.det.multiplicativity", "乘积的行列式", "复合变换的面积倍率等于两个阶段倍率的乘积。", r"\det(\boldsymbol A\boldsymbol B)=\det(\boldsymbol A)\det(\boldsymbol B)", "先经过 \boldsymbol B 再经过 \boldsymbol A，面积缩放因子逐阶段相乘。", "行列式把复合变换的面积效果分解成两个阶段的倍率。", "显示单位平行四边形和第一阶段面积。", "再显示复合变换后的面积与倍率乘积。"),
"ch03.det.transpose": _content("ch03.det.transpose", "转置不变性", "矩阵转置后，有向面积的数值保持不变。", r"\det(\boldsymbol A^{T})=\det(\boldsymbol A)", "转置改变矩阵的行列排列，但不会改变行列式。", "矩阵与转置矩阵给出相同的行列式。", "显示矩阵的两列与有向面积。", "将矩阵转置并比较面积。"),
"ch03.cramer.area-ratio": _content("ch03.cramer.area-ratio", "克拉默法则的面积比解方程组", "定理 3.5（Cramer 法则）", r"x_i=\frac{\det(A_i)}{\det(A)}", "", "", "将 A 的第 i 列替换为 b。", "用替换列后的行列式除以原行列式。", aliases=("克拉默法则", "Cramer 法则")),
"ch03.inverse.undo": _content("ch03.inverse.undo", "逆矩阵", "定义 3.2（逆矩阵）", r"AB=BA=I", "", "", r"判断 $\det(A)\neq0$。", r"按 $2\times2$ 求逆公式计算。", aliases=("2×2 求逆公式", "可逆矩阵")),
"ch03.adjugate.matrix": _content("ch03.adjugate.matrix", "伴随矩阵", "伴随矩阵与伴随矩阵求逆", r"A\operatorname{adj}(A)=\det(A)I", "", "", "计算各元素的代数余子式。", "转置代数余子式矩阵得到伴随矩阵。", aliases=("代数余子式", "伴随矩阵求逆")),
"ch03.det.zero.equivalence": _content("ch03.det.zero.equivalence", "det=0 的等价几何条件", "面积为零、列相关、秩下降和不可逆是同一塌缩现象。", r"det(A)=0 <=> rank(A)<n", "平行四边形退化成线段，多个代数条件在图形上同时出现。", "det=0 表示变换丢失至少一个方向。", "显示共线列向量。", "将二维区域压成一条线。"),
}
