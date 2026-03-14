"""数据飞轮引擎数据模型 [v1.4 重构]

设计变更：飞轮不再有独立的4张表（cycles/trends/metrics），
而是在现有表（pain_points/products/services/scripts）上增加飞轮字段。
本文件仅保留：
- FlywheelEvent: 飞轮事件日志（审计追溯用）
- StrategyCascade: 策略联动方案（人机协作审核用）
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FlywheelEvent(TimestampMixin, Base):
    """飞轮事件日志，记录每次飞轮触发和执行结果"""
    __tablename__ = "flywheel_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(30), default="accumulated")
    trigger_data: Mapped[dict] = mapped_column(JSON, default=dict)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cascades = relationship("StrategyCascade", back_populates="event", cascade="all, delete-orphan")


class StrategyCascade(TimestampMixin, Base):
    """策略联动方案，记录飞轮触发的四层联动调整计划"""
    __tablename__ = "strategy_cascades"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    flywheel_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("flywheel_events.id"), nullable=True
    )
    trigger_signal: Mapped[dict] = mapped_column(JSON, nullable=False)
    pain_point_actions: Mapped[dict] = mapped_column(JSON, default=dict)
    product_actions: Mapped[dict] = mapped_column(JSON, default=dict)
    service_actions: Mapped[dict] = mapped_column(JSON, default=dict)
    script_actions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)

    event = relationship("FlywheelEvent", back_populates="cascades")
