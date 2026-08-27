"""DeepSeek 的 OpenAI-compatible provider。"""

from services.agent_provider import AgentSettings
from .openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, settings: AgentSettings) -> None:
        if not settings.base_url.strip():
            settings = AgentSettings(
                base_url=self.DEFAULT_BASE_URL,
                api_key=settings.api_key,
                model=settings.model,
                timeout_seconds=settings.timeout_seconds,
                provider=settings.provider,
                protocol=settings.protocol,
            )
        super().__init__(settings)


DeepSeekModelProvider = DeepSeekProvider
