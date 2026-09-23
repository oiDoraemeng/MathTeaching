from pathlib import Path
from .chapter_04 import _records
from .model import LessonEntry, topic_entry
CHAPTER = "第6章 基变换与相似变换"
_IDS = ("basis-change.coordinates", "similarity-transform")
_PREFIXES = ("6.2", "6.3")
_TITLES = ("基变换", "相似变换")
def _make():
    records = _records((Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8"), 6)
    chosen = [next(item for item in records if item[0][0].startswith("第6章") and item[2].startswith(prefix)) for prefix in _PREFIXES]
    return tuple(topic_entry(topic_id=f"ch06.{item}", chapter_number=6, section_id=f"ch06.s{index + 2}", title=_TITLES[index], source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)), heading_path=record[0], heading_level=record[1], required_capabilities=("transformed_grid",)) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
