"""兼容 Skill 入口，实际逻辑复用 agent.skills.geometry。"""

from agent.skills.geometry.handler import create_plan


def build_handler():
    return type("GeometrySkillHandler", (), {"create_plan": staticmethod(create_plan)})()
