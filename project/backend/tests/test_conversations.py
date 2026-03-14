import json
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient


def _mock_agent_response():
    return {
        "text": "您好，有什么可以帮您的？",
        "cards": [],
        "suggested_actions": [],
        "skill_used": None,
    }


@pytest.mark.asyncio
class TestConversations:
    async def test_list_conversations_empty(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/conversations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_conversation(self, async_client: AsyncClient, auth_headers):
        payload = {"title": "测试对话"}
        response = await async_client.post("/api/conversations", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "测试对话"

    async def test_create_conversation_default_title(self, async_client: AsyncClient, auth_headers):
        response = await async_client.post("/api/conversations", json={}, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["title"] == "新对话"

    @patch("app.agent.runtime.AgentRuntime.process_message")
    async def test_send_message(self, mock_process, async_client: AsyncClient, auth_headers):
        mock_process.return_value = _mock_agent_response()
        conv = await async_client.post("/api/conversations", json={"title": "chat"}, headers=auth_headers)
        conv_id = conv.json()["id"]

        response = await async_client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "你好"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    async def test_send_message_to_nonexistent(self, async_client: AsyncClient, auth_headers):
        response = await async_client.post(
            "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_messages_empty(self, async_client: AsyncClient, auth_headers):
        conv = await async_client.post("/api/conversations", json={"title": "test"}, headers=auth_headers)
        conv_id = conv.json()["id"]

        response = await async_client.get(
            f"/api/conversations/{conv_id}/messages", headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_messages_nonexistent_conversation(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_conversations_pagination(self, async_client: AsyncClient, auth_headers):
        for i in range(3):
            await async_client.post("/api/conversations", json={"title": f"对话{i}"}, headers=auth_headers)

        response = await async_client.get(
            "/api/conversations", params={"page": 1, "page_size": 2}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    async def test_conversation_unauthorized(self, async_client: AsyncClient):
        response = await async_client.post("/api/conversations", json={"title": "hack"})
        assert response.status_code in (401, 403)
