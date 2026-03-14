"""Comprehensive skill + dispatcher tests to boost coverage."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.openai_provider import OpenAIProvider


def _make_provider():
    return OpenAIProvider(api_key="test-key", api_base="http://test", model="gpt-4o-mini")


# ── SkillDispatcher ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSkillDispatcher:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_dispatch_to_known_skill(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher
        mock_llm.return_value = {"content": json.dumps({
            "skill": "script-recommend",
            "confidence": 0.95,
            "extracted_params": {"scenario": "开场"},
        })}
        dispatcher = SkillDispatcher(_make_provider())
        skill, info = await dispatcher.dispatch("推荐一个开场白话术", {})
        assert skill is not None
        assert info["skill_name"] == "script-recommend"
        assert info["confidence"] == 0.95

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_dispatch_to_general_chat(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher
        mock_llm.return_value = {"content": json.dumps({
            "skill": "general_chat",
            "confidence": 0.8,
            "extracted_params": {},
        })}
        dispatcher = SkillDispatcher(_make_provider())
        skill, info = await dispatcher.dispatch("你好", {})
        assert skill is None
        assert info["skill_name"] == "general_chat"

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_dispatch_unknown_skill_fallback(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher
        mock_llm.return_value = {"content": json.dumps({
            "skill": "nonexistent-skill",
            "confidence": 0.6,
            "extracted_params": {},
        })}
        dispatcher = SkillDispatcher(_make_provider())
        skill, info = await dispatcher.dispatch("blah", {})
        assert skill is None
        assert info["skill_name"] == "nonexistent-skill"

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_dispatch_json_parse_error(self, mock_llm):
        from app.skills.dispatcher import SkillDispatcher
        mock_llm.return_value = {"content": "not valid json"}
        dispatcher = SkillDispatcher(_make_provider())
        skill, info = await dispatcher.dispatch("test", {})
        assert skill is None
        assert info["confidence"] == 0.5

    async def test_dispatch_no_skills_registered(self):
        from app.skills.dispatcher import SkillDispatcher
        from app.skills.registry import SkillRegistry
        dispatcher = SkillDispatcher(_make_provider())
        original = dispatcher.registry.list_skills
        dispatcher.registry.list_skills = lambda: []
        skill, info = await dispatcher.dispatch("hello", {})
        assert skill is None
        assert info["skill_name"] == "general_chat"
        dispatcher.registry.list_skills = original


# ── ChannelMaterialSkill ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestChannelMaterialSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.channel_material import ChannelMaterialSkill
        mock_llm.return_value = {"content": json.dumps({
            "brand_tone": ["专业", "温暖"],
            "selling_points": ["安全可靠", "效果显著", "恢复快"],
            "keywords": ["热玛吉", "紧致", "抗衰"],
            "style": "种草风",
            "target_audience": "25-40岁女性",
        })}
        skill = ChannelMaterialSkill(_make_provider())
        result = await skill.execute("分析这个物料", {
            "material_content": "热玛吉紧致方案...",
            "material_title": "热玛吉推广",
            "channel": "小红书",
            "material_type": "图文",
        })
        assert "品牌调性" in result["text"]
        assert "核心卖点" in result["text"]
        assert "关键词" in result["text"]
        assert "内容风格" in result["text"]
        assert "目标受众" in result["text"]
        assert len(result["cards"]) == 1
        assert result["cards"][0]["type"] == "channel-material-extract"
        assert len(result["suggested_actions"]) == 3

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.channel_material import ChannelMaterialSkill
        mock_llm.return_value = {"content": "not json"}
        skill = ChannelMaterialSkill(_make_provider())
        result = await skill.execute("分析", {})
        assert "已完成渠道物料分析" in result["text"]
        assert result["cards"][0]["data"] == {}


# ── ScriptAnnotateSkill ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestScriptAnnotateSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.script_annotate import ScriptAnnotateSkill
        mock_llm.return_value = {"content": json.dumps({
            "annotations": [
                {"turn_index": 0, "speaker": "service", "label": "good",
                 "strategy_type": "ice_breaking", "note": "好开场", "confidence": 0.9, "extractable": True},
                {"turn_index": 1, "speaker": "service", "label": "bad",
                 "strategy_type": "closing", "note": "过早逼单", "confidence": 0.8, "extractable": False},
                {"turn_index": 2, "speaker": "service", "label": "neutral",
                 "strategy_type": "other", "note": "常规", "confidence": 0.7, "extractable": False},
            ],
            "mining_suggestions": [
                {"type": "good_practice", "description": "开场方式好", "source_turns": [0]}
            ],
        })}
        skill = ScriptAnnotateSkill(_make_provider())
        result = await skill.execute("标注", {"conversation_text": "客服：你好\n客户：咨询"})
        assert "3 轮" in result["text"]
        assert "优秀话术：1" in result["text"]
        assert "问题话术：1" in result["text"]
        assert "知识挖掘" in result["text"]
        assert result["cards"][0]["type"] == "annotation-card"
        data = result["cards"][0]["data"]
        assert data["summary"]["good"] == 1
        assert data["summary"]["bad"] == 1
        assert data["summary"]["extractable"] == 1
        assert any("提取" in a["label"] for a in result["suggested_actions"])
        assert any("知识" in a["label"] for a in result["suggested_actions"])

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.script_annotate import ScriptAnnotateSkill
        mock_llm.return_value = {"content": "bad"}
        skill = ScriptAnnotateSkill(_make_provider())
        result = await skill.execute("标注", {"conversation_text": "对话"})
        assert "0 轮" in result["text"]


# ── ScriptOptimizeSkill ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestScriptOptimizeSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.script_optimize import ScriptOptimizeSkill
        mock_llm.return_value = {"content": json.dumps({
            "strategies": [
                {
                    "priority": "P0",
                    "problem": "开场白缺少共情",
                    "root_cause_type": "script",
                    "solution": "添加共情元素",
                    "current_script": "您好，请问有什么需要？",
                    "suggested_script": "您好！看到您在关注XX，可以聊聊您的需求~",
                    "expected_impact": "回复率提升15%",
                    "risk_level": "low",
                },
                {
                    "priority": "P1",
                    "problem": "过早留联",
                    "root_cause_type": "config",
                    "solution": "延后留联节点",
                    "current_script": "方便留个电话吗？",
                    "suggested_script": "先看看方案，合适的话再加微信详聊~",
                    "expected_impact": "留联率提升10%",
                    "risk_level": "medium",
                },
            ]
        })}
        skill = ScriptOptimizeSkill(_make_provider())
        result = await skill.execute("优化话术", {
            "diagnosis_result": {"classification": {}, "score_result": {}, "root_causes": []},
            "industry": "医美",
        })
        assert "2 条优化策略" in result["text"]
        assert "[P0]" in result["text"]
        assert len(result["cards"]) == 2
        assert result["cards"][0]["type"] == "optimize-strategy"

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.script_optimize import ScriptOptimizeSkill
        mock_llm.return_value = {"content": "bad json"}
        skill = ScriptOptimizeSkill(_make_provider())
        result = await skill.execute("优化", {})
        assert "0 条" in result["text"]
        assert result["cards"] == []


# ── DataInsightSkill ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDataInsightSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.data_insight import DataInsightSkill
        mock_llm.return_value = {"content": json.dumps({
            "text": "本周话术使用数据分析如下",
            "insights": [{"title": "复用率提升", "description": "提升20%", "metric_value": "78%", "trend": "up", "recommendation": "继续"}],
            "charts": [{"chart_type": "bar", "title": "使用量", "data": [{"label": "破冰", "value": 100}]}],
            "suggested_actions": [{"label": "导出", "action": "export"}],
        })}
        skill = DataInsightSkill(_make_provider())
        result = await skill.execute("看数据", {})
        assert result["text"] == "本周话术使用数据分析如下"
        assert len(result["cards"]) == 2
        assert result["cards"][0]["type"] == "data-chart"
        assert result["cards"][1]["type"] == "knowledge-card"

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_with_data_summary(self, mock_llm):
        from app.skills.data_insight import DataInsightSkill
        mock_llm.return_value = {"content": json.dumps({
            "text": "分析结果",
            "insights": [],
            "charts": [],
        })}
        skill = DataInsightSkill(_make_provider())
        result = await skill.execute("看数据", {"data_summary": {"total": 100}})
        assert "分析结果" in result["text"]

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.data_insight import DataInsightSkill
        mock_llm.return_value = {"content": "bad"}
        skill = DataInsightSkill(_make_provider())
        result = await skill.execute("看数据", {})
        assert "抱歉" in result["text"]

    def test_generate_mock_summary(self):
        from app.skills.data_insight import DataInsightSkill
        summary = DataInsightSkill._generate_mock_summary()
        parsed = json.loads(summary)
        assert "total_scripts" in parsed
        assert "top_categories" in parsed


# ── MemoryQuerySkill ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMemoryQuerySkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.memory_query import MemoryQuerySkill
        mock_llm.return_value = {"content": json.dumps({
            "text": "以下是相关知识",
            "knowledge_cards": [
                {"title": "面部松弛痛点", "type": "pain_point", "content": "常见", "related_chain": {
                    "pain_points": ["面部松弛"], "products": ["热玛吉"], "services": ["面诊"], "scripts": ["您关注紧致？"]
                }}
            ],
            "suggested_actions": [{"label": "查看", "action": "view"}],
        })}
        skill = MemoryQuerySkill(_make_provider())
        result = await skill.execute("查找面部松弛的痛点", {
            "pain_points": [{"name": "面部松弛"}],
            "products": [{"name": "热玛吉"}],
            "services": [],
            "related_scripts": ["话术1"],
        })
        assert "相关知识" in result["text"]
        assert len(result["cards"]) == 1
        assert result["cards"][0]["type"] == "knowledge-card"

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.memory_query import MemoryQuerySkill
        mock_llm.return_value = {"content": "bad"}
        skill = MemoryQuerySkill(_make_provider())
        result = await skill.execute("查询", {})
        assert "抱歉" in result["text"]


# ── FlywheelCascadeSkill ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFlywheelCascadeSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.flywheel_cascade import FlywheelCascadeSkill
        mock_llm.return_value = {"content": json.dumps({
            "cascade_actions": [
                {"layer": "pain_point", "action": "update", "target": "面部松弛", "detail": "标记为rising"},
                {"layer": "product", "action": "reprioritize", "target": "热玛吉", "detail": "提升至P1"},
            ],
            "summary": "痛点上升触发产品优先级调整",
        })}
        skill = FlywheelCascadeSkill(_make_provider())
        result = await skill.execute("痛点变化联动", {
            "trigger_event": {"type": "pain_point_rising"},
        })
        assert "text" in result
        assert "cards" in result

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.flywheel_cascade import FlywheelCascadeSkill
        mock_llm.return_value = {"content": "invalid"}
        skill = FlywheelCascadeSkill(_make_provider())
        result = await skill.execute("联动", {})
        assert "text" in result


# ── FlywheelInsightSkill ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFlywheelInsightSkill:
    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_success(self, mock_llm):
        from app.skills.flywheel_insight import FlywheelInsightSkill
        mock_llm.return_value = {"content": json.dumps({
            "insights": [
                {"title": "痛点趋势", "description": "面部松弛上升25%", "recommendation": "增加话术覆盖"}
            ],
            "text": "飞轮洞察分析完成",
        })}
        skill = FlywheelInsightSkill(_make_provider())
        result = await skill.execute("飞轮分析", {})
        assert "text" in result
        assert "cards" in result

    @patch.object(OpenAIProvider, "chat_completion", new_callable=AsyncMock)
    async def test_execute_parse_error(self, mock_llm):
        from app.skills.flywheel_insight import FlywheelInsightSkill
        mock_llm.return_value = {"content": "bad"}
        skill = FlywheelInsightSkill(_make_provider())
        result = await skill.execute("分析", {})
        assert "text" in result


# ── OpenAIProvider ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestOpenAIProvider:
    async def test_chat_completion_success(self):
        from unittest.mock import MagicMock

        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Hello!", role="assistant"),
                finish_reason="stop",
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.chat_completion(
                [{"role": "user", "content": "Hi"}], temperature=0.7
            )
        assert result["content"] == "Hello!"
        assert result["role"] == "assistant"
        assert result["usage"]["total_tokens"] == 15

    async def test_chat_completion_with_response_format(self):
        from unittest.mock import MagicMock

        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"key":"val"}', role="assistant"),
                finish_reason="stop",
            )
        ]
        mock_response.usage = None

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response
        ) as mock_create:
            result = await provider.chat_completion(
                [{"role": "user", "content": "Hi"}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}
        assert result["content"] == '{"key":"val"}'
        assert result["usage"]["total_tokens"] == 0

    async def test_chat_completion_stream(self):
        from unittest.mock import MagicMock

        provider = _make_provider()

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content=" World"))]
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock(delta=MagicMock(content=None))]

        async def mock_aiter():
            for c in [chunk1, chunk2, chunk3]:
                yield c

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_aiter()
        ):
            chunks = []
            async for chunk in provider.chat_completion_stream(
                [{"role": "user", "content": "Hi"}], temperature=0.7
            ):
                chunks.append(chunk)
        assert chunks == ["Hello", " World"]
