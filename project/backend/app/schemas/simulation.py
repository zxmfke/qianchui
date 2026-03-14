import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SimulationCreate(BaseModel):
    scenario: str = Field(min_length=1)
    customer_type: str = "friendly"
    difficulty: int = Field(default=1, ge=1, le=3)


class SimulationMessageSend(BaseModel):
    content: str = Field(min_length=1)


class SimulationHint(BaseModel):
    customer_psychology: str
    suggested_strategy: str


class SimulationMessageResponse(BaseModel):
    ai_response: str
    hint: SimulationHint | None = None


class ScoreDimension(BaseModel):
    dimension: str
    score: int
    comment: str


class SimulationCompleteResponse(BaseModel):
    overall_score: int
    dimensions: list[ScoreDimension]
    improvement_suggestions: list[str]
    summary: str


class SimulationSessionResponse(BaseModel):
    id: uuid.UUID
    scenario: str
    customer_type: str
    difficulty: int
    status: str
    score: dict | None
    messages: list[dict]
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class SimulationListResponse(BaseModel):
    items: list[SimulationSessionResponse]
    total: int
