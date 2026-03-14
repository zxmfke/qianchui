"""Flywheel API tests with full data coverage."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.flywheel import _pain_point_to_trend
from app.models.flywheel import StrategyCascade
from app.models.memory import PainPoint, Product, ServiceItem, product_pain_points
from app.models.script import Script, script_pain_points


# --- Fixtures for test data ---


@pytest_asyncio.fixture
async def pain_points(test_db: AsyncSession, test_enterprise):
    """Create pain points with flywheel fields."""
    pp1 = PainPoint(
        enterprise_id=test_enterprise.id,
        name="面部松弛",
        description="客户关注面部松弛问题",
        mention_count_current=100,
        mention_count_previous=80,
        change_rate=0.25,
        trend_label="rising",
        evidence_keywords=["脸松了", "法令纹"],
    )
    pp2 = PainPoint(
        enterprise_id=test_enterprise.id,
        name="产后修复",
        description="产后修复需求",
        mention_count_current=50,
        mention_count_previous=50,
        change_rate=0.0,
        trend_label="stable",
        evidence_keywords=[],
    )
    pp3 = PainPoint(
        enterprise_id=test_enterprise.id,
        name="新痛点待确认",
        description="疑似新痛点",
        mention_count_current=30,
        mention_count_previous=0,
        change_rate=1.0,
        trend_label="new",
        evidence_keywords=["新词"],
    )
    test_db.add_all([pp1, pp2, pp3])
    await test_db.flush()
    return [pp1, pp2, pp3]


@pytest_asyncio.fixture
async def products(test_db: AsyncSession, test_enterprise, pain_points):
    """Create products with flywheel fields."""
    p1 = Product(
        enterprise_id=test_enterprise.id,
        name="紧致精华",
        description="面部紧致产品",
        dynamic_priority="P1",
        recommendation_hit_rate=0.85,
        priority_reason="痛点上升，优先推广",
    )
    p2 = Product(
        enterprise_id=test_enterprise.id,
        name="基础护理",
        description="基础护理产品",
        dynamic_priority="P2",
        recommendation_hit_rate=0.6,
        priority_reason="稳定需求",
    )
    test_db.add_all([p1, p2])
    await test_db.flush()
    # Link products to pain points
    await test_db.execute(
        product_pain_points.insert().values(
            product_id=p1.id, pain_point_id=pain_points[0].id
        )
    )
    await test_db.execute(
        product_pain_points.insert().values(
            product_id=p2.id, pain_point_id=pain_points[1].id
        )
    )
    await test_db.flush()
    return [p1, p2]


@pytest_asyncio.fixture
async def services(test_db: AsyncSession, test_enterprise):
    """Create services with and without scenario gaps."""
    s1 = ServiceItem(
        enterprise_id=test_enterprise.id,
        name="面诊服务",
        description="面对面咨询",
        usage_count=200,
        effectiveness=0.9,
        has_scenario_gap=False,
        gap_description=None,
    )
    s2 = ServiceItem(
        enterprise_id=test_enterprise.id,
        name="在线咨询",
        description="在线咨询",
        usage_count=150,
        effectiveness=0.5,
        has_scenario_gap=True,
        gap_description="缺少夜间场景覆盖",
    )
    test_db.add_all([s1, s2])
    await test_db.flush()
    return [s1, s2]


@pytest_asyncio.fixture
async def scripts(test_db: AsyncSession, test_enterprise, test_user, pain_points):
    """Create scripts in different lifecycle stages."""
    s1 = Script(
        enterprise_id=test_enterprise.id,
        title="面部松弛话术",
        category="抗衰",
        content="针对面部松弛的营销话术",
        lifecycle_stage="active",
        effectiveness_score=0.8,
        effectiveness_trend="rising",
        usage_contact_rate=0.75,
        source_type="manual",
        status="published",
        created_by=test_user.id,
    )
    s2 = Script(
        enterprise_id=test_enterprise.id,
        title="产后修复话术",
        category="产后",
        content="产后修复营销话术",
        lifecycle_stage="declining",
        effectiveness_score=0.3,
        effectiveness_trend="falling",
        usage_contact_rate=0.2,
        source_type="manual",
        status="published",
        created_by=test_user.id,
    )
    s3 = Script(
        enterprise_id=test_enterprise.id,
        title="草稿话术",
        category="其他",
        content="草稿内容",
        lifecycle_stage="draft",
        effectiveness_score=0.0,
        effectiveness_trend="stable",
        usage_contact_rate=0.0,
        source_type="manual",
        status="draft",
        created_by=test_user.id,
    )
    s4 = Script(
        enterprise_id=test_enterprise.id,
        title="本周新增话术",
        category="新品",
        content="新话术",
        lifecycle_stage="active",
        effectiveness_score=0.5,
        effectiveness_trend="stable",
        usage_contact_rate=0.5,
        source_type="manual",
        status="published",
        created_by=test_user.id,
    )
    test_db.add_all([s1, s2, s3, s4])
    await test_db.flush()
    # Set created_at for s4 to be within last week (for scripts_added_this_week)
    # SQLAlchemy may not allow direct update of server_default columns easily;
    # we'll rely on the test to verify lifecycle stages
    await test_db.execute(
        script_pain_points.insert().values(
            script_id=s1.id, pain_point_id=pain_points[0].id
        )
    )
    await test_db.execute(
        script_pain_points.insert().values(
            script_id=s2.id, pain_point_id=pain_points[1].id
        )
    )
    await test_db.flush()
    return [s1, s2, s3, s4]


@pytest_asyncio.fixture
async def cascades(test_db: AsyncSession, test_enterprise):
    """Create strategy cascades in different statuses."""
    c1 = StrategyCascade(
        enterprise_id=test_enterprise.id,
        flywheel_event_id=None,
        trigger_signal={"signal": "pain_point_rising", "pain_point": "面部松弛"},
        status="pending",
    )
    c2 = StrategyCascade(
        enterprise_id=test_enterprise.id,
        flywheel_event_id=None,
        trigger_signal={"signal": "new_pain_point", "keyword": "产后修复"},
        status="pending",
    )
    c3 = StrategyCascade(
        enterprise_id=test_enterprise.id,
        flywheel_event_id=None,
        trigger_signal={"signal": "test"},
        status="adopted",
    )
    test_db.add_all([c1, c2, c3])
    await test_db.flush()
    return [c1, c2, c3]


# --- Test _pain_point_to_trend ---


@pytest.mark.asyncio
class TestPainPointToTrend:
    """Test _pain_point_to_trend helper with actual pain point data."""

    async def test_pain_point_to_trend_with_data(self, pain_points):
        """Verify _pain_point_to_trend output structure and values."""
        pp = pain_points[0]
        result = _pain_point_to_trend(pp, related_product_count=2, related_script_count=1)
        assert result["id"] == str(pp.id)
        assert result["name"] == "面部松弛"
        assert result["mention_count_current"] == 100
        assert result["mention_count_previous"] == 80
        assert result["change_rate"] == 0.25
        assert result["trend_label"] == "rising"
        assert result["evidence_keywords"] == ["脸松了", "法令纹"]
        assert result["related_product_count"] == 2
        assert result["related_script_count"] == 1

    async def test_pain_point_to_trend_with_nulls(self, test_db, test_enterprise):
        """Verify defaults when pain point has null flywheel fields."""
        pp = PainPoint(
            enterprise_id=test_enterprise.id,
            name="空痛点",
            description="无飞轮数据",
        )
        test_db.add(pp)
        await test_db.flush()
        result = _pain_point_to_trend(pp, 0, 0)
        assert result["mention_count_current"] == 0
        assert result["mention_count_previous"] == 0
        assert result["change_rate"] == 0.0
        assert result["trend_label"] == "stable"
        assert result["evidence_keywords"] == []


# --- Test Dashboard ---


@pytest.mark.asyncio
class TestFlywheelDashboard:
    async def test_get_dashboard(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/dashboard", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pain_point_trends" in data
        assert "product_strategies" in data
        assert "service_strategies" in data
        assert "script_lifecycles" in data
        assert "pending_cascades" in data

    async def test_get_dashboard_unauthorized(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/flywheel/dashboard")
        assert response.status_code in (401, 403)

    async def test_get_dashboard_with_populated_data(
        self,
        async_client: AsyncClient,
        auth_headers,
        pain_points,
        products,
        services,
        scripts,
        cascades,
    ):
        """Dashboard returns populated data when entities exist."""
        response = await async_client.get(
            "/api/v1/flywheel/dashboard", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pain_point_trends"]) == 3
        assert len(data["product_strategies"]) == 2
        assert len(data["service_strategies"]) == 2
        assert len(data["script_lifecycles"]) == 4
        assert len(data["pending_cascades"]) == 2  # only pending
        assert data["new_pain_points_pending"] >= 1  # pp3 has trend_label="new"
        assert data["scenario_gaps"] == 1  # s2 has has_scenario_gap=True
        assert data["scripts_declining"] == 1  # s2 has lifecycle_stage="declining"


# --- Test Pain Points Trends ---


@pytest.mark.asyncio
class TestFlywheelPainPoints:
    async def test_get_pain_point_trends(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/pain-points/trends", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "trends" in data

    async def test_get_pain_point_trends_custom_days(
        self, async_client: AsyncClient, auth_headers
    ):
        response = await async_client.get(
            "/api/v1/flywheel/pain-points/trends",
            params={"days": 60},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["period_days"] == 60

    async def test_get_pain_point_trends_with_data(
        self, async_client: AsyncClient, auth_headers, pain_points, products, scripts
    ):
        """Trends endpoint returns pain points with related counts."""
        response = await async_client.get(
            "/api/v1/flywheel/pain-points/trends", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["trends"]) == 3
        # First pain point has 1 product and 1 script
        first = next(t for t in data["trends"] if t["name"] == "面部松弛")
        assert first["related_product_count"] == 1
        assert first["related_script_count"] == 1
        assert first["trend_label"] == "rising"
        assert first["evidence_keywords"] == ["脸松了", "法令纹"]


# --- Test Products ---


@pytest.mark.asyncio
class TestFlywheelProducts:
    async def test_get_product_priorities(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/products/priorities", headers=auth_headers
        )
        assert response.status_code == 200
        assert "products" in response.json()

    async def test_get_product_priorities_with_data(
        self, async_client: AsyncClient, auth_headers, products
    ):
        """Priorities endpoint returns products with dynamic_priority."""
        response = await async_client.get(
            "/api/v1/flywheel/products/priorities", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 2
        p1 = next(p for p in data["products"] if p["name"] == "紧致精华")
        assert p1["dynamic_priority"] == "P1"
        assert "priority_reason" in p1

    async def test_get_coverage_matrix(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/products/coverage-matrix", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "matrix" in data
        assert "gaps" in data

    async def test_get_coverage_matrix_with_coverage(
        self, async_client: AsyncClient, auth_headers, pain_points, products
    ):
        """Coverage matrix shows covered and uncovered pain points."""
        response = await async_client.get(
            "/api/v1/flywheel/products/coverage-matrix", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["matrix"]) == 3
        # pp3 (新痛点待确认) has no product link -> gap
        assert "新痛点待确认" in data["gaps"]
        # pp1 and pp2 have product links -> not in gaps
        row_pp1 = next(r for r in data["matrix"] if r["pain_point"] == "面部松弛")
        assert row_pp1["coverage"]["紧致精华"] is True
        row_pp3 = next(r for r in data["matrix"] if r["pain_point"] == "新痛点待确认")
        assert all(v is False for v in row_pp3["coverage"].values())


# --- Test Services ---


@pytest.mark.asyncio
class TestFlywheelServices:
    async def test_get_service_effectiveness(
        self, async_client: AsyncClient, auth_headers
    ):
        response = await async_client.get(
            "/api/v1/flywheel/services/effectiveness", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "scenario_gaps" in data

    async def test_get_service_effectiveness_with_gaps(
        self, async_client: AsyncClient, auth_headers, services
    ):
        """Effectiveness endpoint returns services and scenario gaps."""
        response = await async_client.get(
            "/api/v1/flywheel/services/effectiveness", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) == 2
        assert len(data["scenario_gaps"]) == 1
        gap = data["scenario_gaps"][0]
        assert gap["name"] == "在线咨询"
        assert "缺少夜间场景覆盖" in (gap["gap_description"] or "")


# --- Test Scripts ---


@pytest.mark.asyncio
class TestFlywheelScripts:
    async def test_get_script_lifecycle(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/scripts/lifecycle", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "active" in data or "draft" in data

    async def test_get_script_lifecycle_with_stages(
        self, async_client: AsyncClient, auth_headers, scripts
    ):
        """Lifecycle endpoint returns counts per stage."""
        response = await async_client.get(
            "/api/v1/flywheel/scripts/lifecycle", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == 2  # s1, s4
        assert data["declining"] == 1  # s2
        assert data["draft"] == 1  # s3


# --- Test Cascades ---


@pytest.mark.asyncio
class TestFlywheelCascades:
    async def test_list_cascades(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/cascades", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_cascades_filter_status(
        self, async_client: AsyncClient, auth_headers, cascades
    ):
        """Filter cascades by status."""
        response = await async_client.get(
            "/api/v1/flywheel/cascades",
            params={"status": "pending"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(c["status"] == "pending" for c in data["items"])

        response2 = await async_client.get(
            "/api/v1/flywheel/cascades",
            params={"status": "adopted"},
            headers=auth_headers,
        )
        assert response2.status_code == 200
        assert response2.json()["total"] == 1
        assert response2.json()["items"][0]["status"] == "adopted"

    async def test_review_cascade_adopt(
        self, async_client: AsyncClient, auth_headers, cascades
    ):
        """Review cascade with status=adopted."""
        c = cascades[0]
        response = await async_client.post(
            f"/api/v1/flywheel/cascades/{c.id}/review",
            params={"status": "adopted"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cascade_id"] == str(c.id)
        assert data["status"] == "adopted"

    async def test_review_cascade_reject(
        self, async_client: AsyncClient, auth_headers, cascades
    ):
        """Review cascade with status=rejected."""
        c = cascades[1]
        response = await async_client.post(
            f"/api/v1/flywheel/cascades/{c.id}/review",
            params={"status": "rejected"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    async def test_review_cascade_invalid_status(
        self, async_client: AsyncClient, auth_headers, cascades
    ):
        """Review with invalid status returns 400."""
        c = cascades[0]
        response = await async_client.post(
            f"/api/v1/flywheel/cascades/{c.id}/review",
            params={"status": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_review_cascade_not_found(
        self, async_client: AsyncClient, auth_headers
    ):
        """Review non-existent cascade returns 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/flywheel/cascades/{fake_id}/review",
            params={"status": "adopted"},
            headers=auth_headers,
        )
        assert response.status_code == 404


# --- Test Sense ---


@pytest.mark.asyncio
class TestFlywheelSense:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_trigger_sense_mocked_llm(
        self, mock_chat, async_client: AsyncClient, auth_headers, pain_points
    ):
        """Sense endpoint works with mocked LLM."""
        mock_chat.return_value = {
            "content": json.dumps({
                "pain_point_updates": [],
                "unrecognized_keywords": [],
                "should_trigger_cascade": False,
                "summary": "测试扫描完成",
                "trends": [],
                "new_suspects": [],
                "suggested_actions": ["检查xxx"],
            }),
            "role": "assistant",
            "finish_reason": "stop",
        }
        response = await async_client.post(
            "/api/v1/flywheel/sense",
            params={"time_window_days": 30},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["time_window_days"] == 30
        assert "测试扫描完成" in data["message"]
        assert "cards" in data
        assert "suggested_actions" in data


# --- Test Events ---


@pytest.mark.asyncio
class TestFlywheelEvents:
    async def test_list_events(self, async_client: AsyncClient, auth_headers):
        response = await async_client.get(
            "/api/v1/flywheel/events", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["items"] == []
        assert data["total"] == 0
