"""Chapter 8 catalog: the four retained lecture sections."""

from pathlib import Path

from .chapter_04 import _records
from .model import LessonEntry, topic_entry


CHAPTER = "第8章 二次型与主轴定理"
_IDS = (
    "quadratic.matrix-form",
    "quadratic.level-sets",
    "principal-axis",
    "definiteness",
)
_PREFIXES = ("8.1", "8.2", "8.3", "8.4 定性")
_TITLES = ("二次型", "二次型的几何意义", "主轴定理", "定性：正定、负定、不定")


def _make() -> tuple[LessonEntry, ...]:
    source = (Path(__file__).parents[2] / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8")
    records = _records(source, 8)
    chosen = [
        next(item for item in records if item[0][0].startswith("第8章") and item[2].startswith(prefix))
        for prefix in _PREFIXES
    ]
    return tuple(
        topic_entry(
            topic_id=f"ch08.{topic_id}",
            chapter_number=8,
            section_id=f"ch08.s{index}",
            title=title,
            source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)),
            heading_path=record[0],
            heading_level=record[1],
            required_capabilities=("quadratic_level_set",),
        )
        for index, (topic_id, title, record) in enumerate(zip(_IDS, _TITLES, chosen), start=1)
    )


TOPICS = _make()


def entries() -> tuple[LessonEntry, ...]:
    return TOPICS
