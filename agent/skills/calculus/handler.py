"""微积分 Skill：生成曲线、导数、积分和切线的安全命令。"""

from __future__ import annotations

import re

from services.scene_commands import CommandPlan


def create_plan(request: str, context: object = None) -> CommandPlan | None:
    text = str(request).strip()
    lowered = text.lower()
    expression_match = re.search(r"(?:函数|曲线|f\(x\)|y\s*=|function)\s*[:：=]?\s*([^，,；;。]+)", text, re.IGNORECASE)
    expression = expression_match.group(1).strip() if expression_match else "x^2"
    expression = re.split(r"\s*(?:的)?(?:切线|导数|积分|面积|图像)\b", expression, maxsplit=1)[0].strip()
    if expression.startswith("f(x)="):
        expression = expression[5:].strip()
    if expression.startswith("y="):
        expression = expression[2:].strip()
    if "切线" in text or "tangent" in lowered:
        return CommandPlan(
            summary=f"绘制 y={expression} 的切线教学图",
            operations=({"op": "calculus.tangent", "expression": f"y={expression}", "x": 1.0, "curve_alias": "f", "tangent_alias": "tangent_at_1"},),
        )
    if "积分" in text or "integral" in lowered or "面积" in text:
        return CommandPlan(
            summary=f"演示 y={expression} 的积分面积",
            operations=({"op": "calculus.integral_area", "expression": f"y={expression}", "interval": [-1.0, 1.0], "curve_alias": "f", "area_alias": "integral_area"},),
        )
    if "导数" in text or "derivative" in lowered:
        return CommandPlan(
            summary=f"绘制 y={expression} 及其导函数",
            operations=({"op": "calculus.derivative", "expression": f"y={expression}", "curve_alias": "f", "derivative_alias": "f_prime"},),
        )
    if expression_match or "函数" in text or "function" in lowered or "曲线" in text:
        return CommandPlan(
            summary=f"绘制函数 y={expression}",
            operations=({"op": "curve.create", "alias": "f", "kind": "explicit", "expression": f"y={expression}"},),
        )
    return None


def build_handler():
    return type("CalculusSkillHandler", (), {"create_plan": staticmethod(create_plan)})()


class CalculusSkillHandler:
    create_plan = staticmethod(create_plan)


CalculusSkill = CalculusSkillHandler
