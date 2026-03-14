import pytest
from httpx import AsyncClient


SAMPLE_CONVERSATION = """客服：你好有什么需要
客户：我想了解下双眼皮
客服：我们医院双眼皮做得很好
客户：多少钱啊
客服：方便留个电话吗
客户：先说价格
客服：不同方案价格不同
客户：算了吧"""


@pytest.mark.asyncio
class TestOptimization:
    async def test_create_task(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/optimization/tasks",
            params={
                "conversation_text": SAMPLE_CONVERSATION,
                "search_term": "双眼皮",
                "industry": "oral",
                "service_mode": "robot",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert "classification" in data
        assert "score_result" in data

    async def test_create_task_empty_conversation(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/optimization/tasks",
            params={"conversation_text": "没有对话格式的文本"},
        )
        assert response.status_code == 400

    async def test_list_tasks(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/optimization/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_task(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/optimization/tasks/some-id")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "some-id"

    async def test_get_strategies(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/optimization/tasks/some-id/strategies")
        assert response.status_code == 200
        assert "strategies" in response.json()

    async def test_generate_strategies(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/optimization/tasks/some-id/generate-strategies")
        assert response.status_code == 200
        assert "strategies" in response.json()

    async def test_update_strategy_adopted(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/optimization/strategies/s1",
            params={"status": "adopted"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "adopted"

    async def test_update_strategy_rejected(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/optimization/strategies/s1",
            params={"status": "rejected"},
        )
        assert response.status_code == 200

    async def test_update_strategy_invalid_status(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/optimization/strategies/s1",
            params={"status": "invalid"},
        )
        assert response.status_code == 400
