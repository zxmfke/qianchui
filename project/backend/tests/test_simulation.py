import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_start_llm():
    """模拟 LLM 返回的开场白"""
    return {"content": "你好，我想了解一下双眼皮手术"}


def _mock_chat_llm():
    """模拟 LLM 返回的对话回复"""
    return {"content": "嗯，我主要担心恢复期要多久？会不会留疤？"}


def _mock_score_llm():
    """模拟 LLM 返回的评分 JSON"""
    data = {
        "overall_score": 78,
        "dimensions": [
            {"dimension": "专业度", "score": 85, "comment": "项目介绍清晰"},
            {"dimension": "共情能力", "score": 70, "comment": "共情表达偏少"},
            {"dimension": "留联技巧", "score": 75, "comment": "留联时机基本合理"},
        ],
        "improvement_suggestions": ["增加更多共情表达", "留联前应先提供价值信息"],
        "summary": "整体表现良好，共情能力有提升空间",
    }
    return {"content": json.dumps(data, ensure_ascii=False)}


@pytest.mark.asyncio
class TestSimulationSessions:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_create_session(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_start_llm()
        payload = {
            "scenario": "双眼皮咨询",
            "customer_type": "首次咨询",
            "difficulty": 2,
        }
        response = await async_client.post("/api/simulation/sessions", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "active"
        assert data["scenario"] == "双眼皮咨询"

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_send_message(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.side_effect = [_mock_start_llm(), _mock_chat_llm()]

        create_resp = await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "双眼皮咨询", "customer_type": "首次", "difficulty": 1},
            headers=auth_headers,
        )
        session_id = create_resp.json()["id"]

        response = await async_client.post(
            f"/api/simulation/sessions/{session_id}/messages",
            json={"content": "您好，双眼皮有全切和埋线两种方式"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data

    async def test_send_message_nonexistent_session(self, async_client: AsyncClient, auth_headers):
        response = await async_client.post(
            "/api/simulation/sessions/00000000-0000-0000-0000-000000000000/messages",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_complete_session(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.side_effect = [_mock_start_llm(), _mock_score_llm()]

        create_resp = await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "水光针咨询", "customer_type": "价格敏感型", "difficulty": 2},
            headers=auth_headers,
        )
        session_id = create_resp.json()["id"]

        response = await async_client.post(
            f"/api/simulation/sessions/{session_id}/complete",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "dimensions" in data
        assert "improvement_suggestions" in data

    async def test_complete_nonexistent_session(self, async_client: AsyncClient, auth_headers):
        response = await async_client.post(
            "/api/simulation/sessions/00000000-0000-0000-0000-000000000000/complete",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_sessions_empty(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/simulation/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_list_sessions_after_create(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_start_llm()
        await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "test", "customer_type": "首次", "difficulty": 1},
            headers=auth_headers,
        )

        response = await async_client.get("/api/simulation/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_create_session_unauthorized(self, async_client: AsyncClient):
        payload = {"scenario": "test", "customer_type": "首次", "difficulty": 1}
        response = await async_client.post("/api/simulation/sessions", json=payload)
        assert response.status_code in (401, 403)
