from pathlib import Path
from .chapter_04 import _records
from .model import LessonEntry, topic_entry
CHAPTER = "第5章 线性方程组"
_IDS = ("homogeneous.solution-space", "affine.solution-set", "consistency.geometry", "gaussian-elimination", "least-squares.projection")
_PREFIXES = ("5.1", "5.2", "5.3", "5.4", "5.5")
_TITLES = ("齐次线性方程组", "非齐次方程组的解结构", "解的存在性与唯一性", "高斯消元", "最小二乘解")
def _make():
    records = _records((Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8"), 5)
    chosen = [next(item for item in records if item[0][0].startswith("第5章") and item[2].startswith(prefix)) for prefix in _PREFIXES]
    return tuple(topic_entry(topic_id=f"ch05.{item}", chapter_number=5, section_id=f"ch05.s{index + 1}", title=_TITLES[index], source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)), heading_path=record[0], heading_level=record[1], required_capabilities=("subspace_region",)) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
