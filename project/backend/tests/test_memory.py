import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPainPoints:
    async def test_create_pain_point(self, async_client: AsyncClient, auth_headers):
        payload = {"name": "价格敏感", "description": "客户对价格非常在意"}
        response = await async_client.post("/api/memory/pain-points", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "价格敏感"
        assert "id" in data

    async def test_list_pain_points(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/memory/pain-points",
            json={"name": "效果担忧", "description": "担心术后效果不理想"},
            headers=auth_headers,
        )
        response = await async_client.get("/api/memory/pain-points", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_create_pain_point_unauthorized(self, async_client: AsyncClient):
        response = await async_client.post("/api/memory/pain-points", json={"name": "test"})
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
class TestProducts:
    async def test_create_product(self, async_client: AsyncClient, auth_headers):
        payload = {"name": "热玛吉", "description": "抗衰项目", "pain_point_ids": []}
        response = await async_client.post("/api/memory/products", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "热玛吉"

    async def test_create_product_with_pain_point(self, async_client: AsyncClient, auth_headers):
        pp = await async_client.post(
            "/api/memory/pain-points",
            json={"name": "衰老焦虑"},
            headers=auth_headers,
        )
        pp_id = pp.json()["id"]

        payload = {"name": "水光针", "description": "补水项目", "pain_point_ids": [pp_id]}
        response = await async_client.post("/api/memory/products", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "水光针"
        assert len(data["pain_points"]) == 1

    async def test_list_products(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/memory/products",
            json={"name": "吸脂", "pain_point_ids": []},
            headers=auth_headers,
        )
        response = await async_client.get("/api/memory/products", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
class TestServices:
    async def test_create_service(self, async_client: AsyncClient, auth_headers):
        payload = {"name": "术前面诊", "description": "面对面诊断服务", "product_ids": []}
        response = await async_client.post("/api/memory/services", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "术前面诊"

    async def test_create_service_with_product(self, async_client: AsyncClient, auth_headers):
        prod = await async_client.post(
            "/api/memory/products",
            json={"name": "玻尿酸", "pain_point_ids": []},
            headers=auth_headers,
        )
        prod_id = prod.json()["id"]

        payload = {"name": "注射服务", "product_ids": [prod_id]}
        response = await async_client.post("/api/memory/services", json=payload, headers=auth_headers)
        assert response.status_code == 201
        assert len(response.json()["products"]) == 1

    async def test_list_services(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/memory/services", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
class TestKnowledgeChain:
    async def test_get_knowledge_chain_empty(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/memory/knowledge-chain", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pain_points" in data

    async def test_get_knowledge_chain_with_data(self, async_client: AsyncClient, auth_headers):
        pp = await async_client.post(
            "/api/memory/pain-points", json={"name": "恢复期担忧"}, headers=auth_headers
        )
        pp_id = pp.json()["id"]

        await async_client.post(
            "/api/memory/products",
            json={"name": "微创项目", "pain_point_ids": [pp_id]},
            headers=auth_headers,
        )

        response = await async_client.get("/api/memory/knowledge-chain", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["pain_points"]) >= 1
