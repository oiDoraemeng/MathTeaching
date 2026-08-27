"""兼容 Skill 入口，实际逻辑复用 agent.skills.linear_algebra。"""

from agent.skills.linear_algebra.handler import create_plan


def build_handler():
    return type("LinearAlgebraSkillHandler", (), {"create_plan": staticmethod(create_plan)})()
