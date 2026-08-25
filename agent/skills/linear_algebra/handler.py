"""线性代数 Skill 的确定性 CommandPlan 生成器。"""

from __future__ import annotations

import re

from services.scene_commands import CommandPlan


def create_plan(request: str, context: object = None) -> CommandPlan | None:
    text = str(request)
    lowered = text.lower()
    vector = re.search(
        r"a\s*=\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]"
        r".*?b\s*=\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if vector and ("向量" in text or "vector" in lowered):
        values = [float(value) for value in vector.groups()]
        return CommandPlan(
            summary="演示向量加法和平行四边形法",
            operations=({"op": "teach.vector_addition", "a": values[:2], "b": values[2:]},),
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
