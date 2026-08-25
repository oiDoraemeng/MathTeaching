"""Math Teacher Agent：解释数学问题并生成受限命令计划。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from services.agent_provider import AgentMessage, AgentProvider, AgentResponse, SceneContext
from services.scene_commands import CommandPlan, RuleBasedAgentProvider

from .instruction import InstructionStore
from .memory import MemoryStore
from .prompt_manager import PromptManager
from .skill_manager import SkillManager, SkillManifest
from .providers.local_provider import LocalModelProvider


@dataclass(frozen=True)
class AgentTurn:
    response: AgentResponse
    skills: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()


class MathTeacherAgent:
    """数学教学 Agent 的无 Qt 核心。

    本地可识别请求由 Skill 产生确定性计划；其他请求交给兼容 OpenAI 的
    provider。无论来源如何，返回给上层的场景修改都只能是 CommandPlan。
    """

    name = "Math Teacher Agent"

    def __init__(
        self,
        provider: AgentProvider | None = None,
        *,
        skill_manager: SkillManager | None = None,
        memory: MemoryStore | None = None,
        instructions: InstructionStore | None = None,
        prompts: PromptManager | None = None,
    ) -> None:
        self.provider = provider or RuleBasedAgentProvider()
        self.skill_manager = skill_manager or SkillManager()
        self.memory = memory or MemoryStore()
        self.instructions = instructions or InstructionStore()
        self.prompts = prompts or PromptManager()

    def respond(
        self,
        messages: Iterable[AgentMessage] | str,
        scene_context: SceneContext | None = None,
    ) -> AgentResponse:
        turn = self.respond_with_metadata(messages, scene_context)
        return turn.response

    handle = respond
    create_plan = respond

    def respond_with_metadata(
        self,
        messages: Iterable[AgentMessage] | str,
        scene_context: SceneContext | None = None,
    ) -> AgentTurn:
        if isinstance(messages, str):
            message_list = [AgentMessage("user", messages)]
        else:
            message_list = list(messages)
        request = next((item.content for item in reversed(message_list) if item.role == "user"), "")
        selected_prompts = self.prompts.select(request)
        local_result = self.skill_manager.create_plan_for_request(request, scene_context)
        # 已注册 Skill 优先提供确定性计划；远程模型只处理需要开放式解释或
        # 未被本地 Skill 识别的请求。这样即使切换到本地模型适配器，安全边界也一致。
        if local_result is not None and isinstance(self.provider, (RuleBasedAgentProvider, LocalModelProvider)):
            manifest, plan = local_result
            self.memory.remember_topic(manifest.name)
            return AgentTurn(
                AgentResponse(_explanation_for(manifest, request, plan), plan, plan.to_json()),
                (manifest.name,),
                selected_prompts,
            )
        enriched = [
            AgentMessage("system", self.instructions.load()),
            AgentMessage("system", self.prompts.compose(selected_prompts, memory=self.memory.load().to_dict())),
            AgentMessage("system", "可用数学 Skill：" + ", ".join(item.name for item in self.skill_manager.list_skills())),
            *message_list,
        ]
        response = self.provider.create_plan(tuple(enriched), scene_context or SceneContext())
        if response.plan is not None:
            for manifest in self.skill_manager.match(request):
                self.memory.remember_topic(manifest.name)
        return AgentTurn(response, tuple(item.name for item in self.skill_manager.match(request)), selected_prompts)


Agent = MathTeacherAgent


def _explanation_for(manifest: SkillManifest, request: str, plan: CommandPlan) -> str:
    if manifest.name == "linear_algebra":
        if "行列式" in request or "面积" in request:
            return (
                "二维向量 a、b 的行列式 det(a,b)=a_x b_y-a_y b_x 是平行四边形的有向面积；"
                "绝对值给出普通面积，正负表示方向。下面生成图形来对应这两个向量和面积。"
            )
        if "矩阵" in request or "matrix" in request.lower():
            return "矩阵把基向量映射到新的方向，列向量就是变换后的基；我会把它们画出来供比较。"
        return f"我会先用向量和线性变换解释“{request}”，再生成可审核的教学图。"
    if manifest.name == "calculus":
        if "导数" in request or "derivative" in request.lower():
            return "导数是瞬时变化率，也等于曲线上该点切线的斜率；我会同时绘制函数和导函数。"
        if "切线" in request or "tangent" in request.lower():
            return "切线在接触点处与曲线共享同一个局部斜率；我会标出该点并绘制切线。"
        if "积分" in request or "面积" in request or "integral" in request.lower():
            return "定积分把区间内无穷多个窄条面积累加起来；图中会用半透明区域标出积分区间。"
        return f"我会先解释“{request}”中的函数关系，再准备对应图形。"
    return f"我会用几何图形解释“{request}”，计划包含 {len(plan.operations)} 个受限场景操作。"
