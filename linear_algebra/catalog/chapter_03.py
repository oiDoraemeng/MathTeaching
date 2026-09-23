from .model import LessonEntry, topic_entry

CHAPTER = "第3章 行列式"

TOPICS: tuple[LessonEntry, ...] = (
    # 3.1 目录在软件中合并为单一小节「行列式的几何定义」，内容为讲义
    # 3.1.1–3.1.3 原文（定义 3.1、定理 3.1、几何意义速查）。讲义原文不改，
    # 因此锚点取整个 3.1 小节；目录显示名只由 display_title 覆盖，source_path
    # 必须与已发布 artifact 的来源锚点逐字一致（改它会触发 bundle_mismatch）。
    topic_entry(topic_id="ch03.det.oriented-area", chapter_number=3, section_id="ch03.s31", title="行列式的几何定义", source_path=(CHAPTER, "行列式的几何意义", "3.1.1 行列式的几何定义"), heading_path=(CHAPTER, "3.1 问题引入：变换对面积的缩放"), heading_level=3, required_capabilities=("oriented_area_2d", "polygon_2d"), display_title="3.1 行列式的几何意义"),
    # 3.2 按讲义中的三个定理分成三个可选小节：行列式的基本性质、乘积的行列式、转置不变性。
    # 三个主题共用 3.2 原文锚点；第三段 source_path 只作为目录/检索显示名，不改讲义。
    topic_entry(topic_id="ch03.det.basic-properties", chapter_number=3, section_id="ch03.s32", title="行列式的基本性质", source_path=(CHAPTER, "3.2 行列式的核心性质", "定理 3.2（行列式的基本性质）"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.det.multiplicativity", chapter_number=3, section_id="ch03.s32", title="乘积的行列式", source_path=(CHAPTER, "3.2 行列式的核心性质", "定理 3.3（乘积的行列式）"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.det.transpose", chapter_number=3, section_id="ch03.s32", title="转置不变性", source_path=(CHAPTER, "3.2 行列式的核心性质", "定理 3.4（转置不变性）"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d",)),
    # 3.3--3.6 按要求只显示讲义和文字数学案例，不创建绘图窗格。
    topic_entry(topic_id="ch03.cramer.area-ratio", chapter_number=3, section_id="ch03.s33", title="克拉默法则的面积比解方程组", source_path=(CHAPTER, "3.3 克拉默法则", "面积比解方程组"), heading_path=(CHAPTER, "3.3 克拉默法则"), heading_level=3, required_capabilities=()),
    # 3.4.1--3.4.3 合并到父目录下唯一的小节「逆矩阵」。
    topic_entry(topic_id="ch03.inverse.undo", chapter_number=3, section_id="ch03.s34", title="逆矩阵", source_path=(CHAPTER, "3.4 逆矩阵", "3.4.1 定义与几何"), heading_path=(CHAPTER, "3.4 逆矩阵"), heading_level=3, required_capabilities=()),
    # 目录省略讲义标题中的「（选学）」；来源锚点仍保留原文标题。
    topic_entry(topic_id="ch03.adjugate.matrix", chapter_number=3, section_id="ch03.s35", title="伴随矩阵", source_path=(CHAPTER, "3.5 伴随矩阵（选学）", "伴随矩阵"), heading_path=(CHAPTER, "3.5 伴随矩阵（选学）"), heading_level=3, required_capabilities=(), display_title="3.5 伴随矩阵"),
    topic_entry(topic_id="ch03.det.zero.equivalence", chapter_number=3, section_id="ch03.s36", title="det=0 的等价几何条件", source_path=(CHAPTER, "3.6 $\\det = 0$ 的深度解释", "det=0 的等价几何条件"), heading_path=(CHAPTER, "3.6 $\\det = 0$ 的深度解释"), heading_level=3, required_capabilities=()),
)
