import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestABTest:
    async def test_create_ab_test(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/ab-tests",
            params={"name": "开场白优化", "description": "测试新版vs旧版开场白", "duration_days": 7},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "开场白优化"
        assert data["status"] == "draft"
        assert data["duration_days"] == 7

    async def test_create_ab_test_default_duration(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/ab-tests",
            params={"name": "留联话术测试"},
        )
        assert response.status_code == 200
        assert response.json()["duration_days"] == 14

    async def test_list_ab_tests(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/ab-tests")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_ab_test(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/ab-tests/test-123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-123"
        assert data["status"] == "draft"

    async def test_start_ab_test(self, async_client: AsyncClient):
        response = await async_client.put("/api/v1/ab-tests/test-123/start")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    async def test_stop_ab_test(self, async_client: AsyncClient):
        response = await async_client.put("/api/v1/ab-tests/test-123/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    async def test_get_metrics(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/ab-tests/test-123/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["test_id"] == "test-123"
        assert "variants" in data
        assert "significance" in data

    async def test_conclude_promote(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/ab-tests/test-123/conclude",
            params={"decision": "promote"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conclusion"] == "promote"
        assert data["status"] == "completed"

    async def test_conclude_rollback(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/ab-tests/test-123/conclude",
            params={"decision": "rollback"},
        )
        assert response.status_code == 200

    async def test_conclude_invalid_decision(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/ab-tests/test-123/conclude",
            params={"decision": "invalid"},
        )
        assert response.status_code == 400
