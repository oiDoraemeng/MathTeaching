from __future__ import annotations

from .chapter_01 import CONTENT as CHAPTER_1_CONTENT
from .chapter_02 import CONTENT as CHAPTER_2_CONTENT
from .chapter_03 import CONTENT as CHAPTER_3_CONTENT
from .chapter_04 import CONTENT as CHAPTER_4_CONTENT
from .chapter_05 import CONTENT as CHAPTER_5_CONTENT
from .chapter_06 import CONTENT as CHAPTER_6_CONTENT
from .chapter_07 import CONTENT as CHAPTER_7_CONTENT
from .chapter_08 import CONTENT as CHAPTER_8_CONTENT
from .model import ExplanationContent

_CONTENT = {
    **CHAPTER_1_CONTENT, **CHAPTER_2_CONTENT, **CHAPTER_3_CONTENT,
    **CHAPTER_4_CONTENT, **CHAPTER_5_CONTENT, **CHAPTER_6_CONTENT,
    **CHAPTER_7_CONTENT, **CHAPTER_8_CONTENT,
}


def explanation_for(topic_id: str) -> ExplanationContent:
    try:
        return _CONTENT[topic_id]
    except KeyError as error:
        raise KeyError(f"未知线性代数解释: {topic_id}") from error


__all__ = ["ExplanationContent", "explanation_for"]
