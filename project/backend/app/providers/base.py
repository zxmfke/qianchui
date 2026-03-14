from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class ModelProvider(ABC):
    """LLM Model Provider base class — OpenAI API compatible."""

    def __init__(self, api_key: str, api_base: str, model: str, http_proxy: str = ""):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.http_proxy = http_proxy

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> dict:
        """Non-streaming chat completion."""
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Streaming chat completion, yields text chunks."""
        pass
