"""OpenAI provider，协议实现复用现有服务层。"""

from services.agent_provider import AgentSettings, OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI-compatible API 的具名适配器。"""

    pass


ModelProvider = OpenAIProvider
OpenAIModelProvider = OpenAIProvider
