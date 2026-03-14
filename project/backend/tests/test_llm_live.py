"""LLM 真实连通性 + 功能测试

当 LLM API 可达时运行，验证所有 LLM 相关功能是否端到端跑通。
跳过条件：LLM_API_KEY 未配置或 API 不可达。

使用方式：
    pytest tests/test_llm_live.py -v
    pytest tests/test_llm_live.py -v -k "test_chat_completion"
"""

import asyncio
import json

import pytest
import pytest_asyncio

from app.config import get_settings
from app.providers.factory import ModelProviderFactory

settings = get_settings()


def _can_reach_llm() -> bool:
    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "":
        return False
    try:
        import httpx
        r = httpx.get(f"{settings.LLM_API_BASE}/models", timeout=5,
                      headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"})
        return r.status_code in (200, 401)
    except Exception:
        return False


_LLM_AVAILABLE = _can_reach_llm()
skip_if_no_llm = pytest.mark.skipif(not _LLM_AVAILABLE, reason="LLM API not reachable")


def _create_provider():
    return ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )


@skip_if_no_llm
@pytest.mark.asyncio
class TestLLMChatCompletion:
    async def test_basic_chat(self):
        provider = _create_provider()
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Say hello in one word"}],
            temperature=0.1,
        )
        assert "content" in result
        assert len(result["content"]) > 0

    async def test_json_format(self):
        provider = _create_provider()
        result = await provider.chat_completion(
            messages=[{
                "role": "user",
                "content": 'Return a JSON object: {"greeting": "hello"}',
            }],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = result["content"]
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    async def test_streaming(self):
        provider = _create_provider()
        chunks = []
        async for chunk in provider.chat_completion_stream(
            messages=[{"role": "user", "content": "Count from 1 to 3"}],
            temperature=0.1,
        ):
            chunks.append(chunk)
        full = "".join(chunks)
        assert len(full) > 0


@skip_if_no_llm
@pytest.mark.asyncio
class TestLLMSkillsLive:
    async def test_script_recommend_live(self):
        from app.skills.script_recommend import ScriptRecommendSkill
        provider = _create_provider()
        skill = ScriptRecommendSkill(provider)
        result = await skill.execute("价格异议处理", {"enterprise_id": "test"})
        assert "text" in result

    async def test_script_diagnose_live(self):
        from app.skills.script_diagnose import ScriptDiagnoseSkill
        provider = _create_provider()
        skill = ScriptDiagnoseSkill(provider)
        conversation = "客服：您好\n客户：你们产品多少钱\n客服：很便宜的"
        result = await skill.execute(conversation, {"conversation_text": conversation})
        assert "text" in result

    async def test_script_train_live(self):
        from app.skills.script_train import ScriptTrainSkill
        provider = _create_provider()
        skill = ScriptTrainSkill(provider)
        result = await skill.execute("", {
            "params": {"difficulty": 2, "category": "异议处理", "count": 1},
            "industry": "消费医疗",
            "products": "热玛吉",
        })
        assert "text" in result

    async def test_dispatcher_live(self):
        from app.skills.dispatcher import SkillDispatcher
        provider = _create_provider()
        dispatcher = SkillDispatcher(provider)
        skill, info = await dispatcher.dispatch("推荐一个价格异议处理的话术", {})
        assert info["skill_name"] in ("script-recommend", "general_chat")

    async def test_memory_query_live(self):
        from app.skills.memory_query import MemoryQuerySkill
        provider = _create_provider()
        skill = MemoryQuerySkill(provider)
        result = await skill.execute("客户担心价格太贵", {"enterprise_id": "test"})
        assert "text" in result

    async def test_channel_material_live(self):
        from app.skills.channel_material import ChannelMaterialSkill
        provider = _create_provider()
        skill = ChannelMaterialSkill(provider)
        result = await skill.execute("分析该渠道物料", {
            "material_content": "热玛吉紧致提拉，效果立竿见影",
            "material_title": "热玛吉推广视频",
            "channel": "douyin",
            "material_type": "video",
        })
        assert "text" in result

    async def test_data_insight_live(self):
        from app.skills.data_insight import DataInsightSkill
        provider = _create_provider()
        skill = DataInsightSkill(provider)
        result = await skill.execute("分析最近话术使用数据", {"enterprise_id": "test"})
        assert "text" in result

    async def test_flywheel_sense_live(self):
        from app.skills.flywheel_sense import FlywheelSenseSkill
        provider = _create_provider()
        skill = FlywheelSenseSkill(provider)
        result = await skill.execute("扫描痛点趋势", {"enterprise_id": "test"})
        assert "text" in result

    async def test_flywheel_cascade_live(self):
        from app.skills.flywheel_cascade import FlywheelCascadeSkill
        provider = _create_provider()
        skill = FlywheelCascadeSkill(provider)
        result = await skill.execute("", {
            "trigger_type": "pain_point",
            "trigger_data": {"name": "价格敏感", "trend": "rising"},
            "enterprise_id": "test",
        })
        assert "text" in result

    async def test_flywheel_insight_live(self):
        from app.skills.flywheel_insight import FlywheelInsightSkill
        provider = _create_provider()
        skill = FlywheelInsightSkill(provider)
        result = await skill.execute("分析飞轮健康度", {"enterprise_id": "test"})
        assert "text" in result

    async def test_script_optimize_live(self):
        from app.skills.script_optimize import ScriptOptimizeSkill
        provider = _create_provider()
        skill = ScriptOptimizeSkill(provider)
        result = await skill.execute("", {
            "diagnosis_result": {
                "overall_score": 60,
                "psychology_layer": {"score": 50, "issues": ["缺乏共情"]},
                "strategy_layer": {"score": 65, "issues": ["策略单一"]},
                "script_layer": {"score": 70, "issues": ["话术生硬"]},
            },
            "original_conversation": "客服：您好\n客户：太贵了\n客服：不贵的",
        })
        assert "text" in result

    async def test_script_annotate_live(self):
        from app.skills.script_annotate import ScriptAnnotateSkill
        provider = _create_provider()
        skill = ScriptAnnotateSkill(provider)
        result = await skill.execute("", {
            "conversation_text": "客服：您好，欢迎咨询\n客户：我想了解热玛吉\n客服：好的，热玛吉是一种非侵入式的抗衰项目",
        })
        assert "text" in result

    async def test_script_simulate_live(self):
        from app.skills.script_simulate import ScriptSimulateSkill
        provider = _create_provider()
        skill = ScriptSimulateSkill(provider)
        result = await skill.execute("", {
            "mode": "start",
            "scenario": "price_objection",
            "customer_type": "犹豫型",
            "difficulty": "intermediate",
        })
        assert "text" in result
