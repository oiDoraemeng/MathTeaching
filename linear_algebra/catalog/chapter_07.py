from pathlib import Path
from .chapter_04 import _records
from .model import LessonEntry, topic_entry
CHAPTER = "第7章 特征值与特征向量"
_IDS = ("eigen.direction", "characteristic-polynomial", "eigenspace", "diagonalization")
_PREFIXES = ("7.1 定义与几何意义", "7.2 特征多项式", "7.3 求特征向量", "7.4 对角化的几何意义")
_TITLES = ("特征值与特征向量", "特征多项式", "求特征向量", "对角化的几何意义")
def _make():
    records = _records((Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8"), 7)
    chosen = [next(item for item in records if item[0][0].startswith("第7章") and item[2].startswith(prefix)) for prefix in _PREFIXES]
    return tuple(topic_entry(topic_id=f"ch07.{item}", chapter_number=7, section_id=f"ch07.s{index + 1}", title=_TITLES[index], source_path=(record[0][0], record[2], _TITLES[index]), heading_path=record[0], heading_level=record[1], required_capabilities=("transformed_grid",)) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
