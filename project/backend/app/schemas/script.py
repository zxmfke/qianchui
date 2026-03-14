import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScriptCreate(BaseModel):
    title: str = Field(max_length=300)
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    psychology_layer: str | None = None
    strategy_layer: str | None = None
    content: str
    variants: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=1, ge=1, le=3)
    target_role: str = "all"
    pain_point_ids: list[uuid.UUID] = Field(default_factory=list)
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    service_ids: list[uuid.UUID] = Field(default_factory=list)


class ScriptUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    psychology_layer: str | None = None
    strategy_layer: str | None = None
    content: str | None = None
    variants: list[str] | None = None
    difficulty: int | None = Field(default=None, ge=1, le=3)
    target_role: str | None = None
    status: str | None = None
    pain_point_ids: list[uuid.UUID] | None = None
    product_ids: list[uuid.UUID] | None = None
    service_ids: list[uuid.UUID] | None = None


class ScriptResponse(BaseModel):
    id: uuid.UUID
    enterprise_id: uuid.UUID
    title: str
    category: str | None
    tags: list[str]
    status: str
    version: int
    psychology_layer: str | None
    strategy_layer: str | None
    content: str
    variants: list[str]
    difficulty: int
    target_role: str
    usage_count: int
    conversion_rate: float
    user_rating: float
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptListResponse(BaseModel):
    items: list[ScriptResponse]
    total: int
    page: int
    page_size: int


class ScriptUsageCreate(BaseModel):
    context: dict = Field(default_factory=dict)


class CategoryResponse(BaseModel):
    name: str
    count: int
