"""数据飞轮 API [v2.0 重构]

飞轮闭环：诊断→感知痛点→更新痛点库→触发联动→记录事件
所有变更都持久化到数据库，形成可追溯的事件时间线。
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.diagnosis import DiagnosisReport
from app.models.flywheel import FlywheelEvent, StrategyCascade
from app.models.memory import PainPoint, Product, ServiceItem, product_pain_points
from app.models.script import Script, script_pain_points
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.skills.flywheel_sense import FlywheelSenseSkill

router = APIRouter(prefix="/api/v1/flywheel", tags=["flywheel"])


def _pain_point_to_trend(p: PainPoint, related_product_count: int, related_script_count: int) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "mention_count_current": p.mention_count_current or 0,
        "mention_count_previous": p.mention_count_previous or 0,
        "change_rate": p.change_rate or 0.0,
        "trend_label": p.trend_label or "stable",
        "evidence_keywords": p.evidence_keywords or [],
        "related_product_count": related_product_count,
        "related_script_count": related_script_count,
    }


@router.get("/dashboard")
async def get_flywheel_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """飞轮看板：4个齿轮的数据变化全景 + 飞轮健康度"""
    enterprise_id = user.enterprise_id
    eid = enterprise_id

    pp_result = await db.execute(
        select(PainPoint)
        .where(PainPoint.enterprise_id == eid)
        .order_by(PainPoint.change_rate.desc().nullslast())
    )
    pain_points = pp_result.scalars().all()

    pain_point_trends = []
    for p in pain_points:
        pr_count = await db.execute(
            select(func.count()).select_from(product_pain_points).where(
                product_pain_points.c.pain_point_id == p.id
            )
        )
        sc_count = await db.execute(
            select(func.count()).select_from(script_pain_points).where(
                script_pain_points.c.pain_point_id == p.id
            )
        )
        pain_point_trends.append(_pain_point_to_trend(p, pr_count.scalar() or 0, sc_count.scalar() or 0))

    prod_result = await db.execute(
        select(Product)
        .options(selectinload(Product.pain_points))
        .where(Product.enterprise_id == eid)
        .order_by(Product.dynamic_priority.asc())
    )
    products = prod_result.scalars().all()
    product_strategies = [
        {
            "id": str(p.id),
            "name": p.name,
            "dynamic_priority": p.dynamic_priority or "P1",
            "recommendation_hit_rate": p.recommendation_hit_rate or 0.0,
            "priority_reason": p.priority_reason,
            "related_pain_point_trends": [pp.name for pp in p.pain_points],
        }
        for p in products
    ]

    svc_result = await db.execute(
        select(ServiceItem).where(ServiceItem.enterprise_id == eid)
    )
    services = svc_result.scalars().all()
    service_strategies = [
        {
            "id": str(s.id),
            "name": s.name,
            "usage_count": s.usage_count or 0,
            "effectiveness": s.effectiveness or 0.0,
            "has_scenario_gap": s.has_scenario_gap or False,
            "gap_description": s.gap_description,
        }
        for s in services
    ]

    script_result = await db.execute(
        select(Script).where(Script.enterprise_id == eid)
    )
    scripts = script_result.scalars().all()
    script_lifecycles = [
        {
            "id": str(s.id),
            "title": s.title,
            "lifecycle_stage": s.lifecycle_stage or "active",
            "effectiveness_score": s.effectiveness_score or 0.0,
            "effectiveness_trend": s.effectiveness_trend or "stable",
            "usage_contact_rate": s.usage_contact_rate or 0.0,
            "source_type": s.source_type or "manual",
        }
        for s in scripts
    ]

    cascade_result = await db.execute(
        select(StrategyCascade)
        .where(StrategyCascade.enterprise_id == eid, StrategyCascade.status == "pending")
    )
    cascades = cascade_result.scalars().all()
    pending_cascades = [
        {
            "id": str(c.id),
            "flywheel_event_id": str(c.flywheel_event_id) if c.flywheel_event_id else None,
            "trigger_signal": c.trigger_signal,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cascades
    ]

    pain_point_count = len(pain_points)
    new_pain_points_pending = sum(1 for p in pain_points if (p.trend_label or "") == "new")
    scenario_gaps = sum(1 for s in services if s.has_scenario_gap)
    scripts_declining = sum(1 for s in scripts if (s.lifecycle_stage or "") == "declining")
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def _is_recent(created):
        if created is None:
            return False
        dt = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
        return dt >= week_ago

    scripts_added = sum(1 for s in scripts if _is_recent(s.created_at))

    recent_events_result = await db.execute(
        select(FlywheelEvent)
        .where(FlywheelEvent.enterprise_id == eid)
        .order_by(FlywheelEvent.created_at.desc())
        .limit(10)
    )
    recent_events = recent_events_result.scalars().all()

    total_events = (await db.execute(
        select(func.count(FlywheelEvent.id)).where(FlywheelEvent.enterprise_id == eid)
    )).scalar() or 0

    total_diagnosis = (await db.execute(
        select(func.count(DiagnosisReport.id)).where(DiagnosisReport.enterprise_id == eid)
    )).scalar() or 0

    health = _calculate_flywheel_health(
        pain_point_count, len(products), len(services), len(scripts),
        total_events, total_diagnosis, new_pain_points_pending, scenario_gaps,
    )

    return {
        "pain_point_trends": pain_point_trends,
        "product_strategies": product_strategies,
        "service_strategies": service_strategies,
        "script_lifecycles": script_lifecycles,
        "pending_cascades": pending_cascades,
        "new_pain_points_pending": new_pain_points_pending,
        "scenario_gaps": scenario_gaps,
        "scripts_declining": scripts_declining,
        "scripts_added_this_week": scripts_added,
        "flywheel_health": health,
        "recent_events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "trigger_type": e.trigger_type,
                "trigger_data": e.trigger_data,
                "result_summary": e.result_summary,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent_events
        ],
        "total_events": total_events,
        "total_diagnosis": total_diagnosis,
    }


@router.get("/pain-points/trends")
async def get_pain_point_trends(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取痛点趋势数据"""
    eid = user.enterprise_id
    result = await db.execute(
        select(PainPoint)
        .where(PainPoint.enterprise_id == eid)
        .order_by(PainPoint.change_rate.desc().nullslast())
    )
    pain_points = result.scalars().all()
    trends = []
    for p in pain_points:
        pr_count = await db.execute(
            select(func.count()).select_from(product_pain_points).where(
                product_pain_points.c.pain_point_id == p.id
            )
        )
        sc_count = await db.execute(
            select(func.count()).select_from(script_pain_points).where(
                script_pain_points.c.pain_point_id == p.id
            )
        )
        trends.append(_pain_point_to_trend(p, pr_count.scalar() or 0, sc_count.scalar() or 0))
    return {"period_days": days, "trends": trends}


@router.get("/products/priorities")
async def get_product_priorities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取产品动态优先级"""
    result = await db.execute(
        select(Product)
        .where(Product.enterprise_id == user.enterprise_id)
        .order_by(Product.dynamic_priority.asc())
    )
    products = result.scalars().all()
    return {
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "dynamic_priority": p.dynamic_priority or "P1",
                "priority_reason": p.priority_reason,
            }
            for p in products
        ]
    }


@router.get("/products/coverage-matrix")
async def get_coverage_matrix(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取产品覆盖率矩阵"""
    eid = user.enterprise_id
    pp_result = await db.execute(select(PainPoint).where(PainPoint.enterprise_id == eid))
    prod_result = await db.execute(
        select(Product)
        .options(selectinload(Product.pain_points))
        .where(Product.enterprise_id == eid)
    )
    pain_points = pp_result.scalars().all()
    products = prod_result.scalars().all()
    matrix = []
    gaps = []
    for pp in pain_points:
        row = {"pain_point": pp.name, "coverage": {}}
        has_cover = False
        for pr in products:
            related = any(p.id == pp.id for p in pr.pain_points)
            row["coverage"][pr.name] = related
            if related:
                has_cover = True
        matrix.append(row)
        if not has_cover:
            gaps.append(pp.name)
    return {"matrix": matrix, "gaps": gaps}


@router.get("/services/effectiveness")
async def get_service_effectiveness(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取服务场景效果"""
    result = await db.execute(
        select(ServiceItem).where(ServiceItem.enterprise_id == user.enterprise_id)
    )
    services = result.scalars().all()
    scenario_gaps = [s for s in services if s.has_scenario_gap]
    return {
        "services": [
            {
                "id": str(s.id),
                "name": s.name,
                "usage_count": s.usage_count or 0,
                "effectiveness": s.effectiveness or 0.0,
                "has_scenario_gap": s.has_scenario_gap or False,
                "gap_description": s.gap_description,
            }
            for s in services
        ],
        "scenario_gaps": [{"name": s.name, "gap_description": s.gap_description} for s in scenario_gaps],
    }


@router.get("/scripts/lifecycle")
async def get_script_lifecycle(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取话术生命周期分布"""
    result = await db.execute(
        select(Script.lifecycle_stage, func.count(Script.id))
        .where(Script.enterprise_id == user.enterprise_id)
        .group_by(Script.lifecycle_stage)
    )
    rows = result.all()
    stages = {"draft": 0, "review": 0, "active": 0, "declining": 0, "archived": 0}
    for stage, cnt in rows:
        stages[stage or "active"] = cnt
    return stages


@router.get("/cascades")
async def list_cascades(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取策略联动方案列表"""
    q = select(StrategyCascade).where(StrategyCascade.enterprise_id == user.enterprise_id)
    if status:
        q = q.where(StrategyCascade.status == status)
    result = await db.execute(q.order_by(StrategyCascade.created_at.desc()))
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "flywheel_event_id": str(c.flywheel_event_id) if c.flywheel_event_id else None,
                "trigger_signal": c.trigger_signal,
                "pain_point_actions": c.pain_point_actions,
                "product_actions": c.product_actions,
                "service_actions": c.service_actions,
                "script_actions": c.script_actions,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in items
        ],
        "total": len(items),
    }


@router.post("/cascades/{cascade_id}/review")
async def review_cascade(
    cascade_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """审核策略联动方案"""
    if status not in ("adopted", "rejected"):
        raise HTTPException(status_code=400, detail={"message": "无效状态", "message_en": "Invalid status"})
    result = await db.execute(
        select(StrategyCascade).where(
            StrategyCascade.id == uuid.UUID(cascade_id),
            StrategyCascade.enterprise_id == user.enterprise_id,
        )
    )
    cascade = result.scalar_one_or_none()
    if not cascade:
        raise HTTPException(status_code=404, detail={"message": "联动方案未找到", "message_en": "Cascade not found"})

    cascade.status = status
    cascade.reviewed_by = user.id
    cascade.reviewed_at = datetime.now(timezone.utc)

    event = FlywheelEvent(
        enterprise_id=user.enterprise_id,
        event_type="cascade_reviewed",
        trigger_type="user_action",
        trigger_data={
            "cascade_id": cascade_id,
            "decision": status,
        },
        result_summary={"cascade_id": cascade_id, "status": status},
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()

    return {"cascade_id": cascade_id, "status": status}


@router.post("/sense")
async def trigger_sense(
    time_window_days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动触发痛点感知扫描 - 持久化结果到数据库"""
    settings = get_settings()
    provider = ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )
    skill = FlywheelSenseSkill(provider)

    since = datetime.now(timezone.utc) - timedelta(days=time_window_days)
    diag_result = await db.execute(
        select(DiagnosisReport)
        .where(
            DiagnosisReport.enterprise_id == user.enterprise_id,
            DiagnosisReport.created_at >= since,
        )
    )
    reports = diag_result.scalars().all()
    diagnosis_data = {"reports_count": len(reports), "results": [r.result for r in reports]}

    pp_result = await db.execute(
        select(PainPoint).where(PainPoint.enterprise_id == user.enterprise_id)
    )
    pain_points = pp_result.scalars().all()
    pain_points_map = {p.name: p for p in pain_points}
    pain_points_current = [
        {
            "id": str(p.id),
            "name": p.name,
            "mention_count_current": p.mention_count_current,
            "change_rate": p.change_rate,
        }
        for p in pain_points
    ]

    context = {
        "diagnosis_data": diagnosis_data,
        "pain_points_current": pain_points_current,
        "enterprise_memory": "",
        "time_window": f"{time_window_days}天",
    }

    result = await skill.execute("请分析痛点趋势变化", context)

    updates_applied = 0
    new_pain_points_created = 0
    should_cascade = False

    for card in result.get("cards", []):
        if card.get("type") != "flywheel-sense":
            continue
        data = card.get("data", {})

        for update in data.get("pain_point_updates", []):
            pp_name = update.get("name", "")
            pp = pain_points_map.get(pp_name)
            if pp:
                pp.mention_count_previous = pp.mention_count_current
                pp.mention_count_current = update.get("new_mention_count", pp.mention_count_current)
                pp.change_rate = update.get("change_rate", pp.change_rate)
                pp.trend_label = update.get("trend", pp.trend_label)
                if update.get("evidence_keywords"):
                    pp.evidence_keywords = update["evidence_keywords"]
                pp.last_trend_update = datetime.now(timezone.utc)
                updates_applied += 1
            else:
                new_pp = PainPoint(
                    enterprise_id=user.enterprise_id,
                    name=pp_name,
                    description=f"由飞轮感知自动发现",
                    mention_count_current=update.get("new_mention_count", 1),
                    change_rate=update.get("change_rate", 1.0),
                    trend_label="new",
                    evidence_keywords=update.get("evidence_keywords", []),
                    source_type="flywheel_sense",
                    last_trend_update=datetime.now(timezone.utc),
                )
                db.add(new_pp)
                new_pain_points_created += 1

        if data.get("should_trigger_cascade"):
            should_cascade = True

    flywheel_event = FlywheelEvent(
        enterprise_id=user.enterprise_id,
        event_type="pain_point_sense",
        trigger_type="manual",
        trigger_data={
            "time_window_days": time_window_days,
            "reports_analyzed": len(reports),
        },
        result_summary={
            "updates_applied": updates_applied,
            "new_pain_points": new_pain_points_created,
            "should_cascade": should_cascade,
        },
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(flywheel_event)
    await db.flush()

    cascade_id = None
    if should_cascade:
        cascade = StrategyCascade(
            enterprise_id=user.enterprise_id,
            flywheel_event_id=flywheel_event.id,
            trigger_signal={
                "type": "pain_point_shift",
                "updates_applied": updates_applied,
                "new_pain_points": new_pain_points_created,
            },
            pain_point_actions={"review_new_pain_points": new_pain_points_created},
            product_actions={"check_coverage": True},
            service_actions={"check_gaps": True},
            script_actions={"generate_for_new_pain_points": new_pain_points_created > 0},
            status="pending",
        )
        db.add(cascade)
        await db.flush()
        cascade_id = str(cascade.id)

    return {
        "status": "completed",
        "time_window_days": time_window_days,
        "reports_analyzed": len(reports),
        "updates_applied": updates_applied,
        "new_pain_points_created": new_pain_points_created,
        "should_cascade": should_cascade,
        "cascade_id": cascade_id,
        "event_id": str(flywheel_event.id),
        "message": result.get("text", "痛点感知扫描完成"),
    }


@router.get("/events")
async def list_flywheel_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取飞轮事件日志"""
    q = select(FlywheelEvent).where(FlywheelEvent.enterprise_id == user.enterprise_id)
    if event_type:
        q = q.where(FlywheelEvent.event_type == event_type)

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0

    result = await db.execute(
        q.order_by(FlywheelEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = result.scalars().all()

    return {
        "items": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "trigger_type": e.trigger_type,
                "trigger_data": e.trigger_data,
                "result_summary": e.result_summary,
                "status": e.status,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "total": total,
    }


@router.get("/health")
async def get_flywheel_health(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取飞轮健康度"""
    eid = user.enterprise_id

    pp_count = (await db.execute(
        select(func.count(PainPoint.id)).where(PainPoint.enterprise_id == eid)
    )).scalar() or 0
    prod_count = (await db.execute(
        select(func.count(Product.id)).where(Product.enterprise_id == eid)
    )).scalar() or 0
    svc_count = (await db.execute(
        select(func.count(ServiceItem.id)).where(ServiceItem.enterprise_id == eid)
    )).scalar() or 0
    script_count = (await db.execute(
        select(func.count(Script.id)).where(Script.enterprise_id == eid)
    )).scalar() or 0
    event_count = (await db.execute(
        select(func.count(FlywheelEvent.id)).where(FlywheelEvent.enterprise_id == eid)
    )).scalar() or 0
    diag_count = (await db.execute(
        select(func.count(DiagnosisReport.id)).where(DiagnosisReport.enterprise_id == eid)
    )).scalar() or 0
    new_pp = (await db.execute(
        select(func.count(PainPoint.id)).where(
            PainPoint.enterprise_id == eid, PainPoint.trend_label == "new"
        )
    )).scalar() or 0
    gaps = (await db.execute(
        select(func.count(ServiceItem.id)).where(
            ServiceItem.enterprise_id == eid, ServiceItem.has_scenario_gap == True
        )
    )).scalar() or 0

    return _calculate_flywheel_health(
        pp_count, prod_count, svc_count, script_count,
        event_count, diag_count, new_pp, gaps,
    )


def _calculate_flywheel_health(
    pp_count: int, prod_count: int, svc_count: int, script_count: int,
    event_count: int, diag_count: int, new_pp: int, gaps: int,
) -> dict:
    """计算飞轮健康度指标"""
    gear_scores = []

    gear1 = min(100, pp_count * 20) if pp_count > 0 else 0
    gear_scores.append(gear1)

    gear2 = min(100, prod_count * 25) if prod_count > 0 else 0
    gear_scores.append(gear2)

    gear3 = min(100, svc_count * 25)
    if gaps > 0:
        gear3 = max(0, gear3 - gaps * 15)
    gear_scores.append(gear3)

    gear4 = min(100, script_count * 10)
    gear_scores.append(gear4)

    data_flow = min(100, diag_count * 5 + event_count * 10)
    overall = int(sum(gear_scores) / 4 * 0.6 + data_flow * 0.4) if gear_scores else 0

    if overall >= 80:
        status = "healthy"
        label = "飞轮运转良好"
    elif overall >= 50:
        status = "warming"
        label = "飞轮正在热身"
    elif overall > 0:
        status = "cold"
        label = "飞轮刚启动"
    else:
        status = "inactive"
        label = "飞轮未启动"

    bottleneck = None
    min_gear = min(enumerate(gear_scores), key=lambda x: x[1])
    gear_names = ["痛点感知", "产品策略", "服务策略", "话术策略"]
    if min_gear[1] < 50:
        bottleneck = {
            "gear": gear_names[min_gear[0]],
            "score": min_gear[1],
            "suggestion": f"请完善{gear_names[min_gear[0]]}相关数据，提升飞轮效率",
        }

    return {
        "overall_score": overall,
        "status": status,
        "label": label,
        "gear_scores": {
            "pain_points": gear1,
            "products": gear2,
            "services": gear3,
            "scripts": gear4,
        },
        "data_flow_score": data_flow,
        "bottleneck": bottleneck,
        "stats": {
            "pain_points": pp_count,
            "products": prod_count,
            "services": svc_count,
            "scripts": script_count,
            "events": event_count,
            "diagnoses": diag_count,
        },
    }
