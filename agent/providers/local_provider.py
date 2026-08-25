"""离线本地模型 provider；默认使用安全的规则型数学助手。"""

from services.agent_provider import AgentMessage, AgentResponse, SceneContext
from services.scene_commands import RuleBasedAgentProvider


class LocalModelProvider:
    def __init__(self) -> None:
        self._provider = RuleBasedAgentProvider()

    def create_plan(self, messages: tuple[AgentMessage, ...], scene_context: SceneContext) -> AgentResponse:
        return self._provider.create_plan(messages, scene_context)

    def test_connection(self) -> None:
        """本地模型没有网络连接，接口保持与远程 provider 一致。"""
        return None


LocalProvider = LocalModelProvider
