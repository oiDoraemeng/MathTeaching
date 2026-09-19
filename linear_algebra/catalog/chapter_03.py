from .model import LessonEntry, topic_entry

CHAPTER = "第3章 行列式"

TOPICS: tuple[LessonEntry, ...] = (
    # 3.1 目录在软件中合并为单一小节「行列式的几何定义」，内容为讲义
    # 3.1.1–3.1.3 原文（定义 3.1、定理 3.1、几何意义速查）。讲义原文不改，
    # 因此锚点取整个 3.1 小节；目录显示名只由 display_title 覆盖，source_path
    # 必须与已发布 artifact 的来源锚点逐字一致（改它会触发 bundle_mismatch）。
    topic_entry(topic_id="ch03.det.oriented-area", chapter_number=3, section_id="ch03.s31", title="行列式的几何定义", source_path=(CHAPTER, "行列式的几何意义", "3.1.1 行列式的几何定义"), heading_path=(CHAPTER, "3.1 问题引入：变换对面积的缩放"), heading_level=3, required_capabilities=("oriented_area_2d", "polygon_2d"), display_title="3.1 行列式的几何意义"),
    topic_entry(topic_id="ch03.det.row-swap", chapter_number=3, section_id="ch03.s32", title="交换两行翻转方向", source_path=(CHAPTER, "3.2 行列式的核心性质", "交换两行的方向变化"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.det.scaling", chapter_number=3, section_id="ch03.s32", title="一行数乘改变面积比例", source_path=(CHAPTER, "3.2 行列式的核心性质", "一行乘常数的面积变化"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.det.shear", chapter_number=3, section_id="ch03.s32", title="切变保持面积不变", source_path=(CHAPTER, "3.2 行列式的核心性质", "切变保持面积"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.det.multiplicativity", chapter_number=3, section_id="ch03.s32", title="det(AB) 的两阶段面积缩放", source_path=(CHAPTER, "3.2 行列式的核心性质", "det(AB) 的两阶段面积缩放"), heading_path=(CHAPTER, "3.2 行列式的核心性质"), heading_level=3, required_capabilities=("oriented_area_2d", "staged_transform")),
    topic_entry(topic_id="ch03.cramer.area-ratio", chapter_number=3, section_id="ch03.s33", title="克拉默法则的面积比解方程组", source_path=(CHAPTER, "3.3 克拉默法则", "面积比解方程组"), heading_path=(CHAPTER, "3.3 克拉默法则"), heading_level=3, required_capabilities=("oriented_area_2d", "polygon_2d", "annotation_formula")),
    topic_entry(topic_id="ch03.inverse.undo", chapter_number=3, section_id="ch03.s34", title="逆矩阵的几何撤销", source_path=(CHAPTER, "3.4 逆矩阵", "3.4.1 定义与几何"), heading_path=(CHAPTER, "3.4 逆矩阵", "3.4.1 定义与几何"), heading_level=4, required_capabilities=("staged_transform", "transformed_grid")),
    topic_entry(topic_id="ch03.inverse.formula", chapter_number=3, section_id="ch03.s34", title="2×2 求逆公式的几何参数", source_path=(CHAPTER, "3.4 逆矩阵", "3.4.2 $2 \\times 2$ 求逆公式"), heading_path=(CHAPTER, "3.4 逆矩阵", "3.4.2 $2 \\times 2$ 求逆公式"), heading_level=4, required_capabilities=("oriented_area_2d", "annotation_formula")),
    topic_entry(topic_id="ch03.inverse.examples", chapter_number=3, section_id="ch03.s34", title="可逆与退化变换的分层例题", source_path=(CHAPTER, "3.4 逆矩阵", "3.4.3 分层例题"), heading_path=(CHAPTER, "3.4 逆矩阵", "3.4.3 分层例题"), heading_level=4, required_capabilities=("staged_transform", "transformed_grid")),
    topic_entry(topic_id="ch03.det.zero.equivalence", chapter_number=3, section_id="ch03.s36", title="det=0 的等价几何条件", source_path=(CHAPTER, "3.6 $\\det = 0$ 的深度解释", "det=0 的等价几何条件"), heading_path=(CHAPTER, "3.6 $\\det = 0$ 的深度解释"), heading_level=3, required_capabilities=("oriented_area_2d", "subspace_region", "staged_transform")),
)
