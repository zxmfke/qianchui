import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TrainingRecord(TimestampMixin, Base):
    __tablename__ = "training_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("enterprises.id"), nullable=False
    )
    script_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scripts.id")
    )
    question: Mapped[dict] = mapped_column(JSON, nullable=False)
    user_answer: Mapped[str] = mapped_column(String(10), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(10), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    explanation: Mapped[dict | None] = mapped_column(JSON)

    user = relationship("User")
    script = relationship("Script")
