import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_quiz_llm_response():
    """模拟 LLM provider 返回的 chat_completion 结果"""
    data = {
        "questions": [
            {
                "id": "q1",
                "scenario": "客户说太贵了",
                "customer_state": "犹豫中",
                "options": [
                    {"key": "A", "text": "直接降价"},
                    {"key": "B", "text": "强调价值和效果"},
                    {"key": "C", "text": "忽略继续推销"},
                    {"key": "D", "text": "反问客户预算"},
                ],
                "correct_answer": "B",
                "category": "异议处理",
                "difficulty": 2,
                "explanation": {
                    "psychology": "价格异议背后是价值不确定",
                    "strategy": "先确认需求再强调效果",
                    "script": "我理解您的顾虑，其实效果和安全才是最重要的...",
                },
            },
            {
                "id": "q2",
                "scenario": "首次咨询客户",
                "customer_state": "好奇",
                "options": [
                    {"key": "A", "text": "价格"},
                    {"key": "B", "text": "效果"},
                    {"key": "C", "text": "安全性"},
                    {"key": "D", "text": "医生资质"},
                ],
                "correct_answer": "C",
                "category": "客户心理",
                "difficulty": 1,
                "explanation": {
                    "psychology": "首次咨询信任感尚未建立",
                    "strategy": "优先解除安全顾虑",
                    "script": "您放心，我们所有项目都经过严格的安全认证...",
                },
            },
        ]
    }
    return {"content": json.dumps(data, ensure_ascii=False)}


@pytest.mark.asyncio
class TestTrainingQuiz:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_get_quiz(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_quiz_llm_response()
        response = await async_client.get("/api/training/quiz", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "total" in data
        assert data["total"] >= 1

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_get_quiz_with_params(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_quiz_llm_response()
        response = await async_client.get(
            "/api/training/quiz",
            params={"count": 5, "difficulty": 3, "category": "异议处理"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_get_quiz_unauthorized(self, async_client: AsyncClient):
        response = await async_client.get("/api/training/quiz")
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
class TestTrainingAnswer:
    async def test_submit_correct_answer(self, async_client: AsyncClient, auth_headers):
        payload = {
            "question_id": "q1",
            "answer": "B",
            "question_data": {
                "question": "客户说太贵了怎么办？",
                "correct_answer": "B",
                "category": "异议处理",
                "difficulty": 2,
                "explanation": {
                    "psychology": "价格异议",
                    "strategy": "价值强调",
                    "script": "效果才是关键",
                },
            },
        }
        response = await async_client.post("/api/training/quiz/answer", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["correct_answer"] == "B"
        assert "explanation" in data

    async def test_submit_wrong_answer(self, async_client: AsyncClient, auth_headers):
        payload = {
            "question_id": "q2",
            "answer": "A",
            "question_data": {
                "question": "客户犹豫不决的心理是？",
                "correct_answer": "C",
                "category": "客户心理",
                "difficulty": 1,
                "explanation": {"psychology": "", "strategy": "", "script": ""},
            },
        }
        response = await async_client.post("/api/training/quiz/answer", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is False
        assert data["correct_answer"] == "C"

    async def test_multiple_answers_update_accuracy(self, async_client: AsyncClient, auth_headers):
        base = {
            "question_data": {
                "question": "q",
                "correct_answer": "A",
                "category": "综合",
                "difficulty": 1,
                "explanation": {"psychology": "", "strategy": "", "script": ""},
            }
        }
        await async_client.post(
            "/api/training/quiz/answer",
            json={"question_id": "q1", **base, "answer": "A"},
            headers=auth_headers,
        )
        await async_client.post(
            "/api/training/quiz/answer",
            json={"question_id": "q2", **base, "answer": "B"},
            headers=auth_headers,
        )
        resp = await async_client.post(
            "/api/training/quiz/answer",
            json={"question_id": "q3", **base, "answer": "A"},
            headers=auth_headers,
        )
        data = resp.json()
        assert 0.0 < data["user_accuracy"] <= 1.0


@pytest.mark.asyncio
class TestTrainingProgress:
    async def test_get_progress_empty(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/training/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 0
        assert data["accuracy"] == 0.0
        assert data["streak_days"] == 0

    async def test_get_progress_after_answers(self, async_client: AsyncClient, auth_headers):
        payload = {
            "question_id": "q1",
            "answer": "A",
            "question_data": {
                "question": "q1",
                "correct_answer": "A",
                "category": "话术技巧",
                "difficulty": 1,
                "explanation": {"psychology": "", "strategy": "", "script": ""},
            },
        }
        await async_client.post("/api/training/quiz/answer", json=payload, headers=auth_headers)

        response = await async_client.get("/api/training/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] >= 1
        assert data["correct_count"] >= 1

    async def test_get_weak_points(self, async_client: AsyncClient, auth_headers):
        base_q = {
            "question_data": {
                "question": "q",
                "correct_answer": "A",
                "category": "弱项测试",
                "difficulty": 1,
                "explanation": {"psychology": "", "strategy": "", "script": ""},
            }
        }
        for i in range(5):
            await async_client.post(
                "/api/training/quiz/answer",
                json={"question_id": f"weak_{i}", **base_q, "answer": "B"},
                headers=auth_headers,
            )

        response = await async_client.get("/api/training/weak-points", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(w["category"] == "弱项测试" for w in data)
