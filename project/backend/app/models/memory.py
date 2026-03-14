import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

product_pain_points = Table(
    "product_pain_points",
    Base.metadata,
    Column("product_id", Uuid, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("pain_point_id", Uuid, ForeignKey("pain_points.id", ondelete="CASCADE"), primary_key=True),
)

service_products = Table(
    "service_products",
    Base.metadata,
    Column("service_id", Uuid, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Uuid, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class PainPoint(TimestampMixin, Base):
    __tablename__ = "pain_points"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # --- 飞轮字段 [v1.4] ---
    mention_count_current: Mapped[int] = mapped_column(Integer, default=0)
    mention_count_previous: Mapped[int] = mapped_column(Integer, default=0)
    change_rate: Mapped[float] = mapped_column(Float, default=0.0)
    trend_label: Mapped[str] = mapped_column(String(20), default="stable")
    trend_history: Mapped[list] = mapped_column(JSON, default=list)
    evidence_keywords: Mapped[list] = mapped_column(JSON, default=list)
    last_trend_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[str] = mapped_column(String(20), default="manual")

    enterprise = relationship("Enterprise", back_populates="pain_points")
    products = relationship("Product", secondary=product_pain_points, back_populates="pain_points", lazy="selectin")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # --- 飞轮字段 [v1.4] ---
    dynamic_priority: Mapped[str] = mapped_column(String(5), default="P1")
    recommendation_count: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_hit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    priority_reason: Mapped[str | None] = mapped_column(Text)
    last_priority_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enterprise = relationship("Enterprise", back_populates="products")
    pain_points = relationship("PainPoint", secondary=product_pain_points, back_populates="products", lazy="selectin")
    services = relationship("ServiceItem", secondary=service_products, back_populates="products", lazy="selectin")


class ServiceItem(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # --- 飞轮字段 [v1.4] ---
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    effectiveness: Mapped[float] = mapped_column(Float, default=0.0)
    has_scenario_gap: Mapped[bool] = mapped_column(default=False)
    gap_description: Mapped[str | None] = mapped_column(Text)
    last_effectiveness_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enterprise = relationship("Enterprise", back_populates="services")
    products = relationship("Product", secondary=service_products, back_populates="services", lazy="selectin")
