from .model import LessonEntry, topic_entry
CHAPTER = "第5章 线性方程组"
_IDS = ("homogeneous.solution-space", "affine.solution-set", "consistency.geometry", "gaussian-elimination", "least-squares.projection", "fundamental-solution-system", "elementary-matrix-elimination", "least-squares-derivation")
TOPICS = tuple(topic_entry(topic_id=f"ch05.{item}", chapter_number=5, section_id=f"ch05.s{index + 1}", title=item.replace("-", " "), source_path=(CHAPTER, item, item), heading_path=(CHAPTER, item, item), heading_level=2, required_capabilities=("subspace_region",)) for index, item in enumerate(_IDS))
def entries() -> tuple[LessonEntry, ...]: return TOPICS
