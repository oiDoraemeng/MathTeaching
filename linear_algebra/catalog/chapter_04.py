from pathlib import Path
import re
from .model import LessonEntry, topic_entry
from linear_algebra.chapter_04_semantics import semantic_for

CHAPTER = "第4章 线性空间、线性无关与线性变换"
_IDS = ("space.closure", "subspace.classification", "subspace.intersection", "subspace.col-null", "span.dimension", "dependence.redundancy", "nullspace.test", "rank.collapse", "basis.definition", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity")
_PREFIXES = ("4.1.1", "4.1.2", "4.1.2", "4.1.3", "4.2.1", "4.2.2", "4.2.3", "4.2.4", "4.3.1", "4.4.1", "4.4.2", "4.4.3", "4.5.1", "4.5.2")
# 一个讲义小节可以支撑多个可视化主题（例如 4.1.2 支撑「子空间」与「子空间的交与并」）。
# 目录里每个主题必须有唯一的显示名，否则同一小节会出现两条同名条目；标题只用于导航，
# 讲义锚点仍由 heading_path/source_path 逐字给出。
_DISPLAY_TITLES = {"subspace.intersection": "4.1.2 子空间的交与并", "basis.definition": "基的定义"}
# 4.3 目录在软件中合并为单一小节「基的定义」，正文逐字取讲义 4.3.1–4.3.3。讲义原文
# 不改，所以锚点提升到整个 4.3 小节；目录显示名与来源路径是软件侧的展示决策。
_MERGED_SECTIONS = {"basis.definition": ("4.3 基与维数", "基的定义")}
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
    def section_id(record: tuple[tuple[str, ...], int, str]) -> str:
        # Several visual topics live below one lecture section (for example
        # 4.1.1--4.1.3).  The tree must group them under that shared parent,
        # rather than creating one duplicate section node per topic.
        major = record[0][1].split(" ", 1)[0].replace(".", "")
        return f"ch04.s{major}"

    def entry(item: str, record: tuple[tuple[str, ...], int, str]) -> LessonEntry:
        merged = _MERGED_SECTIONS.get(item)
        if merged is not None:
            # 合并后的小节锚点覆盖整个 4.3；来源路径仍逐字给出讲义 4.3 标题。
            heading_path = (record[0][0], merged[0])
            heading_level = 3
            source_path: tuple[str, str, str] = (record[0][0], merged[0], merged[1])
        else:
            heading_path = record[0]
            heading_level = record[1]
            source_path = record[0][-3:] if len(record[0]) >= 3 else (*record[0], record[2])
        return topic_entry(topic_id=f"ch04.{item}", chapter_number=4, section_id=section_id(record), title=_DISPLAY_TITLES.get(item, record[2]), source_path=source_path, heading_path=heading_path, heading_level=heading_level, required_capabilities=semantic_for(f"ch04.{item}").capabilities)

    return tuple(entry(item, record) for item, record in zip(_IDS, chosen))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
