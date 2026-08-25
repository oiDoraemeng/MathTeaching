"""DeepSeek 的 OpenAI-compatible provider。"""

from services.agent_provider import AgentSettings
from .openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, settings: AgentSettings) -> None:
        if not settings.base_url.strip():
            settings = AgentSettings(self.DEFAULT_BASE_URL, settings.api_key, settings.model, settings.timeout_seconds)
        super().__init__(settings)


DeepSeekModelProvider = DeepSeekProvider
