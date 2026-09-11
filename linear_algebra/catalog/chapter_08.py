from pathlib import Path
from .chapter_04 import _records
from .model import LessonEntry, topic_entry
CHAPTER = "第8章 二次型与主轴定理"
_IDS = ("quadratic.matrix-form", "quadratic.level-sets", "principal-axis", "definiteness", "completing-square", "congruence-inertia")
def _make():
    records = _records((Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8"), 8)
    chosen = [next(item for item in records if item[0][0].startswith("第8章") and item[2].startswith(prefix)) for prefix in ("8.1", "8.2", "8.3.1", "8.4", "8.4 配", "8.5")]
    return tuple(topic_entry(topic_id=f"ch08.{item}", chapter_number=8, section_id=f"ch08.s{index + 1}", title=record[2], source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)), heading_path=record[0], heading_level=record[1], required_capabilities=("subspace_region",)) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
