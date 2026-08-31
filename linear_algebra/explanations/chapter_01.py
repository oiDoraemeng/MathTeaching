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
"ch01.vector.magnitude": _content("ch01.vector.magnitude", "向量的几何量：方向、长度与零向量", "用箭头同时表达方向和长度。", r"||v|| = sqrt(v_1^2 + v_2^2)", "箭头的方向记录位移方向，箭头的长度记录位移大小。", "零向量没有方向，非零向量由方向和长度共同确定。", "从同一原点画出向量箭头。", "比较箭头长度与坐标分量。"),
"ch01.vector.point-distinction": _content("ch01.vector.point-distinction", "点与向量的本质区别", "点描述位置，向量描述位移。", r"v = Q - P", "平移一支箭头不会改变向量，但会改变点的位置。", "点和向量使用相同坐标记号时，几何角色仍然不同。", "标出点 P、Q 的位置。", "画出从 P 指向 Q 的位移箭头。"),
"ch01.vector.coordinate-system": _content("ch01.vector.coordinate-system", "坐标系与右手约定", "坐标轴和方向约定决定向量的读法。", r"e_1=(1,0), e_2=(0,1)", "标准基把坐标分量对应到水平和竖直方向，三维时再加入右手方向。", "先固定坐标系，再解释向量的分量与方向。", "显示标准基向量。", "用颜色区分正方向和负方向。"),
"ch01.vector.direction-examples": _content("ch01.vector.direction-examples", "方向、象限与分层例题", "同样的长度可以对应不同的方向。", r"v=(x,y)", "终点所在象限和坐标符号共同决定箭头方向。", "分量符号是判断方向的快速几何线索。", "分别显示四个象限的示例箭头。", "比较它们的长度和夹角。"),
"ch01.ops.addition": _content("ch01.ops.addition", "向量加法", "用平行四边形和首尾相接表达相加。", r"a+b=c", "把 b 平移到 a 的终点，合成向量指向平行四边形对角点。", "向量加法是几何位移的连续执行。", "从原点画出 a 和 b。", "展示平移后的 b 和结果 c。"),
"ch01.ops.subtraction": _content("ch01.ops.subtraction", "向量减法", "减去一个向量等于加上它的相反向量。", r"a-b=a+(-b)", "相反向量反向但长度相同，结果向量连接两个终点。", "减法可还原为加法与方向翻转。", "画出 a 和 -b。", "标出 a-b 的结果箭头。"),
"ch01.ops.scalar": _content("ch01.ops.scalar", "向量数乘与共线", "标量改变长度，负号还会翻转方向。", r"ka=(ka_1,ka_2)", "数乘后的箭头与原箭头共线，比例由 k 决定。", "数乘保持向量所在直线，正负决定同向或反向。", "同时显示 a、2a 和 -a。", "比较它们的长度比例。"),
"ch01.ops.linear-combination": _content("ch01.ops.linear-combination", "线性组合", "数乘和加法组合出新的方向。", r"u=alpha a+beta b", "先伸缩基向量，再首尾相接即可得到组合结果。", "线性组合描述由给定方向生成的可达区域。", "显示 alpha a 与 beta b。", "连接它们的合成结果。"),
"ch01.ops.velocity": _content("ch01.ops.velocity", "速度合成的几何表示", "相对速度和载体速度可以首尾相接。", r"v_total=v_relative+v_carrier", "速度向量的合成与位移向量遵循同一平行四边形法则。", "物理中的速度合成是向量加法的直接应用。", "画出载体速度。", "叠加相对速度并显示总速度。"),
"ch01.ops.cross-product": _content("ch01.ops.cross-product", "叉积的三维旋转方向", "叉积方向由右手规则确定。", r"a x b = |a||b| sin(theta) n", "a 与 b 张成的平面有一个垂直法向量，手性决定正负方向。", "叉积同时编码面积大小和三维旋转方向。", "显示两个三维向量。", "绘制法向量并标出右手旋转。"),
"ch01.ops.scalar-triple": _content("ch01.ops.scalar-triple", "混合积与平行六面体体积", "三个向量张成有向平行六面体。", r"a . (b x c) = det(a,b,c)", "底面积乘以有向高得到体积，交换方向会改变符号。", "混合积的绝对值是体积，符号记录空间方向。", "显示三条棱向量。", "填充平行六面体并标注体积。"),
"ch01.inner.equivalence": _content("ch01.inner.equivalence", "内积两种定义的几何等价", "分量公式与夹角公式由余弦定理连接。", r"a.b=|a||b|cos(theta)", "由三角形第三边的平方展开，可把分量乘积整理成夹角表达。", "代数内积和几何投影描述的是同一个量。", "画出由 a、b 构成的三角形。", "用边长平方展开说明余弦项。"),
"ch01.inner.definitions": _content("ch01.inner.definitions", "内积、夹角与投影", "内积把长度和方向关系压缩成一个数。", r"a.b=|a||b|cos(theta)", "投影长度乘以被投影向量的长度等于内积。", "内积正负分别对应锐角、直角和钝角。", "从同一点画出 a、b。", "显示夹角弧线和投影垂足。"),
"ch01.inner.applications": _content("ch01.inner.applications", "内积的长度、正交与夹角应用", "内积可判断长度、正交和夹角。", r"a.a=|a|^2, a.b=0 => a perpendicular b", "把向量与自身或另一个向量做内积，就能得到长度平方或正交关系。", "内积是长度测量和正交判断的统一工具。", "展示向量与自身的内积。", "展示一对正交向量和直角标记。"),
"ch01.inner.cauchy-schwarz": _content("ch01.inner.cauchy-schwarz", "柯西-施瓦茨不等式的投影界", "投影长度不超过原向量长度。", r"|a.b| <= |a||b|", "投影是直角三角形的一条直角边，因此不会超过斜边。", "不等式是投影几何界的代数表达。", "显示向量 a 和 b。", "比较投影长度与 |a|。"),
"ch01.inner.examples": _content("ch01.inner.examples", "内积几何分层例题", "通过锐角、直角和钝角比较内积符号。", r"sign(a.b)=sign(cos(theta))", "改变夹角会让投影从正值经过零变为负值。", "内积符号直接揭示相对方向。", "分别展示三种夹角。", "标注内积符号的变化。"),
"ch01.projection.definition": _content("ch01.projection.definition", "投影、垂足与残差", "投影把向量分成平行分量和正交残差。", r"v=Proj_u(v)+(v-Proj_u(v))", "从向量终点向目标方向作垂线，垂足给出投影端点。", "投影分解是沿方向测量信息的基本方法。", "画出目标方向 u。", "标出投影向量、垂足和残差。"),
"ch01.projection.properties": _content("ch01.projection.properties", "投影的可加性与齐次性", "投影对加法和数乘保持线性。", r"Proj_u(v+w)=Proj_u(v)+Proj_u(w)", "分别投影再相加，与先相加再投影落在同一点。", "正交投影是一个线性变换。", "显示两个输入向量的投影。", "对比合成向量的投影。"),
"ch01.projection.force": _content("ch01.projection.force", "坐标轴与斜面上的力分解", "力向量可分解为沿轴向和垂直方向的分量。", r"F=F_parallel+F_perpendicular", "投影提供沿斜面方向的有效分量，残差是法向分量。", "工程中的分力计算就是投影几何。", "画出斜面方向。", "标注平行分量和法向分量。"),
"ch01.proof.method": _content("ch01.proof.method", "几何问题转向量的四步方法", "选点、设向量、写关系、翻译回几何。", r"geometry -> vectors -> algebra -> geometry", "同一条几何关系可以用坐标和向量的等式表达。", "向量让平行、共线和中点关系变成可计算对象。", "标出几何对象和对应向量。", "显示从图形到等式的四步链路。"),
"ch01.proof.midline": _content("ch01.proof.midline", "三角形中位线定理", "两边中点连线平行第三边且长度减半。", r"MN=(C-B)/2", "中点坐标相减后直接得到 MN 是 BC 的一半。", "向量等式同时给出平行关系和长度关系。", "显示三角形和两个中点。", "突出中位线与第三边。"),
"ch01.proof.centroid": _content("ch01.proof.centroid", "三角形重心定理", "三条中线交于同一个重心。", r"G=(A+B+C)/3", "三个顶点位置向量的平均值落在每条中线的三等分位置。", "重心是顶点向量的平均，具有对称的几何意义。", "画出三条中线。", "标出它们的公共交点 G。"),
"ch01.proof.parallelogram-diagonals": _content("ch01.proof.parallelogram-diagonals", "平行四边形对角线互相平分", "两条对角线拥有同一个中点。", r"(A+C)/2=(B+D)/2", "用顶点向量相加可以证明两个对角线中点相同。", "对角线平分是平行四边形的向量特征。", "显示四个顶点和两条对角线。", "标出相同的中点。"),
"ch01.high-dimensional.analogy": _content("ch01.high-dimensional.analogy", "从二维、三维到 n 维的向量类比", "高维向量遵循相同的加法、数乘和内积规则。", r"v=(v_1,...,v_n)", "用二维和三维箭头承载高维坐标规则，而不假装绘制 n 维空间。", "低维类比帮助理解高维代数结构。", "并列显示二维、三维和坐标列表。", "标注保持不变的代数规则。"),
}

