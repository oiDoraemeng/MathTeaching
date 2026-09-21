from .model import LessonEntry, topic_entry

CHAPTER = "第1章 向量与几何测量"

TOPICS: tuple[LessonEntry, ...] = (
    topic_entry(topic_id="ch01.vector.magnitude", chapter_number=1, section_id="ch01.s11", title="什么是向量", source_path=(CHAPTER, "1.1 向量的几何表示", "1.1.1 什么是向量"), heading_path=(CHAPTER, "1.1 向量的几何表示", "1.1.1 什么是向量"), heading_level=4, required_capabilities=("vector_2d",)),
    topic_entry(topic_id="ch01.ops.addition", chapter_number=1, section_id="ch01.s12", title="向量加法", source_path=(CHAPTER, "1.2 向量的线性运算", "1.2.1 向量加法"), heading_path=(CHAPTER, "1.2 向量的线性运算", "1.2.1 向量加法"), heading_level=4, required_capabilities=("vector_2d", "polygon_2d")),
    topic_entry(topic_id="ch01.ops.subtraction", chapter_number=1, section_id="ch01.s12", title="向量减法", source_path=(CHAPTER, "1.2 向量的线性运算", "1.2.2 向量减法"), heading_path=(CHAPTER, "1.2 向量的线性运算", "1.2.2 向量减法"), heading_level=4, required_capabilities=("vector_2d", "projection_2d")),
    topic_entry(topic_id="ch01.ops.scalar", chapter_number=1, section_id="ch01.s12", title="向量数乘", source_path=(CHAPTER, "1.2 向量的线性运算", "1.2.3 向量数乘"), heading_path=(CHAPTER, "1.2 向量的线性运算", "1.2.3 向量数乘"), heading_level=4, required_capabilities=("vector_2d",)),
    topic_entry(topic_id="ch01.ops.linear-combination", chapter_number=1, section_id="ch01.s12", title="线性组合", source_path=(CHAPTER, "1.2 向量的线性运算", "1.2.4 线性组合"), heading_path=(CHAPTER, "1.2 向量的线性运算", "1.2.4 线性组合"), heading_level=4, required_capabilities=("vector_2d", "polygon_2d")),
    topic_entry(topic_id="ch01.inner.definitions", chapter_number=1, section_id="ch01.s13", title="内积的两种定义", source_path=(CHAPTER, "1.3 内积", "1.3.1 内积的两种定义"), heading_path=(CHAPTER, "1.3 内积", "1.3.1 内积的两种定义"), heading_level=4, required_capabilities=("vector_2d", "angle_2d", "projection_2d")),
    topic_entry(topic_id="ch01.inner.cauchy-schwarz", chapter_number=1, section_id="ch01.s13", title="柯西—施瓦茨不等式", source_path=(CHAPTER, "1.3 内积", "1.3.3 柯西-施瓦茨不等式"), heading_path=(CHAPTER, "1.3 内积", "1.3.3 柯西-施瓦茨不等式"), heading_level=4, required_capabilities=("vector_2d", "projection_2d", "polygon_2d")),
    topic_entry(topic_id="ch01.projection.definition", chapter_number=1, section_id="ch01.s14", title="投影的定义", source_path=(CHAPTER, "1.4 投影", "1.4.1 投影的定义"), heading_path=(CHAPTER, "1.4 投影", "1.4.1 投影的定义"), heading_level=4, required_capabilities=("vector_2d", "projection_2d", "right_angle_2d")),
    topic_entry(topic_id="ch01.proof.midline", chapter_number=1, section_id="ch01.s15", title="三角形中位线定理", source_path=(CHAPTER, "1.5 几何证明：向量的威力", "1.5.2 核心例题：三角形中位线定理"), heading_path=(CHAPTER, "1.5 几何证明：向量的威力", "1.5.2 核心例题：三角形中位线定理"), heading_level=4, required_capabilities=("vector_2d", "polygon_2d")),
    topic_entry(topic_id="ch01.proof.centroid", chapter_number=1, section_id="ch01.s15", title="三角形重心定理", source_path=(CHAPTER, "1.5 几何证明：向量的威力", "补充例题：三角形重心定理"), heading_path=(CHAPTER, "1.5 几何证明：向量的威力", "1.5.2 核心例题：三角形中位线定理", "补充例题：三角形重心定理"), heading_level=5, required_capabilities=("vector_2d", "polygon_2d", "annotation_formula")),
    topic_entry(topic_id="ch01.proof.parallelogram-diagonals", chapter_number=1, section_id="ch01.s15", title="平行四边形对角线互相平分", source_path=(CHAPTER, "1.5 几何证明：向量的威力", "补充例题：平行四边形对角线互相平分"), heading_path=(CHAPTER, "1.5 几何证明：向量的威力", "1.5.2 核心例题：三角形中位线定理", "补充例题：平行四边形对角线互相平分"), heading_level=5, required_capabilities=("vector_2d", "polygon_2d")),
)
