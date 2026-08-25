"""几何 Skill：只组装命令，不访问 Qt、PyVista 或数学渲染器。"""

from __future__ import annotations

import re

from services.scene_commands import CommandPlan


_POINT = re.compile(r"(?:点\s*)?([A-Za-z][\w]*)?\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]")
_VECTOR = re.compile(
    r"a\s*=\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]"
    r".*?b\s*=\s*[（(]\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[）)]",
    re.IGNORECASE | re.DOTALL,
)


def create_plan(request: str, context: object = None) -> CommandPlan | None:
    text = str(request).strip()
    lowered = text.lower()
    vector = _VECTOR.search(text)
    if vector and ("向量" in text or "vector" in lowered):
        values = [float(value) for value in vector.groups()]
        return CommandPlan(
            scene="2d",
            summary="生成向量加法的几何教学图",
            operations=({"op": "teach.vector_addition", "a": values[:2], "b": values[2:]},),
        )
    point_matches = list(_POINT.finditer(text))
    if "直线" in text or "line" in lowered:
        if len(point_matches) >= 2:
            first, second = point_matches[0], point_matches[1]
            a_alias, b_alias = first.group(1) or "A", second.group(1) or "B"
            return CommandPlan(
                summary=f"创建直线 {a_alias}{b_alias}",
                operations=(
                    {"op": "point.upsert", "alias": a_alias, "coordinates": [float(first.group(2)), float(first.group(3))], "name": a_alias},
                    {"op": "point.upsert", "alias": b_alias, "coordinates": [float(second.group(2)), float(second.group(3))], "name": b_alias},
                    {"op": "linear.upsert", "alias": f"{a_alias}{b_alias}", "kind": "line", "start": a_alias, "end": b_alias},
                ),
            )
    if ("向量" in text or "vector" in lowered) and not vector and point_matches:
        point = point_matches[0]
        end_alias = point.group(1) or "A"
        return CommandPlan(
            summary=f"创建从 O 到 {end_alias} 的向量",
            operations=(
                {"op": "point.upsert", "alias": "O", "coordinates": [0.0, 0.0], "name": "O"},
                {"op": "point.upsert", "alias": end_alias, "coordinates": [float(point.group(2)), float(point.group(3))], "name": end_alias},
                {"op": "linear.upsert", "alias": "v", "kind": "vector", "start": "O", "end": end_alias},
            ),
        )
    point = _POINT.search(text)
    if point and ("点" in text or "point" in lowered):
        alias = point.group(1) or "P"
        return CommandPlan(
            summary=f"创建点 {alias}",
            operations=({"op": "point.upsert", "alias": alias, "coordinates": [float(point.group(2)), float(point.group(3))], "name": alias},),
        )
    curve_match = re.search(r"(?:曲线|函数|curve)\s*(?:y\s*=\s*)?([^，,；;]+)", text, re.IGNORECASE)
    if curve_match and any(word in lowered for word in ("曲线", "函数", "curve")):
        expression = curve_match.group(1).strip().rstrip("。")
        if expression.startswith("="):
            expression = expression[1:].strip()
        return CommandPlan(
            summary=f"绘制曲线 {expression}",
            operations=({"op": "curve.create", "alias": "f", "kind": "explicit", "expression": f"y={expression}"},),
        )
    if any(word in lowered for word in ("曲面", "surface", "平面")):
        if "曲面" in text:
            expression = text.split("曲面", 1)[-1].strip(" ：:，,") or "z=x+y"
        else:
            expression = re.split(r"surface|平面", text, maxsplit=1, flags=re.IGNORECASE)[-1].strip(" ：:，,") or "z=x+y"
        return CommandPlan(
            scene="3d",
            summary=f"准备曲面 {expression}",
            operations=({"op": "surface.create", "alias": "surface", "kind": "explicit", "expression": expression},),
        )
    return None


def build_handler():
    return type("GeometrySkillHandler", (), {"create_plan": staticmethod(create_plan)})()


class GeometrySkillHandler:
    create_plan = staticmethod(create_plan)


GeometrySkill = GeometrySkillHandler
