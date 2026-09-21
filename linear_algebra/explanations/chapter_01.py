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
"ch01.vector.magnitude": _content(
    "ch01.vector.magnitude",
    "什么是向量",
    # 逐句保留讲义中的物理场景和定义衔接句。
    ("我们从一个最简单的物理场景出发：\n"
     "从宿舍到食堂，\"向北走300米，再向东走400米\"。\n"
     "这和\"向东走400米，再向北走300米\"的目标位置完全相同。\n"
     "这两个\"走法\"有方向（北偏东）和长度（500米）。\n"
     "它们描述的是同一个位移。\n"
     "把这个直觉翻译成数学语言："),
    # 讲义公式统一使用粗体向量。
    r"|\boldsymbol v| = \sqrt{x^{2} + y^{2}}",
    # 讲义没有“几何意义”和“结论”小节。
    "",
    "",
    # 定义按讲义顺序排列，省略原编号。
    "**（向量）** 在平面直角坐标系中，一个向量是一个有向线段，其起点固定为坐标原点 $O(0,0)$。向量由其终点坐标唯一确定。",
    "记法：向量一般用粗体小写字母表示，如 $\\boldsymbol v$。也常用其终点坐标 $(x, y)$ 来表示。",
    "关键约定：在线性代数中，所有向量默认从原点出发。这是整门课最重要的操作约定——正是因为起点统一，向量才能和坐标一一对应，几何才能翻译为代数。",
    "**（零向量）** 长度为零的向量称为零向量，记为 $\\boldsymbol 0$ 或 $(0, 0)$。零向量没有方向，是唯一一个\"既是向量又是点\"的向量。",
    "**（向量的模）** 向量 $\\boldsymbol v = (x, y)$ 的长度称为模，记为 $|\\boldsymbol v|$。由勾股定理：",
    "$$|\\boldsymbol v| = \\sqrt{x^{2} + y^{2}}$$",
    "例如，$(3, 4)$ 的模为 $\\sqrt{9 + 16} = 5$。",
),
"ch01.ops.addition": _content("ch01.ops.addition", "向量加法", "用平行四边形和首尾相接表达相加。", r"a+b=c", "把 b 平移到 a 的终点，合成向量指向平行四边形对角点。", "向量加法是几何位移的连续执行。", "从原点画出 a 和 b。", "展示平移后的 b 和结果 c。"),
"ch01.ops.subtraction": _content("ch01.ops.subtraction", "向量减法", "减去一个向量等于加上它的相反向量。", r"a-b=a+(-b)", "相反向量反向但长度相同，结果向量连接两个终点。", "减法可还原为加法与方向翻转。", "画出 a 和 -b。", "标出 a-b 的结果箭头。"),
"ch01.ops.scalar": _content("ch01.ops.scalar", "向量数乘与共线", "标量改变长度，负号还会翻转方向。", r"ka=(ka_1,ka_2)", "数乘后的箭头与原箭头共线，比例由 k 决定。", "数乘保持向量所在直线，正负决定同向或反向。", "同时显示 a、2a 和 -a。", "比较它们的长度比例。"),
"ch01.ops.linear-combination": _content("ch01.ops.linear-combination", "线性组合", "数乘和加法组合出新的方向。", r"u=alpha a+beta b", "先伸缩基向量，再首尾相接即可得到组合结果。", "线性组合描述由给定方向生成的可达区域。", "显示 alpha a 与 beta b。", "连接它们的合成结果。"),
"ch01.inner.definitions": _content("ch01.inner.definitions", "1.3.1 内积的两种定义", "内积把长度和方向关系压缩成一个数。", r"a.b=|a||b|cos(theta)", "投影长度乘以被投影向量的长度等于内积。", "内积正负分别对应锐角、直角和钝角。", "从同一点画出 a、b。", "显示夹角弧线和投影垂足。"),
"ch01.inner.cauchy-schwarz": _content("ch01.inner.cauchy-schwarz", "柯西—施瓦茨不等式", "内积的绝对值不超过两个向量长度的乘积。", r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert", "投影长度不超过原向量长度。", "等号成立当且仅当两个向量共线。", "显示共线与非共线的两组向量。", "比较投影长度与原向量长度。"),
"ch01.projection.definition": _content("ch01.projection.definition", "投影、垂足与残差", "投影把向量分成平行分量和正交残差。", r"v=Proj_u(v)+(v-Proj_u(v))", "从向量终点向目标方向作垂线，垂足给出投影端点。", "投影分解是沿方向测量信息的基本方法。", "画出目标方向 u。", "标出投影向量、垂足和残差。"),
"ch01.proof.midline": _content("ch01.proof.midline", "三角形中位线定理", "两边中点连线平行第三边且长度减半。", r"MN=(C-B)/2", "中点坐标相减后直接得到 MN 是 BC 的一半。", "向量等式同时给出平行关系和长度关系。", "显示三角形和两个中点。", "突出中位线与第三边。"),
"ch01.proof.centroid": _content("ch01.proof.centroid", "三角形重心定理", "三条中线交于同一个重心。", r"G=(A+B+C)/3", "三个顶点位置向量的平均值落在每条中线的三等分位置。", "重心是顶点向量的平均，具有对称的几何意义。", "画出三条中线。", "标出它们的公共交点 G。"),
"ch01.proof.parallelogram-diagonals": _content("ch01.proof.parallelogram-diagonals", "平行四边形对角线互相平分", "两条对角线拥有同一个中点。", r"(A+C)/2=(B+D)/2", "用顶点向量相加可以证明两个对角线中点相同。", "对角线平分是平行四边形的向量特征。", "显示四个顶点和两条对角线。", "标出相同的中点。"),
}
