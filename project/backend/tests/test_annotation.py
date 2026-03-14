import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAnnotations:
    async def test_create_annotation_good(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/annotations",
            params={
                "conversation_text": "sample conversation",
                "turn_index": 3,
                "label": "good",
                "strategy_type": "empathy",
                "note": "这里的共情做得好",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["turn_index"] == 3
        assert data["label"] == "good"
        assert data["strategy_type"] == "empathy"

    async def test_create_annotation_bad(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/annotations",
            params={
                "conversation_text": "sample",
                "turn_index": 1,
                "label": "bad",
            },
        )
        assert response.status_code == 200
        assert response.json()["label"] == "bad"

    async def test_create_annotation_neutral(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/annotations",
            params={
                "conversation_text": "sample",
                "turn_index": 0,
                "label": "neutral",
            },
        )
        assert response.status_code == 200

    async def test_create_annotation_invalid_label(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/annotations",
            params={
                "conversation_text": "sample",
                "turn_index": 0,
                "label": "invalid_label",
            },
        )
        assert response.status_code == 400

    async def test_list_annotations(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/annotations")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_annotations_with_filter(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/annotations",
            params={"label": "good", "page": 1, "page_size": 10},
        )
        assert response.status_code == 200

    async def test_update_annotation(self, async_client: AsyncClient):
        response = await async_client.put(
            "/api/v1/annotations/some-id",
            params={"label": "bad", "note": "重新标注"},
        )
        assert response.status_code == 200
        assert response.json()["updated"] is True

    async def test_ai_pre_annotate(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/annotations/ai-pre-annotate",
            params={"conversation_text": "客服：你好\n客户：我想了解项目"},
        )
        assert response.status_code == 200
        assert "annotations" in response.json()

    async def test_extract_script(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/annotations/some-id/extract-script")
        assert response.status_code == 200

    async def test_mining_suggestions(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/annotations/mining/suggestions")
        assert response.status_code == 200
        assert "suggestions" in response.json()
