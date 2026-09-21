from pathlib import Path
import math

from linear_algebra.registry import catalog_registry, runtime_teaching_store
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.common import RenderContext
from ui.teaching_case_panes import case_plan


def test_vector_addition_skill_requires_evidence_and_nonfixed_cases() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("先向用户确认", "可以是一个、两个、三个或四个", "来源路径与哈希", "\\boldsymbol{}", "已确认的向量加法契约"):
        assert required in skill

    contract = Path(".agents/linear-algebra-explanation-skill/references/vector-addition-accepted-contract.md").read_text(encoding="utf-8")
    for required in ("全部显示", "左右各一个", "结果行或校验行", "标题左对齐", "不得在原点叠加多个同名标签"):
        assert required in contract


def test_geometry_proof_skill_records_the_accepted_figures() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("1.5 几何证明的已确认示例", "geometry-proof-accepted-contract.md", "渲染为空白"):
        assert required in skill

    contract = Path(
        ".agents/linear-algebra-explanation-skill/references/geometry-proof-accepted-contract.md"
    ).read_text(encoding="utf-8")
    for required in (
        "ch01.proof.midline",
        "ch01.proof.centroid",
        "ch01.proof.parallelogram-diagonals",
        "DE = ½ BC",
        "AG : GD = 2 : 1",
        "M(AC) = M(BD) = (a + b) / 2",
        "`→`",
        "`∥`",
        "padding=1.45",
    ):
        assert required in contract


def test_skill_records_the_default_pane_count_and_image_fit_rules() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("流程类小节默认“全部显示”", "按窗格实际宽高比计算缩放", "不强制把原点放在正中间"):
        assert required in skill

    contract = Path(
        ".agents/linear-algebra-explanation-skill/references/vector-addition-accepted-contract.md"
    ).read_text(encoding="utf-8")
    for required in ("default_pane_count = 2", "按窗格实际宽高比", "不强制把原点放在正中间"):
        assert required in contract


def test_skill_selects_layers_by_section_nature() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("定义性的小节", "全部都是案例的小节", "直接沿用讲义本身的组织与格式"):
        assert required in skill


def test_vector_addition_published_content_omits_unjustified_layers() -> None:
    artifact = runtime_teaching_store().published("ch01.ops.addition").artifact
    explanation = artifact.explanation
    assert explanation.derivation == ()
    assert explanation.intuition == ""
    assert explanation.connections == ()
    assert [case.id for case in explanation.case_layout.cases] == [
        "case.addition.objects",
        "case.addition.parallelogram",
    ]
    # 数学案例流程默认“全部显示”：首屏并排显示两个步骤窗格。
    assert explanation.case_layout.default_pane_count == 2


def test_matrix_transform_merges_the_confirmed_2_5_scope() -> None:
    """2.5.1 与 2.5.2 合并为「矩阵变换」，只保留既有网格变形案例。"""

    store = runtime_teaching_store()
    transformed = store.published("ch02.matrix.transformed-grid").artifact.explanation
    assert transformed.title == "矩阵变换"
    assert [(section.id, section.title) for section in transformed.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    for required in (
        "算法一（行视角 — 内积法）",
        "算法二（列视角 — 线性组合法）",
        "**（矩阵变换的基向量解释）**",
        "标准基向量 $\\boldsymbol e_{1}$ 被 $\\boldsymbol A$ 送到的新位置",
        "直觉总结",
        "整个坐标网格被 $\\boldsymbol A$ 拉伸、旋转、压扁",
        "\\begin{pmatrix}",
    ):
        assert required in transformed.definition
    assert "例1：" not in transformed.definition
    assert transformed.formula == ""
    assert transformed.geometric_meaning == ""
    assert [case.purpose for case in transformed.case_layout.cases] == [
        "第一步：标准基向量",
        "第二步：横向拉伸",
        "第三步：逆时针旋转",
        "第四步：两列的像与网格变形",
    ]
    assert transformed.case_layout.default_pane_count == 4
    topic_ids = {topic.id for topic in catalog_registry().topics}
    assert {"ch02.matrix.row-column", "ch02.matrix.stretch-rotate-scale"}.isdisjoint(topic_ids)

    basis = store.published("ch02.matrix.basis").artifact.explanation
    # 讲义 2.7 只有“基”的定义与核心认知，正文保留讲义内容。
    assert [section.title for section in basis.sections] == ["定义", "数学案例"]
    for required in (
        "一句话动机：同一个变换，用不同的基描述，矩阵就不同",
        "**（基）**",
        "$R^{n}$ 中 $n$ 个线性无关的向量组成的一组有序向量",
        "它是标准基，但不是唯一的基",
        "核心认知：变换本身是客观的",
        "描述它的矩阵取决于你用什么基来记录坐标",
    ):
        assert required in basis.definition
    assert [case.purpose for case in basis.case_layout.cases] == [
        "第一步：标准基描述",
        "第二步：换一组基，矩阵改变",
    ]
    assert basis.case_layout.default_pane_count == 2


def test_matrix_vector_case_data_avoids_the_coordinate_axes() -> None:
    """2.5 与 2.7 的自定案例取值避开坐标轴（标准基向量由讲义固定，不在此列）。"""

    store = runtime_teaching_store()
    for topic_id in (
        "ch02.matrix.transformed-grid",
        "ch02.matrix.basis",
    ):
        artifact = store.published(topic_id).artifact
        # 2.7 的基向量由案例定义，其中 b1 与标准基 e1 重合是有意保留的对照。
        fixed = {
            "mv_e1", "mv_e2",
            "mv_stretch_e1", "mv_stretch_e2",
            "mv_rotate_e1", "mv_rotate_e2",
            "mv_basis_e1", "mv_basis_e2", "mv_basis_b1", "mv_basis_b2",
        }
        for entity in artifact.visual_semantics.entities:
            if entity.kind != "vector" or entity.id in fixed:
                continue
            value = tuple(float(item) for item in entity.value)
            assert all(abs(item) > 0.0 for item in value), (topic_id, entity.id, value)


def test_det_geometry_merges_the_first_three_3_1_subsections_into_one_topic() -> None:
    """3.1 目录合并为单一小节：定义（含定理 3.1 公式）、几何意义速查与单案例。"""

    from linear_algebra.catalog.manifest import lecture_manifest, topic_entries

    section = next(node for node in lecture_manifest() if node.id == "ch03.s31")
    assert (section.title, section.children) == ("3.1 行列式的几何意义", ("ch03.det.oriented-area",))
    assert [topic.id for topic in topic_entries() if topic.section_id == "ch03.s31"] == [
        "ch03.det.oriented-area"
    ]

    explanation = runtime_teaching_store().published("ch03.det.oriented-area").artifact.explanation
    # 分节标题听命讲义：公式并入定义块，不单列「公式」；3.1.3 保留速查表标题。
    assert [(item.id, item.title) for item in explanation.sections] == [
        ("definition", "定义"),
        ("geometric_meaning", "几何意义速查"),
        ("worked_examples", "数学案例"),
    ]
    for required in (
        "定义 3.1（行列式——几何定义）",
        r"等于以 $\boldsymbol A$ 的两列为邻边的平行四边形的有向面积。",
        r"定理 3.1（$2 \times 2$ 行列式公式）",
        # 矩阵写成矩阵形式，不再把 pmatrix 压成一行。
        r"$$\det(\begin{pmatrix} a & b \\ c & d \end{pmatrix}) = ad - bc$$",
        '推导直觉：$a$ 和 $d$ 构成"主轴方向的矩形面积"，$bc$ 是"交叉项"的修正。',
        r"$3 \times 3$ 行列式用三阶展开公式，几何上对应平行六面体的有向体积。",
    ):
        assert required in explanation.definition
    assert explanation.formula == ""
    assert explanation.derivation == ()
    assert r"| $\det(\boldsymbol A)$ | 几何含义 |" in explanation.geometric_meaning
    for row in ("$= 0$", "$> 0$", "$< 0$", r"$|\det(\boldsymbol A)| = 1$"):
        assert row in explanation.geometric_meaning
    assert "面积不变（如纯旋转）" in explanation.geometric_meaning
    # 3.1.4 分层例题随该小节删除：正文与检索文本都不再保留。
    assert "分层例题" not in explanation.definition
    assert not any("分层例题" in item for item in explanation.searchable_text)
    # 讲义 3.1.1–3.1.3 无数值案例：按定义自定的两步案例，首屏“全部显示”两格。
    assert explanation.case_layout is not None
    assert [case.id for case in explanation.case_layout.cases] == [
        "case.ch03.det.oriented-area.1",
        "case.ch03.det.oriented-area.2",
    ]
    assert [case.purpose for case in explanation.case_layout.cases] == [
        "第一步：单位正方形",
        "第二步：矩阵变换得到的平行四边形",
    ]
    # 案例正文必须写出矩阵本身，并说明是矩阵变换把单位正方形送过去。
    case_text = "\n".join(
        line for example in explanation.worked_examples for line in example.calculation
    )
    assert r"\boldsymbol A=\begin{pmatrix} 2 & 1 \\ 1 & 3 \end{pmatrix}" in case_text
    assert "矩阵变换" in case_text
    assert "a=2" in case_text and "d=3" in case_text
    assert explanation.case_layout.default_pane_count == 2

    artifact = runtime_teaching_store().published("ch03.det.oriented-area").artifact
    compiled = VisualSemanticsCompiler().compile(
        artifact, context=RenderContext.default("ch03.det.oriented-area")
    )
    # 第二步用外接矩形加两条切角辅助线说明 ad - bc：四条边 + 两条辅助线都是虚线。
    second = case_plan(compiled, "stage.case.ch03.det.oriented-area.2")
    dashed = [operation for operation in second.operations if operation.get("style") == "dashed"]
    assert len(dashed) == 6
    labels = {
        str(operation.get("text"))
        for operation in second.operations
        if operation.get("op") == "annotation.upsert"
    }
    assert {"(a+b)(c+d)=12", "ad-bc=5", "-1.5", "-2"} <= labels
    # 第一步窗格只画单位正方形与两条标准基向量，不含外接矩形构造。
    first = case_plan(compiled, "stage.case.ch03.det.oriented-area.1")
    assert not any(operation.get("style") == "dashed" for operation in first.operations)
    assert {str(operation.get("label")) for operation in first.operations if operation.get("label")} == {
        "e1",
        "e2",
    }


def test_section_2_9_keeps_only_independence_and_rank() -> None:
    """2.9 目录只剩「线性无关与线性相关」「秩」两条，小节显示名为「2.9 线性无关与秩」。"""

    from linear_algebra.catalog.manifest import lecture_manifest, topic_entries

    section = next(node for node in lecture_manifest() if node.id == "ch02.s29")
    assert (section.title, section.children) == (
        "2.9 线性无关与秩",
        ("ch02.subspace.independence", "ch02.subspace.rank"),
    )
    assert [(topic.id, topic.title) for topic in topic_entries() if topic.section_id == "ch02.s29"] == [
        ("ch02.subspace.independence", "线性无关与线性相关"),
        ("ch02.subspace.rank", "秩"),
    ]
    # 讲义原文、锚点与既有编号体系不动：只有软件目录名被 display_title 覆盖。
    assert section.source_path[1] == "2.9 秩、零空间与列空间（为第4章准备的代数工具）"
    assert all(
        topic.source_path[1] == "2.9 秩、零空间与列空间（为第4章准备的代数工具）"
        for topic in topic_entries()
        if topic.section_id == "ch02.s29"
    )


def test_independence_publishes_the_lecture_verbatim_with_three_panes() -> None:
    """2.9.1 逐字给出定义 2.10/2.11、几何理解表与口诀，案例由定义自定（三窗格）。"""

    explanation = runtime_teaching_store().published("ch02.subspace.independence").artifact.explanation
    assert [(section.id, section.title) for section in explanation.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    for required in (
        "**（线性无关）**",
        r"$\boldsymbol v_{1}, \boldsymbol v_{2}, ..., \boldsymbol v_{k}$",
        r"$$c_{1} \cdot \boldsymbol v_{1} + c_{2} \cdot \boldsymbol v_{2} + ... + c_{k} \cdot \boldsymbol v_{k} = 0 \Rightarrow c_{1} = c_{2} = ... = c_{k} = 0$$",
        "**（线性相关）**",
        r'换句话说，线性相关 $=$ 至少有一个向量可以被其他向量"拼出来"。',
        "几何理解（最核心）：",
        r"| 3个在 $R^{3}$ | 不共面（三个方向张成整个空间） | 共面 |",
        r'💡 记忆口诀：线性无关 $=$ 每个向量都是"必要的"，少一个就不完整。',
    ):
        assert required in explanation.definition
    # 讲义这两节只有定义（公式写在定义块内），不再单列「公式」或「几何意义」分节。
    assert explanation.formula == ""
    assert explanation.geometric_meaning == ""
    assert explanation.derivation == ()
    assert [case.purpose for case in explanation.case_layout.cases] == [
        "第一步：两个方向不同（线性无关）",
        "第二步：两个方向相同（线性相关）",
        "第三步：三个向量中有一个能被拼出来（必相关）",
    ]
    assert explanation.case_layout.default_pane_count == 3
    examples = explanation.worked_examples
    assert [example.given for example in examples] == [
        (((2, -1), (1, 2)), (1, 1)),
        (((2, -2), (1, -1)), (1, 1)),
        (((2, -1), (1, 2)), (1, 1)),
    ]
    assert [example.result for example in examples] == [(1, 3), (0, 0), (1, 3)]
    case_text = "\n".join(line for example in examples for line in example.calculation)
    # 案例文本里的向量与矩阵统一按《数学解释规则》加粗。
    for required in (
        r"$\boldsymbol v_{1}=(2,1)$",
        r"$\boldsymbol v_{2}=(-2,-1)=-\boldsymbol v_{1}$",
        r"$\boldsymbol v_{3}=(1,3)$",
    ):
        assert required in case_text


def test_rank_publishes_the_lecture_tables_with_four_panes() -> None:
    """2.9.2 逐字给出定义 2.12、几何理解、矩阵表与定理 2.6；案例用表里四个矩阵。"""

    explanation = runtime_teaching_store().published("ch02.subspace.rank").artifact.explanation
    assert [(section.id, section.title) for section in explanation.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    for required in (
        "**（秩）**",
        r"$\operatorname{rank}(\boldsymbol A)$",
        r'简单理解：秩 $=$ 矩阵"真正有效"的列数',
        "几何理解：",
        r'秩 $=$ 变换后空间的"真实维度"',
        r'$\operatorname{rank} = 1 \rightarrow$  变换后是一条"线"（压缩了一维）',
        r"| $\begin{pmatrix}1 & 2 \\ 2 & 4\end{pmatrix}$ | 1 | 两列共线 $\rightarrow$ 只张成一条线 |",
        r"| $\begin{pmatrix}0 & 0 \\ 0 & 0\end{pmatrix}$ | 0 | 全压到原点 |",
        "**（秩与行列式）**",
        r"$\operatorname{rank}(\boldsymbol A) = n \Leftrightarrow \det(\boldsymbol A) \neq 0 \Leftrightarrow \boldsymbol A$",
    ):
        assert required in explanation.definition
    assert explanation.formula == ""
    assert explanation.geometric_meaning == ""
    assert [case.purpose for case in explanation.case_layout.cases] == [
        "第一步：什么都没压扁（秩 2）",
        "第二步：y 方向被压到零（秩 1）",
        "第三步：两列共线（秩 1）",
        "第四步：全压到原点（秩 0）",
    ]
    assert explanation.case_layout.default_pane_count == 4
    examples = explanation.worked_examples
    assert [example.given for example in examples] == [
        ((1, 0), (0, 1)),
        ((2, 0), (0, 0)),
        ((1, 2), (2, 4)),
        ((0, 0), (0, 0)),
    ]
    assert [example.kind for example in examples] == ["determinant"] * 4
    # 四个矩阵的行列式与讲义表格一致（det = 1、0、0、0）。
    assert [example.result for example in examples] == [1.0, 0.0, 0.0, 0.0]
    assert [example.checks[0].expected for example in examples] == [1.0, 0.0, 0.0, 0.0]


def test_section_2_9_case_panes_share_one_fixed_view() -> None:
    """2.9 的数学案例流程默认“全部显示”：各窗格落在同一个取景下，不出现一大一小。"""

    store = runtime_teaching_store()
    compiler = VisualSemanticsCompiler()
    for topic_id, pane_count in (
        ("ch02.subspace.independence", 3),
        ("ch02.subspace.rank", 4),
    ):
        artifact = store.published(topic_id).artifact
        compiled = compiler.compile(artifact, context=RenderContext.default(topic_id))
        assert len(compiled.storyboard) == pane_count
        view = compiled.plan.operations[-1]
        assert view["op"] == "view.fit" and view.get("bounds")
        for stage in compiled.storyboard:
            plan = case_plan(compiled, stage.id)
            assert plan.operations
    # 秩的四个窗格都以默认视野（±3）为基准，只为讲义表格里的列 (2, 4) 向上让出空间。
    rank = compiler.compile(
        store.published("ch02.subspace.rank").artifact,
        context=RenderContext.default("ch02.subspace.rank"),
    )
    assert rank.plan.operations[-1]["bounds"] == [-3.0, 3.0, -3.0, 4.0]


def _pane_radius(plan) -> float:
    """Return the bounding-sphere radius of the objects that frame one case pane.

    The matrix-case grid is deliberately sampled far beyond the pane viewport and
    clipped by the viewport, so the pane camera ignores it (it is hidden while
    the camera is fitted); it therefore does not take part in the shared view.
    """

    points = [
        (float(operation["coordinates"][0]), float(operation["coordinates"][1]))
        for operation in plan.operations
        if operation.get("op") == "point.upsert"
    ]
    points.extend(
        (float(operation["position"][0]), float(operation["position"][1]))
        for operation in plan.operations
        if operation.get("op") in {"annotation.upsert", "annotation.formula"}
    )
    if not points:
        return 0.0
    width = max(point[0] for point in points) - min(point[0] for point in points)
    height = max(point[1] for point in points) - min(point[1] for point in points)
    return math.hypot(width / 2.0, height / 2.0)


def test_matrix_vector_case_panes_share_one_fixed_view() -> None:
    """数学案例流程默认“全部显示”：各窗格内容都落在同一个取景下，不出现一大一小。"""

    store = runtime_teaching_store()
    compiler = VisualSemanticsCompiler()
    for topic_id, pane_count in (
        ("ch02.matrix.transformed-grid", 4),
        ("ch02.matrix.basis", 2),
    ):
        artifact = store.published(topic_id).artifact
        compiled = compiler.compile(artifact, context=RenderContext.default(topic_id))
        assert len(compiled.storyboard) == pane_count
        view = compiled.plan.operations[-1]
        assert view["op"] == "view.fit" and view.get("bounds")
        for stage in compiled.storyboard:
            plan = case_plan(compiled, stage.id)
            assert plan.operations
            # 窗格相机的取景下界是 6.5：参与取景的内容半径不超过它，各窗格才共用同一缩放。
            assert _pane_radius(plan) <= 6.5, (topic_id, stage.id)
