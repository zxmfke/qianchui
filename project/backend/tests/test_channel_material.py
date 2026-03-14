import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChannelMaterial:
    async def test_create_material(self, async_client: AsyncClient, auth_headers):
        payload = {
            "channel": "douyin",
            "title": "热玛吉短视频",
            "content": "热玛吉是目前最受欢迎的抗衰项目之一...",
            "material_type": "video",
            "tags": ["抗衰", "热玛吉"],
        }
        response = await async_client.post("/api/v1/channel-materials", json=payload, headers=auth_headers)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["title"] == "热玛吉短视频"
        assert data["channel"] == "douyin"
        assert data["material_type"] == "video"
        assert "id" in data

    async def test_create_material_xhs(self, async_client: AsyncClient, auth_headers):
        payload = {
            "channel": "xhs",
            "title": "小红书种草笔记",
            "content": "今天去做了水光针，效果超棒！",
            "material_type": "article",
        }
        response = await async_client.post("/api/v1/channel-materials", json=payload, headers=auth_headers)
        assert response.status_code in (200, 201)
        assert response.json()["channel"] == "xhs"

    async def test_create_material_missing_title(self, async_client: AsyncClient, auth_headers):
        payload = {
            "channel": "douyin",
            "content": "test content",
        }
        response = await async_client.post("/api/v1/channel-materials", json=payload, headers=auth_headers)
        assert response.status_code == 422

    async def test_list_materials(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "wechat", "title": "公众号文章", "content": "微信内容", "material_type": "article"},
            headers=auth_headers,
        )
        response = await async_client.get("/api/v1/channel-materials", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_materials_filter_channel(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "baidu", "title": "百度推广", "content": "百度内容", "material_type": "ad"},
            headers=auth_headers,
        )
        response = await async_client.get(
            "/api/v1/channel-materials", params={"channel": "baidu"}, headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_list_materials_keyword_search(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "玻尿酸推广", "content": "玻尿酸填充内容", "material_type": "video"},
            headers=auth_headers,
        )
        response = await async_client.get(
            "/api/v1/channel-materials", params={"keyword": "玻尿酸"}, headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_list_materials_pagination(self, async_client: AsyncClient, auth_headers):
        for i in range(3):
            await async_client.post(
                "/api/v1/channel-materials",
                json={"channel": "douyin", "title": f"分页测试{i}", "content": "c", "material_type": "video"},
                headers=auth_headers,
            )
        response = await async_client.get(
            "/api/v1/channel-materials", params={"page": 1, "page_size": 2}, headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    async def test_get_material(self, async_client: AsyncClient, auth_headers):
        create_resp = await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "详情测试", "content": "详情内容", "material_type": "video"},
            headers=auth_headers,
        )
        material_id = create_resp.json()["id"]

        response = await async_client.get(f"/api/v1/channel-materials/{material_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "详情测试"

    async def test_get_material_not_found(self, async_client: AsyncClient, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/channel-materials/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_material(self, async_client: AsyncClient, auth_headers):
        create_resp = await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "旧标题", "content": "旧内容", "material_type": "video"},
            headers=auth_headers,
        )
        material_id = create_resp.json()["id"]

        response = await async_client.put(
            f"/api/v1/channel-materials/{material_id}",
            json={"title": "新标题", "tags": ["新标签"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "新标题"
        assert "新标签" in response.json()["tags"]

    async def test_update_material_not_found(self, async_client: AsyncClient, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = await async_client.put(
            f"/api/v1/channel-materials/{fake_id}",
            json={"title": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_delete_material(self, async_client: AsyncClient, auth_headers):
        create_resp = await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "要删除的物料", "content": "c", "material_type": "video"},
            headers=auth_headers,
        )
        material_id = create_resp.json()["id"]

        response = await async_client.delete(f"/api/v1/channel-materials/{material_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

    async def test_delete_material_not_found(self, async_client: AsyncClient, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/channel-materials/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_get_stats(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "stats test", "content": "c", "material_type": "video"},
            headers=auth_headers,
        )
        response = await async_client.get("/api/v1/channel-materials/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "by_channel" in data
        assert "total" in data

    async def test_extract_material(self, async_client: AsyncClient, auth_headers):
        create_resp = await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "提取测试", "content": "热玛吉抗衰老效果显著", "material_type": "video"},
            headers=auth_headers,
        )
        material_id = create_resp.json()["id"]

        response = await async_client.post(f"/api/v1/channel-materials/{material_id}/extract", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "extracted_info" in data

    async def test_extract_material_not_found(self, async_client: AsyncClient, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"/api/v1/channel-materials/{fake_id}/extract", headers=auth_headers)
        assert response.status_code == 404

    async def test_unauthenticated_access(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/channel-materials")
        assert response.status_code == 403

    async def test_list_materials_status_filter(self, async_client: AsyncClient, auth_headers):
        await async_client.post(
            "/api/v1/channel-materials",
            json={"channel": "douyin", "title": "active item", "content": "c", "material_type": "video"},
            headers=auth_headers,
        )
        response = await async_client.get(
            "/api/v1/channel-materials", params={"status": "active"}, headers=auth_headers,
        )
        assert response.status_code == 200
