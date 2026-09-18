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
"ch03.det.row-swap": _content("ch03.det.row-swap", "交换两行翻转方向", "交换两行会改变定向面积的符号。", r"det(PA)=-det(A)", "交换两条基向量相当于把方向从逆时针改成顺时针。", "行交换保留面积绝对值但翻转方向。", "画出原始有向平行四边形。", "交换两列并显示方向翻转。"),
"ch03.det.scaling": _content("ch03.det.scaling", "一行数乘改变面积比例", "一条边伸缩会按相同比例改变面积。", r"det(kA)=k det(A)", "只拉伸一条边时，底或高按 k 倍变化，面积也按 k 倍变化。", "行列式对单方向缩放保持比例性。", "显示原始两条边。", "只伸缩一条边并比较面积。"),
"ch03.det.shear": _content("ch03.det.shear", "切变保持面积不变", "切变改变形状但保持底和高。", r"det([[1,k],[0,1]])=1", "矩形推成平行四边形后，底和高不变，所以面积不变。", "剪切是面积不变的典型线性变换。", "显示矩形和切变网格。", "并列比较两个区域面积。"),
"ch03.det.multiplicativity": _content("ch03.det.multiplicativity", "det(AB) 的两阶段面积缩放", "复合变换的面积倍率等于两次倍率相乘。", r"det(AB)=det(A)det(B)", "先经过 B 再经过 A，面积缩放因子逐阶段相乘。", "行列式把复合变换的面积效果分解成局部倍率。", "显示第一阶段区域。", "再显示第二阶段区域和倍率乘积。"),
"ch03.cramer.area-ratio": _content("ch03.cramer.area-ratio", "克拉默法则的面积比解方程组", "未知坐标可以表示为替换列后的面积比。", r"x=det(b,a_2)/det(a_1,a_2)", "系数列张成的基准平行四边形与替换列平行四边形的面积比给出坐标。", "克拉默法则是面积比读取坐标的几何方法。", "画出两列系数向量。", "替换一列并标注两个有向面积。"),
"ch03.inverse.undo": _content("ch03.inverse.undo", "逆矩阵的几何撤销", "逆矩阵把变形后的网格还原。", r"A^{-1}A=I", "先应用 A 再应用 A^{-1}，每个点回到原位置。", "可逆变换的逆是几何操作的撤销按钮。", "显示原始网格和 A 网格。", "应用逆变换并对比回到原图。"),
"ch03.inverse.formula": _content("ch03.inverse.formula", "2×2 求逆公式的几何参数", "余子式交换和符号改变对应方向修正。", r"A^{-1}=1/det(A)[[d,-b],[-c,a]]", "分母行列式是面积倍率，分子矩阵调整基向量方向。", "求逆公式把面积倍率与方向修正组合起来。", "显示 A 的两列和面积。", "标注逆矩阵中的交换与变号。"),
"ch03.inverse.examples": _content("ch03.inverse.examples", "可逆与退化变换的分层例题", "有面积的变换可逆，塌缩变换不可逆。", r"det(A)!=0 <=> A^{-1} exists", "可逆网格能恢复，退化网格丢失维度后无法唯一回溯。", "是否存在逆由几何是否塌缩决定。", "并列显示可逆和退化矩阵。", "尝试撤销并显示差异。"),
"ch03.det.zero.equivalence": _content("ch03.det.zero.equivalence", "det=0 的等价几何条件", "面积为零、列相关、秩下降和不可逆是同一塌缩现象。", r"det(A)=0 <=> rank(A)<n", "平行四边形退化成线段，多个代数条件在图形上同时出现。", "det=0 表示变换丢失至少一个方向。", "显示共线列向量。", "将二维区域压成一条线。"),
"ch03.det.high-dimensional-volume": _content("ch03.det.high-dimensional-volume", "n 阶行列式与面积、体积类比", "二维面积和三维体积是同一规律的低维实例。", r"|det(A)| = volume scale", "二维填充区域和三维平行六面体分别承载面积与体积缩放。", "行列式推广了从长度到面积、体积及 n 维测度的缩放规律。", "并列显示二维平行四边形和三维平行六面体。", "标注维数类比。"),
"ch03.inverse.reverse-order": _content("ch03.inverse.reverse-order", "逆矩阵乘积的逆序撤销", "复合操作的撤销顺序必须反过来。", r"(AB)^{-1}=B^{-1}A^{-1}", "先做 B 再做 A，撤销时先撤销 A，再撤销 B。", "逆矩阵的乘积顺序反映了撤销动作的时间顺序。", "显示 A 后 B 的变换链。", "用反向箭头展示撤销顺序。"),
}

