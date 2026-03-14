"""
Extended API tests covering previously uncovered code paths.
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.deps import get_current_user, require_role
from app.models.conversation import Conversation, Message
from app.models.diagnosis import DiagnosisReport
from app.models.memory import PainPoint, Product, ServiceItem, product_pain_points, service_products
from app.models.script import Script
from app.models.simulation import SimulationSession
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.auth import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)


# ── Auth ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthExtended:
    async def test_refresh_token_valid(self, async_client: AsyncClient, test_user):
        """POST /api/auth/refresh with valid refresh token returns new tokens."""
        token_data = {
            "sub": str(test_user.id),
            "enterprise_id": str(test_user.enterprise_id),
            "role": test_user.role,
        }
        refresh_token = AuthService.create_refresh_token(token_data)
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """POST /api/auth/refresh with invalid token returns 401."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401

    async def test_get_me_returns_enterprise_info(self, async_client: AsyncClient, auth_headers, test_user):
        """GET /api/auth/me returns user profile with enterprise_id."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["enterprise_id"] == str(test_user.enterprise_id)
        assert data["role"] == "admin"


# ── Conversations ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestConversationsExtended:
    @pytest_asyncio.fixture
    async def conversation_with_messages(self, test_db, test_user, test_enterprise):
        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="Test Conv",
        )
        test_db.add(conv)
        await test_db.flush()
        for i in range(2):
            msg = Message(
                conversation_id=conv.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )
            test_db.add(msg)
        await test_db.flush()
        await test_db.commit()
        await test_db.refresh(conv)
        return conv

    async def test_get_messages_with_actual_messages(
        self, async_client: AsyncClient, auth_headers, conversation_with_messages
    ):
        """GET /{conversation_id}/messages returns actual messages."""
        conv_id = str(conversation_with_messages.id)
        response = await async_client.get(
            f"/api/conversations/{conv_id}/messages",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content"] == "Message 0"
        assert data[1]["content"] == "Message 1"

    async def test_get_messages_nonexistent_conversation(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /{conversation_id}/messages for non-existent conversation returns 404."""
        response = await async_client.get(
            "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_post_messages_nonexistent_conversation(
        self, async_client: AsyncClient, auth_headers
    ):
        """POST /{conversation_id}/messages for non-existent conversation returns 404."""
        with patch("app.agent.runtime.AgentRuntime.process_message", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
                json={"content": "hello"},
                headers=auth_headers,
            )
        assert response.status_code == 404

    @patch("app.agent.runtime.AgentRuntime.process_message_stream")
    async def test_stream_returns_streaming_response(
        self, mock_stream, async_client: AsyncClient, auth_headers
    ):
        """GET /{conversation_id}/stream returns StreamingResponse."""
        async def mock_gen():
            yield "data: {\"type\":\"chunk\",\"content\":\"hi\"}\n\n"

        mock_stream.return_value = mock_gen()

        conv_resp = await async_client.post(
            "/api/conversations",
            json={"title": "stream test"},
            headers=auth_headers,
        )
        conv_id = conv_resp.json()["id"]

        response = await async_client.post(
            f"/api/conversations/{conv_id}/stream",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


# ── Scripts ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestScriptsExtended:
    @pytest_asyncio.fixture
    async def sample_script(self, test_db, test_enterprise, test_user):
        script = Script(
            enterprise_id=test_enterprise.id,
            title="Test Script",
            content="Test content",
            category="开场白",
            tags=["tag1"],
            status="published",
            difficulty=2,
            created_by=test_user.id,
        )
        test_db.add(script)
        await test_db.flush()
        await test_db.commit()
        await test_db.refresh(script)
        return script

    async def test_list_scripts_with_search(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """GET /api/scripts with search param."""
        response = await async_client.get(
            "/api/scripts",
            params={"search": "Test"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("Test" in s["title"] for s in data["items"])

    async def test_list_scripts_with_category_status_difficulty(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """GET /api/scripts with category, status, difficulty params."""
        response = await async_client.get(
            "/api/scripts",
            params={"category": "开场白", "status": "published", "difficulty": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(s["category"] == "开场白" for s in data["items"])
        assert all(s["status"] == "published" for s in data["items"])
        assert all(s["difficulty"] == 2 for s in data["items"])

    async def test_get_script_found(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """GET /api/scripts/{id} when script exists."""
        response = await async_client.get(
            f"/api/scripts/{sample_script.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Script"

    async def test_get_script_not_found(self, async_client: AsyncClient, auth_headers):
        """GET /api/scripts/{id} when script does not exist."""
        response = await async_client.get(
            "/api/scripts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_put_script_update(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """PUT /api/scripts/{id} updates script."""
        response = await async_client.put(
            f"/api/scripts/{sample_script.id}",
            json={"title": "Updated Title", "content": "Updated content"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_delete_script_found(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """DELETE /api/scripts/{id} when script exists."""
        response = await async_client.delete(
            f"/api/scripts/{sample_script.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_delete_script_not_found(self, async_client: AsyncClient, auth_headers):
        """DELETE /api/scripts/{id} when script does not exist."""
        response = await async_client.delete(
            "/api/scripts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_post_script_usage(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """POST /api/scripts/{id}/usage records usage."""
        response = await async_client.post(
            f"/api/scripts/{sample_script.id}/usage",
            json={"context": {"action": "copy"}},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "message" in data

    async def test_get_script_categories(
        self, async_client: AsyncClient, auth_headers, sample_script
    ):
        """GET /api/scripts/categories returns categories."""
        response = await async_client.get(
            "/api/scripts/categories",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(c["name"] == "开场白" for c in data)


# ── Diagnosis ────────────────────────────────────────────────────────────────

def _mock_diagnose_llm_response():
    data = {
        "overall_score": 72,
        "diagnosis": {
            "psychology_layer": {"score": 75, "issues": []},
            "strategy_layer": {"score": 68, "issues": []},
            "script_layer": {"score": 70, "issues": []},
        },
        "improvement_plan": ["优化开场白"],
    }
    return {"content": json.dumps(data, ensure_ascii=False)}


@pytest.mark.asyncio
class TestDiagnosisExtended:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_analyze_with_mocked_llm(
        self, mock_llm, async_client: AsyncClient, auth_headers
    ):
        """POST /api/diagnosis/analyze with mocked LLM."""
        mock_llm.return_value = _mock_diagnose_llm_response()
        payload = {"conversation_text": "客服：你好\n客户：我想了解双眼皮\n客服：好的"}
        response = await async_client.post(
            "/api/diagnosis/analyze",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert data["result"]["overall_score"] == 72

    async def test_list_reports_with_pagination(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /api/diagnosis/reports with pagination."""
        response = await async_client.get(
            "/api/diagnosis/reports",
            params={"page": 1, "page_size": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_get_report_found(
        self, mock_llm, async_client: AsyncClient, auth_headers, test_db, test_user, test_enterprise
    ):
        """GET /api/diagnosis/reports/{id} when report exists."""
        mock_llm.return_value = _mock_diagnose_llm_response()
        resp = await async_client.post(
            "/api/diagnosis/analyze",
            json={"conversation_text": "客服：你好\n客户：咨询"},
            headers=auth_headers,
        )
        report_id = resp.json()["report_id"]

        response = await async_client.get(
            f"/api/diagnosis/reports/{report_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == report_id

    async def test_get_report_not_found(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /api/diagnosis/reports/{id} when report does not exist."""
        response = await async_client.get(
            "/api/diagnosis/reports/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ── Simulation ────────────────────────────────────────────────────────────────

def _mock_sim_start():
    return {"content": "你好，我想了解一下双眼皮"}


def _mock_sim_chat():
    return {"content": "嗯，我主要担心恢复期"}


def _mock_sim_score():
    return {
        "content": json.dumps({
            "overall_score": 78,
            "dimensions": [{"dimension": "专业度", "score": 85, "comment": "好"}],
            "improvement_suggestions": ["建议1"],
            "summary": "演练结束",
        }, ensure_ascii=False)
    }


@pytest.mark.asyncio
class TestSimulationExtended:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_send_message_with_mocked_llm(
        self, mock_llm, async_client: AsyncClient, auth_headers
    ):
        """POST /api/simulation/sessions/{id}/messages with mocked LLM."""
        mock_llm.side_effect = [_mock_sim_start(), _mock_sim_chat(), {"content": json.dumps({"customer_psychology": "分析", "suggested_strategy": "建议"})}]

        create_resp = await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "双眼皮", "customer_type": "首次", "difficulty": 1},
            headers=auth_headers,
        )
        session_id = create_resp.json()["id"]

        response = await async_client.post(
            f"/api/simulation/sessions/{session_id}/messages",
            json={"content": "您好，双眼皮有全切和埋线两种"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "ai_response" in response.json()

    async def test_send_message_nonexistent_session(
        self, async_client: AsyncClient, auth_headers
    ):
        """POST /api/simulation/sessions/{id}/messages for non-existent session returns 404."""
        response = await async_client.post(
            "/api/simulation/sessions/00000000-0000-0000-0000-000000000000/messages",
            json={"content": "hello"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_complete_with_mocked_llm(
        self, mock_llm, async_client: AsyncClient, auth_headers
    ):
        """POST /api/simulation/sessions/{id}/complete with mocked LLM scoring."""
        mock_llm.side_effect = [_mock_sim_start(), _mock_sim_score()]

        create_resp = await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "水光针", "customer_type": "价格敏感", "difficulty": 2},
            headers=auth_headers,
        )
        session_id = create_resp.json()["id"]

        response = await async_client.post(
            f"/api/simulation/sessions/{session_id}/complete",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 78
        assert "dimensions" in data

    async def test_complete_nonexistent_session(
        self, async_client: AsyncClient, auth_headers
    ):
        """POST /api/simulation/sessions/{id}/complete for non-existent session returns 404."""
        response = await async_client.post(
            "/api/simulation/sessions/00000000-0000-0000-0000-000000000000/complete",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_list_sessions_with_pagination(
        self, mock_llm, async_client: AsyncClient, auth_headers
    ):
        """GET /api/simulation/sessions with pagination."""
        mock_llm.return_value = _mock_sim_start()
        await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "test", "customer_type": "首次", "difficulty": 1},
            headers=auth_headers,
        )

        response = await async_client.get(
            "/api/simulation/sessions",
            params={"page": 1, "page_size": 10},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1


# ── Memory ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMemoryExtended:
    async def test_list_products_with_pain_points(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /api/memory/products returns products with pain_point relations."""
        pp_resp = await async_client.post(
            "/api/memory/pain-points",
            json={"name": "焦虑", "description": "desc"},
            headers=auth_headers,
        )
        pp_id = pp_resp.json()["id"]

        await async_client.post(
            "/api/memory/products",
            json={"name": "热玛吉", "pain_point_ids": [pp_id]},
            headers=auth_headers,
        )

        response = await async_client.get("/api/memory/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        prod = next(p for p in data if p["name"] == "热玛吉")
        assert len(prod["pain_points"]) >= 1

    async def test_create_product_with_pain_point_ids(
        self, async_client: AsyncClient, auth_headers
    ):
        """POST /api/memory/products with pain_point_ids."""
        pp_resp = await async_client.post(
            "/api/memory/pain-points",
            json={"name": "效果担忧"},
            headers=auth_headers,
        )
        pp_id = pp_resp.json()["id"]

        response = await async_client.post(
            "/api/memory/products",
            json={"name": "玻尿酸", "pain_point_ids": [pp_id]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert len(response.json()["pain_points"]) == 1

    async def test_list_services_with_products(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /api/memory/services returns services with product relations."""
        prod_resp = await async_client.post(
            "/api/memory/products",
            json={"name": "水光", "pain_point_ids": []},
            headers=auth_headers,
        )
        prod_id = prod_resp.json()["id"]

        await async_client.post(
            "/api/memory/services",
            json={"name": "面诊", "product_ids": [prod_id]},
            headers=auth_headers,
        )

        response = await async_client.get("/api/memory/services", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert any(s["name"] == "面诊" for s in data)

    async def test_create_service_with_product_ids(
        self, async_client: AsyncClient, auth_headers
    ):
        """POST /api/memory/services with product_ids."""
        prod_resp = await async_client.post(
            "/api/memory/products",
            json={"name": "吸脂", "pain_point_ids": []},
            headers=auth_headers,
        )
        prod_id = prod_resp.json()["id"]

        response = await async_client.post(
            "/api/memory/services",
            json={"name": "咨询", "product_ids": [prod_id]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert len(response.json()["products"]) == 1

    async def test_get_knowledge_chain_full_traversal(
        self, async_client: AsyncClient, auth_headers
    ):
        """GET /api/memory/knowledge-chain full chain traversal."""
        pp_resp = await async_client.post(
            "/api/memory/pain-points",
            json={"name": "恢复期"},
            headers=auth_headers,
        )
        pp_id = pp_resp.json()["id"]

        prod_resp = await async_client.post(
            "/api/memory/products",
            json={"name": "微创", "pain_point_ids": [pp_id]},
            headers=auth_headers,
        )
        prod_id = prod_resp.json()["id"]

        await async_client.post(
            "/api/memory/services",
            json={"name": "服务A", "product_ids": [prod_id]},
            headers=auth_headers,
        )

        response = await async_client.get("/api/memory/knowledge-chain", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["pain_points"]) >= 1
        node = data["pain_points"][0]
        assert node["type"] == "pain_point"
        assert len(node["children"]) >= 1


# ── API Deps (require_role, inactive user) ───────────────────────────────────

@pytest.mark.asyncio
class TestApiDeps:
    async def test_require_role_authorized(self, test_user):
        """require_role allows user with matching role."""
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.headers = {"accept-language": "zh"}
        admin_checker = require_role("admin", "owner")
        result = await admin_checker(mock_request, test_user)
        assert result == test_user

    async def test_require_role_forbidden(self, test_user, test_enterprise):
        """require_role raises 403 for user without matching role."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        mock_request = MagicMock()
        mock_request.headers = {"accept-language": "zh"}
        staff_user = User(
            id=uuid.uuid4(),
            username="staff",
            email="staff@test.com",
            hashed_password="x",
            enterprise_id=test_enterprise.id,
            role="staff",
            is_active=True,
        )
        admin_checker = require_role("admin", "owner")

        with pytest.raises(HTTPException) as exc_info:
            await admin_checker(mock_request, staff_user)
        assert exc_info.value.status_code == 403

    async def test_inactive_user_returns_403(
        self, async_client: AsyncClient, test_db, test_enterprise
    ):
        """Inactive user gets 403 when accessing protected endpoint."""
        inactive_user = User(
            id=uuid.uuid4(),
            username="inactive",
            email="inactive@example.com",
            hashed_password=AuthService.hash_password("pass"),
            enterprise_id=test_enterprise.id,
            role="admin",
            is_active=False,
        )
        test_db.add(inactive_user)
        await test_db.commit()

        token = AuthService.create_access_token({
            "sub": str(inactive_user.id),
            "enterprise_id": str(inactive_user.enterprise_id),
            "role": inactive_user.role,
        })
        headers = {"Authorization": f"Bearer {token}"}

        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 403


# ── app.utils.auth ───────────────────────────────────────────────────────────

class TestUtilsAuth:
    def test_hash_password(self):
        """hash_password produces different hash for same input (salt)."""
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2
        assert len(h1) > 20

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        hashed = hash_password("mypass")
        assert verify_password("mypass", hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password returns False for wrong password."""
        hashed = hash_password("mypass")
        assert verify_password("wrong", hashed) is False

    def test_create_access_token(self):
        """create_access_token produces valid JWT."""
        token = create_access_token({"sub": "user-123", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_token_valid(self):
        """verify_token returns payload for valid token."""
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_token_invalid(self):
        """verify_token returns None for invalid token."""
        payload = verify_token("invalid-token")
        assert payload is None


# ── app.utils.deps ───────────────────────────────────────────────────────────
# Note: app.utils.deps defines get_current_user (OAuth2PasswordBearer) and
# get_current_enterprise. No API routes currently use these; app.api.deps is used.
# Token validation is covered by TestUtilsAuth.verify_token_*.
