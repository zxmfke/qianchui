"""LLM 集成测试 — 测试真实 LLM 调用（需要网络+有效 API Key）

运行方式:
  pytest tests/test_llm_integration.py -v -s  (需要网络和有效的 LLM_API_KEY)

若网络不可用，测试会自动跳过。
"""

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, patch

from app.config import get_settings
from app.providers.factory import ModelProviderFactory
from app.providers.openai_provider import OpenAIProvider


def _make_provider():
    settings = get_settings()
    return ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )


async def _check_llm_reachable() -> bool:
    try:
        provider = _make_provider()
        await provider.chat_completion(
            [{"role": "user", "content": "ping"}],
            temperature=0.1,
        )
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def llm_available():
    """Check if LLM is reachable; skip all tests in module if not."""
    loop = asyncio.new_event_loop()
    try:
        available = loop.run_until_complete(_check_llm_reachable())
    except Exception:
        available = False
    finally:
        loop.close()
    if not available:
        pytest.skip("LLM API not reachable, skipping integration tests")
    return True


# ═══════════════════════════════════════════════════════════════════════
# Mock-based LLM tests (always run, no network needed)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestProviderFactory:
    async def test_create_known_provider(self):
        provider = ModelProviderFactory.create_provider(
            provider_type="moonshot",
            api_key="test-key",
            api_base="https://test.api",
            model="test-model",
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"
        assert provider.model == "test-model"

    async def test_create_unknown_provider_defaults_to_openai(self):
        provider = ModelProviderFactory.create_provider(
            provider_type="unknown_vendor",
            api_key="key",
            api_base="https://test",
            model="m",
        )
        assert isinstance(provider, OpenAIProvider)

    async def test_list_providers(self):
        providers = ModelProviderFactory.list_providers()
        assert "openai" in providers
        assert "moonshot" in providers
        assert "deepseek" in providers

    async def test_get_defaults(self):
        defaults = ModelProviderFactory.get_defaults("moonshot")
        assert "api_base" in defaults
        assert "model" in defaults

    async def test_get_defaults_unknown(self):
        defaults = ModelProviderFactory.get_defaults("nonexistent")
        assert defaults == {}

    async def test_register_provider(self):
        class CustomProvider(OpenAIProvider):
            pass

        ModelProviderFactory.register_provider("custom", CustomProvider)
        assert "custom" in ModelProviderFactory.list_providers()
        provider = ModelProviderFactory.create_provider(
            provider_type="custom", api_key="k", api_base="b", model="m",
        )
        assert isinstance(provider, CustomProvider)

        del ModelProviderFactory._providers["custom"]


@pytest.mark.asyncio
class TestOpenAIProviderMocked:
    @patch("app.providers.openai_provider.AsyncOpenAI")
    async def test_chat_completion(self, mock_openai_cls):
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = AsyncMock()
        mock_choice.message.content = "Hello!"
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(api_key="test", api_base="https://test", model="gpt-4")
        result = await provider.chat_completion(
            [{"role": "user", "content": "hi"}],
            temperature=0.5,
        )

        assert result["content"] == "Hello!"
        assert result["usage"]["total_tokens"] == 15

    @patch("app.providers.openai_provider.AsyncOpenAI")
    async def test_chat_completion_with_response_format(self, mock_openai_cls):
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = AsyncMock()
        mock_choice.message.content = '{"key": "value"}'
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(api_key="test", api_base="https://test", model="gpt-4")
        result = await provider.chat_completion(
            [{"role": "user", "content": "return json"}],
            response_format={"type": "json_object"},
        )

        data = json.loads(result["content"])
        assert data["key"] == "value"

    @patch("app.providers.openai_provider.AsyncOpenAI")
    async def test_chat_completion_stream(self, mock_openai_cls):
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client

        class MockChunk:
            def __init__(self, text):
                self.choices = [type("C", (), {"delta": type("D", (), {"content": text})()})]

        async def mock_stream():
            for text in ["Hello", " World", "!"]:
                yield MockChunk(text)

        mock_client.chat.completions.create.return_value = mock_stream()

        provider = OpenAIProvider(api_key="test", api_base="https://test", model="gpt-4")
        chunks = []
        async for chunk in provider.chat_completion_stream(
            [{"role": "user", "content": "hi"}],
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello World!"


@pytest.mark.asyncio
class TestSkillsWithMockedLLM:
    """Test all skill execute methods with mocked LLM."""

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_recommend(self, mock_llm):
        from app.skills.script_recommend import ScriptRecommendSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "text": "推荐话术",
                "recommendations": [{
                    "title": "价格异议",
                    "psychology": {"trust_stage": "好奇", "emotion": "犹豫", "decision_stage": "评估", "analysis": "分析"},
                    "strategy": {"name": "异议处理", "framework": "认同→转化", "key_principle": "先认同"},
                    "scripts": [{"text": "话术内容", "scenario": "价格", "tone": "温和"}],
                }],
                "suggested_actions": [],
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptRecommendSkill(provider)
        result = await skill.execute("价格异议处理", {})
        assert "text" in result
        assert len(result.get("cards", [])) > 0

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_diagnose(self, mock_llm):
        from app.skills.script_diagnose import ScriptDiagnoseSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "overall_score": 72,
                "diagnosis": {
                    "psychology_layer": {"score": 65, "issues": ["缺乏共情"]},
                    "strategy_layer": {"score": 70, "issues": []},
                    "script_layer": {"score": 80, "issues": []},
                },
                "improvement_plan": ["加强共情"],
                "summary": "整体尚可",
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptDiagnoseSkill(provider)
        result = await skill.execute("客服：您好\n客户：你们价格多少", {"conversation_text": "..."})
        assert "text" in result
        cards = result.get("cards", [])
        assert any(c["type"] == "diagnosis-report" for c in cards)

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_train(self, mock_llm):
        from app.skills.script_train import ScriptTrainSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "questions": [{
                    "id": "Q001",
                    "scenario": "客户问价格",
                    "customer_state": "收集信息",
                    "options": [
                        {"key": "A", "text": "选项A"},
                        {"key": "B", "text": "选项B"},
                        {"key": "C", "text": "选项C"},
                        {"key": "D", "text": "选项D"},
                    ],
                    "correct_answer": "B",
                    "category": "异议处理",
                    "difficulty": 2,
                    "explanation": {"psychology": "p", "strategy": "s", "script": "sc"},
                    "wrong_explanations": {"A": "a", "C": "c", "D": "d"},
                }],
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptTrainSkill(provider)
        result = await skill.execute("", {"params": {"difficulty": 2, "category": "综合", "count": 1}})
        assert "text" in result
        cards = result.get("cards", [])
        assert any(c["type"] == "training-quiz" for c in cards)

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_optimize(self, mock_llm):
        from app.skills.script_optimize import ScriptOptimizeSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "strategies": [{
                    "current_script": "旧话术",
                    "suggested_script": "新话术",
                    "expected_effect": "转化率提升10%",
                    "risk": "low",
                    "dimension": "strategy_layer",
                }],
                "summary": "优化建议",
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptOptimizeSkill(provider)
        result = await skill.execute("优化建议", {"diagnosis_result": {"overall_score": 65}})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_annotate(self, mock_llm):
        from app.skills.script_annotate import ScriptAnnotateSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "annotations": [{"turn": 1, "quality": "good", "strategy": "引导", "knowledge": ""}],
                "quality_summary": {"good_count": 1, "bad_count": 0},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptAnnotateSkill(provider)
        result = await skill.execute("标注对话", {"conversation_text": "客服：您好\n客户：价格多少"})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_script_simulate(self, mock_llm):
        from app.skills.script_simulate import ScriptSimulateSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "customer_response": "嗯，你们那个热玛吉多少钱啊？",
                "hint": {"customer_psychology": "好奇", "suggested_strategy": "引导需求"},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ScriptSimulateSkill(provider)
        result = await skill.execute("", {"mode": "start", "scenario": "价格咨询"})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_data_insight(self, mock_llm):
        from app.skills.data_insight import DataInsightSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "insight": "话术使用率本周提升15%",
                "chart_data": {"labels": ["周一", "周二"], "values": [10, 15]},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = DataInsightSkill(provider)
        result = await skill.execute("分析本周数据", {})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_memory_query(self, mock_llm):
        from app.skills.memory_query import MemoryQuerySkill

        mock_llm.return_value = {
            "content": json.dumps({
                "results": [{"type": "pain_point", "name": "价格敏感", "description": "客户对价格关注度高"}],
                "chain": {"pain_point": "价格敏感", "product": "热玛吉", "service": "术前咨询", "script": "价值引导话术"},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = MemoryQuerySkill(provider)
        result = await skill.execute("查询价格相关痛点", {})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_channel_material_skill(self, mock_llm):
        from app.skills.channel_material import ChannelMaterialSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "brand_tone": "专业可信",
                "selling_points": ["效果好", "安全"],
                "keywords": ["热玛吉", "抗衰"],
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = ChannelMaterialSkill(provider)
        result = await skill.execute("分析物料", {"material_content": "热玛吉效果"})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_flywheel_sense(self, mock_llm):
        from app.skills.flywheel_sense import FlywheelSenseSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "trends": [{"name": "价格敏感", "trend": "rising", "this_week": 45, "last_week": 30}],
                "summary": "价格敏感度上升",
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = FlywheelSenseSkill(provider)
        result = await skill.execute("扫描痛点趋势", {})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_flywheel_cascade(self, mock_llm):
        from app.skills.flywheel_cascade import FlywheelCascadeSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "cascade_plan": {"pain_point": "价格", "product_change": "新套餐", "service_change": "话术更新", "script_change": "新话术"},
                "summary": "联动方案",
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = FlywheelCascadeSkill(provider)
        result = await skill.execute("生成联动方案", {"pain_point_changes": [{"name": "价格"}]})
        assert "text" in result

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_flywheel_insight(self, mock_llm):
        from app.skills.flywheel_insight import FlywheelInsightSkill

        mock_llm.return_value = {
            "content": json.dumps({
                "health_score": 78,
                "dimensions": [{"name": "数据新鲜度", "score": 85}],
                "recommendations": ["补充新痛点数据"],
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        skill = FlywheelInsightSkill(provider)
        result = await skill.execute("分析飞轮健康度", {})
        assert "text" in result


@pytest.mark.asyncio
class TestSkillDispatcherMocked:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_dispatch_to_recommend(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher

        mock_llm.return_value = {
            "content": json.dumps({
                "skill": "script-recommend",
                "confidence": 0.95,
                "extracted_params": {"scenario": "价格异议"},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        dispatcher = SkillDispatcher(provider)
        skill, result = await dispatcher.dispatch("帮我推荐价格异议处理话术", {})
        assert result["skill_name"] == "script-recommend"
        assert result["confidence"] == 0.95

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_dispatch_general_chat(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher

        mock_llm.return_value = {
            "content": json.dumps({
                "skill": "general_chat",
                "confidence": 0.9,
                "extracted_params": {},
            })
        }

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        dispatcher = SkillDispatcher(provider)
        skill, result = await dispatcher.dispatch("今天天气怎么样", {})
        assert skill is None
        assert result["skill_name"] == "general_chat"

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_dispatch_json_parse_error(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher

        mock_llm.return_value = {"content": "not a json"}

        provider = OpenAIProvider(api_key="t", api_base="h", model="m")
        dispatcher = SkillDispatcher(provider)
        skill, result = await dispatcher.dispatch("test", {})
        assert result["skill_name"] == "general_chat"
        assert result["confidence"] == 0.5


# ═══════════════════════════════════════════════════════════════════════
# Real LLM tests (only run when network is available)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestRealLLM:
    """These tests call the real LLM API. They only run when the API is reachable."""

    async def test_basic_chat(self, llm_available):
        provider = _make_provider()
        result = await provider.chat_completion(
            [{"role": "user", "content": "Say hello in one word"}],
            temperature=0.1,
        )
        assert "content" in result
        assert len(result["content"]) > 0
        assert "usage" in result

    async def test_json_response(self, llm_available):
        provider = _make_provider()
        result = await provider.chat_completion(
            [{"role": "user", "content": 'Return a JSON object with key "greeting" and value "hello"'}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(result["content"])
        assert "greeting" in data

    async def test_streaming(self, llm_available):
        provider = _make_provider()
        chunks = []
        async for chunk in provider.chat_completion_stream(
            [{"role": "user", "content": "Count from 1 to 3"}],
            temperature=0.1,
        ):
            chunks.append(chunk)
        full_text = "".join(chunks)
        assert len(full_text) > 0

    async def test_skill_recommend_real(self, llm_available):
        from app.skills.script_recommend import ScriptRecommendSkill

        provider = _make_provider()
        skill = ScriptRecommendSkill(provider)
        result = await skill.execute("价格异议处理", {"customer_profile": {"type": "价格敏感型"}})
        assert "text" in result
        assert len(result["text"]) > 0

    async def test_skill_diagnose_real(self, llm_available):
        from app.skills.script_diagnose import ScriptDiagnoseSkill

        provider = _make_provider()
        skill = ScriptDiagnoseSkill(provider)
        conv = "客服：您好，请问有什么可以帮您？\n客户：你们种植牙多少钱？\n客服：我们种植牙3000起"
        result = await skill.execute(conv, {"conversation_text": conv})
        assert "text" in result

    async def test_dispatcher_real(self, llm_available):
        from app.skills.dispatcher import SkillDispatcher

        provider = _make_provider()
        dispatcher = SkillDispatcher(provider)
        skill, dispatch_result = await dispatcher.dispatch("帮我推荐价格异议处理的话术", {})
        assert dispatch_result["skill_name"] in ("script-recommend", "general_chat")
        assert 0 <= dispatch_result["confidence"] <= 1
