import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

script_pain_points = Table(
    "script_pain_points",
    Base.metadata,
    Column("script_id", Uuid, ForeignKey("scripts.id", ondelete="CASCADE"), primary_key=True),
    Column("pain_point_id", Uuid, ForeignKey("pain_points.id", ondelete="CASCADE"), primary_key=True),
)

script_products = Table(
    "script_products",
    Base.metadata,
    Column("script_id", Uuid, ForeignKey("scripts.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Uuid, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)

script_services = Table(
    "script_services",
    Base.metadata,
    Column("script_id", Uuid, ForeignKey("scripts.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", Uuid, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Script(TimestampMixin, Base):
    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)

    psychology_layer: Mapped[str | None] = mapped_column(Text)
    strategy_layer: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variants: Mapped[list] = mapped_column(JSON, default=list)

    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    target_role: Mapped[str] = mapped_column(String(20), default="all")

    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    user_rating: Mapped[float] = mapped_column(Float, default=0.0)

    # --- 飞轮字段 [v1.4] ---
    lifecycle_stage: Mapped[str] = mapped_column(String(20), default="active")
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)
    effectiveness_trend: Mapped[str] = mapped_column(String(20), default="stable")
    usage_contact_rate: Mapped[float] = mapped_column(Float, default=0.0)
    source_type: Mapped[str] = mapped_column(String(20), default="manual")

    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))

    enterprise = relationship("Enterprise", back_populates="scripts")
    creator = relationship("User", foreign_keys=[created_by])
    pain_points = relationship("PainPoint", secondary=script_pain_points, lazy="selectin")
    products = relationship("Product", secondary=script_products, lazy="selectin")
    services = relationship("ServiceItem", secondary=script_services, lazy="selectin")
    usages = relationship("ScriptUsage", back_populates="script", lazy="selectin")


class ScriptUsage(TimestampMixin, Base):
    __tablename__ = "script_usages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    script_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scripts.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    script = relationship("Script", back_populates="usages")
    user = relationship("User")
