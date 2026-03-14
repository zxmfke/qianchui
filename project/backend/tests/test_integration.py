"""聚合测试 — 跨模块端到端流程验证

测试完整的业务流程，确保模块之间的数据流转正确。
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestE2EKnowledgeChain:
    """端到端流程：痛点 → 产品 → 服务 → 话术 → 知识链路"""

    async def test_full_knowledge_chain_flow(self, async_client: AsyncClient, auth_headers):
        # 1. 创建痛点
        pp_resp = await async_client.post(
            "/api/memory/pain-points",
            json={"name": "面部松弛", "description": "客户关注面部松弛问题"},
            headers=auth_headers,
        )
        assert pp_resp.status_code == 201
        pp_id = pp_resp.json()["id"]

        # 2. 创建产品并关联痛点
        prod_resp = await async_client.post(
            "/api/memory/products",
            json={"name": "热玛吉", "description": "紧致提拉项目", "pain_point_ids": [pp_id]},
            headers=auth_headers,
        )
        assert prod_resp.status_code == 201
        prod_id = prod_resp.json()["id"]
        assert len(prod_resp.json()["pain_points"]) == 1
        assert prod_resp.json()["pain_points"][0]["name"] == "面部松弛"

        # 3. 创建服务并关联产品
        svc_resp = await async_client.post(
            "/api/memory/services",
            json={"name": "面诊服务", "description": "面对面咨询", "product_ids": [prod_id]},
            headers=auth_headers,
        )
        assert svc_resp.status_code == 201
        svc_id = svc_resp.json()["id"]
        assert len(svc_resp.json()["products"]) == 1

        # 4. 创建话术
        script_resp = await async_client.post(
            "/api/scripts",
            json={
                "title": "面部松弛开场话术",
                "content": "您好，看到您关注面部紧致，您是否有面部松弛的困扰呢？",
                "category": "开场白",
                "tags": ["紧致", "热玛吉"],
                "pain_point_ids": [pp_id],
                "product_ids": [prod_id],
                "service_ids": [svc_id],
            },
            headers=auth_headers,
        )
        assert script_resp.status_code == 201
        script_data = script_resp.json()
        assert script_data["title"] == "面部松弛开场话术"

        # 5. 验证知识链路完整性
        chain_resp = await async_client.get(
            "/api/memory/knowledge-chain", headers=auth_headers
        )
        assert chain_resp.status_code == 200
        chain = chain_resp.json()
        assert len(chain["pain_points"]) >= 1
        pp_node = next(n for n in chain["pain_points"] if n["name"] == "面部松弛")
        assert pp_node["type"] == "pain_point"
        assert len(pp_node["children"]) >= 1  # 有产品子节点
        prod_node = pp_node["children"][0]
        assert prod_node["name"] == "热玛吉"
        assert len(prod_node["children"]) >= 1  # 有服务子节点

        # 6. 验证飞轮看板能看到数据
        fw_resp = await async_client.get(
            "/api/v1/flywheel/dashboard", headers=auth_headers
        )
        assert fw_resp.status_code == 200
        fw_data = fw_resp.json()
        assert len(fw_data["pain_point_trends"]) >= 1
        assert len(fw_data["product_strategies"]) >= 1
        assert len(fw_data["service_strategies"]) >= 1
        assert len(fw_data["script_lifecycles"]) >= 1


@pytest.mark.asyncio
class TestE2ETrainingFlow:
    """端到端流程：生成题目 → 答题 → 查看进度 → 检查弱项"""

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_full_training_flow(self, mock_llm, async_client: AsyncClient, auth_headers):
        # 1. 生成练习题
        mock_llm.return_value = {"content": json.dumps({
            "questions": [
                {
                    "id": "q1", "scenario": "客户说太贵", "customer_state": "犹豫",
                    "options": [
                        {"key": "A", "text": "降价"}, {"key": "B", "text": "强调价值"},
                        {"key": "C", "text": "忽略"}, {"key": "D", "text": "反问"}
                    ],
                    "correct_answer": "B", "category": "异议处理", "difficulty": 2,
                    "explanation": {"psychology": "心理", "strategy": "策略", "script": "话术"},
                },
            ]
        })}

        quiz_resp = await async_client.get("/api/training/quiz", headers=auth_headers)
        assert quiz_resp.status_code == 200
        questions = quiz_resp.json()["questions"]
        assert len(questions) >= 1

        # 2. 提交正确答案（question_data 需要包含 correct_answer，QuizQuestion 模型会过滤）
        full_question_data = {
            **questions[0],
            "correct_answer": "B",
            "explanation": {"psychology": "心理", "strategy": "策略", "script": "话术"},
        }
        answer_resp = await async_client.post(
            "/api/training/quiz/answer",
            json={
                "question_id": "q1",
                "answer": "B",
                "question_data": full_question_data,
            },
            headers=auth_headers,
        )
        assert answer_resp.status_code == 200
        assert answer_resp.json()["is_correct"] is True

        # 3. 提交错误答案（制造弱项）
        for i in range(3):
            await async_client.post(
                "/api/training/quiz/answer",
                json={
                    "question_id": f"q_wrong_{i}",
                    "answer": "A",
                    "question_data": {
                        "question": "q", "correct_answer": "C",
                        "category": "客户心理", "difficulty": 1,
                        "explanation": {"psychology": "", "strategy": "", "script": ""},
                    },
                },
                headers=auth_headers,
            )

        # 4. 查看进度
        progress_resp = await async_client.get("/api/training/progress", headers=auth_headers)
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress["total_questions"] == 4
        assert progress["correct_count"] == 1
        assert 0.0 < progress["accuracy"] < 1.0
        assert progress["streak_days"] >= 1

        # 5. 查看弱项
        weak_resp = await async_client.get("/api/training/weak-points", headers=auth_headers)
        assert weak_resp.status_code == 200
        weak_points = weak_resp.json()
        assert any(w["category"] == "客户心理" for w in weak_points)


@pytest.mark.asyncio
class TestE2ESimulationFlow:
    """端到端流程：创建模拟 → 对话 → 结束评分 → 查看历史"""

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_full_simulation_flow(self, mock_llm, async_client: AsyncClient, auth_headers):
        mock_llm.side_effect = [
            # 1. create_session → _start_simulation (1 call)
            {"content": "你好，我想了解一下双眼皮手术"},
            # 2. send_message → _chat_turn: customer response (1 call)
            {"content": "嗯，我比较担心恢复期多长"},
            # 3. send_message → _chat_turn: hint generation (1 call)
            {"content": json.dumps({
                "customer_psychology": "犹豫中",
                "suggested_strategy": "提供案例",
            })},
            # 4. complete_session → _score_simulation (1 call)
            {"content": json.dumps({
                "overall_score": 82,
                "dimensions": [
                    {"dimension": "专业度", "score": 85, "comment": "不错"},
                    {"dimension": "共情力", "score": 78, "comment": "可以更好"},
                ],
                "improvement_suggestions": ["多用案例说服"],
                "summary": "整体表现良好",
            })},
        ]

        # 1. 创建模拟会话
        create_resp = await async_client.post(
            "/api/simulation/sessions",
            json={"scenario": "双眼皮咨询", "customer_type": "首次咨询", "difficulty": 2},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        session = create_resp.json()
        session_id = session["id"]
        assert session["status"] == "active"

        # 2. 发送消息
        msg_resp = await async_client.post(
            f"/api/simulation/sessions/{session_id}/messages",
            json={"content": "双眼皮有全切和埋线两种，您比较倾向哪种呢？"},
            headers=auth_headers,
        )
        assert msg_resp.status_code == 200
        assert "ai_response" in msg_resp.json()

        # 3. 结束评分
        complete_resp = await async_client.post(
            f"/api/simulation/sessions/{session_id}/complete",
            headers=auth_headers,
        )
        assert complete_resp.status_code == 200
        score = complete_resp.json()
        assert score["overall_score"] == 82
        assert len(score["dimensions"]) == 2
        assert score["summary"] == "整体表现良好"

        # 4. 查看历史
        list_resp = await async_client.get(
            "/api/simulation/sessions", headers=auth_headers
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1


@pytest.mark.asyncio
class TestE2EDiagnosisToOptimization:
    """端到端流程：诊断对话 → 查看报告 → 生成优化方案 → 创建优化任务"""

    @patch("app.providers.openai_provider.OpenAIProvider.chat_completion")
    async def test_diagnosis_to_optimization(self, mock_llm, async_client: AsyncClient, auth_headers):
        # 1. 诊断对话
        mock_llm.return_value = {"content": json.dumps({
            "overall_score": 65,
            "diagnosis": {
                "psychology_layer": {"score": 70, "issues": [
                    {"turn": 1, "issue": "缺少共情", "original": "你好", "suggested": "您好！看到您关注吸脂"}
                ]},
                "strategy_layer": {"score": 60, "issues": [
                    {"turn": 2, "issue": "逼单过早", "current_strategy": "直接逼单", "suggested_strategy": "先提供价值"}
                ]},
                "script_layer": {"score": 65, "issues": [
                    {"turn": 2, "issue": "模板化", "original": "方便留个电话吗", "suggested": "可以先加微信看方案"}
                ]},
            },
            "improvement_plan": ["优化开场", "延后逼单"],
        })}

        diag_resp = await async_client.post(
            "/api/diagnosis/analyze",
            json={"conversation_text": "客服：你好\n客户：想了解吸脂\n客服：方便留个电话吗"},
            headers=auth_headers,
        )
        assert diag_resp.status_code == 200
        report_id = diag_resp.json()["report_id"]

        # 2. 查看报告
        report_resp = await async_client.get(
            f"/api/diagnosis/reports/{report_id}", headers=auth_headers
        )
        assert report_resp.status_code == 200
        assert report_resp.json()["result"]["overall_score"] == 65

        # 3. 创建优化任务（优化 API 使用 v1 前缀，参数为查询参数）
        task_resp = await async_client.post(
            "/api/v1/optimization/tasks",
            params={"conversation_text": "客服：你好\n客户：想了解吸脂\n客服：方便留个电话吗"},
        )
        assert task_resp.status_code == 200
        task_id = task_resp.json()["task_id"]

        # 4. 生成优化策略
        strategy_resp = await async_client.post(
            f"/api/v1/optimization/tasks/{task_id}/generate-strategies",
        )
        assert strategy_resp.status_code == 200

        # 5. 获取策略列表
        strats_resp = await async_client.get(
            f"/api/v1/optimization/tasks/{task_id}/strategies",
        )
        assert strats_resp.status_code == 200


@pytest.mark.asyncio
class TestE2EConversationFlow:
    """端到端流程：创建对话 → 发消息 → 获取消息历史"""

    @patch("app.agent.runtime.AgentRuntime.process_message", new_callable=AsyncMock)
    async def test_conversation_with_messages(self, mock_process, async_client: AsyncClient, auth_headers):
        mock_process.return_value = {
            "conversation_id": "will-be-overridden",
            "message_id": "msg-1",
            "text": "您好！请问有什么可以帮助您的？",
            "cards": [],
            "suggested_actions": [{"label": "推荐话术", "action": "script_recommend"}],
            "skill_used": "general_chat",
        }

        # 1. 创建对话
        conv_resp = await async_client.post(
            "/api/conversations",
            json={"title": "咨询对话"},
            headers=auth_headers,
        )
        assert conv_resp.status_code == 201
        conv_id = conv_resp.json()["id"]

        # 2. 发消息
        msg_resp = await async_client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "你好，我想了解一下热玛吉"},
            headers=auth_headers,
        )
        assert msg_resp.status_code == 200
        assert "text" in msg_resp.json()

        # 3. 获取消息历史
        history_resp = await async_client.get(
            f"/api/conversations/{conv_id}/messages", headers=auth_headers
        )
        assert history_resp.status_code == 200


@pytest.mark.asyncio
class TestE2EAnnotationToABTest:
    """端到端流程：创建标注 → 创建 AB 测试 → 开始 → 获取指标"""

    async def test_annotation_and_ab_test_flow(self, async_client: AsyncClient, auth_headers):
        # 1. 创建标注（使用查询参数）
        annot_resp = await async_client.post(
            "/api/v1/annotations",
            params={
                "conversation_text": "客服：你好\n客户：咨询",
                "turn_index": 0,
                "label": "good",
                "strategy_type": "ice_breaking",
                "note": "很好的开场白",
            },
        )
        assert annot_resp.status_code == 200
        assert annot_resp.json()["label"] == "good"

        # 2. 创建 AB 测试（使用查询参数）
        ab_resp = await async_client.post(
            "/api/v1/ab-tests",
            params={"name": "开场白AB测试", "description": "测试新旧开场白效果"},
        )
        assert ab_resp.status_code == 200
        ab_id = ab_resp.json()["id"]

        # 3. 开始测试（PUT）
        start_resp = await async_client.put(
            f"/api/v1/ab-tests/{ab_id}/start",
        )
        assert start_resp.status_code == 200

        # 4. 获取指标
        metrics_resp = await async_client.get(
            f"/api/v1/ab-tests/{ab_id}/metrics",
        )
        assert metrics_resp.status_code == 200

        # 5. 停止测试（PUT）
        stop_resp = await async_client.put(
            f"/api/v1/ab-tests/{ab_id}/stop",
        )
        assert stop_resp.status_code == 200

        # 6. 查看列表
        list_resp = await async_client.get("/api/v1/ab-tests")
        assert list_resp.status_code == 200


@pytest.mark.asyncio
class TestE2EChannelMaterialFlow:
    """端到端流程：创建渠道物料 → 查询 → 统计"""

    async def test_channel_material_crud_flow(self, async_client: AsyncClient, auth_headers):
        create_resp = await async_client.post(
            "/api/v1/channel-materials",
            json={
                "title": "热玛吉抖音视频脚本",
                "channel": "douyin",
                "material_type": "video",
                "content": "热玛吉紧致提拉...",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code in (200, 201)
        mat_id = create_resp.json()["id"]

        list_resp = await async_client.get("/api/v1/channel-materials", headers=auth_headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        filter_resp = await async_client.get(
            "/api/v1/channel-materials", params={"channel": "douyin"}, headers=auth_headers,
        )
        assert filter_resp.status_code == 200

        detail_resp = await async_client.get(f"/api/v1/channel-materials/{mat_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["title"] == "热玛吉抖音视频脚本"

        update_resp = await async_client.put(
            f"/api/v1/channel-materials/{mat_id}",
            json={"title": "更新后的标题", "status": "active"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        del_resp = await async_client.delete(f"/api/v1/channel-materials/{mat_id}", headers=auth_headers)
        assert del_resp.status_code == 200
