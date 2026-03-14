import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDashboard:
    async def test_get_overview(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/dashboard/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_scripts" in data
        assert "total_usage_count" in data or "total_usages" in data
        assert "active_users_today" in data or "active_users" in data

    async def test_get_overview_unauthorized(self, async_client: AsyncClient):
        response = await async_client.get("/api/dashboard/overview")
        assert response.status_code in (401, 403)

    async def test_get_script_ranking(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/dashboard/script-ranking", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "by_usage" in data or "items" in data

    async def test_get_script_ranking_with_limit(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/dashboard/script-ranking", params={"limit": 5}, headers=auth_headers
        )
        assert response.status_code == 200

    async def test_get_team_stats(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/dashboard/team-stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "total_members" in data

    async def test_get_trends_default(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/dashboard/trends", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "usage_trend" in data

    async def test_get_trends_custom_days(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/dashboard/trends", params={"days": 30}, headers=auth_headers
        )
        assert response.status_code == 200
