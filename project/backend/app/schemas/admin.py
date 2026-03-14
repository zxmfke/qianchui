import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── System Overview ──────────────────────────────────────────────────

class SystemOverview(BaseModel):
    total_enterprises: int
    active_enterprises: int
    total_users: int
    active_users: int
    total_scripts: int
    total_conversations: int
    total_messages: int
    total_training_records: int
    total_simulations: int
    total_diagnosis_reports: int
    total_channel_materials: int


class DailyStats(BaseModel):
    date: str
    new_enterprises: int
    new_users: int
    new_scripts: int
    new_conversations: int


class SystemTrend(BaseModel):
    daily_stats: list[DailyStats]


# ── Enterprise Management ───────────────────────────────────────────

class EnterpriseListItem(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    is_active: bool
    user_count: int
    script_count: int
    conversation_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EnterpriseStats(BaseModel):
    user_count: int
    script_count: int
    conversation_count: int
    training_count: int
    simulation_count: int
    diagnosis_count: int
    channel_material_count: int
    pain_point_count: int
    product_count: int
    service_count: int


class EnterpriseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = None
    is_active: bool = True


class EnterpriseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    industry: str | None = None
    is_active: bool | None = None
    config: dict | None = None


# ── User/Account Management ─────────────────────────────────────────

class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    enterprise_id: uuid.UUID
    enterprise_name: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6)
    role: str = Field(default="staff", pattern=r"^(super_admin|admin|manager|staff)$")
    enterprise_id: uuid.UUID
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=2, max_length=100)
    role: str | None = Field(None, pattern=r"^(super_admin|admin|manager|staff)$")
    is_active: bool | None = None
    enterprise_id: uuid.UUID | None = None
    password: str | None = Field(None, min_length=6)


# ── Enterprise Detail (depends on UserListItem & EnterpriseStats) ───

class EnterpriseDetail(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    users: list[UserListItem]
    stats: EnterpriseStats

    model_config = {"from_attributes": True}


# ── Admin Data Query (conversational) ───────────────────────────────

class AdminDataQuery(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AdminDataQueryResponse(BaseModel):
    answer: str
    data: dict | None = None
