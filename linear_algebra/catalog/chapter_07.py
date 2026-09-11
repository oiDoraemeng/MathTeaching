from .model import LessonEntry, topic_entry
CHAPTER = "第7章 特征值与特征向量"
_IDS = ("eigen.direction", "characteristic-polynomial", "eigenspace", "diagonalization", "gram-schmidt", "orthogonal-transform")
TOPICS = tuple(topic_entry(topic_id=f"ch07.{item}", chapter_number=7, section_id=f"ch07.s{index + 1}", title=item.replace("-", " "), source_path=(CHAPTER, item, item), heading_path=(CHAPTER, item, item), heading_level=2, required_capabilities=("transformed_grid",)) for index, item in enumerate(_IDS))
def entries() -> tuple[LessonEntry, ...]: return TOPICS
