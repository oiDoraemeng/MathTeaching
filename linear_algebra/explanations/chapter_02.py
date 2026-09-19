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
"ch02.batch.inner-products": _content("ch02.batch.inner-products", "行向量与矩阵乘法", "一行乘矩阵同时得到多个内积。", r"uV=(u.v_1,...,u.v_n)", "矩阵的每一列提供一个待比较方向，结果是一组投影或角度数据。", "批量内积把重复的几何测量组织成一次矩阵运算。", "画出同一个 u 与多列向量。", "用结果标出每个方向上的内积。"),
"ch02.batch.projection": _content("ch02.batch.projection", "投影矩阵把一批向量压到方向上", "同一个投影矩阵可以作用于许多输入向量。", r"P=uu^T, Pv=Proj_u(v)", "所有输出落在同一条目标方向上，垂直分量被消除。", "投影矩阵是批量执行正交投影的线性变换。", "显示多个输入向量。", "把它们同时压到目标轴。"),
"ch02.matrix.additive-distributivity": _content("ch02.matrix.additive-distributivity", "矩阵加法与变换分配律", "先加矩阵再变换等于分别变换后相加。", r"(A+B)x=Ax+Bx", "两条变换路径的终点重合，说明矩阵加法继承了向量加法。", "分配律可以用终点一致的几何图验证。", "画出 A、B 对同一向量的作用。", "比较两条路径的结果。"),
"ch02.matrix.transformed-grid": _content("ch02.matrix.transformed-grid", "矩阵变换", "矩阵乘向量可按行计算，也可按列解释；矩阵的两列决定网格如何变形。", r"\boldsymbol A\boldsymbol x=x_1\boldsymbol A\boldsymbol e_1+x_2\boldsymbol A\boldsymbol e_2", "标准基的两个方向被送到矩阵两列，所有网格线随之移动。", "观察基向量就能预测线性变换的整体形状。", "显示原始正交网格。", "叠加变换后的网格和基向量。"),
"ch02.matrix.composition": _content("ch02.matrix.composition", "复合变换与 AB ≠ BA", "先做 B 后做 A 等于 AB，顺序通常不可交换。", r"(AB)x=A(Bx)", "同一输入经过两种顺序会到达不同终点，显示非交换性。", "矩阵乘法是变换复合，最右侧矩阵先作用。", "画出先切变后旋转。", "并列展示先旋转后切变。"),
"ch02.matrix.basis": _content("ch02.matrix.basis", "矩阵的列与新基坐标", "同一向量在不同基下坐标不同。", r"x=[x]_B^1 b_1+[x]_B^2 b_2", "新基向量是两根新尺子，坐标系改变但几何向量不变。", "矩阵列描述新基，坐标描述组合系数。", "显示标准基和新基。", "标出同一向量的两套坐标。"),
"ch02.matrix.powers": _content("ch02.matrix.powers", "矩阵幂表示重复变换", "矩阵幂记录同一变换连续执行的结果。", r"A^k x=A(A(...Ax))", "重复作用会让网格持续旋转、拉伸或压缩。", "矩阵幂是离散动态过程的几何记录。", "显示 A、A^2、A^3 的网格。", "标注每次变换的阶段。"),
"ch02.subspace.independence": _content("ch02.subspace.independence", "线性无关与线性相关", "只有全零系数才能把线性无关的向量组合出零向量。", r"c_1 v_1+c_2 v_2=0\Rightarrow c_1=c_2=0", "平面中两个方向不共线时线性无关；共线时其中一个能被另一个拼出来。", "线性无关表示每个向量都是必要的。", "显示不共线的两个方向。", "切换到共线的一组作对比。", "再用第三个向量说明多余方向。"),
"ch02.subspace.rank": _content("ch02.subspace.rank", "秩", "秩是矩阵列向量中最大线性无关组的个数。", r"rank(A)=dim(Col(A))", "秩等于变换后空间的真实维度：满秩是面，秩 1 是线，秩 0 是点。", "秩数出变换还有多少有效自由度。", "显示满秩网格。", "依次压缩到一条线和原点。"),
}
