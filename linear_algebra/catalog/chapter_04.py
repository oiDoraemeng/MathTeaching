from pathlib import Path
import re
from .model import LessonEntry, topic_entry
from linear_algebra.chapter_04_semantics import semantic_for

CHAPTER = "第4章 线性空间、线性无关与线性变换"
_IDS = ("space.closure", "subspace.classification", "subspace.intersection", "subspace.col-null", "span.dimension", "dependence.redundancy", "nullspace.test", "rank.collapse", "basis.span", "dimension.ladder", "coordinates.readout", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity")
_PREFIXES = ("4.1.1", "4.1.2", "4.1.2", "4.1.3", "4.2.1", "4.2.2", "4.2.3", "4.2.4", "4.3.1", "4.3.2", "4.3.3", "4.4.1", "4.4.2", "4.4.3", "4.5.1", "4.5.2")
def _records(text, chapter_number=4):
    lines=text.splitlines(); chapter=None; stack=[]; out=[]
    for line in lines:
        m=re.match(r'^(#{1,6})\s+(.+?)\s*$',line)
        if not m: continue
        level=len(m.group(1)); title=m.group(2).strip()
        if title.startswith(f'第{chapter_number}章'): chapter=title; stack=[(1,title)]
        elif chapter and re.match(r'^\d+\.', title):
            stack=[x for x in stack if x[0]<level]; stack.append((level,title)); out.append((tuple(x[1] for x in stack),level,title))
    return out
def _make() -> tuple[LessonEntry, ...]:
    source = Path(__file__).parents[2] / ".agents" / "线性代数讲义.md"
    records = _records(source.read_text(encoding="utf-8"))
    chosen = [next(item for item in records if item[2].startswith(prefix)) for prefix in _PREFIXES]
    return tuple(topic_entry(topic_id=f"ch04.{item}", chapter_number=4, section_id=f"ch04.s{index + 1}", title=record[2], source_path=(record[0][-3:] if len(record[0]) >= 3 else record[0] + (record[2],)), heading_path=record[0], heading_level=record[1], required_capabilities=semantic_for(f"ch04.{item}").capabilities) for index, (item, record) in enumerate(zip(_IDS, chosen)))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
