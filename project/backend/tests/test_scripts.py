import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestScripts:
    @pytest_asyncio.fixture
    async def sample_script(self, async_client: AsyncClient, auth_headers) -> dict:
        payload = {
            "title": "首次咨询开场白",
            "content": "您好，我是XX医美的专属顾问，很高兴为您服务。请问您今天想了解哪方面的项目呢？",
            "category": "开场白",
            "tags": ["医美", "开场白", "首次咨询"],
        }
        response = await async_client.post("/api/scripts", json=payload, headers=auth_headers)
        assert response.status_code == 201
        return response.json()

    async def test_create_script(self, async_client: AsyncClient, auth_headers):
        payload = {
            "title": "价格异议处理",
            "content": "我理解您对价格的顾虑。我们的价格包含了术前检查、手术、术后护理的全流程服务...",
            "category": "异议处理",
            "tags": ["异议处理", "价格"],
        }
        response = await async_client.post("/api/scripts", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "价格异议处理"
        assert data["category"] == "异议处理"
        assert "id" in data
        assert "created_at" in data

    async def test_list_scripts(self, async_client: AsyncClient, auth_headers, sample_script):
        response = await async_client.get("/api/scripts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    async def test_list_scripts_with_filter(self, async_client: AsyncClient, auth_headers, sample_script):
        response = await async_client.get(
            "/api/scripts", params={"category": "开场白"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["category"] == "开场白" for item in data["items"])

    async def test_get_script(self, async_client: AsyncClient, auth_headers, sample_script):
        script_id = sample_script["id"]
        response = await async_client.get(f"/api/scripts/{script_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == script_id
        assert data["title"] == "首次咨询开场白"

    async def test_get_script_not_found(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/scripts/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert response.status_code == 404

    async def test_update_script(self, async_client: AsyncClient, auth_headers, sample_script):
        script_id = sample_script["id"]
        payload = {
            "title": "首次咨询开场白（优化版）",
            "content": "您好！欢迎咨询XX医美，我是您的专属美学顾问。请问您对哪方面比较感兴趣？",
        }
        response = await async_client.put(
            f"/api/scripts/{script_id}", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "首次咨询开场白（优化版）"
        assert data["version"] > sample_script.get("version", 1)

    async def test_delete_script(self, async_client: AsyncClient, auth_headers, sample_script):
        script_id = sample_script["id"]
        response = await async_client.delete(f"/api/scripts/{script_id}", headers=auth_headers)
        assert response.status_code == 204

        response = await async_client.get(f"/api/scripts/{script_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_script_search(self, async_client: AsyncClient, auth_headers, sample_script):
        response = await async_client.get(
            "/api/scripts", params={"search": "开场白"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    async def test_record_usage(self, async_client: AsyncClient, auth_headers, sample_script):
        script_id = sample_script["id"]
        payload = {
            "context": {"action": "copy", "source": "客服对话中使用"},
        }
        response = await async_client.post(
            f"/api/scripts/{script_id}/usage", json=payload, headers=auth_headers
        )
        assert response.status_code == 201

    async def test_create_script_unauthorized(self, async_client: AsyncClient):
        payload = {
            "title": "无权限话术",
            "content": "这条不该成功",
            "category": "测试",
        }
        response = await async_client.post("/api/scripts", json=payload)
        assert response.status_code in (401, 403)
