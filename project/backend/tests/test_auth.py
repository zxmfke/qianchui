import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuth:
    async def test_register_user(self, async_client: AsyncClient):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "enterprise_name": "新企业",
        }
        response = await async_client.post("/api/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user):
        payload = {
            "username": "anotheruser",
            "email": "test@example.com",
            "password": "securepass123",
            "enterprise_name": "另一个企业",
        }
        response = await async_client.post("/api/auth/register", json=payload)
        assert response.status_code == 400

    async def test_login_success(self, async_client: AsyncClient, test_user):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        payload = {
            "email": "test@example.com",
            "password": "wrongpassword",
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        payload = {
            "email": "ghost@example.com",
            "password": "whatever",
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    async def test_get_current_user(self, async_client: AsyncClient, test_user, auth_headers):
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    async def test_unauthorized_access(self, async_client: AsyncClient):
        response = await async_client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    async def test_invalid_token(self, async_client: AsyncClient):
        headers = {"Authorization": "Bearer invalid-token-here"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
