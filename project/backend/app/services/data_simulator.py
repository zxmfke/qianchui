"""Background data simulator — generates fake conversation data every 2 hours.

Simulates real user activity so the product dashboards stay dynamic.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.conversation import Conversation, Message
from app.models.script import Script, ScriptUsage
from app.models.training import TrainingRecord
from app.models.user import User

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours

CUSTOMER_OPENERS = [
    "你们的产品多少钱？",
    "我想了解一下你们的服务",
    "你们和XX品牌相比有什么优势？",
    "我上次买的东西效果不太好",
    "朋友推荐我来看看，能介绍一下吗？",
    "你们最近有什么优惠活动？",
    "我在考虑要不要买，但还有些犹豫",
    "能不能给我发一些案例看看？",
    "我之前在别家买过，感觉一般",
    "种植牙大概要多少费用？",
    "你们的热玛吉效果怎么样？",
    "我想做个双眼皮，恢复期多长？",
    "你们的课程适合零基础吗？",
    "减肥项目安全吗？有副作用吗？",
    "你们能提供分期付款吗？",
]

AGENT_REPLIES = [
    "您好！感谢您的咨询，我来为您详细介绍一下。",
    "非常理解您的顾虑，很多客户最初也有同样的疑问。",
    "您问的这个问题特别好，说明您非常专业。我帮您分析一下...",
    "根据您的情况，我建议您可以考虑我们的专业方案。",
    "价格方面我们有多种套餐可选，性价比都非常高。",
    "效果方面您完全可以放心，我给您看几个真实案例。",
    "我们目前有一个限时活动，现在咨询可以享受8折优惠。",
    "您方便留个联系方式吗？我让专业顾问给您做个详细方案。",
    "对比下来我们的优势主要在三个方面：技术、服务和性价比。",
    "很多跟您情况类似的客户反馈效果都非常好，满意度在95%以上。",
]

CUSTOMER_FOLLOWUPS = [
    "嗯，听起来不错，还有其他方案吗？",
    "价格能再优惠一点吗？",
    "效果有保障吗？",
    "我再考虑考虑",
    "好的，我留个电话吧",
    "可以先试用一下吗？",
    "你们的售后服务怎么样？",
    "周末可以预约吗？",
    "有没有老客户推荐的优惠？",
    "嗯好的，那我先了解一下",
]

TRAINING_QUESTIONS = [
    {
        "question": "客户说「太贵了」时，最佳回应是？",
        "options": [
            {"key": "A", "text": "给您打个折吧"},
            {"key": "B", "text": "一分钱一分货"},
            {"key": "C", "text": "您觉得贵是跟什么对比呢？"},
            {"key": "D", "text": "不买拉倒"},
        ],
        "correct": "C",
        "explanation": "先理解客户的参照系，再做价值引导",
    },
    {
        "question": "面对犹豫不决的客户，以下哪种做法最好？",
        "options": [
            {"key": "A", "text": "反复催促"},
            {"key": "B", "text": "用限时优惠+成功案例推动决策"},
            {"key": "C", "text": "放弃跟进"},
            {"key": "D", "text": "降价到最低"},
        ],
        "correct": "B",
        "explanation": "合理紧迫感+社会证明辅助决策",
    },
    {
        "question": "客户投诉时，第一步应该？",
        "options": [
            {"key": "A", "text": "解释原因"},
            {"key": "B", "text": "推给上级"},
            {"key": "C", "text": "先共情安抚情绪"},
            {"key": "D", "text": "直接赔偿"},
        ],
        "correct": "C",
        "explanation": "先处理情绪再处理事情",
    },
]

CATEGORIES = ["异议处理", "开场白", "竞品应对", "促成", "售后", "复购"]


async def _generate_batch(session: AsyncSession) -> int:
    """Generate a batch of simulated data. Returns number of conversations created."""
    users = (await session.execute(
        select(User).where(User.role != "super_admin", User.is_active.is_(True))
    )).scalars().all()
    if not users:
        return 0

    scripts = (await session.execute(
        select(Script).where(Script.status == "published").limit(50)
    )).scalars().all()

    now = datetime.now(timezone.utc)
    conv_count = random.randint(3, 8)
    created = 0

    for _ in range(conv_count):
        user = random.choice(users)
        title = random.choice(CUSTOMER_OPENERS)[:30]

        conv = Conversation(
            id=uuid4(),
            user_id=user.id,
            enterprise_id=user.enterprise_id,
            title=title,
            created_at=now - timedelta(minutes=random.randint(0, 110)),
        )
        session.add(conv)
        await session.flush()

        msg_count = random.randint(3, 8)
        for j in range(msg_count):
            if j == 0:
                content = random.choice(CUSTOMER_OPENERS)
                role = "user"
            elif j % 2 == 1:
                content = random.choice(AGENT_REPLIES)
                role = "assistant"
            else:
                content = random.choice(CUSTOMER_FOLLOWUPS)
                role = "user"

            msg = Message(
                id=uuid4(),
                conversation_id=conv.id,
                role=role,
                content=content,
                created_at=conv.created_at + timedelta(minutes=j * random.randint(1, 3)),
            )
            session.add(msg)

        created += 1

    if scripts:
        for _ in range(random.randint(5, 15)):
            su = ScriptUsage(
                id=uuid4(),
                script_id=random.choice(scripts).id,
                user_id=random.choice(users).id,
                enterprise_id=random.choice(users).enterprise_id,
                context={"source": random.choice(["chat", "recommend", "search"])},
                created_at=now - timedelta(minutes=random.randint(0, 110)),
            )
            session.add(su)

    for _ in range(random.randint(2, 5)):
        user = random.choice(users)
        q = random.choice(TRAINING_QUESTIONS)
        is_correct = random.random() < 0.7
        tr = TrainingRecord(
            id=uuid4(),
            user_id=user.id,
            enterprise_id=user.enterprise_id,
            script_id=random.choice(scripts).id if scripts else None,
            question={"question": q["question"], "options": q["options"]},
            user_answer=q["correct"] if is_correct else random.choice(["A", "B", "C", "D"]),
            correct_answer=q["correct"],
            is_correct=is_correct,
            category=random.choice(CATEGORIES),
            difficulty=random.randint(1, 3),
            explanation={"text": q["explanation"]},
            created_at=now - timedelta(minutes=random.randint(0, 110)),
        )
        session.add(tr)

    await session.commit()
    return created


async def run_simulator() -> None:
    """Background loop: generate fake data every INTERVAL_SECONDS."""
    logger.info("Data simulator started (interval=%ds)", INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                count = await _generate_batch(session)
                logger.info("Simulator: generated %d conversations + usage/training data", count)
        except Exception:
            logger.exception("Simulator batch failed")
