from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.i18n import get_error_message, get_lang

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    lang = get_lang(request)
    token = credentials.credentials
    payload = AuthService.decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail=get_error_message("invalid_token", lang),
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(payload["sub"])

    if not user:
        raise HTTPException(
            status_code=401,
            detail=get_error_message("user_not_found", lang),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail=get_error_message("account_disabled", lang),
        )

    return user


def require_role(*roles: str):
    async def role_checker(
        request: Request,
        user: User = Depends(get_current_user),
    ) -> User:
        if user.role not in roles:
            lang = get_lang(request)
            raise HTTPException(
                status_code=403,
                detail=get_error_message("access_denied", lang),
            )
        return user
    return role_checker
