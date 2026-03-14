from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import (
    OverviewResponse,
    ScriptRankingResponse,
    TeamStatsResponse,
    TrendsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    data = await service.get_overview(str(user.enterprise_id))
    return OverviewResponse(**data)


@router.get("/script-ranking", response_model=ScriptRankingResponse)
async def get_script_ranking(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    data = await service.get_script_ranking(str(user.enterprise_id), limit=limit)
    return ScriptRankingResponse(**data)


@router.get("/team-stats", response_model=TeamStatsResponse)
async def get_team_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    data = await service.get_team_stats(str(user.enterprise_id))
    return TeamStatsResponse(**data)


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    data = await service.get_trends(str(user.enterprise_id), days=days)
    return TrendsResponse(**data)
