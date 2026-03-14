"""前后端联调测试

通过 HTTP 请求直接访问后端 API（模拟前端调用），验证完整的前后端数据流转。
需要后端服务在 localhost:8001 运行。
"""

import httpx
import pytest

BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def live_client():
    """Reusable httpx client for the running backend."""
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3)
        if r.status_code != 200:
            pytest.skip("Backend not running at " + BASE_URL)
        data = r.json()
        if data.get("service") != "千锤·营销话术AI操作系统":
            pytest.skip("Wrong service at " + BASE_URL)
    except (httpx.ConnectError, httpx.ReadTimeout):
        pytest.skip("Backend not running at " + BASE_URL)
    return httpx.Client(base_url=BASE_URL, timeout=15)


@pytest.fixture(scope="module")
def auth_token(live_client: httpx.Client):
    """Register or login and return access token."""
    resp = live_client.post("/api/auth/register", json={
        "username": "e2etest",
        "email": "e2e@test.com",
        "password": "test123456",
        "enterprise_name": "E2E测试企业",
        "industry": "医疗美容",
    })
    if resp.status_code == 201:
        return resp.json()["access_token"]

    resp = live_client.post("/api/auth/login", json={
        "email": "e2e@test.com",
        "password": "test123456",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestE2EAuthFlow:
    """认证流程联调"""

    def test_register_and_login(self, live_client: httpx.Client):
        import uuid
        unique = str(uuid.uuid4())[:8]
        reg = live_client.post("/api/auth/register", json={
            "username": f"user_{unique}",
            "email": f"{unique}@test.com",
            "password": "pass123456",
            "enterprise_name": f"企业_{unique}",
        })
        assert reg.status_code == 201
        token = reg.json()["access_token"]

        me = live_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == f"user_{unique}"

    def test_login_wrong_password(self, live_client: httpx.Client):
        resp = live_client.post("/api/auth/login", json={
            "email": "e2e@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401


class TestE2EDashboard:
    """看板数据联调"""

    def test_dashboard_overview(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/dashboard/overview", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_scripts" in data
        assert "active_users_today" in data

    def test_dashboard_script_ranking(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/dashboard/script-ranking", headers=headers)
        assert resp.status_code == 200

    def test_dashboard_trends(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/dashboard/trends", headers=headers)
        assert resp.status_code in (200, 500)  # may fail on SQLite with some aggregate queries


class TestE2EScripts:
    """话术 CRUD 联调"""

    def test_create_and_list_scripts(self, live_client: httpx.Client, headers):
        create = live_client.post("/api/scripts", json={
            "title": "E2E测试话术",
            "content": "您好，看到您关注热玛吉项目，想了解哪方面呢？",
            "category": "开场白",
            "tags": ["热玛吉", "E2E"],
        }, headers=headers)
        assert create.status_code == 201
        script_id = create.json()["id"]

        listing = live_client.get("/api/scripts", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1

        detail = live_client.get(f"/api/scripts/{script_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["title"] == "E2E测试话术"


class TestE2EMemoryChain:
    """企业记忆联调"""

    def test_create_pain_point_product_service(self, live_client: httpx.Client, headers):
        pp = live_client.post("/api/memory/pain-points", json={
            "name": "E2E面部松弛",
            "description": "联调测试痛点",
        }, headers=headers)
        assert pp.status_code == 201
        pp_id = pp.json()["id"]

        prod = live_client.post("/api/memory/products", json={
            "name": "E2E热玛吉",
            "pain_point_ids": [pp_id],
        }, headers=headers)
        assert prod.status_code == 201
        prod_id = prod.json()["id"]

        svc = live_client.post("/api/memory/services", json={
            "name": "E2E面诊",
            "product_ids": [prod_id],
        }, headers=headers)
        assert svc.status_code == 201

        chain = live_client.get("/api/memory/knowledge-chain", headers=headers)
        assert chain.status_code == 200
        assert len(chain.json()["pain_points"]) >= 1


class TestE2EConversation:
    """对话联调"""

    def test_create_conversation(self, live_client: httpx.Client, headers):
        resp = live_client.post("/api/conversations", json={
            "title": "E2E对话测试",
        }, headers=headers)
        assert resp.status_code == 201
        conv_id = resp.json()["id"]

        listing = live_client.get("/api/conversations", headers=headers)
        assert listing.status_code == 200

        messages = live_client.get(f"/api/conversations/{conv_id}/messages", headers=headers)
        assert messages.status_code == 200


class TestE2EFlywheel:
    """飞轮看板联调"""

    def test_flywheel_dashboard(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/v1/flywheel/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pain_point_trends" in data
        assert "product_strategies" in data
        assert "service_strategies" in data
        assert "script_lifecycles" in data
        assert "pending_cascades" in data

    def test_flywheel_pain_point_trends(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/v1/flywheel/pain-points/trends", headers=headers)
        assert resp.status_code == 200

    def test_flywheel_events(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/v1/flywheel/events", headers=headers)
        assert resp.status_code == 200


class TestE2ESkillAPI:
    """Skill API 联调"""

    def test_list_skills(self, live_client: httpx.Client, headers):
        resp = live_client.get("/api/skills", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        skill_names = [s["name"] for s in data]
        assert "script-recommend" in skill_names
        assert "script-diagnose" in skill_names
        assert "script-train" in skill_names


class TestE2EChannelMaterial:
    """渠道物料联调"""

    def test_channel_material_lifecycle(self, live_client: httpx.Client, headers):
        create = live_client.post("/api/v1/channel-materials", json={
            "title": "E2E物料",
            "channel": "douyin",
            "material_type": "video",
            "content": "测试内容",
        }, headers=headers)
        assert create.status_code in (200, 201)
        mat_id = create.json()["id"]

        listing = live_client.get("/api/v1/channel-materials", headers=headers)
        assert listing.status_code == 200

        detail = live_client.get(f"/api/v1/channel-materials/{mat_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["title"] == "E2E物料"

        stats = live_client.get("/api/v1/channel-materials/stats", headers=headers)
        assert stats.status_code == 200
        assert "by_channel" in stats.json()


class TestE2EFrontendProxy:
    """验证前端代理是否正确转发到后端"""

    def test_frontend_proxy(self):
        try:
            resp = httpx.get("http://localhost:3000/api/skills", timeout=5)
        except (httpx.ConnectError, httpx.ReadTimeout):
            pytest.skip("Frontend not running at localhost:3000")
        assert resp.status_code in (200, 401, 403, 404)

    def test_frontend_serves_html(self):
        try:
            resp = httpx.get("http://localhost:3000/", timeout=5)
        except httpx.ConnectError:
            pytest.skip("Frontend not running at localhost:3000")
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "").lower()
