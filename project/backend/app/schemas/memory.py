import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PainPointCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class PainPointResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = None
    pain_point_ids: list[uuid.UUID] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    pain_points: list[PainPointResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceItemCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = None
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ServiceItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    products: list[ProductResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeChainNode(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    children: list["KnowledgeChainNode"] = Field(default_factory=list)


class KnowledgeChainResponse(BaseModel):
    pain_points: list[KnowledgeChainNode]
