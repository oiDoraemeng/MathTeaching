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


__all__ = ["get_builder_for", "register_builders"]
