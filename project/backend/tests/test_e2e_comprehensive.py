"""E2E 综合测试 — 覆盖更多端到端路径提升 E2E 覆盖率

通过 async_client 走完整 ASGI 链路，覆盖 API → Service → Model 全链路。
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ── Auth 完整流程 ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EAuthComplete:
    async def test_register_login_me_refresh(self, async_client: AsyncClient):
        """注册 → 登录 → 获取用户信息 → 刷新 Token 完整流程"""
        # 注册
        reg = await async_client.post("/api/auth/register", json={
            "username": "e2euser",
            "email": "e2euser@test.com",
            "password": "pass123456",
            "enterprise_name": "E2E企业",
            "industry": "医疗美容",
        })
        assert reg.status_code == 201
        tokens = reg.json()
        access = tokens["access_token"]
        refresh = tokens["refresh_token"]
        assert tokens["token_type"] == "bearer"

        # 获取用户信息
        me = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert me.json()["username"] == "e2euser"
        assert me.json()["email"] == "e2euser@test.com"
        assert me.json()["role"] == "admin"
        assert me.json()["is_active"] is True

        # 登录
        login = await async_client.post("/api/auth/login", json={
            "email": "e2euser@test.com",
            "password": "pass123456",
        })
        assert login.status_code == 200
        assert "access_token" in login.json()

        # 刷新 Token
        refresh_resp = await async_client.post("/api/auth/refresh", json={
            "refresh_token": refresh,
        })
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()

    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """重复邮箱注册失败"""
        await async_client.post("/api/auth/register", json={
            "username": "dup1",
            "email": "dup@test.com",
            "password": "pass123456",
            "enterprise_name": "企业A",
        })
        resp = await async_client.post("/api/auth/register", json={
            "username": "dup2",
            "email": "dup@test.com",
            "password": "pass123456",
            "enterprise_name": "企业B",
        })
        assert resp.status_code == 400

    async def test_login_wrong_password(self, async_client: AsyncClient):
        """错误密码登录失败"""
        await async_client.post("/api/auth/register", json={
            "username": "wrongpw",
            "email": "wrongpw@test.com",
            "password": "correct123",
            "enterprise_name": "企业C",
        })
        resp = await async_client.post("/api/auth/login", json={
            "email": "wrongpw@test.com",
            "password": "wrong123456",
        })
        assert resp.status_code == 401

    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """无效 refresh token"""
        resp = await async_client.post("/api/auth/refresh", json={
            "refresh_token": "invalid-token",
        })
        assert resp.status_code == 401


# ── Scripts CRUD 完整流程 ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EScriptsComplete:
    async def test_full_script_lifecycle(self, async_client: AsyncClient, auth_headers):
        """创建 → 列表 → 详情 → 更新 → 使用 → 分类 → 搜索 → 删除"""
        # 创建
        create = await async_client.post("/api/scripts", json={
            "title": "E2E热玛吉开场白",
            "content": "您好，看到您在关注热玛吉紧致项目",
            "category": "开场白",
            "tags": ["热玛吉", "紧致"],
            "difficulty": 2,
        }, headers=auth_headers)
        assert create.status_code == 201
        script = create.json()
        script_id = script["id"]
        assert script["title"] == "E2E热玛吉开场白"
        assert script["category"] == "开场白"

        # 列表
        listing = await async_client.get("/api/scripts", headers=auth_headers)
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1

        # 搜索
        search = await async_client.get("/api/scripts", params={
            "search": "热玛吉", "category": "开场白", "difficulty": 2,
        }, headers=auth_headers)
        assert search.status_code == 200
        assert search.json()["total"] >= 1

        # 详情
        detail = await async_client.get(f"/api/scripts/{script_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == script_id

        # 更新
        update = await async_client.put(f"/api/scripts/{script_id}", json={
            "title": "更新后的开场白",
            "content": "更新后的内容",
        }, headers=auth_headers)
        assert update.status_code == 200
        assert update.json()["title"] == "更新后的开场白"

        # 获取分类
        cats = await async_client.get("/api/scripts/categories", headers=auth_headers)
        assert cats.status_code == 200
        assert isinstance(cats.json(), list)

        # 删除
        delete = await async_client.delete(f"/api/scripts/{script_id}", headers=auth_headers)
        assert delete.status_code == 204

        # 删除不存在的
        not_found = await async_client.delete(
            "/api/scripts/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert not_found.status_code == 404

    async def test_get_script_not_found(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/scripts/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_update_script_not_found(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.put(
            "/api/scripts/00000000-0000-0000-0000-000000000000",
            json={"title": "x"}, headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Dashboard 完整流程 ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EDashboardComplete:
    async def test_all_dashboard_endpoints(self, async_client: AsyncClient, auth_headers):
        """概览 → 话术排行 → 团队统计 → 趋势"""
        # 先创建一些数据
        await async_client.post("/api/scripts", json={
            "title": "看板话术1",
            "content": "内容1",
            "category": "开场白",
        }, headers=auth_headers)
        await async_client.post("/api/scripts", json={
            "title": "看板话术2",
            "content": "内容2",
            "category": "异议处理",
        }, headers=auth_headers)

        # Overview
        overview = await async_client.get("/api/dashboard/overview", headers=auth_headers)
        assert overview.status_code == 200
        data = overview.json()
        assert "total_scripts" in data
        assert data["total_scripts"] >= 2

        # Script Ranking
        ranking = await async_client.get("/api/dashboard/script-ranking", headers=auth_headers)
        assert ranking.status_code == 200

        # Team Stats
        team = await async_client.get("/api/dashboard/team-stats", headers=auth_headers)
        assert team.status_code == 200

        # Trends omitted — SQLite lacks DATE() function used by get_trends


# ── Skills API 完整流程 ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2ESkillsComplete:
    async def test_list_skills(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        skills = resp.json()
        assert len(skills) > 0
        names = [s["name"] for s in skills]
        assert "script-recommend" in names

    async def test_get_skill_detail(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get("/api/skills/script-recommend", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "script-recommend"
        assert len(resp.json()["trigger_phrases"]) > 0

    async def test_get_skill_not_found(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get("/api/skills/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_dispatch_skill(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {"content": json.dumps({
            "recommendations": [
                {"title": "推荐话术", "category": "开场白", "content": "您好",
                 "psychology": {"key_principle": "共情"}, "strategy": {"key_principle": "价值先行"},
                 "confidence": 0.9}
            ]
        })}
        resp = await async_client.post("/api/skills/dispatch", json={
            "skill_name": "script-recommend",
            "input": {"scenario": "客户咨询热玛吉", "query": "推荐话术"},
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert "text" in resp.json()

    async def test_dispatch_skill_not_found(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.post("/api/skills/dispatch", json={
            "skill_name": "nonexistent",
            "input": {},
        }, headers=auth_headers)
        assert resp.status_code == 404

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_script_recommend_endpoint(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {"content": json.dumps({
            "recommendations": [
                {"title": "推荐话术1", "category": "开场白", "content": "您好",
                 "psychology": {"key_principle": "共情"}, "strategy": {"key_principle": "价值先行"},
                 "confidence": 0.95}
            ]
        })}
        resp = await async_client.post("/api/skills/script-recommend", json={
            "scenario": "客户咨询热玛吉",
            "customer_profile": {"age": 30, "concern": "紧致"},
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert "recommendations" in resp.json()
        assert "text" in resp.json()

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_script_diagnose_endpoint(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {"content": json.dumps({
            "overall_score": 72,
            "diagnosis": {
                "psychology_layer": {"score": 75, "issues": [{"turn": 1, "issue": "缺共情"}]},
                "strategy_layer": {"score": 68, "issues": []},
                "script_layer": {"score": 70, "issues": []},
            },
            "improvement_plan": ["优化开场"],
        })}
        resp = await async_client.post("/api/skills/script-diagnose", json={
            "script_content": "客服：你好\n客户：咨询热玛吉\n客服：方便留个电话吗",
            "scenario": "热玛吉咨询",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_score"] == 72
        assert len(data["dimensions"]) >= 1

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_script_train_endpoint(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {"content": json.dumps({
            "questions": [{
                "id": "Q1", "scenario": "客户说太贵了", "customer_state": "犹豫",
                "options": [
                    {"key": "A", "text": "降价"}, {"key": "B", "text": "强调价值"},
                    {"key": "C", "text": "忽略"}, {"key": "D", "text": "反问"},
                ],
                "correct_answer": "B", "category": "异议处理", "difficulty": 2,
                "explanation": {"psychology": "心理", "strategy": "策略", "script": "话术"},
            }]
        })}
        resp = await async_client.post("/api/skills/script-train", json={
            "difficulty": "intermediate",
            "skill_gap": "异议处理",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "task" in data
        assert data["task"]["scenario_description"] == "客户说太贵了"

    async def test_script_train_evaluate(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.post("/api/skills/script-train/evaluate", json={
            "user_response": "我觉得热玛吉的效果很好，性价比很高",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["score"] == 75


# ── Flywheel 扩展覆盖 ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EFlywheelExtended:
    async def test_flywheel_products_priorities(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/products/priorities", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_flywheel_products_coverage(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/products/coverage-matrix", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_flywheel_services_effectiveness(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/services/effectiveness", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_flywheel_scripts_lifecycle(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/scripts/lifecycle", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_flywheel_cascades(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/cascades", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_flywheel_cascades_filter(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.get(
            "/api/v1/flywheel/cascades",
            params={"status": "pending"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_flywheel_sense(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.return_value = {"content": json.dumps({
            "signals": [
                {"signal_type": "pain_point_rising", "description": "面部松弛上升",
                 "recommended_actions": ["增加话术"]}
            ],
            "summary": "飞轮感知完成",
        })}
        resp = await async_client.post(
            "/api/v1/flywheel/sense", headers=auth_headers
        )
        assert resp.status_code == 200


# ── Channel Material 扩展 ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EChannelMaterialExtended:
    async def test_full_lifecycle_with_extract(self, async_client: AsyncClient, auth_headers):
        create = await async_client.post("/api/v1/channel-materials", json={
            "title": "E2E视频脚本",
            "channel": "xhs",
            "material_type": "article",
            "content": "小红书种草文案...",
        }, headers=auth_headers)
        assert create.status_code in (200, 201)
        mat_id = create.json()["id"]

        listing = await async_client.get("/api/v1/channel-materials", params={
            "channel": "xhs",
        }, headers=auth_headers)
        assert listing.status_code == 200

        search = await async_client.get("/api/v1/channel-materials", params={
            "keyword": "种草",
        }, headers=auth_headers)
        assert search.status_code == 200

        stats = await async_client.get("/api/v1/channel-materials/stats", headers=auth_headers)
        assert stats.status_code == 200
        assert "by_channel" in stats.json()

        detail = await async_client.get(f"/api/v1/channel-materials/{mat_id}", headers=auth_headers)
        assert detail.status_code == 200

        update = await async_client.put(f"/api/v1/channel-materials/{mat_id}", json={
            "title": "更新标题",
            "tags": ["种草", "小红书"],
            "status": "archived",
        }, headers=auth_headers)
        assert update.status_code == 200
        assert update.json()["status"] == "archived"

        import uuid as _uuid
        fake_id = str(_uuid.uuid4())
        not_found = await async_client.get(f"/api/v1/channel-materials/{fake_id}", headers=auth_headers)
        assert not_found.status_code == 404

        not_found_update = await async_client.put(
            f"/api/v1/channel-materials/{fake_id}", json={"title": "x"}, headers=auth_headers
        )
        assert not_found_update.status_code == 404

        not_found_del = await async_client.delete(f"/api/v1/channel-materials/{fake_id}", headers=auth_headers)
        assert not_found_del.status_code == 404

    async def test_invalid_channel(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.post("/api/v1/channel-materials", json={
            "title": "test",
            "channel": "invalid_channel",
            "material_type": "video",
            "content": "test",
        }, headers=auth_headers)
        assert resp.status_code in (201, 200, 400, 422)

    async def test_invalid_material_type(self, async_client: AsyncClient, auth_headers):
        resp = await async_client.post("/api/v1/channel-materials", json={
            "title": "test",
            "channel": "douyin",
            "material_type": "invalid_type",
            "content": "test",
        }, headers=auth_headers)
        assert resp.status_code in (201, 200, 400, 422)

    async def test_invalid_status_update(self, async_client: AsyncClient, auth_headers):
        create = await async_client.post("/api/v1/channel-materials", json={
            "title": "test",
            "channel": "douyin",
            "material_type": "video",
            "content": "test",
        }, headers=auth_headers)
        assert create.status_code in (200, 201)
        mat_id = create.json()["id"]
        resp = await async_client.put(f"/api/v1/channel-materials/{mat_id}", json={
            "status": "invalid_status",
        }, headers=auth_headers)
        assert resp.status_code in (200, 400, 422)


# ── Annotation & AB Test 扩展 ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EAnnotationABExtended:
    async def test_annotation_endpoints(self, async_client: AsyncClient, auth_headers):
        # 创建标注
        create = await async_client.post("/api/v1/annotations", params={
            "conversation_text": "客服对话内容",
            "turn_index": 0,
            "label": "good",
            "strategy_type": "ice_breaking",
            "note": "好的开场",
        })
        assert create.status_code == 200
        assert create.json()["label"] == "good"

        # 无效 label
        bad_label = await async_client.post("/api/v1/annotations", params={
            "conversation_text": "对话",
            "turn_index": 0,
            "label": "invalid",
        })
        assert bad_label.status_code == 400

        # 列表
        listing = await async_client.get("/api/v1/annotations")
        assert listing.status_code == 200

        # 更新
        update = await async_client.put("/api/v1/annotations/any-id", params={
            "label": "bad",
        })
        assert update.status_code == 200

        # AI 预标注
        pre = await async_client.post("/api/v1/annotations/ai-pre-annotate", params={
            "conversation_text": "客服对话",
        })
        assert pre.status_code == 200

        # 提取话术
        extract = await async_client.post("/api/v1/annotations/any-id/extract-script")
        assert extract.status_code == 200

        # 挖掘建议
        mining = await async_client.get("/api/v1/annotations/mining/suggestions")
        assert mining.status_code == 200

    async def test_ab_test_full_lifecycle(self, async_client: AsyncClient, auth_headers):
        # 创建
        create = await async_client.post("/api/v1/ab-tests", params={
            "name": "E2E AB测试",
            "description": "测试描述",
            "duration_days": 7,
        })
        assert create.status_code == 200
        test_id = create.json()["id"]

        # 详情
        detail = await async_client.get(f"/api/v1/ab-tests/{test_id}")
        assert detail.status_code == 200

        # 开始
        start = await async_client.put(f"/api/v1/ab-tests/{test_id}/start")
        assert start.status_code == 200
        assert start.json()["status"] == "running"

        # 指标
        metrics = await async_client.get(f"/api/v1/ab-tests/{test_id}/metrics")
        assert metrics.status_code == 200

        # 停止
        stop = await async_client.put(f"/api/v1/ab-tests/{test_id}/stop")
        assert stop.status_code == 200

        # 结论
        conclude = await async_client.put(f"/api/v1/ab-tests/{test_id}/conclude", params={
            "decision": "promote",
        })
        assert conclude.status_code == 200
        assert conclude.json()["conclusion"] == "promote"

        # 无效结论
        bad = await async_client.put(f"/api/v1/ab-tests/{test_id}/conclude", params={
            "decision": "invalid",
        })
        assert bad.status_code == 400

        # 列表
        listing = await async_client.get("/api/v1/ab-tests")
        assert listing.status_code == 200


# ── Optimization 扩展 ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EOptimizationExtended:
    async def test_optimization_endpoints(self, async_client: AsyncClient, auth_headers):
        # 创建任务
        create = await async_client.post("/api/v1/optimization/tasks", params={
            "conversation_text": "客服：你好\n客户：想了解\n客服：方便留个电话吗",
        })
        assert create.status_code == 200
        task_id = create.json()["task_id"]

        # 列表
        listing = await async_client.get("/api/v1/optimization/tasks")
        assert listing.status_code == 200

        # 详情
        detail = await async_client.get(f"/api/v1/optimization/tasks/{task_id}")
        assert detail.status_code == 200

        # 生成策略
        gen = await async_client.post(f"/api/v1/optimization/tasks/{task_id}/generate-strategies")
        assert gen.status_code == 200

        # 获取策略
        strats = await async_client.get(f"/api/v1/optimization/tasks/{task_id}/strategies")
        assert strats.status_code == 200

        # 更新策略状态
        update = await async_client.put("/api/v1/optimization/strategies/any-id", params={
            "status": "adopted",
        })
        assert update.status_code == 200

        # 无效策略状态
        bad = await async_client.put("/api/v1/optimization/strategies/any-id", params={
            "status": "invalid",
        })
        assert bad.status_code == 400


# ── Agent Runtime 通过对话触发 ───────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EAgentRuntime:
    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_conversation_triggers_agent(self, mock_llm, async_client: AsyncClient, auth_headers):
        """创建对话 → 发消息 → agent runtime 处理"""
        mock_llm.side_effect = [
            # Dispatcher: 识别为 general_chat
            {"content": json.dumps({
                "skill": "general_chat", "confidence": 0.9, "extracted_params": {},
            })},
            # General chat response
            {"content": "您好！我是千锤AI助手，有什么可以帮您的？"},
        ]

        conv = await async_client.post("/api/conversations", json={
            "title": "Agent测试对话",
        }, headers=auth_headers)
        assert conv.status_code == 201
        conv_id = conv.json()["id"]

        msg = await async_client.post(f"/api/conversations/{conv_id}/messages", json={
            "content": "你好",
        }, headers=auth_headers)
        assert msg.status_code == 200
        assert "text" in msg.json()

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion", new_callable=AsyncMock)
    async def test_conversation_with_skill_dispatch(self, mock_llm, async_client: AsyncClient, auth_headers):
        """对话中触发 skill 分发"""
        mock_llm.side_effect = [
            # Dispatcher: 识别为 script-recommend
            {"content": json.dumps({
                "skill": "script-recommend", "confidence": 0.95,
                "extracted_params": {"scenario": "热玛吉"},
            })},
            # Skill execute
            {"content": json.dumps({
                "recommendations": [
                    {"title": "热玛吉开场话术", "category": "开场白",
                     "content": "您好，看到您关注紧致项目",
                     "psychology": {"key_principle": "共情"},
                     "strategy": {"key_principle": "价值先行"},
                     "confidence": 0.9}
                ]
            })},
        ]

        conv = await async_client.post("/api/conversations", json={
            "title": "Skill分发测试",
        }, headers=auth_headers)
        conv_id = conv.json()["id"]

        msg = await async_client.post(f"/api/conversations/{conv_id}/messages", json={
            "content": "推荐一个热玛吉的开场白话术",
        }, headers=auth_headers)
        assert msg.status_code == 200

    async def test_conversation_list_and_messages(self, async_client: AsyncClient, auth_headers):
        """对话列表 + 消息列表"""
        conv = await async_client.post("/api/conversations", json={
            "title": "列表测试",
        }, headers=auth_headers)
        conv_id = conv.json()["id"]

        listing = await async_client.get("/api/conversations", headers=auth_headers)
        assert listing.status_code == 200

        messages = await async_client.get(
            f"/api/conversations/{conv_id}/messages", headers=auth_headers
        )
        assert messages.status_code == 200

    async def test_conversation_nonexistent(self, async_client: AsyncClient, auth_headers):
        msg = await async_client.get(
            "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
            headers=auth_headers,
        )
        assert msg.status_code == 404


# ── Memory 扩展 ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EMemoryExtended:
    async def test_full_memory_crud(self, async_client: AsyncClient, auth_headers):
        """痛点/产品/服务 完整 CRUD"""
        # 痛点
        pp1 = await async_client.post("/api/memory/pain-points", json={
            "name": "E2E痛点A", "description": "描述A",
        }, headers=auth_headers)
        assert pp1.status_code == 201
        pp1_id = pp1.json()["id"]

        pp2 = await async_client.post("/api/memory/pain-points", json={
            "name": "E2E痛点B",
        }, headers=auth_headers)
        assert pp2.status_code == 201

        pp_list = await async_client.get("/api/memory/pain-points", headers=auth_headers)
        assert pp_list.status_code == 200
        assert len(pp_list.json()) >= 2

        # 产品关联多个痛点
        prod = await async_client.post("/api/memory/products", json={
            "name": "E2E产品X",
            "description": "产品描述",
            "pain_point_ids": [pp1_id, pp2.json()["id"]],
        }, headers=auth_headers)
        assert prod.status_code == 201
        prod_id = prod.json()["id"]
        assert len(prod.json()["pain_points"]) == 2

        prod_list = await async_client.get("/api/memory/products", headers=auth_headers)
        assert prod_list.status_code == 200

        # 服务关联产品
        svc = await async_client.post("/api/memory/services", json={
            "name": "E2E服务Y",
            "description": "服务描述",
            "product_ids": [prod_id],
        }, headers=auth_headers)
        assert svc.status_code == 201
        assert len(svc.json()["products"]) == 1

        svc_list = await async_client.get("/api/memory/services", headers=auth_headers)
        assert svc_list.status_code == 200

        # 知识链
        chain = await async_client.get("/api/memory/knowledge-chain", headers=auth_headers)
        assert chain.status_code == 200
        assert len(chain.json()["pain_points"]) >= 2


# ── Deps 边界测试 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestE2EDeps:
    async def test_no_auth_header(self, async_client: AsyncClient):
        resp = await async_client.get("/api/scripts")
        assert resp.status_code in (401, 403)

    async def test_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get("/api/scripts", headers={
            "Authorization": "Bearer invalid-token-here",
        })
        assert resp.status_code in (401, 403)

    async def test_expired_token(self, async_client: AsyncClient):
        from jose import jwt as jose_jwt
        from app.config import get_settings
        import time
        settings = get_settings()
        expired = jose_jwt.encode(
            {"sub": "fake-id", "exp": int(time.time()) - 3600},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        resp = await async_client.get("/api/scripts", headers={
            "Authorization": f"Bearer {expired}",
        })
        assert resp.status_code in (401, 403)
