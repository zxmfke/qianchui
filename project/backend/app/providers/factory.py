from app.providers.base import ModelProvider
from app.providers.openai_provider import OpenAIProvider


class ModelProviderFactory:
    """Factory for creating model providers.

    All providers use OpenAI-compatible protocol (OpenAI SDK).
    Simply configure different api_base and model for each vendor.
    """

    _providers: dict[str, type[ModelProvider]] = {
        "openai": OpenAIProvider,
        "moonshot": OpenAIProvider,
        "deepseek": OpenAIProvider,
        "zhipu": OpenAIProvider,
        "qwen": OpenAIProvider,
        "baichuan": OpenAIProvider,
        "minimax": OpenAIProvider,
        "yi": OpenAIProvider,
        "stepfun": OpenAIProvider,
        "siliconflow": OpenAIProvider,
        "together": OpenAIProvider,
        "groq": OpenAIProvider,
        "openrouter": OpenAIProvider,
    }

    KNOWN_DEFAULTS: dict[str, dict[str, str]] = {
        "openai": {"api_base": "https://api.openai.com/v1", "model": "gpt-4o"},
        "moonshot": {"api_base": "https://api.moonshot.ai/v1", "model": "kimi-k2-turbo-preview"},
        "deepseek": {"api_base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
        "zhipu": {"api_base": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
        "qwen": {"api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
        "baichuan": {"api_base": "https://api.baichuan-ai.com/v1", "model": "Baichuan4"},
        "minimax": {"api_base": "https://api.minimax.chat/v1", "model": "abab6.5s-chat"},
        "yi": {"api_base": "https://api.lingyiwanwu.com/v1", "model": "yi-large"},
        "stepfun": {"api_base": "https://api.stepfun.com/v1", "model": "step-2-16k"},
        "siliconflow": {"api_base": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen2.5-72B-Instruct"},
        "together": {"api_base": "https://api.together.xyz/v1", "model": "meta-llama/Llama-3-70b-chat-hf"},
        "groq": {"api_base": "https://api.groq.com/openai/v1", "model": "llama-3.1-70b-versatile"},
        "openrouter": {"api_base": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o"},
    }

    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        api_key: str,
        api_base: str,
        model: str,
        http_proxy: str = "",
    ) -> ModelProvider:
        provider_cls = cls._providers.get(provider_type, OpenAIProvider)
        return provider_cls(api_key=api_key, api_base=api_base, model=model, http_proxy=http_proxy)

    @classmethod
    def register_provider(cls, name: str, provider_cls: type[ModelProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(cls._providers.keys())

    @classmethod
    def get_defaults(cls, provider_type: str) -> dict[str, str]:
        return cls.KNOWN_DEFAULTS.get(provider_type, {})
