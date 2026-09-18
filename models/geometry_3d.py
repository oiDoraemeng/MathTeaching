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
Linear3DStyle: TypeAlias = Literal["solid", "dashed"]


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
    # 虚线只用于辅助构造（被压到零的方向、投影连线等），向量箭头始终是实线。
    style: Linear3DStyle = "solid"
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class AlgebraVector3D:
    """A 3-D vector represented by one editable algebra row."""

    alias: str
    end: Vector3
    visible: bool = True
    color: str = "#2777b6"
    symbol: str | None = None

    @property
    def id(self) -> str:
        return self.alias

    @property
    def kind(self) -> str:
        return "vector3d"

    @property
    def name(self) -> str:
        return self.alias

    @property
    def latex(self) -> str:
        vector_name = self.symbol
        if not vector_name:
            suffix = self.alias.removeprefix("manual_vector_") or self.alias
            vector_name = rf"\vec{{v}}_{{{suffix}}}"
        x, y, z = (self._format(component) for component in self.end)
        return rf"{vector_name}=\begin{{pmatrix}}{x}\\{y}\\{z}\end{{pmatrix}}"

    @staticmethod
    def _format(value: float) -> str:
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
        return "0" if text in {"", "-0"} else text


@dataclass(frozen=True)
class AlgebraPlane3D:
    """A teaching plane represented by a read-only algebra equation."""

    alias: str
    origin: Vector3
    normal: Vector3
    label: str | None = None
    visible: bool = True
    color: str = "#5b8def"

    @property
    def id(self) -> str:
        return self.alias

    @property
    def kind(self) -> str:
        return "plane3d"

    @property
    def name(self) -> str:
        return self.label or self.alias

    @property
    def latex(self) -> str:
        coefficients = [float(value) for value in self.normal]
        constant = sum(coefficient * float(point) for coefficient, point in zip(coefficients, self.origin))
        first_nonzero = next((value for value in coefficients if abs(value) > 1e-9), 0.0)
        if first_nonzero < 0.0:
            coefficients = [-value for value in coefficients]
            constant = -constant
        terms: list[str] = []
        for coefficient, variable in zip(coefficients, ("x", "y", "z")):
            if abs(coefficient) <= 1e-9:
                continue
            magnitude = self._format(abs(coefficient))
            factor = "" if magnitude == "1" else magnitude
            if not terms:
                prefix = "-" if coefficient < 0.0 else ""
            else:
                prefix = "-" if coefficient < 0.0 else "+"
            terms.append(f"{prefix}{factor}{variable}")
        return f"{''.join(terms) or '0'}={self._format(constant)}"

    @staticmethod
    def _format(value: float) -> str:
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
        return "0" if text in {"", "-0"} else text


@dataclass(frozen=True)
class AlgebraAnnotation3D:
    """A user-placed 3-D mark represented by an editable algebra row."""

    alias: str
    position: Vector3
    text: str
    source: str
    visible: bool = True
    color: str = "#263241"

    @property
    def id(self) -> str:
        return self.alias

    @property
    def kind(self) -> str:
        return "annotation3d"

    @property
    def name(self) -> str:
        suffix = self.alias.removeprefix("manual_annotation_") or self.alias
        return f"标记 {suffix}"

    @property
    def latex(self) -> str:
        return self.source


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
