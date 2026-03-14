import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import AgentRuntime
from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.training import TrainingRecord
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.schemas.training import (
    AnswerExplanation,
    QuizAnswerResult,
    QuizAnswerSubmit,
    QuizResponse,
    TrainingProgressResponse,
    WeakPointItem,
)
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/training", tags=["training"])


FALLBACK_QUESTIONS = [
    {
        "id": "fb-q1",
        "question": "当客户说'你们的产品太贵了'时，以下哪种回应最有效？",
        "scenario": "客户对价格敏感，正在比价阶段",
        "customer_state": "价格犹豫",
        "options": [
            {"key": "A", "text": "我们可以打折"},
            {"key": "B", "text": "一分钱一分货"},
            {"key": "C", "text": "您觉得贵是跟什么对比呢？先了解您的参照系"},
            {"key": "D", "text": "这已经是最低价了"},
        ],
        "correct_answer": "C",
        "category": "异议处理",
        "difficulty": 2,
        "explanation": {
            "psychology": "客户说贵是基于某个参照系的比较，先了解参照系才能有效回应",
            "strategy": "通过提问了解客户的比较对象，然后做针对性的价值引导",
            "script": "您觉得贵是跟什么对比呢？其实对比下来我们的性价比是最高的",
        },
    },
    {
        "id": "fb-q2",
        "question": "客户第一次咨询时，以下哪个开场白最能建立信任？",
        "scenario": "新客户首次咨询，对品牌缺乏了解",
        "customer_state": "初次接触，防备心强",
        "options": [
            {"key": "A", "text": "买不买都没关系，先了解下"},
            {"key": "B", "text": "结合客户关注点个性化问候，展示专业性"},
            {"key": "C", "text": "直接介绍产品优势"},
            {"key": "D", "text": "先发优惠券吸引注意"},
        ],
        "correct_answer": "B",
        "category": "开场白",
        "difficulty": 1,
        "explanation": {
            "psychology": "首次咨询客户防备心强，个性化问候能降低防备、建立初步信任",
            "strategy": "通过展示对客户需求的了解来建立专业形象",
            "script": "您好！看您关注了我们的XX产品，很多关注这方面的客户都有类似的困扰",
        },
    },
    {
        "id": "fb-q3",
        "question": "客户说'我再考虑考虑'时，以下哪种做法最合适？",
        "scenario": "客户已了解产品但犹豫不决",
        "customer_state": "兴趣度中等，决策动力不足",
        "options": [
            {"key": "A", "text": "一直催促客户尽快决定"},
            {"key": "B", "text": "直接放弃跟进"},
            {"key": "C", "text": "用限时优惠+成功案例推动决策"},
            {"key": "D", "text": "威胁说马上涨价"},
        ],
        "correct_answer": "C",
        "category": "促成",
        "difficulty": 2,
        "explanation": {
            "psychology": "客户犹豫通常是因为价值感不够强或缺少紧迫感",
            "strategy": "用合理的紧迫感和社会证明帮助客户做决策",
            "script": "理解您需要考虑。这样，本月有个限时优惠，已经有38位客户签约了",
        },
    },
    {
        "id": "fb-q4",
        "question": "处理客户投诉时，第一步应该怎么做？",
        "scenario": "客户对产品/服务不满意，情绪激动",
        "customer_state": "愤怒/不满",
        "options": [
            {"key": "A", "text": "立刻解释原因"},
            {"key": "B", "text": "推卸给其他部门"},
            {"key": "C", "text": "先共情安抚客户情绪"},
            {"key": "D", "text": "直接赔偿了事"},
        ],
        "correct_answer": "C",
        "category": "售后",
        "difficulty": 1,
        "explanation": {
            "psychology": "投诉客户情绪激动，先处理情绪再处理事情",
            "strategy": "共情→承诺→解决→补偿，四步处理投诉",
            "script": "非常理解您的心情，遇到这种情况确实很不愉快。我现在就帮您优先处理",
        },
    },
    {
        "id": "fb-q5",
        "question": "客户说竞品更好时，应该怎么回应？",
        "scenario": "客户正在多家对比，提到竞品优势",
        "customer_state": "理性比较中",
        "options": [
            {"key": "A", "text": "贬低竞品的不足"},
            {"key": "B", "text": "承认竞品优势，再引导到自身差异化优势"},
            {"key": "C", "text": "忽略不回应，继续介绍自己的产品"},
            {"key": "D", "text": "直接降价匹配竞品"},
        ],
        "correct_answer": "B",
        "category": "竞品应对",
        "difficulty": 2,
        "explanation": {
            "psychology": "客户拿竞品对比说明正在权衡，承认竞品优势体现专业性和诚意",
            "strategy": "先认同再差异化，用具体数据和案例支撑",
            "script": "XX产品确实不错。不过在核心技术上我们有三个独特优势...",
        },
    },
    {
        "id": "fb-q6",
        "question": "如何有效引导老客户转介绍？",
        "scenario": "老客户对产品满意，有转介绍潜力",
        "customer_state": "满意度高，关系良好",
        "options": [
            {"key": "A", "text": "直接要求客户推荐朋友"},
            {"key": "B", "text": "先确认客户满意度，再自然引入转介绍计划和双方利益"},
            {"key": "C", "text": "给钱让客户推荐"},
            {"key": "D", "text": "不需要引导，好产品自己会传播"},
        ],
        "correct_answer": "B",
        "category": "复购",
        "difficulty": 3,
        "explanation": {
            "psychology": "转介绍建立在满意度基础上，双方获益的机制降低推荐心理门槛",
            "strategy": "确认满意→自然过渡→互利机制→降低门槛",
            "script": "听您说对服务很满意太开心了！我们有老带新计划，您和朋友都能享受优惠",
        },
    },
]


@router.get("/quiz", response_model=QuizResponse)
async def get_quiz(
    count: int = Query(3, ge=1, le=10),
    difficulty: int = Query(2, ge=1, le=3),
    category: str = Query("综合"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        settings = get_settings()
        provider = ModelProviderFactory.create_provider(
            provider_type=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
        )

        skill = SkillRegistry().get_skill("script-train")
        if not skill:
            from app.skills.script_train import ScriptTrainSkill
            skill = ScriptTrainSkill(provider)

        context = {
            "params": {"difficulty": difficulty, "category": category, "count": count},
            "industry": "消费医疗",
            "products": "热玛吉、水光针、吸脂塑形",
        }

        result = await skill.execute("", context)
        questions = [card["data"] for card in result.get("cards", []) if card["type"] == "training-quiz"]
        if questions:
            return QuizResponse(questions=questions, total=len(questions))
    except Exception:
        pass

    import random
    pool = [q for q in FALLBACK_QUESTIONS if q["difficulty"] <= difficulty]
    if category != "综合":
        filtered = [q for q in pool if q["category"] == category]
        if filtered:
            pool = filtered
    selected = random.sample(pool, min(count, len(pool)))
    return QuizResponse(questions=selected, total=len(selected))


@router.post("/quiz/answer", response_model=QuizAnswerResult)
async def submit_answer(
    body: QuizAnswerSubmit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question_data = body.question_data
    correct_answer = question_data.get("correct_answer", "")
    is_correct = body.answer.upper() == correct_answer.upper()

    explanation_raw = question_data.get("explanation", {})
    explanation = AnswerExplanation(
        psychology=explanation_raw.get("psychology", ""),
        strategy=explanation_raw.get("strategy", ""),
        script=explanation_raw.get("script", ""),
    )

    record = TrainingRecord(
        user_id=user.id,
        enterprise_id=user.enterprise_id,
        question=question_data,
        user_answer=body.answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        category=question_data.get("category", ""),
        difficulty=question_data.get("difficulty", 1),
        explanation=explanation_raw,
    )
    db.add(record)
    await db.flush()

    total_result = await db.execute(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.user_id == user.id)
    )
    total = total_result.scalar() or 0

    correct_result = await db.execute(
        select(func.count(TrainingRecord.id)).where(
            TrainingRecord.user_id == user.id,
            TrainingRecord.is_correct.is_(True),
        )
    )
    correct_count = correct_result.scalar() or 0

    category_name = question_data.get("category", "")
    cat_total_r = await db.execute(
        select(func.count(TrainingRecord.id)).where(
            TrainingRecord.user_id == user.id,
            TrainingRecord.category == category_name,
        )
    )
    cat_total = cat_total_r.scalar() or 0

    cat_correct_r = await db.execute(
        select(func.count(TrainingRecord.id)).where(
            TrainingRecord.user_id == user.id,
            TrainingRecord.category == category_name,
            TrainingRecord.is_correct.is_(True),
        )
    )
    cat_correct = cat_correct_r.scalar() or 0

    return QuizAnswerResult(
        is_correct=is_correct,
        correct_answer=correct_answer,
        explanation=explanation,
        user_accuracy=round(correct_count / total, 4) if total > 0 else 0.0,
        category_accuracy=round(cat_correct / cat_total, 4) if cat_total > 0 else 0.0,
    )


@router.get("/progress", response_model=TrainingProgressResponse)
async def get_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_result = await db.execute(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.user_id == user.id)
    )
    total = total_result.scalar() or 0

    correct_result = await db.execute(
        select(func.count(TrainingRecord.id)).where(
            TrainingRecord.user_id == user.id,
            TrainingRecord.is_correct.is_(True),
        )
    )
    correct = correct_result.scalar() or 0

    now = datetime.now(timezone.utc)
    streak = 0
    for days_ago in range(30):
        day = now - timedelta(days=days_ago)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_result = await db.execute(
            select(func.count(TrainingRecord.id)).where(
                TrainingRecord.user_id == user.id,
                TrainingRecord.created_at >= day_start,
                TrainingRecord.created_at < day_end,
            )
        )
        if (day_result.scalar() or 0) > 0:
            streak += 1
        else:
            if days_ago > 0:
                break

    cat_stats = await db.execute(
        select(
            TrainingRecord.category,
            func.count(TrainingRecord.id).label("total"),
            func.sum(case((TrainingRecord.is_correct.is_(True), 1), else_=0)).label("correct"),
        )
        .where(TrainingRecord.user_id == user.id)
        .group_by(TrainingRecord.category)
    )
    cat_rows = cat_stats.all()

    weak_points = []
    recent_categories = []
    for row in cat_rows:
        cat_name = row[0] or "未分类"
        cat_total = row[1]
        cat_correct = row[2] or 0
        accuracy = cat_correct / cat_total if cat_total > 0 else 0.0
        recent_categories.append(cat_name)
        if accuracy < 0.7:
            weak_points.append(WeakPointItem(
                category=cat_name,
                accuracy=round(accuracy, 4),
                total_questions=cat_total,
                wrong_count=cat_total - cat_correct,
            ))

    weak_points.sort(key=lambda x: x.accuracy)

    return TrainingProgressResponse(
        total_questions=total,
        correct_count=correct,
        accuracy=round(correct / total, 4) if total > 0 else 0.0,
        streak_days=streak,
        weak_points=weak_points,
        recent_categories=recent_categories[:5],
    )


@router.get("/weak-points", response_model=list[WeakPointItem])
async def get_weak_points(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cat_stats = await db.execute(
        select(
            TrainingRecord.category,
            func.count(TrainingRecord.id).label("total"),
            func.sum(case((TrainingRecord.is_correct.is_(True), 1), else_=0)).label("correct"),
        )
        .where(TrainingRecord.user_id == user.id)
        .group_by(TrainingRecord.category)
        .having(
            func.sum(case((TrainingRecord.is_correct.is_(True), 1), else_=0))
            < func.count(TrainingRecord.id) * 0.7
        )
    )
    rows = cat_stats.all()

    items = []
    for row in rows:
        cat_name = row[0] or "未分类"
        cat_total = row[1]
        cat_correct = row[2] or 0
        items.append(WeakPointItem(
            category=cat_name,
            accuracy=round(cat_correct / cat_total, 4) if cat_total > 0 else 0.0,
            total_questions=cat_total,
            wrong_count=cat_total - cat_correct,
        ))

    items.sort(key=lambda x: x.accuracy)
    return items
