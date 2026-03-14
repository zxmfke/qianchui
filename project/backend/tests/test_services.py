"""Unit tests for services, agent context, runtime, and schemas."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ConversationContext
from app.agent.runtime import AgentRuntime
from app.models.conversation import Conversation, Message
from app.models.enterprise import Enterprise
from app.models.memory import PainPoint, Product, ServiceItem
from app.models.script import Script, ScriptUsage
from app.models.simulation import SimulationSession
from app.models.training import TrainingRecord
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.flywheel import (
    CascadeReviewRequest,
    FlywheelDashboardResponse,
    PainPointTrendView,
    ProductStrategyView,
    ScriptLifecycleView,
    ServiceStrategyView,
    StrategyCascadeCreate,
    StrategyCascadeResponse,
)
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService
from app.services.script_service import ScriptService


# --- ScriptService ---


@pytest.mark.asyncio
class TestScriptService:
    @pytest_asyncio.fixture
    async def pain_point(self, test_db: AsyncSession, test_enterprise):
        pp = PainPoint(
            enterprise_id=test_enterprise.id,
            name="价格敏感",
            description="客户对价格敏感",
        )
        test_db.add(pp)
        await test_db.flush()
        return pp

    @pytest_asyncio.fixture
    async def product(self, test_db: AsyncSession, test_enterprise):
        p = Product(
            enterprise_id=test_enterprise.id,
            name="热玛吉",
            description="抗衰项目",
        )
        test_db.add(p)
        await test_db.flush()
        return p

    @pytest_asyncio.fixture
    async def service_item(self, test_db: AsyncSession, test_enterprise):
        s = ServiceItem(
            enterprise_id=test_enterprise.id,
            name="咨询顾问",
            description="一对一咨询",
        )
        test_db.add(s)
        await test_db.flush()
        return s

    async def test_list_scripts_empty(self, test_db: AsyncSession, test_enterprise):
        svc = ScriptService(test_db)
        scripts, total = await svc.list_scripts(str(test_enterprise.id))
        assert scripts == []
        assert total == 0

    async def test_list_scripts_with_search(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="价格异议处理",
            content="我理解您的顾虑，价格方面...",
        )
        await test_db.flush()

        scripts, total = await svc.list_scripts(
            str(test_enterprise.id), search="价格"
        )
        assert total >= 1
        assert any("价格" in s.title or "价格" in s.content for s in scripts)

    async def test_list_scripts_with_category(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="异议处理",
            content="内容",
            category="异议处理",
        )
        await test_db.flush()

        scripts, total = await svc.list_scripts(
            str(test_enterprise.id), category="异议处理"
        )
        assert total >= 1
        assert all(s.category == "异议处理" for s in scripts)

    async def test_list_scripts_with_status(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="草稿话术",
            content="内容",
        )
        await test_db.flush()

        scripts, total = await svc.list_scripts(
            str(test_enterprise.id), status="draft"
        )
        assert total >= 1
        assert all(s.status == "draft" for s in scripts)

    async def test_list_scripts_with_difficulty(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="高难度话术",
            content="内容",
            difficulty=3,
        )
        await test_db.flush()

        scripts, total = await svc.list_scripts(
            str(test_enterprise.id), difficulty=3
        )
        assert total >= 1
        assert all(s.difficulty == 3 for s in scripts)

    async def test_create_script_with_links(
        self,
        test_db: AsyncSession,
        test_enterprise,
        test_user,
        pain_point,
        product,
        service_item,
    ):
        svc = ScriptService(test_db)
        script = await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="综合话术",
            content="内容",
            pain_point_ids=[pain_point.id],
            product_ids=[product.id],
            service_ids=[service_item.id],
        )
        await test_db.refresh(script)
        assert script.id is not None
        assert script.title == "综合话术"
        assert len(script.pain_points) == 1
        assert len(script.products) == 1
        assert len(script.services) == 1

    async def test_get_script_found(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        created = await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="测试话术",
            content="内容",
        )
        await test_db.flush()

        found = await svc.get_script(str(created.id), str(test_enterprise.id))
        assert found is not None
        assert found.id == created.id
        assert found.title == "测试话术"

    async def test_get_script_not_found(
        self, test_db: AsyncSession, test_enterprise
    ):
        svc = ScriptService(test_db)
        found = await svc.get_script(str(uuid4()), str(test_enterprise.id))
        assert found is None

    async def test_update_script_with_links(
        self,
        test_db: AsyncSession,
        test_enterprise,
        test_user,
        pain_point,
        product,
    ):
        svc = ScriptService(test_db)
        script = await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="原标题",
            content="原内容",
            pain_point_ids=[pain_point.id],
        )
        await test_db.flush()
        original_version = script.version

        updated = await svc.update_script(
            str(script.id),
            str(test_enterprise.id),
            title="新标题",
            pain_point_ids=[pain_point.id],
            product_ids=[product.id],
        )
        assert updated is not None
        assert updated.title == "新标题"
        assert updated.version == original_version + 1
        assert len(updated.products) == 1

    async def test_delete_script_found(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        script = await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="待删除",
            content="内容",
        )
        await test_db.flush()

        ok = await svc.delete_script(str(script.id), str(test_enterprise.id))
        assert ok is True
        found = await svc.get_script(str(script.id), str(test_enterprise.id))
        assert found is None

    async def test_delete_script_not_found(
        self, test_db: AsyncSession, test_enterprise
    ):
        svc = ScriptService(test_db)
        ok = await svc.delete_script(str(uuid4()), str(test_enterprise.id))
        assert ok is False

    async def test_record_usage_increments_count(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        script = await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="使用话术",
            content="内容",
        )
        await test_db.flush()
        initial_count = script.usage_count

        usage = await svc.record_usage(
            str(script.id),
            str(test_user.id),
            str(test_enterprise.id),
            context={"source": "test"},
        )
        await test_db.refresh(script)
        assert usage.id is not None
        assert script.usage_count == initial_count + 1

    async def test_get_categories(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = ScriptService(test_db)
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="话术1",
            content="内容",
            category="异议处理",
        )
        await svc.create_script(
            enterprise_id=str(test_enterprise.id),
            user_id=str(test_user.id),
            title="话术2",
            content="内容",
            category="异议处理",
        )
        await test_db.flush()

        categories = await svc.get_categories(str(test_enterprise.id))
        assert len(categories) >= 1
        assert any(c["name"] == "异议处理" for c in categories)


# --- DashboardService ---


@pytest.mark.asyncio
class TestDashboardService:
    async def test_get_overview_empty(self, test_db: AsyncSession, test_enterprise):
        svc = DashboardService(test_db)
        overview = await svc.get_overview(str(test_enterprise.id))
        assert "total_scripts" in overview
        assert "total_usage_count" in overview
        assert "training_completion_rate" in overview
        assert overview["total_scripts"] == 0
        assert overview["total_usage_count"] == 0

    async def test_get_overview_with_data(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        script = Script(
            enterprise_id=test_enterprise.id,
            title="测试话术",
            content="内容",
            status="published",
            created_by=test_user.id,
        )
        test_db.add(script)
        await test_db.flush()

        usage = ScriptUsage(
            script_id=script.id,
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
        )
        test_db.add(usage)

        training = TrainingRecord(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            question={"q": "test"},
            user_answer="A",
            correct_answer="A",
            is_correct=True,
        )
        test_db.add(training)
        await test_db.flush()

        svc = DashboardService(test_db)
        overview = await svc.get_overview(str(test_enterprise.id))
        assert overview["total_scripts"] >= 1
        assert overview["total_usage_count"] >= 1
        assert overview["training_completion_rate"] >= 0

    async def test_get_script_ranking(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        script = Script(
            enterprise_id=test_enterprise.id,
            title="热门话术",
            content="内容",
            status="published",
            usage_count=10,
            conversion_rate=0.5,
            created_by=test_user.id,
        )
        test_db.add(script)
        await test_db.flush()

        svc = DashboardService(test_db)
        ranking = await svc.get_script_ranking(str(test_enterprise.id), limit=5)
        assert "by_usage" in ranking
        assert "by_conversion" in ranking
        assert len(ranking["by_usage"]) >= 1
        assert ranking["by_usage"][0]["title"] == "热门话术"

    async def test_get_team_stats(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        svc = DashboardService(test_db)
        stats = await svc.get_team_stats(str(test_enterprise.id))
        assert "members" in stats
        assert "total_members" in stats
        assert stats["total_members"] >= 1

    async def test_get_trends(
        self, test_db: AsyncSession, test_enterprise
    ):
        svc = DashboardService(test_db)
        trends = await svc.get_trends(str(test_enterprise.id), days=7)
        assert "usage_trend" in trends
        assert "new_scripts_trend" in trends
        assert "training_trend" in trends
        assert trends["period"] == "7d"


# --- AuthService ---


@pytest.mark.asyncio
class TestAuthService:
    async def test_register_success(
        self, test_db: AsyncSession
    ):
        svc = AuthService(test_db)
        user, enterprise = await svc.register(
            email="new@example.com",
            username="newuser",
            password="pass123",
            enterprise_name="新企业",
            industry="医疗",
        )
        assert user.id is not None
        assert user.email == "new@example.com"
        assert enterprise.name == "新企业"

    async def test_register_duplicate_email(
        self, test_db: AsyncSession, test_user
    ):
        svc = AuthService(test_db)
        with pytest.raises(Exception, match="该邮箱已被注册"):
            await svc.register(
                email=test_user.email,
                username="other",
                password="pass",
                enterprise_name="企业",
            )

    async def test_login_success(
        self, test_db: AsyncSession, test_user
    ):
        svc = AuthService(test_db)
        user, access, refresh = await svc.login(
            test_user.email,
            "testpass123",
        )
        assert user.id == test_user.id
        assert access is not None
        assert refresh is not None

    async def test_login_wrong_password(
        self, test_db: AsyncSession, test_user
    ):
        svc = AuthService(test_db)
        with pytest.raises(Exception, match="用户名或密码错误"):
            await svc.login(test_user.email, "wrongpass")

    async def test_login_inactive_user(
        self, test_db: AsyncSession, test_enterprise
    ):
        inactive = User(
            id=uuid4(),
            username="inactive",
            email="inactive@example.com",
            hashed_password=AuthService.hash_password("pass"),
            enterprise_id=test_enterprise.id,
            role="staff",
            is_active=False,
        )
        test_db.add(inactive)
        await test_db.flush()

        svc = AuthService(test_db)
        with pytest.raises(Exception, match="账号已被禁用"):
            await svc.login("inactive@example.com", "pass")

    def test_decode_token_valid(self):
        user_id = str(uuid4())
        token = AuthService.create_access_token({
            "sub": user_id,
            "enterprise_id": str(uuid4()),
            "role": "admin",
        })
        payload = AuthService.decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id

    def test_decode_token_invalid(self):
        payload = AuthService.decode_token("invalid.token.here")
        assert payload is None

    async def test_refresh_tokens_valid(
        self, test_db: AsyncSession, test_user
    ):
        svc = AuthService(test_db)
        _, _, refresh = await svc.login(test_user.email, "testpass123")
        new_access, new_refresh = await svc.refresh_tokens(refresh)
        assert new_access is not None
        assert new_refresh is not None

    async def test_refresh_tokens_invalid(self, test_db: AsyncSession):
        svc = AuthService(test_db)
        with pytest.raises(Exception, match="无效的刷新令牌"):
            await svc.refresh_tokens("invalid.refresh.token")

    async def test_get_user_by_id(
        self, test_db: AsyncSession, test_user
    ):
        svc = AuthService(test_db)
        user = await svc.get_user_by_id(str(test_user.id))
        assert user is not None
        assert user.id == test_user.id


# --- ConversationContext ---


@pytest.mark.asyncio
class TestConversationContext:
    async def test_get_or_create_conversation_create_new(
        self, test_db: AsyncSession, test_user, test_enterprise
    ):
        ctx = ConversationContext(test_db)
        conv = await ctx.get_or_create_conversation(
            conversation_id=None,
            user_id=str(test_user.id),
            enterprise_id=str(test_enterprise.id),
        )
        assert conv.id is not None
        assert conv.title == "新对话"

    async def test_get_or_create_conversation_get_existing(
        self, test_db: AsyncSession, test_user, test_enterprise
    ):
        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="已有对话",
        )
        test_db.add(conv)
        await test_db.flush()

        ctx = ConversationContext(test_db)
        found = await ctx.get_or_create_conversation(
            conversation_id=str(conv.id),
            user_id=str(test_user.id),
            enterprise_id=str(test_enterprise.id),
        )
        assert found.id == conv.id
        assert found.title == "已有对话"

    async def test_get_conversation_history(
        self, test_db: AsyncSession, test_user, test_enterprise
    ):
        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="对话",
        )
        test_db.add(conv)
        await test_db.flush()

        msg = Message(
            conversation_id=conv.id,
            role="user",
            content="你好",
        )
        test_db.add(msg)
        await test_db.flush()

        ctx = ConversationContext(test_db)
        history = await ctx.get_conversation_history(conv.id, limit=10)
        assert len(history) >= 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "你好"

    async def test_load_enterprise_memory(
        self, test_db: AsyncSession, test_enterprise
    ):
        pp = PainPoint(
            enterprise_id=test_enterprise.id,
            name="痛点1",
            description="描述",
        )
        test_db.add(pp)
        await test_db.flush()

        ctx = ConversationContext(test_db)
        memory = await ctx.load_enterprise_memory(str(test_enterprise.id))
        assert "pain_points" in memory
        assert "products" in memory
        assert "services" in memory
        assert len(memory["pain_points"]) >= 1

    async def test_load_relevant_scripts(
        self, test_db: AsyncSession, test_enterprise, test_user
    ):
        script = Script(
            enterprise_id=test_enterprise.id,
            title="推荐话术",
            content="内容",
            status="published",
            created_by=test_user.id,
        )
        test_db.add(script)
        await test_db.flush()

        ctx = ConversationContext(test_db)
        scripts = await ctx.load_relevant_scripts(
            str(test_enterprise.id), "推荐", limit=5
        )
        assert isinstance(scripts, list)
        assert len(scripts) >= 1
        assert scripts[0]["title"] == "推荐话术"

    def test_build_system_prompt(self, test_db: AsyncSession):
        ctx = ConversationContext(test_db)
        memory = {
            "pain_points": [{"name": "痛点", "description": "描述"}],
            "products": [{"name": "产品", "description": "产品描述"}],
            "services": [{"name": "服务", "description": "服务描述"}],
        }
        prompt = ctx.build_system_prompt("测试企业", memory)
        assert "测试企业" in prompt
        assert "痛点" in prompt
        assert "产品" in prompt
        assert "服务" in prompt

    async def test_save_message(
        self, test_db: AsyncSession, test_user, test_enterprise
    ):
        conv = Conversation(
            user_id=test_user.id,
            enterprise_id=test_enterprise.id,
            title="对话",
        )
        test_db.add(conv)
        await test_db.flush()

        ctx = ConversationContext(test_db)
        msg = await ctx.save_message(
            conv.id,
            "assistant",
            "AI回复",
            skill_used="general_chat",
            cards=[{"type": "card"}],
        )
        assert msg.id is not None
        assert msg.content == "AI回复"
        assert msg.skill_used == "general_chat"


# --- AgentRuntime ---


@pytest.mark.asyncio
class TestAgentRuntime:
    @patch("app.skills.dispatcher.SkillDispatcher.dispatch", new_callable=AsyncMock)
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_process_message_with_mocked_dispatcher_and_skill(
        self,
        mock_llm,
        mock_dispatch,
        test_db: AsyncSession,
        test_user,
        test_enterprise,
    ):
        mock_skill = MagicMock()
        mock_skill.name = "script_recommend"
        mock_skill.execute = AsyncMock(
            return_value={
                "text": "为您推荐了以下话术",
                "cards": [{"title": "推荐"}],
                "suggested_actions": [],
            }
        )
        mock_dispatch.return_value = (mock_skill, {"params": {}})

        runtime = AgentRuntime(test_db)
        result = await runtime.process_message(
            user_input="推荐话术",
            conversation_id=None,
            user_id=str(test_user.id),
            enterprise_id=str(test_enterprise.id),
        )
        assert "conversation_id" in result
        assert "text" in result
        assert result["text"] == "为您推荐了以下话术"
        assert result["skill_used"] == "script_recommend"

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_general_chat_with_mocked_llm(
        self,
        mock_llm,
        test_db: AsyncSession,
        test_user,
        test_enterprise,
    ):
        mock_llm.return_value = {"content": "AI回复内容"}

        runtime = AgentRuntime(test_db)
        result = await runtime._general_chat(
            user_input="你好",
            history=[],
            memory={"pain_points": [], "products": [], "services": []},
        )
        assert result["text"] == "AI回复内容"
        assert "suggested_actions" in result


# --- Schemas ---


class TestPaginationParams:
    def test_offset_property(self):
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0

        params = PaginationParams(page=2, page_size=10)
        assert params.offset == 10

        params = PaginationParams(page=3, page_size=5)
        assert params.offset == 10


class TestPaginatedResponse:
    def test_create_class_method(self):
        items = [{"id": 1}, {"id": 2}]
        resp = PaginatedResponse.create(items=items, total=100, page=1, page_size=20)
        assert resp.items == items
        assert resp.total == 100
        assert resp.page == 1
        assert resp.page_size == 20
        assert resp.total_pages == 5


class TestFlywheelSchemas:
    def test_pain_point_trend_view(self):
        view = PainPointTrendView(
            id=uuid4(),
            name="痛点",
            mention_count_current=10,
            trend_label="up",
        )
        assert view.name == "痛点"
        assert view.mention_count_current == 10

    def test_product_strategy_view(self):
        view = ProductStrategyView(
            id=uuid4(),
            name="产品",
            dynamic_priority="P1",
        )
        assert view.name == "产品"
        assert view.dynamic_priority == "P1"

    def test_service_strategy_view(self):
        view = ServiceStrategyView(
            id=uuid4(),
            name="服务",
            usage_count=5,
        )
        assert view.name == "服务"
        assert view.usage_count == 5

    def test_script_lifecycle_view(self):
        view = ScriptLifecycleView(
            id=uuid4(),
            title="话术",
            lifecycle_stage="active",
        )
        assert view.title == "话术"
        assert view.lifecycle_stage == "active"

    def test_strategy_cascade_create(self):
        create = StrategyCascadeCreate(trigger_signal={"type": "test"})
        assert create.trigger_signal == {"type": "test"}

    def test_strategy_cascade_response(self):
        resp = StrategyCascadeResponse(
            id=uuid4(),
            enterprise_id=uuid4(),
            trigger_signal={},
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.status == "pending"

    def test_cascade_review_request(self):
        req = CascadeReviewRequest(status="adopted")
        assert req.status == "adopted"

    def test_flywheel_dashboard_response(self):
        resp = FlywheelDashboardResponse(
            pain_point_trends=[],
            product_strategies=[],
            service_strategies=[],
            script_lifecycles=[],
        )
        assert resp.pending_cascades == []
        assert resp.new_pain_points_pending == 0
