"""兼容 Skill 入口，实际逻辑复用 agent.skills.calculus。"""

from agent.skills.calculus.handler import create_plan


def build_handler():
    return type("CalculusSkillHandler", (), {"create_plan": staticmethod(create_plan)})()
