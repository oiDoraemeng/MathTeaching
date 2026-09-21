"""Deterministic, renderer-independent visualization recipe primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal, Sequence

from linear_algebra.catalog.model import LessonEntry
from .limits import RenderLimits, limits_for

if TYPE_CHECKING:
    from services.scene_commands import CommandPlan



@dataclass(frozen=True)
class RenderContext:
    topic_id: str
    bounds: tuple[float, ...] = (-3.0, 3.0, -3.0, 3.0)
    seed: int = 17
    render_profile: str = "lecture-v1"

    @property
    def limits(self) -> RenderLimits:
        return limits_for(self.render_profile)

    @classmethod
    def default(cls, topic_id: str) -> "RenderContext":
        # 固定种子保证未来参数化样本可复现。
        return cls(topic_id=topic_id, seed=17)


@dataclass(frozen=True)
class VisualizationRecipe:
    id: str
    scene: Literal["2d", "3d"]
    required_capabilities: tuple[str, ...]
    builder: Callable[[RenderContext], CommandPlan]


def recipe_for_entry(entry: LessonEntry) -> VisualizationRecipe:
    """Create visualization recipe from lesson entry using topic-specific builders."""
    from .builders import get_builder_for

    # 获取主题专用构建器。
    builder_func = get_builder_for(entry.visualization_id)

    if builder_func is None:
        # 目录中的每个主题都必须有构建器。
        raise ValueError(
            f"No builder found for {entry.visualization_id}. "
            f"All topics must have a specific builder."
        )

    scene: Literal["2d", "3d"] = "3d" if _uses_3d(entry.required_capabilities) else "2d"

    return VisualizationRecipe(
        id=entry.visualization_id,
        scene=scene,
        required_capabilities=entry.required_capabilities,
        builder=builder_func,
    )


def _uses_3d(capabilities: tuple[str, ...]) -> bool:
    return any(
        capability in capabilities
        for capability in ("vector_3d", "right_hand_3d", "parallelepiped_3d", "oriented_volume_3d")
    )


#: 数学模式会忽略普通空格，列对齐必须写成显式的间距命令。
_MATH_COLUMN_GAP = r"\quad "
_MATH_PADDING = r"\ "


def _math_cell(value: float, width: int) -> str:
    """把元素补成定宽单元格，补位用数学空格命令（普通空格在数学模式里会被丢掉）。"""

    text = f"{float(value):g}"
    return _MATH_PADDING * max(0, width - len(text)) + text


def _math_matrix_body(rows: Sequence[str]) -> str:
    """把多行元素堆成 ``\\genfrac`` 结构，外层补上跨行的方括号。

    ``\\genfrac`` 的定界符留空、线宽为 ``0`` 时就是纯粹的上下堆叠，因此
    ``\\left[`` / ``\\right]`` 会自动长到能包住所有行的高度。
    """

    body = rows[-1]
    for row in reversed(rows[:-1]):
        body = rf"\genfrac{{}}{{}}{{0}}{{}}{{{row}}}{{{body}}}"
    return rf"\left[{body}\right]"


def matrix_label_text(name: str, matrix: Sequence[Sequence[float]]) -> str:
    """返回矩阵标注的数学排版文本，例如 ``$A=\\left[\\genfrac{}{}{0}{}{2\\quad 0}{0\\quad 1}\\right]$``。

    标注平时只能画纯文本，但 VTK 的文本渲染器会把 ``$...$`` 交给数学排版器
    （matplotlib mathtext）：用 ``\\genfrac`` 堆叠行、用 ``\\left[`` / ``\\right]``
    长出跨行括号，就得到教科书里的矩阵写法。数学排版器不可用时，显示层
    ``rendering.math_labels.display_text`` 会把这段文本降级成两行纯文本。
    """

    rows = [[float(value) for value in row] for row in matrix]
    if not rows or not rows[0]:
        return str(name)
    widths = [
        max((len(f"{row[index]:g}") for row in rows if index < len(row)), default=1)
        for index in range(max(len(row) for row in rows))
    ]
    lines = [
        _MATH_COLUMN_GAP.join(
            _math_cell(value, widths[index]) for index, value in enumerate(row)
        )
        for row in rows
    ]
    return f"${name}={_math_matrix_body(lines)}$"
