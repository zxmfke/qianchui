from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.script import (
    CategoryResponse,
    ScriptCreate,
    ScriptListResponse,
    ScriptResponse,
    ScriptUpdate,
    ScriptUsageCreate,
)
from app.services.script_service import ScriptService

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


@router.get("", response_model=ScriptListResponse)
async def list_scripts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    difficulty: int | None = Query(None, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    scripts, total = await service.list_scripts(
        enterprise_id=str(user.enterprise_id),
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        status=status_filter,
        difficulty=difficulty,
    )
    return ScriptListResponse(
        items=[ScriptResponse.model_validate(s) for s in scripts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def create_script(
    body: ScriptCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    script = await service.create_script(
        enterprise_id=str(user.enterprise_id),
        user_id=str(user.id),
        title=body.title,
        content=body.content,
        category=body.category,
        tags=body.tags,
        psychology_layer=body.psychology_layer,
        strategy_layer=body.strategy_layer,
        variants=body.variants,
        difficulty=body.difficulty,
        target_role=body.target_role,
        pain_point_ids=body.pain_point_ids,
        product_ids=body.product_ids,
        service_ids=body.service_ids,
    )
    return ScriptResponse.model_validate(script)


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    categories = await service.get_categories(str(user.enterprise_id))
    return [CategoryResponse(**c) for c in categories]


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    script = await service.get_script(script_id, str(user.enterprise_id))
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "话术不存在", "message_en": "Script not found"})
    return ScriptResponse.model_validate(script)


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: str,
    body: ScriptUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    update_data = body.model_dump(exclude_unset=True)
    script = await service.update_script(
        script_id=script_id,
        enterprise_id=str(user.enterprise_id),
        **update_data,
    )
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "话术不存在", "message_en": "Script not found"})
    return ScriptResponse.model_validate(script)


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    deleted = await service.delete_script(script_id, str(user.enterprise_id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "话术不存在", "message_en": "Script not found"})


@router.post("/{script_id}/usage", status_code=status.HTTP_201_CREATED)
async def record_usage(
    script_id: str,
    body: ScriptUsageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ScriptService(db)
    script = await service.get_script(script_id, str(user.enterprise_id))
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "话术不存在", "message_en": "Script not found"})

    usage = await service.record_usage(
        script_id=script_id,
        user_id=str(user.id),
        enterprise_id=str(user.enterprise_id),
        context=body.context,
    )
    return {"id": str(usage.id), "message": "复用记录已保存"}
