"""话术优化闭环 API [v2.0 重构]

打通 诊断→优化任务→策略生成→策略采纳 的完整数据流。
每个优化任务关联一份诊断报告，策略落库可追溯。
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.diagnosis import DiagnosisReport
from app.models.flywheel import FlywheelEvent
from app.models.optimization import OptimizationStrategy, OptimizationTask
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


# ── Schemas ──────────────────────────────────────────────────────────

class CreateTaskFromDiagnosis(BaseModel):
    diagnosis_report_id: str
    title: str | None = None


class CreateTaskFromText(BaseModel):
    conversation_text: str = Field(..., min_length=10)
    title: str | None = None


class StrategyStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(adopted|rejected|modified)$")


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/tasks")
async def create_optimization_task(
    body: CreateTaskFromText,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从对话文本创建优化任务：先诊断，再建任务"""
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

    root_causes = []
    for layer_key in ["psychology_layer", "strategy_layer", "script_layer"]:
        layer = report_card.get(layer_key, {})
        for issue in layer.get("issues", []):
            root_causes.append({
                "layer": layer_key,
                "issue": issue.get("issue", ""),
                "turn": issue.get("turn"),
            })

    task = OptimizationTask(
        enterprise_id=user.enterprise_id,
        diagnosis_report_id=report.id,
        title=body.title or f"优化任务 - 评分{overall_score}分",
        status="diagnosed",
        priority="P0" if overall_score < 60 else "P1" if overall_score < 75 else "P2",
        classification={
            "overall_score": overall_score,
            "psychology_score": report_card.get("psychology_layer", {}).get("score", 0),
            "strategy_score": report_card.get("strategy_layer", {}).get("score", 0),
            "script_score": report_card.get("script_layer", {}).get("score", 0),
        },
        score_result=report_card,
        root_causes=root_causes,
        created_by=user.id,
    )
    db.add(task)
    await db.flush()

    return {
        "task_id": str(task.id),
        "diagnosis_report_id": str(report.id),
        "status": task.status,
        "priority": task.priority,
        "overall_score": overall_score,
        "root_causes": root_causes,
        "classification": task.classification,
    }


@router.post("/tasks/from-diagnosis")
async def create_task_from_diagnosis(
    body: CreateTaskFromDiagnosis,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从已有诊断报告创建优化任务"""
    result = await db.execute(
        select(DiagnosisReport).where(
            DiagnosisReport.id == uuid.UUID(body.diagnosis_report_id),
            DiagnosisReport.enterprise_id == user.enterprise_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail={"message": "诊断报告不存在", "message_en": "Report not found"})

    report_card = report.result or {}
    overall_score = report.overall_score or 0

    root_causes = []
    for layer_key in ["psychology_layer", "strategy_layer", "script_layer"]:
        layer = report_card.get(layer_key, {})
        for issue in layer.get("issues", []):
            root_causes.append({
                "layer": layer_key,
                "issue": issue.get("issue", ""),
                "turn": issue.get("turn"),
            })

    task = OptimizationTask(
        enterprise_id=user.enterprise_id,
        diagnosis_report_id=report.id,
        title=body.title or f"优化任务 - 评分{overall_score}分",
        status="diagnosed",
        priority="P0" if overall_score < 60 else "P1" if overall_score < 75 else "P2",
        classification={
            "overall_score": overall_score,
            "psychology_score": report_card.get("psychology_layer", {}).get("score", 0),
            "strategy_score": report_card.get("strategy_layer", {}).get("score", 0),
            "script_score": report_card.get("script_layer", {}).get("score", 0),
        },
        score_result=report_card,
        root_causes=root_causes,
        created_by=user.id,
    )
    db.add(task)
    await db.flush()

    return {
        "task_id": str(task.id),
        "diagnosis_report_id": body.diagnosis_report_id,
        "status": task.status,
        "priority": task.priority,
        "overall_score": overall_score,
        "root_causes": root_causes,
    }


@router.get("/tasks")
async def list_optimization_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出优化任务（分页），含策略统计"""
    q = select(OptimizationTask).where(
        OptimizationTask.enterprise_id == user.enterprise_id
    )
    if status:
        q = q.where(OptimizationTask.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        q.options(selectinload(OptimizationTask.strategies))
        .order_by(OptimizationTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tasks = result.scalars().all()

    items = []
    for t in tasks:
        adopted = sum(1 for s in t.strategies if s.status == "adopted")
        items.append({
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "classification": t.classification,
            "root_causes_count": len(t.root_causes) if t.root_causes else 0,
            "strategies_count": len(t.strategies),
            "strategies_adopted": adopted,
            "diagnosis_report_id": str(t.diagnosis_report_id) if t.diagnosis_report_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {"items": items, "total": total}


@router.get("/tasks/{task_id}")
async def get_optimization_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取优化任务详情"""
    result = await db.execute(
        select(OptimizationTask)
        .options(selectinload(OptimizationTask.strategies))
        .where(
            OptimizationTask.id == uuid.UUID(task_id),
            OptimizationTask.enterprise_id == user.enterprise_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"message": "任务不存在", "message_en": "Task not found"})

    strategies = [
        {
            "id": str(s.id),
            "priority": s.priority,
            "problem": s.problem,
            "root_cause_type": s.root_cause_type,
            "solution": s.solution,
            "current_script": s.current_script,
            "suggested_script": s.suggested_script,
            "expected_impact": s.expected_impact,
            "risk_level": s.risk_level,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in task.strategies
    ]

    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "classification": task.classification,
        "score_result": task.score_result,
        "root_causes": task.root_causes,
        "diagnosis_report_id": str(task.diagnosis_report_id) if task.diagnosis_report_id else None,
        "strategies": strategies,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/tasks/{task_id}/strategies")
async def get_strategies(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取任务的优化策略列表"""
    result = await db.execute(
        select(OptimizationTask).where(
            OptimizationTask.id == uuid.UUID(task_id),
            OptimizationTask.enterprise_id == user.enterprise_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"message": "任务不存在", "message_en": "Task not found"})

    strat_result = await db.execute(
        select(OptimizationStrategy)
        .where(OptimizationStrategy.task_id == task.id)
        .order_by(OptimizationStrategy.priority.asc(), OptimizationStrategy.created_at.asc())
    )
    strategies = strat_result.scalars().all()

    return {
        "strategies": [
            {
                "id": str(s.id),
                "priority": s.priority,
                "problem": s.problem,
                "root_cause_type": s.root_cause_type,
                "solution": s.solution,
                "current_script": s.current_script,
                "suggested_script": s.suggested_script,
                "expected_impact": s.expected_impact,
                "risk_level": s.risk_level,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in strategies
        ]
    }


@router.post("/tasks/{task_id}/generate-strategies")
async def generate_strategies(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """基于诊断结果用 LLM 生成优化策略"""
    result = await db.execute(
        select(OptimizationTask)
        .options(selectinload(OptimizationTask.strategies))
        .where(
            OptimizationTask.id == uuid.UUID(task_id),
            OptimizationTask.enterprise_id == user.enterprise_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"message": "任务不存在", "message_en": "Task not found"})

    settings = get_settings()
    provider = ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )

    skill = SkillRegistry().get_skill("script-optimize")
    if not skill:
        from app.skills.script_optimize import ScriptOptimizeSkill
        skill = ScriptOptimizeSkill(provider)

    context = {
        "diagnosis_result": task.score_result,
        "root_causes": task.root_causes,
        "classification": task.classification,
    }

    llm_result = await skill.execute("请根据诊断结果生成优化策略", context)

    strategies_data = []
    for card in llm_result.get("cards", []):
        if card["type"] in ("optimization-strategy", "script-optimization"):
            data = card.get("data", {})
            items = data.get("strategies", data.get("items", [data]))
            if isinstance(items, list):
                strategies_data.extend(items)
            else:
                strategies_data.append(items)

    if not strategies_data:
        strategies_data = _extract_strategies_from_root_causes(task.root_causes, task.score_result)

    created = []
    for idx, sd in enumerate(strategies_data):
        s = OptimizationStrategy(
            task_id=task.id,
            priority=sd.get("priority", "P1" if idx == 0 else "P2"),
            problem=sd.get("problem", sd.get("issue", "待优化问题")),
            root_cause_type=sd.get("root_cause_type", sd.get("type", "script")),
            solution=sd.get("solution", sd.get("suggestion", "")),
            current_script=sd.get("current_script", sd.get("original", "")),
            suggested_script=sd.get("suggested_script", sd.get("suggested", "")),
            expected_impact=sd.get("expected_impact", sd.get("impact", "")),
            risk_level=sd.get("risk_level", "low"),
            status="pending",
        )
        db.add(s)
        created.append(s)

    task.status = "strategies_generated"
    await db.flush()

    flywheel_event = FlywheelEvent(
        enterprise_id=user.enterprise_id,
        event_type="optimization_strategies_generated",
        trigger_type="user_action",
        trigger_data={
            "task_id": str(task.id),
            "strategies_count": len(created),
        },
        result_summary={"strategies_count": len(created)},
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(flywheel_event)
    await db.flush()

    return {
        "strategies": [
            {
                "id": str(s.id),
                "priority": s.priority,
                "problem": s.problem,
                "root_cause_type": s.root_cause_type,
                "solution": s.solution,
                "current_script": s.current_script,
                "suggested_script": s.suggested_script,
                "expected_impact": s.expected_impact,
                "risk_level": s.risk_level,
                "status": s.status,
            }
            for s in created
        ],
        "count": len(created),
    }


@router.put("/strategies/{strategy_id}")
async def update_strategy_status(
    strategy_id: str,
    body: StrategyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新策略状态（采纳/拒绝/修改后采纳）"""
    result = await db.execute(
        select(OptimizationStrategy)
        .join(OptimizationTask)
        .where(
            OptimizationStrategy.id == uuid.UUID(strategy_id),
            OptimizationTask.enterprise_id == user.enterprise_id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail={"message": "策略不存在", "message_en": "Strategy not found"})

    strategy.status = body.status
    if body.status == "adopted":
        strategy.adopted_at = datetime.now(timezone.utc)

    flywheel_event = FlywheelEvent(
        enterprise_id=user.enterprise_id,
        event_type="strategy_status_changed",
        trigger_type="user_action",
        trigger_data={
            "strategy_id": strategy_id,
            "new_status": body.status,
            "problem": strategy.problem,
        },
        result_summary={"status": body.status},
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(flywheel_event)
    await db.flush()

    return {
        "strategy_id": strategy_id,
        "status": body.status,
        "adopted_at": strategy.adopted_at.isoformat() if strategy.adopted_at else None,
    }


@router.get("/stats")
async def get_optimization_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """优化中心统计概览"""
    eid = user.enterprise_id

    total_tasks = (await db.execute(
        select(func.count(OptimizationTask.id)).where(OptimizationTask.enterprise_id == eid)
    )).scalar() or 0

    total_strategies = (await db.execute(
        select(func.count(OptimizationStrategy.id))
        .join(OptimizationTask)
        .where(OptimizationTask.enterprise_id == eid)
    )).scalar() or 0

    adopted_strategies = (await db.execute(
        select(func.count(OptimizationStrategy.id))
        .join(OptimizationTask)
        .where(OptimizationTask.enterprise_id == eid, OptimizationStrategy.status == "adopted")
    )).scalar() or 0

    avg_score = (await db.execute(
        select(func.avg(DiagnosisReport.overall_score)).where(DiagnosisReport.enterprise_id == eid)
    )).scalar()

    return {
        "total_tasks": total_tasks,
        "total_strategies": total_strategies,
        "adopted_strategies": adopted_strategies,
        "adoption_rate": round(adopted_strategies / total_strategies, 2) if total_strategies > 0 else 0,
        "avg_diagnosis_score": round(float(avg_score), 1) if avg_score else 0,
    }


def _extract_strategies_from_root_causes(root_causes: list, score_result: dict) -> list:
    """从根因分析中提取策略（LLM 降级方案）"""
    strategies = []
    for rc in (root_causes or []):
        layer = rc.get("layer", "script_layer")
        issue = rc.get("issue", "")
        if not issue:
            continue

        layer_data = score_result.get(layer, {})
        issues = layer_data.get("issues", [])
        original = ""
        suggested = ""
        for i in issues:
            if i.get("issue") == issue:
                original = i.get("original", "")
                suggested = i.get("suggested", "")
                break

        strategies.append({
            "priority": "P0" if len(strategies) == 0 else "P1",
            "problem": issue,
            "root_cause_type": "config" if "配置" in issue or "节奏" in issue else "script",
            "solution": suggested or f"针对「{issue}」进行话术优化",
            "current_script": original,
            "suggested_script": suggested,
            "expected_impact": "预计提升对话效果",
            "risk_level": "low",
        })

    return strategies[:5]
