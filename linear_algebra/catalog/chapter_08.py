from .model import LessonEntry, topic_entry
CHAPTER = "第8章 二次型与主轴定理"
_IDS = ("quadratic.matrix-form", "quadratic.level-sets", "principal-axis", "definiteness", "completing-square", "congruence-inertia")
TOPICS = tuple(topic_entry(topic_id=f"ch08.{item}", chapter_number=8, section_id=f"ch08.s{index + 1}", title=item.replace("-", " "), source_path=(CHAPTER, item, item), heading_path=(CHAPTER, item, item), heading_level=2, required_capabilities=("subspace_region",)) for index, item in enumerate(_IDS))
def entries() -> tuple[LessonEntry, ...]: return TOPICS
