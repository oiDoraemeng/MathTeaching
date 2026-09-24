"""Versioned runtime catalog metadata; independent of lecture source files."""

from .model import LessonEntry, topic_entry

CHAPTERS = {
    4: '第4章 线性空间、线性无关与线性变换（全书核心枢纽）',
    5: '第5章 线性方程组',
    6: '第6章 基变换与相似变换',
    7: '第7章 特征值与特征向量',
    8: '第8章 二次型与主轴定理',
}

_TOPICS: tuple[LessonEntry, ...] = (
    topic_entry(topic_id='ch04.subspace.col-null', chapter_number=4, section_id='ch04.s41', title='线性空间', source_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.1 线性空间与子空间', '线性空间'), heading_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.1 线性空间与子空间'), heading_level=3, required_capabilities=('vector_3d', 'subspace_region', 'linear3d', 'plane3d'), occurrence=1, display_title=''),
    topic_entry(topic_id='ch04.dependence.redundancy', chapter_number=4, section_id='ch04.s42', title='线性相关与线性无关', source_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.2 线性组合、线性相关与线性无关', '线性相关与线性无关'), heading_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.2 线性组合、线性相关与线性无关', '4.2.1 生成集 Span'), heading_level=4, required_capabilities=('vector_3d', 'subspace_region', 'linear3d', 'plane3d'), occurrence=1, display_title=''),
    topic_entry(topic_id='ch04.basis.definition', chapter_number=4, section_id='ch04.s43', title='基的定义', source_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.3 基与维数', '基的定义'), heading_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.3 基与维数'), heading_level=3, required_capabilities=('transformed_grid', 'vector_2d'), occurrence=1, display_title=''),
    topic_entry(topic_id='ch04.linear-map.definition', chapter_number=4, section_id='ch04.s44', title='线性变换的定义', source_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.4 线性变换', '线性变换的定义'), heading_path=('第4章 线性空间、线性无关与线性变换（全书核心枢纽）', '4.4 线性变换', '4.4.1 线性变换的定义'), heading_level=4, required_capabilities=('transformed_grid', 'vector_2d', 'polygon_2d'), occurrence=1, display_title=''),
    topic_entry(topic_id='ch05.homogeneous.solution-space', chapter_number=5, section_id='ch05.s1', title='齐次线性方程组', source_path=('第5章 线性方程组', '5.1 齐次方程组 $Ax = 0$', '5.1 齐次方程组 $Ax = 0$'), heading_path=('第5章 线性方程组', '5.1 齐次方程组 $Ax = 0$'), heading_level=3, required_capabilities=('subspace_region',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch05.affine.solution-set', chapter_number=5, section_id='ch05.s2', title='非齐次方程组的解结构', source_path=('第5章 线性方程组', '5.2 非齐次方程组 $Ax = b$', '5.2 非齐次方程组 $Ax = b$'), heading_path=('第5章 线性方程组', '5.2 非齐次方程组 $Ax = b$'), heading_level=3, required_capabilities=('subspace_region',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch05.consistency.geometry', chapter_number=5, section_id='ch05.s3', title='解的存在性与唯一性', source_path=('第5章 线性方程组', '5.3 解的存在性与唯一性', '5.3 解的存在性与唯一性'), heading_path=('第5章 线性方程组', '5.3 解的存在性与唯一性'), heading_level=3, required_capabilities=('subspace_region',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch05.gaussian-elimination', chapter_number=5, section_id='ch05.s4', title='高斯消元', source_path=('第5章 线性方程组', '5.4 高斯消元', '5.4 高斯消元'), heading_path=('第5章 线性方程组', '5.4 高斯消元'), heading_level=3, required_capabilities=('subspace_region',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch05.least-squares.projection', chapter_number=5, section_id='ch05.s5', title='最小二乘解', source_path=('第5章 线性方程组', '5.5 最小二乘问题（选学阅读）', '5.5 最小二乘问题（选学阅读）'), heading_path=('第5章 线性方程组', '5.5 最小二乘问题（选学阅读）'), heading_level=3, required_capabilities=('subspace_region',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch06.basis-change.coordinates', chapter_number=6, section_id='ch06.s2', title='基变换', source_path=('第6章 基变换与相似变换', '6.2 基变换——同一个向量在不同基下的坐标', '6.2 基变换——同一个向量在不同基下的坐标'), heading_path=('第6章 基变换与相似变换', '6.2 基变换——同一个向量在不同基下的坐标'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch06.similarity-transform', chapter_number=6, section_id='ch06.s3', title='相似变换', source_path=('第6章 基变换与相似变换', '6.3 相似变换——同一个变换在不同基下的矩阵', '6.3 相似变换——同一个变换在不同基下的矩阵'), heading_path=('第6章 基变换与相似变换', '6.3 相似变换——同一个变换在不同基下的矩阵'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch07.eigen.direction', chapter_number=7, section_id='ch07.s1', title='特征值与特征向量', source_path=('第7章 特征值与特征向量', '7.1 定义与几何意义', '特征值与特征向量'), heading_path=('第7章 特征值与特征向量', '7.1 定义与几何意义'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch07.characteristic-polynomial', chapter_number=7, section_id='ch07.s2', title='特征多项式', source_path=('第7章 特征值与特征向量', '7.2 特征多项式', '特征多项式'), heading_path=('第7章 特征值与特征向量', '7.2 特征多项式'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch07.eigenspace', chapter_number=7, section_id='ch07.s3', title='求特征向量', source_path=('第7章 特征值与特征向量', '7.3 求特征向量', '求特征向量'), heading_path=('第7章 特征值与特征向量', '7.3 求特征向量'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch07.diagonalization', chapter_number=7, section_id='ch07.s4', title='对角化的几何意义', source_path=('第7章 特征值与特征向量', '7.4 对角化的几何意义', '对角化的几何意义'), heading_path=('第7章 特征值与特征向量', '7.4 对角化的几何意义'), heading_level=3, required_capabilities=('transformed_grid',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch08.quadratic.matrix-form', chapter_number=8, section_id='ch08.s1', title='二次型', source_path=('第8章 二次型与主轴定理', '8.1 二次型的定义与矩阵表示', '8.1 二次型的定义与矩阵表示'), heading_path=('第8章 二次型与主轴定理', '8.1 二次型的定义与矩阵表示'), heading_level=3, required_capabilities=('quadratic_level_set',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch08.quadratic.level-sets', chapter_number=8, section_id='ch08.s2', title='二次型的几何意义', source_path=('第8章 二次型与主轴定理', '8.2 二次型的几何意义', '8.2 二次型的几何意义'), heading_path=('第8章 二次型与主轴定理', '8.2 二次型的几何意义'), heading_level=3, required_capabilities=('quadratic_level_set',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch08.principal-axis', chapter_number=8, section_id='ch08.s3', title='主轴定理', source_path=('第8章 二次型与主轴定理', '8.3 主轴定理：把歪的图形"转正"', '8.3 主轴定理：把歪的图形"转正"'), heading_path=('第8章 二次型与主轴定理', '8.3 主轴定理：把歪的图形"转正"'), heading_level=3, required_capabilities=('quadratic_level_set',), occurrence=1, display_title=''),
    topic_entry(topic_id='ch08.definiteness', chapter_number=8, section_id='ch08.s4', title='定性：正定、负定、不定', source_path=('第8章 二次型与主轴定理', '8.4 定性：正定、负定、不定', '8.4 定性：正定、负定、不定'), heading_path=('第8章 二次型与主轴定理', '8.4 定性：正定、负定、不定'), heading_level=3, required_capabilities=('quadratic_level_set',), occurrence=1, display_title=''),
)

CHAPTER_4_TOPICS = tuple(topic for topic in _TOPICS if topic.chapter_number == 4)
CHAPTER_5_TOPICS = tuple(topic for topic in _TOPICS if topic.chapter_number == 5)
CHAPTER_6_TOPICS = tuple(topic for topic in _TOPICS if topic.chapter_number == 6)
CHAPTER_7_TOPICS = tuple(topic for topic in _TOPICS if topic.chapter_number == 7)
CHAPTER_8_TOPICS = tuple(topic for topic in _TOPICS if topic.chapter_number == 8)
