import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import (
    ACCOUNT_DISABLED,
    EMAIL_REGISTERED,
    INVALID_CREDENTIALS,
    INVALID_REFRESH,
    USER_NOT_FOUND,
)
from app.models.enterprise import Enterprise
from app.models.user import User
from app.utils.crypto import resolve_password

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict | None:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        enterprise_name: str,
        industry: str | None = None,
    ) -> tuple[User, Enterprise]:
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise EMAIL_REGISTERED()

        plain_password = resolve_password(password)

        enterprise = Enterprise(
            name=enterprise_name,
            industry=industry,
        )
        self.db.add(enterprise)
        await self.db.flush()

        user = User(
            enterprise_id=enterprise.id,
            email=email,
            username=username,
            hashed_password=self.hash_password(plain_password),
            role="admin",
        )
        self.db.add(user)
        await self.db.flush()

        return user, enterprise

    async def login(self, account: str, password: str) -> tuple[User, str, str]:
        result = await self.db.execute(
            select(User).where(
                or_(User.email == account, User.username == account)
            )
        )
        user = result.scalar_one_or_none()

        plain_password = resolve_password(password)

        if not user or not self.verify_password(plain_password, user.hashed_password):
            raise INVALID_CREDENTIALS()

        if not user.is_active:
            raise ACCOUNT_DISABLED()

        user.last_login_at = datetime.now(timezone.utc)

        token_data = {
            "sub": str(user.id),
            "enterprise_id": str(user.enterprise_id),
            "role": user.role,
        }
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        return user, access_token, refresh_token

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        payload = self.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise INVALID_REFRESH()

        user = await self.get_user_by_id(payload["sub"])
        if not user:
            raise USER_NOT_FOUND()

        token_data = {
            "sub": str(user.id),
            "enterprise_id": str(user.enterprise_id),
            "role": user.role,
        }
        new_access = self.create_access_token(token_data)
        new_refresh = self.create_refresh_token(token_data)

        return new_access, new_refresh
