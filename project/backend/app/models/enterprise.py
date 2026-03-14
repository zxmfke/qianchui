import uuid

from sqlalchemy import Boolean, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Enterprise(TimestampMixin, Base):
    __tablename__ = "enterprises"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users = relationship("User", back_populates="enterprise", lazy="selectin")
    scripts = relationship("Script", back_populates="enterprise", lazy="selectin")
    pain_points = relationship("PainPoint", back_populates="enterprise", lazy="selectin")
    products = relationship("Product", back_populates="enterprise", lazy="selectin")
    services = relationship("ServiceItem", back_populates="enterprise", lazy="selectin")
