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
"ch02.matrix.row-column": _content("ch02.matrix.row-column", "矩阵乘向量的行视角与列视角", "行视角计算分量，列视角解释组合。", r"Ax=x_1a_1+x_2a_2", "同一个结果既可以看作行内积，也可以看作列向量的线性组合。", "两种算法描述同一个几何终点。", "显示矩阵两列和输入坐标。", "用首尾相接得到 Ax。"),
"ch02.matrix.transformed-grid": _content("ch02.matrix.transformed-grid", "基向量变换与网格变形", "矩阵的两列决定整个网格如何变形。", r"Ae_1=a_1, Ae_2=a_2", "标准基的两个方向被送到矩阵两列，所有网格线随之移动。", "观察基向量就能预测线性变换的整体形状。", "显示原始正交网格。", "叠加变换后的网格和基向量。"),
"ch02.matrix.stretch-rotate-scale": _content("ch02.matrix.stretch-rotate-scale", "拉伸、旋转与缩放的矩阵图像", "不同矩阵会留下不同的网格形状。", r"A=diag(2,1), R_90, S=0.5I", "横向拉伸、旋转和整体缩放可通过网格对比直接观察。", "矩阵列向量是新尺子的方向和长度。", "依次应用三种矩阵。", "对比每一步的基向量和网格。"),
"ch02.matrix.composition": _content("ch02.matrix.composition", "复合变换与 AB ≠ BA", "先做 B 后做 A 等于 AB，顺序通常不可交换。", r"(AB)x=A(Bx)", "同一输入经过两种顺序会到达不同终点，显示非交换性。", "矩阵乘法是变换复合，最右侧矩阵先作用。", "画出先切变后旋转。", "并列展示先旋转后切变。"),
"ch02.matrix.basis": _content("ch02.matrix.basis", "矩阵的列与新基坐标", "同一向量在不同基下坐标不同。", r"x=[x]_B^1 b_1+[x]_B^2 b_2", "新基向量是两根新尺子，坐标系改变但几何向量不变。", "矩阵列描述新基，坐标描述组合系数。", "显示标准基和新基。", "标出同一向量的两套坐标。"),
"ch02.matrix.powers": _content("ch02.matrix.powers", "矩阵幂表示重复变换", "矩阵幂记录同一变换连续执行的结果。", r"A^k x=A(A(...Ax))", "重复作用会让网格持续旋转、拉伸或压缩。", "矩阵幂是离散动态过程的几何记录。", "显示 A、A^2、A^3 的网格。", "标注每次变换的阶段。"),
"ch02.subspace.independence": _content("ch02.subspace.independence", "线性无关与线性相关的方向图", "多余方向可以被其他向量拼出。", r"c_1v_1+c_2v_2=0", "二维中不共线的两个方向独立，共线时一个方向是另一个的倍数。", "线性无关表示每个方向都提供新信息。", "显示不共线向量组。", "切换到共线向量组作对比。"),
"ch02.subspace.rank": _content("ch02.subspace.rank", "秩与输出空间的真实维度", "秩是变换保留下来的有效维数。", r"rank(A)=dim(Col(A))", "网格被压到平面、直线或原点时，输出空间维数分别为 2、1、0。", "秩衡量变换后还剩多少几何自由度。", "显示满秩网格。", "逐步压缩到一条线和一个点。"),
"ch02.subspace.null": _content("ch02.subspace.null", "零空间是被压到原点的方向", "零空间收集所有被变换完全消除的输入。", r"Null(A)={x:Ax=0}", "零空间方向上的箭头经过变换后全部落在原点。", "零空间记录信息丢失的方向。", "显示输入方向族。", "将它们映射到同一个原点。"),
"ch02.subspace.column": _content("ch02.subspace.column", "列空间是变换可到达的位置", "列空间包含所有可能的输出位置。", r"Col(A)={Ax:x in R^n}", "输出点只能落在列向量张成的直线或平面中。", "列空间描述变换的可达区域。", "显示多组输入向量。", "观察所有输出形成的子空间。"),
"ch02.subspace.rank-nullity": _content("ch02.subspace.rank-nullity", "秩-零化度的维数守恒", "保留的维数加上丢失的维数等于输入维数。", r"rank(A)+nullity(A)=n", "用颜色分别标出输出子空间和被压扁的方向。", "秩-零化度是线性变换的维数守恒律。", "显示一条保留方向和一条零空间方向。", "在图旁标出 1+1=2。"),
"ch02.high-dimensional.analogy": _content("ch02.high-dimensional.analogy", "n 维矩阵运算的低维类比", "矩阵运算规则不随维数改变。", r"A:R^n -> R^m", "二维网格和三维箭头只是高维线性变换的可视化切片。", "低维图形表达结构，高维坐标保留代数规则。", "并列显示二维网格与三维向量。", "说明它们共享同一套矩阵规则。"),
}

