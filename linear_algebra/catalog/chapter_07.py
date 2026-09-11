from pathlib import Path
from .chapter_04 import _records
from .model import LessonEntry, topic_entry
CHAPTER = "第7章 特征值与特征向量"
_IDS = ("eigen.direction", "characteristic-polynomial", "eigenspace", "diagonalization", "gram-schmidt", "orthogonal-transform")
def _make():
    records = _records((Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8"), 7)
    chosen = [next(item for item in records if item[0][0].startswith("第7章") and item[2].startswith(prefix)) for prefix in ("7.1.1", "7.2.1", "7.3", "7.4", "7.5", "7.6")]
    return tuple(topic_entry(topic_id=f"ch07.{item}", chapter_number=7, section_id=f"ch07.s{index + 1}", title=record[2], source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)), heading_path=record[0], heading_level=record[1], required_capabilities=("transformed_grid",)) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
