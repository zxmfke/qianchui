"""Integration tests for the admin module — cross-module flows.

Covers:
  1. Auth → Admin role gate (normal user denied, super_admin accepted)
  2. Full lifecycle: login → overview → create enterprise → create user → query
  3. Data consistency: counts in overview match after CRUD operations
  4. Tenant isolation: admin APIs aggregate across all enterprises
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.enterprise import Enterprise
from app.models.user import User
from app.models.script import Script
from app.models.conversation import Conversation
from app.services.auth_service import AuthService


@pytest.mark.asyncio
class TestAdminAuthIntegration:
    """Auth + Admin permission flow."""

    async def test_normal_user_cannot_access_admin(self, async_client, test_user, auth_headers):
        """admin role user should be rejected by super_admin-only endpoints."""
        endpoints = [
            ("GET", "/api/admin/overview"),
            ("GET", "/api/admin/trends"),
            ("GET", "/api/admin/enterprises"),
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/query"),
        ]
        for method, url in endpoints:
            if method == "GET":
                r = await async_client.get(url, headers=auth_headers)
            else:
                r = await async_client.post(url, headers=auth_headers, json={"question": "test"})
            assert r.status_code == 403, f"{method} {url} should be 403 for admin, got {r.status_code}"

    async def test_login_then_admin_access(self, async_client, test_db, super_admin_enterprise):
        """Register a super_admin, login via auth API, then access admin endpoints."""
        user = User(
            username="sa_login_test",
            email="sa_login@test.com",
            hashed_password=AuthService.hash_password("sapass123"),
            enterprise_id=super_admin_enterprise.id,
            role="super_admin",
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        login_r = await async_client.post("/api/auth/login", json={
            "username": "sa_login_test", "password": "sapass123",
        })
        assert login_r.status_code == 200
        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        overview_r = await async_client.get("/api/admin/overview", headers=headers)
        assert overview_r.status_code == 200
        assert "total_enterprises" in overview_r.json()


@pytest.mark.asyncio
class TestAdminLifecycleIntegration:
    """Full CRUD lifecycle through admin API."""

    async def test_enterprise_user_lifecycle(
        self, async_client, super_admin_headers, test_db, super_admin_enterprise
    ):
        """Create enterprise → create user inside it → check overview → delete user → delete enterprise."""

        # 1. Create enterprise
        create_ent = await async_client.post("/api/admin/enterprises", headers=super_admin_headers, json={
            "name": "集成测试企业", "industry": "科技互联网",
        })
        assert create_ent.status_code == 201
        ent_id = create_ent.json()["id"]

        # 2. Create user in that enterprise
        create_usr = await async_client.post("/api/admin/users", headers=super_admin_headers, json={
            "email": "lifecycle@test.com",
            "username": "lifecycle_user",
            "password": "pass123456",
            "role": "staff",
            "enterprise_id": ent_id,
        })
        assert create_usr.status_code == 201
        usr_id = create_usr.json()["id"]
        assert create_usr.json()["enterprise_name"] == "集成测试企业"

        # 3. Verify overview counts increased
        ov = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        assert ov.json()["total_enterprises"] >= 2
        assert ov.json()["total_users"] >= 2

        # 4. Verify enterprise detail shows the user
        detail = await async_client.get(f"/api/admin/enterprises/{ent_id}", headers=super_admin_headers)
        assert detail.status_code == 200
        assert detail.json()["stats"]["user_count"] == 1
        assert any(u["username"] == "lifecycle_user" for u in detail.json()["users"])

        # 5. Verify user appears in users list
        users_r = await async_client.get(
            f"/api/admin/users?enterprise_id={ent_id}", headers=super_admin_headers,
        )
        assert users_r.json()["total"] == 1

        # 6. Update user role
        upd = await async_client.put(
            f"/api/admin/users/{usr_id}", headers=super_admin_headers, json={"role": "manager"},
        )
        assert upd.status_code == 200
        assert upd.json()["role"] == "manager"

        # 7. Delete user
        del_usr = await async_client.delete(f"/api/admin/users/{usr_id}", headers=super_admin_headers)
        assert del_usr.status_code == 204

        # 8. Delete enterprise
        del_ent = await async_client.delete(f"/api/admin/enterprises/{ent_id}", headers=super_admin_headers)
        assert del_ent.status_code == 204

        # 9. Verify they're gone
        ent_check = await async_client.get(f"/api/admin/enterprises/{ent_id}", headers=super_admin_headers)
        assert ent_check.status_code == 400


@pytest.mark.asyncio
class TestAdminDataConsistency:
    """Overview numbers match actual data."""

    async def test_overview_counts_after_seeding(
        self, async_client, super_admin_headers, test_db,
        test_enterprise, test_user, super_admin_enterprise, super_admin_user,
    ):
        """Seed multiple entities and verify overview tallies."""
        script1 = Script(
            enterprise_id=test_enterprise.id, title="话术A", content="内容A",
            created_by=test_user.id,
        )
        script2 = Script(
            enterprise_id=test_enterprise.id, title="话术B", content="内容B",
            created_by=test_user.id,
        )
        conv = Conversation(
            user_id=test_user.id, enterprise_id=test_enterprise.id, title="对话1",
        )
        test_db.add_all([script1, script2, conv])
        await test_db.commit()

        ov = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        data = ov.json()
        assert data["total_enterprises"] == 2
        assert data["total_users"] == 2
        assert data["total_scripts"] == 2
        assert data["total_conversations"] == 1

    async def test_trends_reflect_new_data(
        self, async_client, super_admin_headers, test_db,
        test_enterprise, test_user, super_admin_enterprise,
    ):
        """Today's data should show in trends."""
        script = Script(
            enterprise_id=test_enterprise.id, title="趋势话术", content="abc",
            created_by=test_user.id,
        )
        test_db.add(script)
        await test_db.commit()

        trends = await async_client.get("/api/admin/trends?days=1", headers=super_admin_headers)
        assert trends.status_code == 200
        daily = trends.json()["daily_stats"]
        assert len(daily) == 1
        assert daily[0]["new_scripts"] >= 1


@pytest.mark.asyncio
class TestAdminQueryIntegration:
    """Data query returns correct results after seeding real data."""

    async def test_query_total_matches_overview(
        self, async_client, super_admin_headers, test_db,
        test_enterprise, test_user, super_admin_enterprise, super_admin_user,
    ):
        """'一共有多少企业' should match overview.total_enterprises."""
        ov = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        expected = ov.json()["total_enterprises"]

        q = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "一共有多少企业",
        })
        assert q.json()["data"]["total_enterprises"] == expected

    async def test_query_user_total_after_creation(
        self, async_client, super_admin_headers, test_db,
        test_enterprise, test_user, super_admin_enterprise, super_admin_user,
    ):
        """Create a user then query total — should increase."""
        q_before = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "一共有多少用户",
        })
        before = q_before.json()["data"]["total_users"]

        await async_client.post("/api/admin/users", headers=super_admin_headers, json={
            "email": "querycheck@test.com", "username": "querycheck",
            "password": "pass123456", "role": "staff",
            "enterprise_id": str(test_enterprise.id),
        })

        q_after = await async_client.post("/api/admin/query", headers=super_admin_headers, json={
            "question": "一共有多少用户",
        })
        assert q_after.json()["data"]["total_users"] == before + 1


@pytest.mark.asyncio
class TestAdminCrossEnterpriseAggregation:
    """Admin APIs should aggregate data across multiple enterprises."""

    async def test_overview_counts_multiple_enterprises(
        self, async_client, super_admin_headers, test_db, super_admin_enterprise,
    ):
        ent_a = Enterprise(name="企业A", industry="教育")
        ent_b = Enterprise(name="企业B", industry="金融")
        test_db.add_all([ent_a, ent_b])
        await test_db.commit()
        await test_db.refresh(ent_a)
        await test_db.refresh(ent_b)

        user_a = User(
            username="user_a", email="a@test.com",
            hashed_password=AuthService.hash_password("p"),
            enterprise_id=ent_a.id, role="staff",
        )
        user_b = User(
            username="user_b", email="b@test.com",
            hashed_password=AuthService.hash_password("p"),
            enterprise_id=ent_b.id, role="admin",
        )
        test_db.add_all([user_a, user_b])
        await test_db.commit()
        await test_db.refresh(user_a)
        await test_db.refresh(user_b)

        s_a = Script(enterprise_id=ent_a.id, title="SA", content="a", created_by=user_a.id)
        s_b = Script(enterprise_id=ent_b.id, title="SB", content="b", created_by=user_b.id)
        test_db.add_all([s_a, s_b])
        await test_db.commit()

        ov = await async_client.get("/api/admin/overview", headers=super_admin_headers)
        data = ov.json()
        assert data["total_enterprises"] >= 3
        assert data["total_users"] >= 3
        assert data["total_scripts"] >= 2

    async def test_enterprise_list_shows_all(
        self, async_client, super_admin_headers, test_db, super_admin_enterprise,
    ):
        for i in range(3):
            test_db.add(Enterprise(name=f"批量企业{i}", industry="test"))
        await test_db.commit()

        r = await async_client.get("/api/admin/enterprises", headers=super_admin_headers)
        assert r.json()["total"] >= 4
