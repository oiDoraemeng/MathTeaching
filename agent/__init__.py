"""Math3DTeaching 的数学 Agent 运行时。

Agent 层只负责理解请求、选择教学资源并生成 :class:`CommandPlan`。
场景执行仍由 ``services.scene_commands.SceneCommandService`` 负责。
"""

from .agent import MathTeacherAgent
from .runtime import AgentRuntime
from .skill_manager import SkillManager

__all__ = ["AgentRuntime", "MathTeacherAgent", "SkillManager"]
