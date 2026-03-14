import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_recommend_response():
    return {
        "content": json.dumps({
            "text": "为您推荐了以下话术：",
            "recommendations": [
                {
                    "title": "价格异议处理话术",
                    "psychology": {
                        "trust_stage": "好奇",
                        "emotion": "犹豫",
                        "decision_stage": "评估",
                        "analysis": "客户对价格敏感"
                    },
                    "strategy": {
                        "name": "异议处理",
                        "framework": "认同→转化→引导",
                        "key_principle": "先认同再引导"
                    },
                    "scripts": [
                        {
                            "text": "我理解您的顾虑...",
                            "scenario": "价格咨询",
                            "tone": "温和专业"
                        }
                    ]
                }
            ],
            "suggested_actions": []
        })
    }


def _mock_diagnose_response():
    return {
        "content": json.dumps({
            "overall_score": 72,
            "diagnosis": {
                "psychology_layer": {"score": 65, "issues": []},
                "strategy_layer": {"score": 70, "issues": []},
                "script_layer": {"score": 80, "issues": []},
            },
            "improvement_plan": ["加强共情表达", "注意策略切换时机"],
            "summary": "整体表现尚可，心理层判断需加强"
        })
    }


def _mock_train_response():
    return {
        "content": json.dumps({
            "questions": [
                {
                    "id": "Q001",
                    "scenario": "客户说：你们这个项目多少钱？",
                    "customer_state": "客户处于信息收集阶段",
                    "options": [
                        {"key": "A", "text": "我们的价格是..."},
                        {"key": "B", "text": "您好，在报价之前..."},
                        {"key": "C", "text": "价格很优惠的..."},
                        {"key": "D", "text": "看您做什么项目..."}
                    ],
                    "correct_answer": "B",
                    "category": "异议处理",
                    "difficulty": 2,
                    "explanation": {
                        "psychology": "客户处于评估阶段",
                        "strategy": "先挖需再报价",
                        "script": "B选项体现了专业度"
                    },
                    "wrong_explanations": {
                        "A": "直接报价过于急促",
                        "C": "过于随意",
                        "D": "反问不够温和"
                    }
                }
            ]
        })
    }


@pytest.mark.asyncio
class TestScriptRecommendSkill:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_recommend_by_scenario(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_recommend_response()
        payload = {
            "scenario": "客户询问价格",
            "customer_profile": {
                "stage": "首次咨询",
                "concern": "价格敏感",
            },
        }
        response = await async_client.post(
            "/api/skills/script-recommend", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        for rec in data["recommendations"]:
            assert "script_id" in rec or "title" in rec
            assert "relevance_score" in rec
            assert "reason" in rec

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_recommend_empty_scenario(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_recommend_response()
        payload = {"scenario": ""}
        response = await async_client.post(
            "/api/skills/script-recommend", json=payload, headers=auth_headers
        )
        assert response.status_code in (200, 422)


@pytest.mark.asyncio
class TestScriptDiagnoseSkill:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_diagnose_script(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_diagnose_response()
        payload = {
            "script_content": "你要不要做双眼皮？我们现在打折。",
            "scenario": "首次咨询",
        }
        response = await async_client.post(
            "/api/skills/script-diagnose", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "dimensions" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert 0 <= data["overall_score"] <= 100

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_diagnose_high_quality_script(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {
            "content": json.dumps({
                "overall_score": 88,
                "diagnosis": {
                    "psychology_layer": {"score": 85, "issues": []},
                    "strategy_layer": {"score": 90, "issues": []},
                    "script_layer": {"score": 88, "issues": []},
                },
                "improvement_plan": [],
                "summary": "话术质量很高"
            })
        }
        payload = {
            "script_content": (
                "您好，非常感谢您对我们的信任。关于双眼皮手术，我想先了解一下您的具体需求。"
                "每个人的眼部条件不同，我们会根据您的面部特征为您定制最适合的方案。"
                "您方便先做一个简单的面诊吗？这样我可以给您更专业的建议。"
            ),
            "scenario": "首次咨询",
        }
        response = await async_client.post(
            "/api/skills/script-diagnose", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] >= 60


@pytest.mark.asyncio
class TestScriptTrainSkill:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_generate_training_task(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_train_response()
        payload = {
            "skill_gap": "异议处理",
            "difficulty": "intermediate",
        }
        response = await async_client.post(
            "/api/skills/script-train", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "task" in data
        assert "scenario_description" in data["task"]
        assert "expected_skills" in data["task"]

    async def test_evaluate_training_response(self, async_client: AsyncClient, auth_headers):
        payload = {
            "task_id": "mock-task-id",
            "user_response": "我理解您的顾虑，价格确实是重要的考虑因素。不过我想和您分享...",
        }
        response = await async_client.post(
            "/api/skills/script-train/evaluate", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "feedback" in data


@pytest.mark.asyncio
class TestSkillRegistry:
    async def test_list_skills(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/skills", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        skill_names = [s["name"] for s in data]
        assert "script-recommend" in skill_names
        assert "script-diagnose" in skill_names
        assert "script-train" in skill_names

    async def test_get_skill_detail(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/skills/script-recommend", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "script-recommend"
        assert "description" in data


@pytest.mark.asyncio
class TestSkillDispatcher:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_dispatch_known_skill(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_recommend_response()
        payload = {
            "skill_name": "script-recommend",
            "input": {
                "scenario": "客户犹豫不决",
            },
        }
        response = await async_client.post(
            "/api/skills/dispatch", json=payload, headers=auth_headers
        )
        assert response.status_code == 200

    async def test_dispatch_unknown_skill(self, async_client: AsyncClient, auth_headers):
        payload = {
            "skill_name": "nonexistent-skill",
            "input": {},
        }
        response = await async_client.post(
            "/api/skills/dispatch", json=payload, headers=auth_headers
        )
        assert response.status_code == 404
