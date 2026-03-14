"""数据飞轮 Pydantic schemas [v1.4 重构]

飞轮数据主要来自现有表（pain_points/products/services/scripts）的飞轮字段，
本文件定义的是飞轮看板聚合视图和联动方案的 API 模型。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- 痛点趋势（聚合自 pain_points 表的飞轮字段） ---

class PainPointTrendView(BaseModel):
    """痛点趋势视图，聚合自 pain_points 表"""
    id: UUID
    name: str
    mention_count_current: int = 0
    mention_count_previous: int = 0
    change_rate: float = 0.0
    trend_label: str = "stable"
    trend_history: list = []
    evidence_keywords: list[str] = []
    source_type: str = "manual"
    related_product_count: int = 0
    related_script_count: int = 0

    class Config:
        from_attributes = True


# --- 产品策略视图（聚合自 products 表的飞轮字段） ---

class ProductStrategyView(BaseModel):
    """产品策略视图，聚合自 products 表"""
    id: UUID
    name: str
    dynamic_priority: str = "P1"
    recommendation_count: int = 0
    recommendation_hit_rate: float = 0.0
    priority_reason: str | None = None
    related_pain_point_trends: list[str] = []

    class Config:
        from_attributes = True


# --- 服务策略视图（聚合自 services 表的飞轮字段） ---

class ServiceStrategyView(BaseModel):
    """服务策略视图，聚合自 services 表"""
    id: UUID
    name: str
    usage_count: int = 0
    effectiveness: float = 0.0
    has_scenario_gap: bool = False
    gap_description: str | None = None

    class Config:
        from_attributes = True


# --- 话术生命周期视图（聚合自 scripts 表的飞轮字段） ---

class ScriptLifecycleView(BaseModel):
    """话术生命周期视图，聚合自 scripts 表"""
    id: UUID
    title: str
    lifecycle_stage: str = "active"
    effectiveness_score: float = 0.0
    effectiveness_trend: str = "stable"
    usage_contact_rate: float = 0.0
    source_type: str = "manual"

    class Config:
        from_attributes = True


# --- 策略联动方案 ---

class StrategyCascadeCreate(BaseModel):
    trigger_signal: dict
    pain_point_actions: dict = {}
    product_actions: dict = {}
    service_actions: dict = {}
    script_actions: dict = {}


class StrategyCascadeResponse(BaseModel):
    id: UUID
    enterprise_id: UUID
    flywheel_event_id: UUID | None = None
    trigger_signal: dict
    pain_point_actions: dict = {}
    product_actions: dict = {}
    service_actions: dict = {}
    script_actions: dict = {}
    status: str = "pending"
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    executed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CascadeReviewRequest(BaseModel):
    status: str = Field(..., pattern="^(adopted|rejected)$")


# --- 飞轮看板（聚合视图） ---

class FlywheelDashboardResponse(BaseModel):
    """飞轮看板：4个齿轮的数据变化全景"""
    pain_point_trends: list[PainPointTrendView] = []
    product_strategies: list[ProductStrategyView] = []
    service_strategies: list[ServiceStrategyView] = []
    script_lifecycles: list[ScriptLifecycleView] = []
    pending_cascades: list[StrategyCascadeResponse] = []
    new_pain_points_pending: int = 0
    scenario_gaps: int = 0
    scripts_declining: int = 0
    scripts_added_this_week: int = 0
