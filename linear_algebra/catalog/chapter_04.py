from pathlib import Path
import re
from .model import LessonEntry, topic_entry
from linear_algebra.chapter_04_semantics import semantic_for

CHAPTER = "第4章 线性空间、线性无关与线性变换"
_IDS = ("subspace.col-null", "dependence.redundancy", "basis.definition", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns")
_PREFIXES = ("4.1 线性空间与子空间", "4.2.2", "4.3.1", "4.4.1", "4.4.2", "4.4.3")
# 4.1.1–4.1.3 在软件中合并为单一小节「线性空间」；4.2.1–4.2.2、4.3.1–4.3.3 同理。
# 讲义原文不改，锚点提升到各自的父小节，目录显示名仅是软件侧展示决策。
_DISPLAY_TITLES = {
    "subspace.col-null": "线性空间",
    "dependence.redundancy": "线性相关与线性无关",
    "basis.definition": "基的定义",
}
_MERGED_SECTIONS = {
    "subspace.col-null": ("4.1 线性空间与子空间", "线性空间"),
    # 目录只显示一个合并条目；来源仓库再精确合并 4.2.1 与 4.2.2，不能把后续的
    # 4.2.3、4.2.4 一并纳入。
    "dependence.redundancy": ("4.2 线性组合、线性相关与线性无关", "线性相关与线性无关", "4.2.1 生成集 Span"),
    "basis.definition": ("4.3 基与维数", "基的定义"),
}
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
            # 合并后的小节锚点覆盖整个父小节；来源路径仍逐字给出讲义标题。
            heading_path = (record[0][0], merged[0], merged[2]) if len(merged) == 3 else (record[0][0], merged[0])
            heading_level = 4 if len(merged) == 3 else 3
            source_path: tuple[str, str, str] = (record[0][0], merged[0], merged[1])
        else:
            heading_path = record[0]
            heading_level = record[1]
            source_path = record[0][-3:] if len(record[0]) >= 3 else (*record[0], record[2])
        return topic_entry(topic_id=f"ch04.{item}", chapter_number=4, section_id=section_id(record), title=_DISPLAY_TITLES.get(item, record[2]), source_path=source_path, heading_path=heading_path, heading_level=heading_level, required_capabilities=semantic_for(f"ch04.{item}").capabilities)

    return tuple(entry(item, record) for item, record in zip(_IDS, chosen))
TOPICS = _make()
def entries() -> tuple[LessonEntry, ...]: return TOPICS
