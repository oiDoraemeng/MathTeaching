"""三维线性代数教学图形的数据模型。

这些对象只保存可序列化的几何参数，不依赖 Qt 或 PyVista；渲染器可以在
GUI、测试和导出场景中复用同一份数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias
from uuid import uuid4


Vector3: TypeAlias = tuple[float, float, float]
Linear3DKind: TypeAlias = Literal["segment", "vector"]


def vector3(value: tuple[float, float, float] | list[float]) -> Vector3:
    """Normalize a three-component vector to floats."""
    if len(value) != 3:
        raise ValueError("A 3D vector must contain exactly three components")
    return float(value[0]), float(value[1]), float(value[2])


@dataclass(frozen=True)
class Linear3D:
    alias: str
    start: Vector3
    end: Vector3
    kind: Linear3DKind = "vector"
    color: str = "#2777b6"
    line_width: float = 3.0
    role: str = "primary"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class Plane3D:
    alias: str
    origin: Vector3
    normal: Vector3
    size: float = 2.0
    opacity: float = 0.24
    color: str = "#5b8def"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class Parallelogram3D:
    alias: str
    origin: Vector3
    vectors: tuple[Vector3, Vector3]
    opacity: float = 0.24
    color: str = "#4c9f70"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class Parallelepiped3D:
    alias: str
    origin: Vector3
    vectors: tuple[Vector3, Vector3, Vector3]
    opacity: float = 0.2
    color: str = "#4c9f70"
    id: str = field(default_factory=lambda: uuid4().hex)


Solid3D: TypeAlias = Parallelogram3D | Parallelepiped3D
