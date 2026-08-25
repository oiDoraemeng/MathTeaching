"""统一的模型 Provider 工厂。"""

from __future__ import annotations

from typing import Literal

from services.agent_provider import AgentProvider, AgentSettings

from .deepseek_provider import DeepSeekProvider
from .local_provider import LocalModelProvider
from .openai_provider import OpenAIProvider


ProviderName = Literal["openai", "deepseek", "local"]


class ModelProvider:
    """根据设置创建 OpenAI、DeepSeek 或本地规则模型。"""

    @staticmethod
    def create(name: ProviderName, settings: AgentSettings | None = None) -> AgentProvider:
        normalized = str(name).lower()
        if normalized == "local":
            return LocalModelProvider()
        if settings is None:
            raise ValueError("远程模型需要 AgentSettings")
        if normalized == "deepseek":
            return DeepSeekProvider(settings)
        if normalized == "openai":
            return OpenAIProvider(settings)
        raise ValueError(f"未知模型 Provider: {name}")
