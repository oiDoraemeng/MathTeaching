"""Versioned local capability contracts for the Math3D teaching agent."""

from .contracts import (
    CAPABILITY_CATALOG_VERSION,
    CapabilityError,
    CapabilityResult,
    CapabilitySpec,
    SceneScope,
    ToolCall,
)
from .registry import CapabilityRegistry, build_default_registry

__all__ = [
    "CAPABILITY_CATALOG_VERSION",
    "CapabilityError",
    "CapabilityResult",
    "CapabilitySpec",
    "CapabilityRegistry",
    "SceneScope",
    "ToolCall",
    "build_default_registry",
]
