"""Tests for app.utils.deps module (OAuth2-based auth, currently 0% coverage)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.auth import create_access_token
from app.utils.deps import get_current_user, get_current_enterprise


@pytest.mark.asyncio
class TestUtilsDeps:
    async def test_get_current_user_valid_token(self, test_db: AsyncSession, test_user):
        token = create_access_token({
            "sub": str(test_user.id),
            "role": test_user.role,
        })
        user = await get_current_user(token=token, db=test_db)
        assert user.id == test_user.id
        assert user.username == "testuser"

    async def test_get_current_user_invalid_token(self, test_db: AsyncSession):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid-token", db=test_db)
        assert exc_info.value.status_code == 401

    async def test_get_current_user_no_sub(self, test_db: AsyncSession):
        from fastapi import HTTPException
        token = create_access_token({"role": "admin"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)
        assert exc_info.value.status_code == 401

    async def test_get_current_user_invalid_uuid(self, test_db: AsyncSession):
        from fastapi import HTTPException
        token = create_access_token({"sub": "not-a-uuid"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)
        assert exc_info.value.status_code == 401

    async def test_get_current_user_user_not_found(self, test_db: AsyncSession):
        from fastapi import HTTPException
        token = create_access_token({"sub": str(uuid.uuid4())})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)
        assert exc_info.value.status_code == 401

    async def test_get_current_user_inactive(self, test_db: AsyncSession, test_enterprise):
        from fastapi import HTTPException
        inactive = User(
            id=uuid.uuid4(),
            username="inactive",
            email="inactive@test.com",
            hashed_password=AuthService.hash_password("pw"),
            enterprise_id=test_enterprise.id,
            role="admin",
            is_active=False,
        )
        test_db.add(inactive)
        await test_db.flush()

        token = create_access_token({"sub": str(inactive.id)})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)
        assert exc_info.value.status_code == 401

    async def test_get_current_enterprise(self, test_user):
        eid = await get_current_enterprise(test_user)
        assert eid == test_user.enterprise_id
