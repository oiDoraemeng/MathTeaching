"""Builder registry for topic-specific visualizations."""

from __future__ import annotations

from typing import Callable, Optional

_ALL_BUILDERS: dict[str, Callable] = {}


def get_builder_for(visualization_id: str) -> Optional[Callable]:
    """Get builder function for specified topic visualization ID."""
    return _ALL_BUILDERS.get(visualization_id)


def register_builders(builders: dict[str, Callable]) -> None:
    """Register a batch of builders."""
    _ALL_BUILDERS.update(builders)


# 导入并注册全部章节构建器。
from .chapter_01 import BUILDERS as CHAPTER_01_BUILDERS
from .chapter_02 import BUILDERS as CHAPTER_02_BUILDERS
from .chapter_03 import BUILDERS as CHAPTER_03_BUILDERS
from .chapter_04 import BUILDERS as CHAPTER_04_BUILDERS
from .chapter_05 import BUILDERS as CHAPTER_05_BUILDERS
from .chapter_06 import BUILDERS as CHAPTER_06_BUILDERS
from .chapter_07 import BUILDERS as CHAPTER_07_BUILDERS
from .chapter_08 import BUILDERS as CHAPTER_08_BUILDERS

register_builders(CHAPTER_01_BUILDERS)
register_builders(CHAPTER_02_BUILDERS)
register_builders(CHAPTER_03_BUILDERS)
register_builders(CHAPTER_04_BUILDERS)
register_builders(CHAPTER_05_BUILDERS)
register_builders(CHAPTER_06_BUILDERS)
register_builders(CHAPTER_07_BUILDERS)
register_builders(CHAPTER_08_BUILDERS)

__all__ = ["get_builder_for", "register_builders"]
