import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class CardData(BaseModel):
    type: str
    data: dict


class SuggestedAction(BaseModel):
    label: str
    action: str
    params: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    skill_used: str | None
    cards: list[dict]
    suggested_actions: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    message_count: int = 0
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
