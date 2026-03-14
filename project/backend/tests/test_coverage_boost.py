"""Tests to boost coverage for under-covered modules."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.providers.factory import ModelProviderFactory
from app.utils.crypto import decrypt_password, get_public_key_pem, resolve_password


# ── crypto.py ────────────────────────────────────────────────────────────────

class TestCryptoUtils:
    def test_get_public_key_pem(self):
        pem = get_public_key_pem()
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")
        assert pem.endswith("-----END PUBLIC KEY-----\n")

    def test_decrypt_password_roundtrip(self):
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from app.utils.crypto import _private_key

        pub_key = _private_key.public_key()
        plaintext = "my_secret_password_123"
        encrypted = pub_key.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        encrypted_b64 = base64.b64encode(encrypted).decode()
        result = decrypt_password(encrypted_b64)
        assert result == plaintext

    def test_resolve_password_short_plaintext(self):
        assert resolve_password("short") == "short"

    def test_resolve_password_long_non_encrypted(self):
        long_str = "a" * 200
        assert resolve_password(long_str) == long_str

    def test_resolve_password_rsa_encrypted(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from app.utils.crypto import _private_key

        pub_key = _private_key.public_key()
        plaintext = "test_password"
        encrypted = pub_key.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        encrypted_b64 = base64.b64encode(encrypted).decode()
        result = resolve_password(encrypted_b64)
        assert result == plaintext


# ── i18n.py ──────────────────────────────────────────────────────────────────

class TestI18n:
    def test_get_error_message_zh(self):
        from app.utils.i18n import get_error_message
        msg = get_error_message("invalid_credentials", "zh")
        assert msg == "用户名或密码错误"

    def test_get_error_message_en(self):
        from app.utils.i18n import get_error_message
        msg = get_error_message("invalid_credentials", "en")
        assert msg == "Invalid username or password"

    def test_get_error_message_unknown_key(self):
        from app.utils.i18n import get_error_message
        msg = get_error_message("nonexistent_key", "zh")
        assert "错误" in msg or "error" in msg.lower()

    def test_get_error_message_unknown_key_en(self):
        from app.utils.i18n import get_error_message
        msg = get_error_message("nonexistent_key", "en")
        assert "error" in msg.lower()

    def test_get_lang_zh(self):
        from app.utils.i18n import get_lang
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {"accept-language": "zh-CN,zh;q=0.9"}
        assert get_lang(req) == "zh"

    def test_get_lang_en(self):
        from app.utils.i18n import get_lang
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {"accept-language": "en-US,en;q=0.9"}
        assert get_lang(req) == "en"

    def test_get_lang_default(self):
        from app.utils.i18n import get_lang
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {}
        assert get_lang(req) == "zh"


# ── agent/runtime.py ────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAgentRuntime:
    async def test_fallback_response(self):
        from app.agent.runtime import AgentRuntime
        result = AgentRuntime._fallback_response("hello")
        assert "text" in result
        assert len(result["text"]) > 0

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_general_chat(self, mock_llm, test_db: AsyncSession):
        from app.agent.runtime import AgentRuntime
        mock_llm.return_value = {"content": "你好！有什么可以帮你的吗？"}

        runtime = AgentRuntime(test_db)
        result = await runtime._general_chat(
            user_input="你好",
            history=[],
            memory={},
        )
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_process_message(self, mock_llm, test_db: AsyncSession, test_enterprise, test_user):
        from app.agent.runtime import AgentRuntime
        from app.models.conversation import Conversation

        mock_llm.return_value = {
            "content": json.dumps({
                "skill": "general_chat",
                "confidence": 1.0,
                "extracted_params": {},
            })
        }

        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="test",
        )
        test_db.add(conv)
        await test_db.flush()

        runtime = AgentRuntime(test_db)

        with patch.object(runtime, "_general_chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "text": "你好！",
                "cards": [],
                "suggested_actions": [],
            }
            result = await runtime.process_message(
                user_input="你好",
                conversation_id=str(conv.id),
                user_id=str(test_user.id),
                enterprise_id=str(test_enterprise.id),
            )
            assert "text" in result


# ── providers/base.py ────────────────────────────────────────────────────────

class TestModelProviderBase:
    def test_provider_init(self):
        from app.providers.base import ModelProvider

        class DummyProvider(ModelProvider):
            async def chat_completion(self, messages, temperature=0.7, response_format=None):
                return {"content": "test"}

            async def chat_completion_stream(self, messages, temperature=0.7):
                yield "test"

        p = DummyProvider(api_key="key", api_base="http://test", model="test-model")
        assert p.api_key == "key"
        assert p.api_base == "http://test"
        assert p.model == "test-model"


# ── skills/base.py ───────────────────────────────────────────────────────────

class TestSkillBase:
    def test_skill_attributes(self):
        from app.skills.base import Skill
        from app.providers.base import ModelProvider

        class DummySkill(Skill):
            def __init__(self, provider: ModelProvider):
                self.provider = provider

            @property
            def name(self) -> str:
                return "test-skill"

            @property
            def description(self) -> str:
                return "A test skill"

            @property
            def trigger_phrases(self) -> list[str]:
                return ["test"]

            async def execute(self, user_input, context):
                return {"text": "ok"}

        from app.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test", api_base="http://test", model="test")
        skill = DummySkill(provider)
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert skill.trigger_phrases == ["test"]


# ── conversations streaming ──────────────────────────────────────────────────

@pytest.mark.asyncio
class TestConversationStreaming:
    @patch("app.agent.runtime.AgentRuntime.process_message_stream")
    async def test_stream_endpoint(self, mock_stream, async_client: AsyncClient, auth_headers, test_db, test_enterprise, test_user):
        from app.models.conversation import Conversation

        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="stream test",
        )
        test_db.add(conv)
        await test_db.flush()

        async def mock_gen():
            yield 'data: {"type":"chunk","content":"hello"}\n\n'
            yield 'data: {"type":"done"}\n\n'

        mock_stream.return_value = mock_gen()

        response = await async_client.post(
            f"/api/conversations/{conv.id}/stream",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 200


# ── training quiz with fallback ──────────────────────────────────────────────

@pytest.mark.asyncio
class TestTrainingFallback:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_quiz_with_llm_failure_uses_fallback(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.side_effect = Exception("LLM unavailable")
        response = await async_client.get("/api/training/quiz", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0


# ── database.py ──────────────────────────────────────────────────────────────

class TestDatabaseConfig:
    def test_settings_loaded(self):
        s = get_settings()
        assert s.DATABASE_URL is not None
        assert s.SECRET_KEY is not None
        assert s.LLM_PROVIDER is not None


# ── factory.py ───────────────────────────────────────────────────────────────

class TestProviderFactory:
    def test_list_providers(self):
        providers = ModelProviderFactory.list_providers()
        assert "openai" in providers
        assert "moonshot" in providers
        assert "deepseek" in providers

    def test_get_defaults(self):
        defaults = ModelProviderFactory.get_defaults("moonshot")
        assert "api_base" in defaults
        assert "model" in defaults

    def test_get_defaults_unknown(self):
        defaults = ModelProviderFactory.get_defaults("nonexistent")
        assert defaults == {}

    def test_create_provider_unknown_falls_back_to_openai(self):
        provider = ModelProviderFactory.create_provider(
            provider_type="unknown_provider",
            api_key="test",
            api_base="http://test",
            model="test",
        )
        from app.providers.openai_provider import OpenAIProvider
        assert isinstance(provider, OpenAIProvider)

    def test_register_provider(self):
        from app.providers.openai_provider import OpenAIProvider
        ModelProviderFactory.register_provider("custom_test", OpenAIProvider)
        assert "custom_test" in ModelProviderFactory.list_providers()
        del ModelProviderFactory._providers["custom_test"]
