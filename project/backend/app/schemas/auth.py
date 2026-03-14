import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6)
    enterprise_name: str = Field(min_length=1, max_length=200)
    industry: str | None = None


class UserLogin(BaseModel):
    account: str | None = None
    username: str | None = None
    email: str | None = None
    password: str

    def resolve_account(self) -> str:
        """Return the effective login identifier (email / username / account)."""
        return self.account or self.username or self.email or ""


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    name: str = ""
    role: str
    enterprise_id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    def model_post_init(self, __context) -> None:
        if not self.name:
            self.name = self.username


class ErrorBody(BaseModel):
    code: int
    message: str
