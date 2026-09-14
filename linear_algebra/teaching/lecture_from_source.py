"""Excerpt-grounded lecture prose for the generated teaching artifacts.

``.agents/线性代数讲义.md`` is the authoritative teaching text of this project.
Every artifact already carries the verbatim lecture excerpt of its section in
``source.excerpt``.  Chapters 3-8 previously had no lesson table, so the
generative pipeline fell back to the one-line deterministic template
(``f"{title} 的对象和定义。"``) and the software showed a summary instead of the
lecture.

This module routes the excerpt back into the explanation fields **without
rewriting a single character**: the lecture's own markers (``一句话动机`` /
``本节目标`` / ``定义`` / ``定理`` / ``推导`` / ``证明`` / ``例题`` / ``几何`` …
and the ``####`` sub-headings) decide which field each paragraph lands in, and
every non-empty body line is carried over verbatim.

Merging rules:

* a field that still holds the deterministic filler is *replaced* by the
  lecture text;
* a field that holds hand-authored prose (for example the ``lecture_ch02``
  lesson table) is *kept* and the lecture text is appended after it.

Nothing is compressed and nothing is invented.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

# The one-line placeholders emitted by the deterministic generator.
_TEMPLATE_DEFINITION = re.compile(r"^.+ 的对象和定义。$")
_TEMPLATE_SUMMARY = re.compile(r"^.+ 的确定性数学语义 artifact。$")

# Boilerplate body lines that carry no lecture content.
_FILLERS = frozenset({
    "与前置线性表示相连。",
    "向量在有限维空间中的方向和尺度保持可读。",
    "二维示意推广到有限维时保留代数关系。",
    "先识别对象，再核对公式和不变量。",
    "数值关系与讲义定义一致。",
    "先定义，再公式，最后读数值例。",
    "不要混淆对象和坐标。",
})

# Structured placeholders produced from relation parameters.
_FILLER_PATTERNS = (
    re.compile(r"^代入 v=\([\d,\s\.\-]+\)。$"),
    re.compile(r"^计算得到 result=.*。$"),
    re.compile(r"^(?:换到特征基|特征值独立缩放|换回标准坐标): .+$"),
)

DEFINITION = "definition"
DERIVATION = "derivation"
INTUITION = "intuition"
SUMMARY = "summary"
GEOMETRIC = "geometric_meaning"
PITFALLS = "pitfalls"
INVARIANTS = "invariants"
CONNECTIONS = "connections"
CONCLUSION = "conclusion"
READ_GUIDE = "read_guide"

# Lecture markers, most specific first, mapped to their explanation bucket.
_KEYWORD_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("证明", "证毕"), DERIVATION),
    (("一句话动机", "动机"), INTUITION),
    (("本节目标", "学习目标", "目标"), SUMMARY),
    (("本章小结", "小结", "总结", "要点回顾"), CONCLUSION),
    (("自检", "思考题", "练习题", "练习", "思考"), READ_GUIDE),
    (("误区", "易错", "注意", "警示", "反例", "常见错误"), PITFALLS),
    (("不变量",), INVARIANTS),
    (("连接", "关联", "联系", "对比", "补充说明"), CONNECTIONS),
    (("几何直观", "几何意义", "几何上", "直观理解", "几何"), GEOMETRIC),
    (("推导直觉", "推导", "验证", "三步走", "三步理解", "为什么"), DERIVATION),
    (("例题", "例", "补充例题"), DERIVATION),
    (("定理", "命题", "引理", "推论", "性质", "判据", "公式"), DEFINITION),
    (("定义", "概念"), DEFINITION),
)

_HEADING_PREFIX = re.compile(r"^\s*(?:#{1,6}\s*|>\s*|\*\s+|\-\s+|\d+\.\s+)*")
_HEADING_ONLY = re.compile(r"^\s*#{1,6}\s*")


def _is_filler_text(text: str) -> bool:
    """Return True when ``text`` holds no hand-authored lecture prose."""
    if not text.strip():
        return True
    if _TEMPLATE_DEFINITION.match(text.strip()) or _TEMPLATE_SUMMARY.match(text.strip()):
        return True
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in _FILLERS:
            continue
        if any(pattern.match(line) for pattern in _FILLER_PATTERNS):
            continue
        return False
    return True


def looks_like_template(explanation: Mapping[str, Any]) -> bool:
    """Return True when the definition/summary still look generated."""
    definition = str(explanation.get("definition", ""))
    summary = str(explanation.get("summary", ""))
    return bool(
        _TEMPLATE_DEFINITION.match(definition.strip())
        or _TEMPLATE_SUMMARY.match(summary.strip())
    )


def _head(line: str) -> str:
    """Strip markdown heading/list markers and surrounding space."""
    return _HEADING_PREFIX.sub("", line).strip()


def _bucket_for(line: str) -> str | None:
    head = _head(line)
    if not head:
        return None
    if "证明" in head or "推导" in head:
        return DERIVATION
    for keywords, bucket in _KEYWORD_RULES:
        if head.startswith(keywords):
            return bucket
    return None


def _is_inline_header(bucket: str, line: str) -> bool:
    """A ``本节目标：…`` style line opens a bucket without switching the rest."""
    return bucket in (SUMMARY, INTUITION) and not _HEADING_ONLY.match(line)


def route_excerpt(excerpt: str) -> tuple[str, dict[str, list[str]]]:
    """Split a lecture excerpt into labelled buckets, verbatim.

    Returns the section heading (if the excerpt starts with one) and a mapping
    from explanation bucket to the raw lines that belong to it.
    """
    lines = excerpt.splitlines()
    heading = ""
    for line in lines:
        if not line.strip():
            continue
        if _HEADING_ONLY.match(line):
            heading = _head(line)
        break

    buckets: dict[str, list[str]] = {}
    current = DEFINITION
    for line in lines:
        if not line.strip():
            continue
        bucket = _bucket_for(line)
        if bucket is not None and _is_inline_header(bucket, line):
            buckets.setdefault(bucket, []).append(line.rstrip())
            current = DEFINITION
            continue
        if bucket is not None:
            current = bucket
        buckets.setdefault(current, []).append(line.rstrip())

    # A ``本章小结`` without body text is really a definition header.
    conclusion_lines = buckets.get(CONCLUSION, [])
    if conclusion_lines and not _body_only(conclusion_lines):
        buckets[DEFINITION] = buckets.get(DEFINITION, []) + conclusion_lines
        del buckets[CONCLUSION]

    # ``本节目标：…`` / ``一句话动机：…`` keep only the marker line; the rest
    # of the block is real lecture body text that belongs to the definition.
    for bucket in (SUMMARY, INTUITION):
        header_lines = buckets.get(bucket, [])
        if len(header_lines) > 1:
            buckets[DEFINITION] = buckets.get(DEFINITION, []) + header_lines[1:]
            buckets[bucket] = header_lines[:1]

    return heading, buckets


def _paragraphs(lines: list[str]) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", "\n".join(lines))]
    return [block for block in blocks if block]


def _single(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line.strip()).strip()


def _inline(lines: list[str], keywords: tuple[str, ...]) -> str:
    """Return the first ``keywords``-prefixed heading verbatim, if any."""
    for line in lines:
        head = _head(line)
        for keyword in keywords:
            if head.startswith(keyword) and len(head) > len(keyword) + 1:
                return head
    return ""


def _body_only(lines: list[str]) -> list[str]:
    """Keep only real body lines (drop markdown heading-only markers)."""
    return [line for line in lines if not _HEADING_ONLY.match(line) and _head(line)]


def _merge_text(existing: Any, lecture: str) -> str:
    current = str(existing or "").strip()
    if not lecture:
        return "" if _is_filler_text(current) else current
    if _is_filler_text(current):
        return lecture
    if lecture in current:
        return current
    return f"{current}\n\n{lecture}"


def _merge_list(existing: Any, lecture: list[str]) -> list[str]:
    merged = [str(item).strip() for item in existing] if isinstance(existing, list) else []
    merged = [item for item in merged if item and not _is_filler_text(item)]
    for item in lecture:
        if item not in merged:
            merged.append(item)
    return merged


def _chapter_of(payload: Mapping[str, Any]) -> int | None:
    topic_id = str(payload.get("topic_id", ""))
    match = re.match(r"^ch(\d+)\.", topic_id)
    return int(match.group(1)) if match else None


def apply(payload: dict[str, Any]) -> bool:
    """Merge the ``source.excerpt`` lecture text into ``explanation``.

    Returns True when lecture content was routed in, False when the payload is
    out of scope (chapter 1 or without a usable excerpt).
    """
    chapter = _chapter_of(payload)
    if chapter is not None and chapter < 2:
        return False
    source = payload.get("source")
    if not isinstance(source, Mapping):
        return False
    excerpt = str(source.get("excerpt", "")).strip()
    if not excerpt:
        return False
    heading, buckets = route_excerpt(excerpt)
    if not buckets:
        return False

    explanation = payload.setdefault("explanation", {})
    assert isinstance(explanation, dict)

    definition = _single(buckets.get(DEFINITION, []))
    explanation["definition"] = _merge_text(explanation.get("definition"), definition)

    derivation = _paragraphs(buckets.get(DERIVATION, []))
    explanation["derivation"] = _merge_list(explanation.get("derivation"), derivation)

    intuition_lines = buckets.get(INTUITION, [])
    intuition = _inline(intuition_lines, ("一句话动机", "动机")) or _single(intuition_lines)
    explanation["intuition"] = _merge_text(explanation.get("intuition"), intuition)

    geometric = _single(buckets.get(GEOMETRIC, []))
    explanation["geometric_meaning"] = _merge_text(
        explanation.get("geometric_meaning"), geometric
    )

    conclusion_lines = buckets.get(CONCLUSION, [])
    conclusion = _single(conclusion_lines) if _body_only(conclusion_lines) else ""
    explanation["conclusion"] = _merge_text(explanation.get("conclusion"), conclusion)

    for bucket, field in (
        (PITFALLS, "pitfalls"),
        (READ_GUIDE, "read_guide"),
        (INVARIANTS, "invariants"),
        (CONNECTIONS, "connections"),
    ):
        items = _paragraphs(buckets.get(bucket, []))
        explanation[field] = _merge_list(explanation.get(field), items)

    summary = _inline(
        buckets.get(SUMMARY, []), ("本节目标", "学习目标", "目标")
    ) or _single(buckets.get(SUMMARY, []))
    if not summary:
        summary = intuition
    if not summary and heading:
        summary = heading
    explanation["summary"] = _merge_text(explanation.get("summary"), summary)

    for field in ("analogy_boundary", "transfer_note"):
        value = explanation.get(field)
        if isinstance(value, str) and _is_filler_text(value):
            explanation.pop(field, None)

    from linear_algebra.teaching import lecture_content

    lecture_content._sync_sections(explanation)
    explanation["searchable_text"] = lecture_content._searchable_text(explanation)
    return True


__all__ = ["apply", "looks_like_template", "route_excerpt"]
