"""Unit tests for /api/admin/* — super admin APIs."""

import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.enterprise import Enterprise
from app.models.user import User
from app.models.script import Script
from app.models.conversation import Conversation, Message
from app.models.training import TrainingRecord
from app.models.simulation import SimulationSession
from app.models.diagnosis import DiagnosisReport
from app.models.channel_material import ChannelMaterial
from app.services.auth_service import AuthService


# ── Permission Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAdminPermissions:
    """Non-super_admin users should be rejected with 403."""

    async def test_overview_requires_super_admin(self, async_client, auth_headers):
        r = await async_client.get("/api/admin/overview", headers=auth_headers)
        assert r.status_code == 403

    async def test_trends_requires_super_admin(self, async_client, auth_headers):
        r = await async_client.get("/api/admin/trends", headers=auth_headers)
        assert r.status_code == 403

    async def test_enterprises_requires_super_admin(self, async_client, auth_headers):
        r = await async_client.get("/api/admin/enterprises", headers=auth_headers)
        assert r.status_code == 403

    async def test_users_requires_super_admin(self, async_client, auth_headers):
        r = await async_client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_query_requires_super_admin(self, async_client, auth_headers):
        r = await async_client.post("/api/admin/query", headers=auth_headers, json={"question": "总览"})
        assert r.status_code == 403

    async def test_unauthenticated_rejected(self, async_client):
        r = await async_client.get("/api/admin/overview")
        assert r.status_code in (401, 403)


# ── System Overview ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSystemOverview:

    async def test_overview_returns_all_fields(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        expected_fields = [
            "total_enterprises", "active_enterprises", "total_users", "active_users",
            "total_scripts", "total_conversations", "total_messages",
            "total_training_records", "total_simulations",
            "total_diagnosis_reports", "total_channel_materials",
        ]
        for f in expected_fields:
            assert f in data, f"missing field: {f}"
            assert isinstance(data[f], int)

    async def test_overview_counts_are_correct(
        self, async_client, super_admin_headers, test_db, test_enterprise, test_user
    ):
        script = Script(
            enterprise_id=test_enterprise.id, title="测试话术",
            content="内容", created_by=test_user.id,
        )
        test_db.add(script)
        conv = Conversation(user_id=test_user.id, enterprise_id=test_enterprise.id, title="test")
        test_db.add(conv)
        await test_db.commit()

        r = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_enterprises"] >= 2
        assert data["total_users"] >= 2
        assert data["total_scripts"] >= 1
        assert data["total_conversations"] >= 1


# ── System Trends ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSystemTrends:

    async def test_trends_default_30_days(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/trends", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "daily_stats" in data
        assert len(data["daily_stats"]) == 30

    async def test_trends_custom_days(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/trends?days=7", headers=super_admin_headers)
        assert r.status_code == 200
        assert len(r.json()["daily_stats"]) == 7

    async def test_trends_each_day_has_fields(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/trends?days=3", headers=super_admin_headers)
        for day in r.json()["daily_stats"]:
            assert "date" in day
            assert "new_enterprises" in day
            assert "new_users" in day
            assert "new_scripts" in day
            assert "new_conversations" in day


# ── Enterprise CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEnterpriseCRUD:

    async def test_list_enterprises(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/enterprises", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_enterprises_with_search(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/enterprises?search=测试", headers=super_admin_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(e["name"] == "测试企业" for e in items)

    async def test_list_enterprises_pagination(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.get("/api/admin/enterprises?page=1&page_size=1", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    async def test_create_enterprise(self, async_client, super_admin_headers):
        r = await async_client.post("/api/admin/enterprises", headers=super_admin_headers, json={
            "name": "新企业", "industry": "教育培训",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "新企业"
        assert data["industry"] == "教育培训"
        assert data["is_active"] is True
        assert data["user_count"] == 0

    async def test_get_enterprise_detail(self, async_client, super_admin_headers, test_enterprise, test_user, test_db):
        ent_id = test_enterprise.id
        test_db.expunge_all()
        r = await async_client.get(f"/api/admin/enterprises/{ent_id}", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "测试企业"
        assert "stats" in data
        assert "users" in data
        assert data["stats"]["user_count"] >= 1

    async def test_get_enterprise_not_found(self, async_client, super_admin_headers):
        r = await async_client.get(f"/api/admin/enterprises/{uuid4()}", headers=super_admin_headers)
        assert r.status_code == 400

    async def test_update_enterprise(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.put(
            f"/api/admin/enterprises/{test_enterprise.id}",
            headers=super_admin_headers,
            json={"name": "更新名称", "industry": "金融保险"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "更新名称"
        assert r.json()["industry"] == "金融保险"

    async def test_update_enterprise_partial(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.put(
            f"/api/admin/enterprises/{test_enterprise.id}",
            headers=super_admin_headers,
            json={"is_active": False},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    async def test_delete_enterprise(self, async_client, super_admin_headers, test_db):
        ent = Enterprise(name="待删除企业", industry="test")
        test_db.add(ent)
        await test_db.commit()
        await test_db.refresh(ent)

        r = await async_client.delete(f"/api/admin/enterprises/{ent.id}", headers=super_admin_headers)
        assert r.status_code == 204

        r2 = await async_client.get(f"/api/admin/enterprises/{ent.id}", headers=super_admin_headers)
        assert r2.status_code == 400

    async def test_delete_enterprise_not_found(self, async_client, super_admin_headers):
        r = await async_client.delete(f"/api/admin/enterprises/{uuid4()}", headers=super_admin_headers)
        assert r.status_code == 400


# ── Account CRUD ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAccountCRUD:

    async def test_list_users(self, async_client, super_admin_headers, test_user):
        r = await async_client.get("/api/admin/users", headers=super_admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_users_filter_by_role(self, async_client, super_admin_headers, test_user):
        r = await async_client.get("/api/admin/users?role=admin", headers=super_admin_headers)
        assert r.status_code == 200
        for u in r.json()["items"]:
            assert u["role"] == "admin"

    async def test_list_users_filter_by_enterprise(
        self, async_client, super_admin_headers, test_user, test_enterprise
    ):
        r = await async_client.get(
            f"/api/admin/users?enterprise_id={test_enterprise.id}",
            headers=super_admin_headers,
        )
        assert r.status_code == 200
        for u in r.json()["items"]:
            assert u["enterprise_id"] == str(test_enterprise.id)

    async def test_list_users_search(self, async_client, super_admin_headers, test_user):
        r = await async_client.get("/api/admin/users?search=testuser", headers=super_admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    async def test_create_user(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/users", headers=super_admin_headers, json={
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "password123",
            "role": "staff",
            "enterprise_id": str(test_enterprise.id),
        })
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "newuser"
        assert data["role"] == "staff"
        assert data["enterprise_name"] == "测试企业"

    async def test_create_user_duplicate_email(self, async_client, super_admin_headers, test_enterprise, test_user):
        r = await async_client.post("/api/admin/users", headers=super_admin_headers, json={
            "email": "test@example.com",
            "username": "unique_name",
            "password": "password123",
            "role": "staff",
            "enterprise_id": str(test_enterprise.id),
        })
        assert r.status_code == 400

    async def test_create_user_invalid_enterprise(self, async_client, super_admin_headers):
        r = await async_client.post("/api/admin/users", headers=super_admin_headers, json={
            "email": "x@test.com",
            "username": "xuser",
            "password": "password123",
            "role": "staff",
            "enterprise_id": str(uuid4()),
        })
        assert r.status_code == 400

    async def test_update_user(self, async_client, super_admin_headers, test_user):
        r = await async_client.put(
            f"/api/admin/users/{test_user.id}",
            headers=super_admin_headers,
            json={"role": "manager"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "manager"

    async def test_update_user_password(self, async_client, super_admin_headers, test_user):
        r = await async_client.put(
            f"/api/admin/users/{test_user.id}",
            headers=super_admin_headers,
            json={"password": "newpass456"},
        )
        assert r.status_code == 200

    async def test_delete_user(self, async_client, super_admin_headers, test_db, test_enterprise):
        user = User(
            username="todelete", email="del@test.com",
            hashed_password=AuthService.hash_password("pass"),
            enterprise_id=test_enterprise.id, role="staff",
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        r = await async_client.delete(f"/api/admin/users/{user.id}", headers=super_admin_headers)
        assert r.status_code == 204

    async def test_delete_self_forbidden(self, async_client, super_admin_headers, super_admin_user):
        r = await async_client.delete(
            f"/api/admin/users/{super_admin_user.id}", headers=super_admin_headers,
        )
        assert r.status_code == 403

    async def test_delete_user_not_found(self, async_client, super_admin_headers):
        r = await async_client.delete(f"/api/admin/users/{uuid4()}", headers=super_admin_headers)
        assert r.status_code == 400

    async def test_user_list_includes_enterprise_name(self, async_client, super_admin_headers, test_user):
        r = await async_client.get("/api/admin/users", headers=super_admin_headers)
        items = r.json()["items"]
        for u in items:
            assert "enterprise_name" in u


# ── Admin Data Query ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAdminDataQuery:

    async def test_query_overview(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "系统总览",
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "企业" in data["answer"] or "系统" in data["answer"]
        assert data["data"] is not None

    async def test_query_enterprise_total(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "一共有多少企业",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["total_enterprises"] >= 1

    async def test_query_user_total(self, async_client, super_admin_headers, test_user):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "一共有多少用户",
        })
        assert r.status_code == 200
        assert r.json()["data"]["total_users"] >= 1

    async def test_query_yesterday_enterprises(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "昨天新增多少企业",
        })
        assert r.status_code == 200
        assert "yesterday_new_enterprises" in r.json()["data"]

    async def test_query_today_scripts(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "今天新增了多少话术",
        })
        assert r.status_code == 200
        assert "today_new_scripts" in r.json()["data"]

    async def test_query_unknown(self, async_client, super_admin_headers, test_enterprise):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "天气怎么样",
        })
        assert r.status_code == 200
        assert "抱歉" in r.json()["answer"]
        assert r.json()["data"] is None

    async def test_query_empty_rejected(self, async_client, super_admin_headers):
        r = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "",
        })
        assert r.status_code == 422
