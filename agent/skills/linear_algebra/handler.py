"""线性代数 Skill 的确定性 CommandPlan 生成器。"""

from __future__ import annotations

import re

from services.scene_commands import CommandPlan


# 允许 a/b 与坐标括号之间出现「改为/改成/变成/点/向量/=/＝」等连接词，
# 从而支持「把 a 改为 (2,2)」「a 点改为（2.2）」这类只改单个向量的表述。
_VECTOR_COMPONENT = re.compile(
    r"(?P<name>[ab])(?![a-zA-Z0-9_])\s*(?:改为|改成|变成|修改为|变为|设置为|改成|向量|点|坐标|=|＝)*\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]",
    re.IGNORECASE,
)


def _parse_vector_components(text: str) -> dict[str, tuple[float, float]]:
    """分别解析 a=(x,y) 与 b=(x,y)，允许只出现其中一个。"""
    components: dict[str, tuple[float, float]] = {}
    for match in _VECTOR_COMPONENT.finditer(text):
        name = match.group("name").lower()
        components[name] = (float(match.group(2)), float(match.group(3)))
    return components


def _vector_from_context(name: str, context: object) -> tuple[float, float] | None:
    """从场景上下文中已有的点坐标补全向量（默认原点出发）。"""
    geometry = getattr(context, "geometry", None)
    if not geometry:
        return None
    for item in geometry:
        alias = str(getattr(item, "agent_alias", "") or item.get("alias", "") or "")
        if alias != name:
            continue
        coordinates = item.get("coordinates") if isinstance(item, dict) else getattr(item, "coordinates", None)
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2:
            try:
                return (float(coordinates[0]), float(coordinates[1]))
            except (TypeError, ValueError):
                return None
    return None


def create_plan(request: str, context: object = None) -> CommandPlan | None:
    text = str(request)
    lowered = text.lower()
    components = _parse_vector_components(text)
    # 只要解析到 a/b 的坐标，就视为向量相关请求；「向量」一词在首次请求
    # 中出现，而后续「把 a 改为 (2,2)」这类修改可能不再重复「向量」二字。
    if components:
        a = components.get("a") or _vector_from_context("a", context) or _vector_from_context("A", context)
        b = components.get("b") or _vector_from_context("b", context) or _vector_from_context("B", context)
        # 场景中的点别名可能是 a_end/b_end；补全失败时回退到端点别名。
        if a is None:
            a = _vector_from_context("a_end", context)
        if b is None:
            b = _vector_from_context("b_end", context)
        if a is not None and b is not None:
            return CommandPlan(
                summary="演示向量加法和平行四边形法",
                operations=({"op": "teach.vector_addition", "a": list(a), "b": list(b)},),
            )
    if "行列式" in text or "determinant" in lowered or "面积" in text:
        return CommandPlan(
            summary="用平行四边形演示行列式的有向面积",
            operations=(
                {"op": "linear_algebra.determinant_area", "a": [2, 1], "b": [1, 3], "show_basis": True},
                {"op": "annotation.upsert", "alias": "determinant_hint", "text": "|det(a,b)| = 面积", "position": [1.5, 2.2]},
            ),
        )
    matrix = re.search(
        r"(?:矩阵|matrix).*?\[\s*([-+\d.]+)\s*[,，]\s*([-+\d.]+)\s*[,，;；]\s*"
        r"([-+\d.]+)\s*[,，]\s*([-+\d.]+)\s*\]",
        text,
        re.IGNORECASE,
    )
    if matrix or "矩阵" in text or "matrix" in lowered:
        values = [float(value) for value in matrix.groups()] if matrix else [1, 0, 0, 1]
        return CommandPlan(
            summary="准备矩阵线性变换教学演示",
            operations=({"op": "linear_algebra.matrix_transform", "matrix": [values[:2], values[2:]], "basis": "standard"},),
        )
    return None


def build_handler():
    return type("LinearAlgebraSkillHandler", (), {"create_plan": staticmethod(create_plan)})()


class LinearAlgebraSkillHandler:
    create_plan = staticmethod(create_plan)


LinearAlgebraSkill = LinearAlgebraSkillHandler
