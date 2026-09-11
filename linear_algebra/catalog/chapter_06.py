from .model import LessonEntry, topic_entry
CHAPTER = "第6章 基变换与相似变换"
_IDS = ("basis-change.motivation", "basis-change.coordinates", "similarity-transform")
TOPICS = tuple(topic_entry(topic_id=f"ch06.{item}", chapter_number=6, section_id=f"ch06.s{index + 1}", title=item.replace("-", " "), source_path=(CHAPTER, item, item), heading_path=(CHAPTER, item, item), heading_level=2, required_capabilities=("transformed_grid",)) for index, item in enumerate(_IDS))
def entries() -> tuple[LessonEntry, ...]: return TOPICS
