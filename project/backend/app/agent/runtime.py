import json
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ConversationContext
from app.config import get_settings
from app.providers.base import ModelProvider
from app.providers.factory import ModelProviderFactory
from app.skills.dispatcher import SkillDispatcher

logger = logging.getLogger(__name__)

GENERAL_CHAT_PROMPT = """你是「千锤」—— 一个专业的营销话术AI助手。

当用户的问题不属于任何特定Skill时，你作为通用对话助手回答。

## 回答原则
- 保持专业、友好的语气
- 如果问题与话术/营销/客服相关，给出实用建议
- 如果用户似乎想使用某个功能，主动引导到正确的Skill
- 可以介绍系统功能：话术推荐、对话诊断、培训刷题、模拟演练、数据看板、企业记忆

## 快捷指令提示
你可以提示用户使用以下快捷指令：
- /推荐 [场景] — 推荐话术
- /诊断 — 诊断对话
- /刷题 — 每日刷题
- /演练 [场景] — 模拟演练
- /看板 — 查看数据
"""


class AgentRuntime:
    """Core agent runtime — intent recognition → skill dispatch → execute → respond."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.provider = self._create_provider()
        self.dispatcher = SkillDispatcher(self.provider)
        self.context_manager = ConversationContext(db)

    def _create_provider(self) -> ModelProvider:
        return ModelProviderFactory.create_provider(
            provider_type=self.settings.LLM_PROVIDER,
            api_key=self.settings.LLM_API_KEY,
            api_base=self.settings.LLM_API_BASE,
            model=self.settings.LLM_MODEL,
        )

    async def process_message(
        self,
        user_input: str,
        conversation_id: str | None,
        user_id: str,
        enterprise_id: str,
    ) -> dict:
        conversation = await self.context_manager.get_or_create_conversation(
            conversation_id, user_id, enterprise_id
        )

        await self.context_manager.save_message(
            conversation.id, "user", user_input
        )

        try:
            memory = await self.context_manager.load_enterprise_memory(enterprise_id)
            relevant_scripts = await self.context_manager.load_relevant_scripts(enterprise_id, user_input)
            history = await self.context_manager.get_conversation_history(conversation.id)

            context = {
                "enterprise_memory": memory,
                "relevant_scripts": relevant_scripts,
                "conversation_history": history,
                "user_id": user_id,
                "enterprise_id": enterprise_id,
                "params": {},
            }

            skill, dispatch_info = await self.dispatcher.dispatch(user_input, context)
            context["params"] = dispatch_info.get("params", {})
            context["industry"] = "消费医疗"
            products_list = [p["name"] for p in memory.get("products", [])]
            context["products"] = products_list if products_list else "热玛吉、水光针、吸脂塑形"

            if skill is not None:
                result = await skill.execute(user_input, context)
                skill_name = skill.name
            else:
                result = await self._general_chat(user_input, history, memory)
                skill_name = "general_chat"
        except Exception as e:
            logger.exception("LLM call failed: %s", e)
            result = self._fallback_response(user_input)
            skill_name = "fallback"

        ai_message = await self.context_manager.save_message(
            conversation.id,
            "assistant",
            result["text"],
            skill_used=skill_name,
            cards=result.get("cards", []),
            suggested_actions=result.get("suggested_actions", []),
        )

        return {
            "conversation_id": str(conversation.id),
            "message_id": str(ai_message.id),
            "text": result["text"],
            "cards": result.get("cards", []),
            "suggested_actions": result.get("suggested_actions", []),
            "skill_used": skill_name,
        }

    async def process_message_stream(
        self,
        user_input: str,
        conversation_id: str | None,
        user_id: str,
        enterprise_id: str,
    ) -> AsyncIterator[str]:
        conversation = await self.context_manager.get_or_create_conversation(
            conversation_id, user_id, enterprise_id
        )

        await self.context_manager.save_message(
            conversation.id, "user", user_input
        )

        yield f"data: {json.dumps({'type': 'start', 'conversation_id': str(conversation.id)})}\n\n"

        try:
            memory = await self.context_manager.load_enterprise_memory(enterprise_id)
            history = await self.context_manager.get_conversation_history(conversation.id)

            system_prompt = self.context_manager.build_system_prompt(
                enterprise_name="企业",
                memory=memory,
            )

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history[-10:])
            messages.append({"role": "user", "content": user_input})

            full_response = ""
            async for chunk in self.provider.chat_completion_stream(messages, temperature=0.7):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        except Exception as e:
            logger.exception("Stream LLM call failed: %s", e)
            fallback = self._fallback_response(user_input)
            full_response = fallback["text"]
            for word in full_response:
                yield f"data: {json.dumps({'type': 'chunk', 'content': word})}\n\n"

        await self.context_manager.save_message(
            conversation.id,
            "assistant",
            full_response,
            skill_used="stream_chat",
        )

        yield f"data: {json.dumps({'type': 'end', 'conversation_id': str(conversation.id)})}\n\n"

    @staticmethod
    def _fallback_response(user_input: str) -> dict:
        """When LLM API is unreachable, return a helpful fallback."""
        import random
        tips = [
            "你可以试试输入 /推荐 获客 来获取话术推荐",
            "输入 /诊断 可以分析你的对话质量",
            "输入 /刷题 开始每日培训",
            "输入 /演练 价格异议 来进行模拟演练",
        ]
        return {
            "text": (
                f"你好！我是千锤AI助手。我收到了你的消息：「{user_input[:50]}」\n\n"
                "⚠️ 当前AI模型服务暂时无法连接（可能是网络问题），"
                "我会用预置回复来响应。当模型服务恢复后，你将获得完整的AI对话体验。\n\n"
                f"💡 小提示：{random.choice(tips)}\n\n"
                "如需检查配置，请确认 .env 中的 LLM_API_KEY 和 LLM_API_BASE 正确，"
                "且服务器能访问对应的API地址。"
            ),
            "cards": [],
            "suggested_actions": [
                {"label": "推荐话术", "action": "script_recommend"},
                {"label": "开始刷题", "action": "script_train"},
                {"label": "查看看板", "action": "data_insight"},
            ],
        }

    async def _general_chat(
        self,
        user_input: str,
        history: list[dict],
        memory: dict,
    ) -> dict:
        system_prompt = GENERAL_CHAT_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_input})

        result = await self.provider.chat_completion(messages, temperature=0.7)

        return {
            "text": result["content"],
            "cards": [],
            "suggested_actions": [
                {"label": "推荐话术", "action": "script_recommend"},
                {"label": "开始刷题", "action": "script_train"},
                {"label": "查看看板", "action": "data_insight"},
            ],
        }
