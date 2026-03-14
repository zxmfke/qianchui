import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.memory import PainPoint, Product, ServiceItem
from app.models.script import Script


SYSTEM_PROMPT_TEMPLATE = """你是「千锤」—— 一个专业的营销话术AI助手。

你服务于 {enterprise_name} 企业，帮助其营销/客服团队提升话术能力。

## 核心能力
你可以：
1. 推荐合适的营销话术（根据场景、客户类型）
2. 诊断对话质量（分析真实对话，找出问题）
3. 生成培训题目（刷题式学习话术技巧）
4. 模拟客户演练（AI扮演客户进行对话练习）
5. 提供数据洞察（话术使用数据分析）
6. 查询企业记忆（痛点→产品→服务→话术链路）

## 话术三层结构
所有话术都遵循三层结构：
- 心理层（WHY）：分析客户心理状态
- 策略层（HOW）：选择沟通策略框架
- 话术层（WHAT）：提供具体话术文本

## 企业知识
### 痛点
{pain_points}

### 产品
{products}

### 服务
{services}

## 对话规则
- 始终保持专业、友好的语气
- 输出要结构化，便于阅读
- 优先从企业记忆中检索相关知识
- 回答要具体、可操作，不要空泛
- 当用户意图不明确时，主动引导和澄清"""


class ConversationContext:
    """Manages conversation history, enterprise memory, and system prompt."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str,
        enterprise_id: str,
    ) -> Conversation:
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        conversation = Conversation(
            user_id=uuid.UUID(user_id),
            enterprise_id=uuid.UUID(enterprise_id),
            title="新对话",
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        messages = list(reversed(messages))
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

    async def load_enterprise_memory(self, enterprise_id: str) -> dict:
        eid = uuid.UUID(enterprise_id)

        pain_result = await self.db.execute(
            select(PainPoint).where(PainPoint.enterprise_id == eid)
        )
        pain_points = pain_result.scalars().all()

        product_result = await self.db.execute(
            select(Product).where(Product.enterprise_id == eid)
        )
        products = product_result.scalars().all()

        service_result = await self.db.execute(
            select(ServiceItem).where(ServiceItem.enterprise_id == eid)
        )
        services = service_result.scalars().all()

        return {
            "pain_points": [{"id": str(p.id), "name": p.name, "description": p.description} for p in pain_points],
            "products": [{"id": str(p.id), "name": p.name, "description": p.description} for p in products],
            "services": [{"id": str(s.id), "name": s.name, "description": s.description} for s in services],
        }

    async def load_relevant_scripts(
        self,
        enterprise_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        eid = uuid.UUID(enterprise_id)
        result = await self.db.execute(
            select(Script)
            .where(Script.enterprise_id == eid, Script.status == "published")
            .order_by(Script.usage_count.desc())
            .limit(limit)
        )
        scripts = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "category": s.category,
                "psychology_layer": s.psychology_layer,
                "strategy_layer": s.strategy_layer,
                "content": s.content,
                "usage_count": s.usage_count,
            }
            for s in scripts
        ]

    def build_system_prompt(
        self,
        enterprise_name: str,
        memory: dict,
    ) -> str:
        pain_str = "\n".join(
            f"- {p['name']}: {p.get('description', '')}" for p in memory.get("pain_points", [])
        ) or "暂无痛点数据"

        product_str = "\n".join(
            f"- {p['name']}: {p.get('description', '')}" for p in memory.get("products", [])
        ) or "暂无产品数据"

        service_str = "\n".join(
            f"- {s['name']}: {s.get('description', '')}" for s in memory.get("services", [])
        ) or "暂无服务数据"

        return SYSTEM_PROMPT_TEMPLATE.format(
            enterprise_name=enterprise_name,
            pain_points=pain_str,
            products=product_str,
            services=service_str,
        )

    async def save_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        skill_used: str | None = None,
        cards: list | None = None,
        suggested_actions: list | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            skill_used=skill_used,
            cards=cards or [],
            suggested_actions=suggested_actions or [],
        )
        self.db.add(message)
        await self.db.flush()
        return message
