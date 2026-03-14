"""Tests for LLM proxy endpoint (transparent pass-through + action alias fix)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient


def _make_openai_response(content="Hello!", tool_calls=None):
    """Helper to build a mock OpenAI chat completion response."""
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "test-model",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


@pytest.mark.asyncio
class TestLLMProxy:
    @patch("app.api.llm_proxy.httpx.AsyncClient")
    async def test_chat_completions_non_stream(self, mock_client_cls, async_client: AsyncClient, auth_headers):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_openai_response("Hello! I'm here to help.")

        mock_ctx = AsyncMock()
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["choices"][0]["message"]["content"] == "Hello! I'm here to help."
        assert data["choices"][0]["finish_reason"] == "stop"

    async def test_chat_completions_empty_messages(self, async_client: AsyncClient, auth_headers):
        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={"model": "test-model", "messages": [], "stream": False},
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_chat_completions_no_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 403

    @patch("app.api.llm_proxy.httpx.AsyncClient")
    async def test_chat_completions_llm_error(self, mock_client_cls, async_client: AsyncClient, auth_headers):
        mock_ctx = AsyncMock()
        mock_ctx.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers=auth_headers,
        )
        assert response.status_code == 502

    async def test_list_models(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/proxy/llm/models", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) > 0

    @patch("app.api.llm_proxy.httpx.AsyncClient")
    async def test_tools_passed_through(self, mock_client_cls, async_client: AsyncClient, auth_headers):
        """Verify that tools/tool_choice are forwarded to upstream LLM."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_openai_response("ok")

        mock_ctx = AsyncMock()
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        tools = [{"type": "function", "function": {"name": "AgentOutput", "parameters": {}}}]
        tool_choice = {"type": "function", "function": {"name": "AgentOutput"}}

        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "tools": tools,
                "tool_choice": tool_choice,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        sent_body = mock_ctx.post.call_args[1]["json"]
        assert "tools" in sent_body
        assert "tool_choice" in sent_body
        assert sent_body["tools"] == tools

    @patch("app.api.llm_proxy.httpx.AsyncClient")
    async def test_action_alias_fix(self, mock_client_cls, async_client: AsyncClient, auth_headers):
        """Verify that 'click' action in LLM response is remapped to 'click_element_by_index'."""
        agent_output = {
            "evaluation_previous_goal": "ok",
            "memory": "",
            "next_goal": "click button",
            "action": {"click": {"index": 5}},
        }
        tool_calls = [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "AgentOutput",
                "arguments": json.dumps(agent_output),
            },
        }]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_openai_response(content=None, tool_calls=tool_calls)

        mock_ctx = AsyncMock()
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={"messages": [{"role": "user", "content": "click the button"}]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        tc = data["choices"][0]["message"]["tool_calls"][0]
        args = json.loads(tc["function"]["arguments"])
        assert "click_element_by_index" in args["action"]
        assert "click" not in args["action"]
        assert args["action"]["click_element_by_index"]["index"] == 5

    @patch("app.api.llm_proxy.httpx.AsyncClient")
    async def test_upstream_error_returns_502(self, mock_client_cls, async_client: AsyncClient, auth_headers):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error": "invalid api key"}'

        mock_ctx = AsyncMock()
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await async_client.post(
            "/api/proxy/llm/chat/completions",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            headers=auth_headers,
        )
        assert response.status_code == 502
