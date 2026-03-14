import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_diagnose_llm_response():
    """模拟 LLM provider 的返回格式"""
    data = {
        "overall_score": 72,
        "diagnosis": {
            "psychology_layer": {
                "score": 75,
                "issues": [{"turn": 3, "issue": "未识别客户犹豫情绪"}],
            },
            "strategy_layer": {
                "score": 68,
                "issues": [
                    {
                        "turn": 5,
                        "issue": "留联时机过早",
                        "current_strategy": "直接要联系方式",
                        "suggested_strategy": "先提供价值再留联",
                    }
                ],
            },
            "script_layer": {
                "score": 70,
                "issues": [
                    {
                        "turn": 1,
                        "issue": "开场白缺乏吸引力",
                        "original": "你好有什么需要",
                        "suggested": "您好！我是资深顾问...",
                    }
                ],
            },
        },
        "improvement_plan": ["优化开场白", "调整留联节奏", "增加共情表达"],
    }
    return {"content": json.dumps(data, ensure_ascii=False)}


SAMPLE_CONVERSATION = """客服：你好有什么需要
客户：我想了解下双眼皮
客服：我们医院双眼皮做得很好
客户：多少钱啊
客服：方便留个电话吗，我让医生给您详细介绍
客户：先说价格
客服：不同方案价格不同，留个电话方便沟通
客户：算了吧"""


@pytest.mark.asyncio
class TestDiagnosisAnalyze:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_analyze_conversation(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_diagnose_llm_response()
        payload = {"conversation_text": SAMPLE_CONVERSATION}
        response = await async_client.post("/api/diagnosis/analyze", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "result" in data
        assert data["result"]["overall_score"] == 72
        assert "psychology_layer" in data["result"]
        assert "strategy_layer" in data["result"]
        assert "script_layer" in data["result"]
        assert "improvement_plan" in data["result"]

    async def test_analyze_too_short(self, async_client: AsyncClient, auth_headers):
        payload = {"conversation_text": "太短了"}
        response = await async_client.post("/api/diagnosis/analyze", json=payload, headers=auth_headers)
        assert response.status_code == 422

    async def test_analyze_unauthorized(self, async_client: AsyncClient):
        payload = {"conversation_text": SAMPLE_CONVERSATION}
        response = await async_client.post("/api/diagnosis/analyze", json=payload)
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
class TestDiagnosisReports:
    async def test_list_reports_empty(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get("/api/diagnosis/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_list_reports_after_analyze(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_diagnose_llm_response()
        await async_client.post(
            "/api/diagnosis/analyze",
            json={"conversation_text": SAMPLE_CONVERSATION},
            headers=auth_headers,
        )

        response = await async_client.get("/api/diagnosis/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_get_report_by_id(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = _mock_diagnose_llm_response()
        resp = await async_client.post(
            "/api/diagnosis/analyze",
            json={"conversation_text": SAMPLE_CONVERSATION},
            headers=auth_headers,
        )
        report_id = resp.json()["report_id"]

        response = await async_client.get(f"/api/diagnosis/reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report_id
        assert data["overall_score"] == 72

    async def test_get_report_not_found(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/diagnosis/reports/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_reports_with_pagination(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/diagnosis/reports",
            params={"page": 1, "page_size": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
