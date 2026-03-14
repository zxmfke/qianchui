"""话术优化闭环系统数据模型 [v1.1 新增]

包含：优化任务、优化策略、对话标注、AB测试、行业评分配置
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class OptimizationTask(TimestampMixin, Base):
    __tablename__ = "optimization_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    diagnosis_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("diagnosis_reports.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    classification: Mapped[dict] = mapped_column(JSON, default=dict)
    score_result: Mapped[dict] = mapped_column(JSON, default=dict)
    root_causes: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )

    strategies = relationship("OptimizationStrategy", back_populates="task", cascade="all, delete-orphan")
    diagnosis_report = relationship("DiagnosisReport")


class OptimizationStrategy(Base):
    __tablename__ = "optimization_strategies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("optimization_tasks.id"), nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_type: Mapped[str] = mapped_column(String(20), nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    current_script: Mapped[str | None] = mapped_column(Text)
    suggested_script: Mapped[str | None] = mapped_column(Text)
    expected_impact: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task = relationship("OptimizationTask", back_populates="strategies")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    diagnosis_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("diagnosis_reports.id"), nullable=True
    )
    conversation_text: Mapped[str] = mapped_column(Text, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    strategy_type: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    extracted_script_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scripts.id"), nullable=True
    )
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ABTest(TimestampMixin, Base):
    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("optimization_tasks.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    confidence_threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=0.95)
    conclusion: Mapped[str | None] = mapped_column(String(20))
    conclusion_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )

    variants = relationship("ABTestVariant", back_populates="test", cascade="all, delete-orphan")


class ABTestVariant(Base):
    __tablename__ = "ab_test_variants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ab_tests.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_control: Mapped[bool] = mapped_column(Boolean, default=False)
    script_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    traffic_ratio: Mapped[float] = mapped_column(Numeric(3, 2), default=0.50)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    test = relationship("ABTest", back_populates="variants")
    metrics = relationship("ABTestMetric", back_populates="variant", cascade="all, delete-orphan")


class ABTestMetric(Base):
    __tablename__ = "ab_test_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ab_test_variants.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    dialog_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    avg_depth: Mapped[float] = mapped_column(Numeric(4, 1), default=0)
    avg_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    variant = relationship("ABTestVariant", back_populates="metrics")


class IndustryProfile(TimestampMixin, Base):
    __tablename__ = "industry_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension_weights: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        default=lambda: {"A1": 20, "A2": 15, "B1": 15, "B2": 15, "B3": 10, "C1": 15, "C2": 10},
    )
    contact_ideal_position: Mapped[float] = mapped_column(Numeric(3, 2), default=0.35)
    keywords: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
