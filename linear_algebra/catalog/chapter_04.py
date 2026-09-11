from .model import LessonEntry, topic_entry

CHAPTER = "第4章 线性空间、线性无关与线性变换"
_IDS = ("space.closure", "subspace.classification", "subspace.intersection", "subspace.col-null", "span.dimension", "dependence.redundancy", "nullspace.test", "rank.collapse", "basis.span", "dimension.ladder", "coordinates.readout", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity")
TOPICS = tuple(topic_entry(topic_id=f"ch04.{item}", chapter_number=4, section_id=f"ch04.s{index + 1}", title=item.replace("-", " "), source_path=(CHAPTER, item, item), heading_path=(CHAPTER, item, item), heading_level=2, required_capabilities=("subspace_region",)) for index, item in enumerate(_IDS))
def entries() -> tuple[LessonEntry, ...]: return TOPICS
