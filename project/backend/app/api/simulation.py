import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.simulation import SimulationSession
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.schemas.simulation import (
    SimulationCompleteResponse,
    SimulationCreate,
    SimulationListResponse,
    SimulationMessageResponse,
    SimulationMessageSend,
    SimulationSessionResponse,
)
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _get_provider():
    settings = get_settings()
    return ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )


@router.post("/sessions", response_model=SimulationSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SimulationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    provider = _get_provider()

    skill = SkillRegistry().get_skill("script-simulate")
    if not skill:
        from app.skills.script_simulate import ScriptSimulateSkill
        skill = ScriptSimulateSkill(provider)

    context = {
        "mode": "start",
        "scenario": body.scenario,
        "customer_type": body.customer_type,
        "difficulty": body.difficulty,
        "enterprise_context": "消费医疗行业",
    }

    result = await skill.execute("", context)

    opening = ""
    for card in result.get("cards", []):
        if card["type"] == "simulation-start":
            opening = card["data"].get("customer_opening", "")

    session = SimulationSession(
        user_id=user.id,
        enterprise_id=user.enterprise_id,
        scenario=body.scenario,
        customer_type=body.customer_type,
        difficulty=body.difficulty,
        messages=[{"role": "customer", "content": opening}],
        status="active",
    )
    db.add(session)
    await db.flush()

    return SimulationSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/messages", response_model=SimulationMessageResponse)
async def send_simulation_message(
    session_id: str,
    body: SimulationMessageSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SimulationSession).where(
            SimulationSession.id == uuid.UUID(session_id),
            SimulationSession.user_id == user.id,
            SimulationSession.status == "active",
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "演练会话不存在或已结束", "message_en": "Simulation session not found or already ended"})

    provider = _get_provider()
    skill = SkillRegistry().get_skill("script-simulate")
    if not skill:
        from app.skills.script_simulate import ScriptSimulateSkill
        skill = ScriptSimulateSkill(provider)

    current_messages = list(session.messages or [])
    current_messages.append({"role": "consultant", "content": body.content})

    context = {
        "mode": "chat",
        "scenario": session.scenario,
        "customer_type": session.customer_type,
        "difficulty": session.difficulty,
        "conversation_history": current_messages,
        "show_hints": True,
        "enterprise_context": "消费医疗行业",
    }

    skill_result = await skill.execute(body.content, context)

    current_messages.append({"role": "customer", "content": skill_result["text"]})
    session.messages = current_messages
    await db.flush()

    hint = skill_result.get("hint")
    hint_data = None
    if hint:
        from app.schemas.simulation import SimulationHint
        hint_data = SimulationHint(
            customer_psychology=hint.get("customer_psychology", ""),
            suggested_strategy=hint.get("suggested_strategy", ""),
        )

    return SimulationMessageResponse(
        ai_response=skill_result["text"],
        hint=hint_data,
    )


@router.post("/sessions/{session_id}/complete", response_model=SimulationCompleteResponse)
async def complete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SimulationSession).where(
            SimulationSession.id == uuid.UUID(session_id),
            SimulationSession.user_id == user.id,
            SimulationSession.status == "active",
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "演练会话不存在或已结束", "message_en": "Simulation session not found or already ended"})

    provider = _get_provider()
    skill = SkillRegistry().get_skill("script-simulate")
    if not skill:
        from app.skills.script_simulate import ScriptSimulateSkill
        skill = ScriptSimulateSkill(provider)

    context = {
        "mode": "score",
        "scenario": session.scenario,
        "customer_type": session.customer_type,
        "difficulty": session.difficulty,
        "conversation_history": session.messages or [],
    }

    skill_result = await skill.execute("", context)

    score_data = {}
    for card in skill_result.get("cards", []):
        if card["type"] == "simulation-score":
            score_data = card["data"]

    session.score = score_data
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return SimulationCompleteResponse(
        overall_score=score_data.get("overall_score", 0),
        dimensions=score_data.get("dimensions", []),
        improvement_suggestions=score_data.get("improvement_suggestions", []),
        summary=score_data.get("summary", "演练结束"),
    )


@router.get("/sessions", response_model=SimulationListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count_result = await db.execute(
        select(func.count(SimulationSession.id)).where(SimulationSession.user_id == user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(SimulationSession)
        .where(SimulationSession.user_id == user.id)
        .order_by(SimulationSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    sessions = result.scalars().all()

    return SimulationListResponse(
        items=[SimulationSessionResponse.model_validate(s) for s in sessions],
        total=total,
    )
