from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.exceptions import BizError
from app.models.user import User
from app.schemas.auth import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.utils.crypto import get_public_key_pem
from app.utils.i18n import BIZ_ERROR_CODE_TO_KEY, get_error_message, get_lang

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/public-key")
async def public_key():
    return {"public_key": get_public_key_pem()}


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    lang = get_lang(request)
    try:
        auth_service = AuthService(db)
        user, enterprise = await auth_service.register(
            email=body.email,
            username=body.username,
            password=body.password,
            enterprise_name=body.enterprise_name,
            industry=body.industry,
        )
    except BizError as exc:
        key = BIZ_ERROR_CODE_TO_KEY.get(exc.code, "internal_error")
        raise HTTPException(
            status_code=exc.http_status,
            detail=get_error_message(key, lang),
        )

    token_data = {
        "sub": str(user.id),
        "enterprise_id": str(user.enterprise_id),
        "role": user.role,
    }
    return TokenResponse(
        access_token=AuthService.create_access_token(token_data),
        refresh_token=AuthService.create_refresh_token(token_data),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    lang = get_lang(request)
    account = body.resolve_account()
    if not account:
        raise HTTPException(
            status_code=400,
            detail=get_error_message("provide_username_or_email", lang),
        )

    try:
        auth_service = AuthService(db)
        user, access_token, refresh_token = await auth_service.login(
            account=account, password=body.password,
        )
    except BizError as exc:
        key = BIZ_ERROR_CODE_TO_KEY.get(exc.code, "internal_error")
        raise HTTPException(
            status_code=exc.http_status,
            detail=get_error_message(key, lang),
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    lang = get_lang(request)
    try:
        auth_service = AuthService(db)
        access_token, refresh_token = await auth_service.refresh_tokens(body.refresh_token)
    except BizError as exc:
        key = BIZ_ERROR_CODE_TO_KEY.get(exc.code, "internal_error")
        raise HTTPException(
            status_code=exc.http_status,
            detail=get_error_message(key, lang),
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
