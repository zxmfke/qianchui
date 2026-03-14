"""话术诊断 API [v2.0]

诊断完成后自动记录飞轮事件，驱动数据飞轮运转。
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.diagnosis import DiagnosisReport
from app.models.flywheel import FlywheelEvent
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.schemas.diagnosis import (
    DiagnosisAnalyzeRequest,
    DiagnosisAnalyzeResponse,
    DiagnosisReportListResponse,
    DiagnosisReportResponse,
    DiagnosisResult,
)
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])


@router.post("/analyze", response_model=DiagnosisAnalyzeResponse)
async def analyze_conversation(
    body: DiagnosisAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    provider = ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )

    skill = SkillRegistry().get_skill("script-diagnose")
    if not skill:
        from app.skills.script_diagnose import ScriptDiagnoseSkill
        skill = ScriptDiagnoseSkill(provider)

    context = {"conversation_text": body.conversation_text}
    result = await skill.execute(body.conversation_text, context)

    report_card = {}
    for card in result.get("cards", []):
        if card["type"] == "diagnosis-report":
            report_card = card["data"]

    overall_score = report_card.get("overall_score", 0)

    report = DiagnosisReport(
        enterprise_id=user.enterprise_id,
        user_id=user.id,
        conversation_text=body.conversation_text,
        result=report_card,
        overall_score=overall_score,
    )
    db.add(report)
    await db.flush()

    flywheel_event = FlywheelEvent(
        enterprise_id=user.enterprise_id,
        event_type="diagnosis_completed",
        trigger_type="user_action",
        trigger_data={
            "report_id": str(report.id),
            "overall_score": overall_score,
            "conversation_length": len(body.conversation_text),
        },
        result_summary={
            "overall_score": overall_score,
            "psychology_score": report_card.get("psychology_layer", {}).get("score", 0),
            "strategy_score": report_card.get("strategy_layer", {}).get("score", 0),
            "script_score": report_card.get("script_layer", {}).get("score", 0),
            "issues_count": sum(
                len(report_card.get(k, {}).get("issues", []))
                for k in ["psychology_layer", "strategy_layer", "script_layer"]
            ),
        },
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(flywheel_event)
    await db.flush()

    diagnosis_result = DiagnosisResult(
        overall_score=overall_score,
        psychology_layer=report_card.get("psychology_layer", {"score": 0, "issues": []}),
        strategy_layer=report_card.get("strategy_layer", {"score": 0, "issues": []}),
        script_layer=report_card.get("script_layer", {"score": 0, "issues": []}),
        improvement_plan=report_card.get("improvement_plan", []),
    )

    return DiagnosisAnalyzeResponse(
        report_id=report.id,
        result=diagnosis_result,
    )


@router.get("/reports", response_model=DiagnosisReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count_result = await db.execute(
        select(func.count(DiagnosisReport.id)).where(
            DiagnosisReport.enterprise_id == user.enterprise_id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(DiagnosisReport)
        .where(DiagnosisReport.enterprise_id == user.enterprise_id)
        .order_by(DiagnosisReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    reports = result.scalars().all()

    return DiagnosisReportListResponse(
        items=[DiagnosisReportResponse.model_validate(r) for r in reports],
        total=total,
    )


@router.get("/reports/{report_id}", response_model=DiagnosisReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DiagnosisReport).where(
            DiagnosisReport.id == uuid.UUID(report_id),
            DiagnosisReport.enterprise_id == user.enterprise_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "诊断报告不存在", "message_en": "Diagnosis report not found"})

    return DiagnosisReportResponse.model_validate(report)


@router.get("/stats")
async def get_diagnosis_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """诊断统计"""
    eid = user.enterprise_id

    total = (await db.execute(
        select(func.count(DiagnosisReport.id)).where(DiagnosisReport.enterprise_id == eid)
    )).scalar() or 0

    avg_score = (await db.execute(
        select(func.avg(DiagnosisReport.overall_score)).where(DiagnosisReport.enterprise_id == eid)
    )).scalar()

    return {
        "total_reports": total,
        "avg_score": round(float(avg_score), 1) if avg_score else 0,
    }
