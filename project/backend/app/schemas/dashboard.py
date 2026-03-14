from datetime import datetime

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_scripts: int
    published_scripts: int
    today_usage_count: int
    total_usage_count: int
    avg_conversion_rate: float
    active_users_today: int
    training_completion_rate: float
    avg_simulation_score: float


class ScriptRankingItem(BaseModel):
    script_id: str
    title: str
    category: str | None
    usage_count: int
    conversion_rate: float
    user_rating: float


class ScriptRankingResponse(BaseModel):
    by_usage: list[ScriptRankingItem]
    by_conversion: list[ScriptRankingItem]


class TeamMemberStats(BaseModel):
    user_id: str
    username: str
    role: str
    scripts_used: int
    training_accuracy: float
    training_completed: int
    simulation_avg_score: float
    simulation_count: int


class TeamStatsResponse(BaseModel):
    members: list[TeamMemberStats]
    total_members: int


class TrendPoint(BaseModel):
    date: str
    value: float


class TrendsResponse(BaseModel):
    usage_trend: list[TrendPoint]
    new_scripts_trend: list[TrendPoint]
    training_trend: list[TrendPoint]
    period: str
