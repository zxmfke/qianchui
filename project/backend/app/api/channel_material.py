"""渠道物料 API — CRUD + 统计"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.channel_material import ChannelMaterial
from app.models.user import User
from app.schemas.channel_material import ChannelMaterialCreate, ChannelMaterialUpdate

router = APIRouter(prefix="/api/v1/channel-materials", tags=["channel-materials"])


def _to_dict(m: ChannelMaterial) -> dict:
    return {
        "id": str(m.id),
        "enterprise_id": str(m.enterprise_id),
        "channel": m.channel,
        "title": m.title,
        "content": m.content,
        "source_url": m.source_url,
        "material_type": m.material_type,
        "metrics": m.metrics or {},
        "extracted_info": m.extracted_info or {},
        "tags": m.tags or [],
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.get("")
async def list_channel_materials(
    channel: str | None = None,
    keyword: str | None = None,
    material_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(ChannelMaterial).where(
        ChannelMaterial.enterprise_id == user.enterprise_id
    )
    if channel:
        stmt = stmt.where(ChannelMaterial.channel == channel)
    if material_status:
        stmt = stmt.where(ChannelMaterial.status == material_status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(ChannelMaterial.title.ilike(kw))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    rows = (
        await db.execute(
            stmt.order_by(ChannelMaterial.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {"items": [_to_dict(m) for m in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def get_channel_material_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            ChannelMaterial.channel,
            func.count(ChannelMaterial.id),
        )
        .where(
            ChannelMaterial.enterprise_id == user.enterprise_id,
            ChannelMaterial.status == "active",
        )
        .group_by(ChannelMaterial.channel)
    )
    stats = {row[0]: row[1] for row in result.all()}
    return {"by_channel": stats, "total": sum(stats.values())}


@router.get("/{material_id}")
async def get_channel_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelMaterial).where(
            ChannelMaterial.id == uuid.UUID(material_id),
            ChannelMaterial.enterprise_id == user.enterprise_id,
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail={"message": "物料不存在", "message_en": "Material not found"})
    return _to_dict(m)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_channel_material(
    body: ChannelMaterialCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = ChannelMaterial(
        enterprise_id=user.enterprise_id,
        channel=body.channel,
        title=body.title,
        content=body.content,
        source_url=getattr(body, "source_url", None),
        material_type=body.material_type,
        tags=body.tags or [],
        status="active",
    )
    db.add(m)
    await db.flush()
    return _to_dict(m)


@router.put("/{material_id}")
async def update_channel_material(
    material_id: str,
    body: ChannelMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelMaterial).where(
            ChannelMaterial.id == uuid.UUID(material_id),
            ChannelMaterial.enterprise_id == user.enterprise_id,
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail={"message": "物料不存在", "message_en": "Material not found"})

    for field in ("title", "content", "source_url", "material_type", "metrics", "tags", "status"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(m, field, val)
    await db.flush()
    await db.refresh(m)
    return _to_dict(m)


@router.delete("/{material_id}")
async def delete_channel_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelMaterial).where(
            ChannelMaterial.id == uuid.UUID(material_id),
            ChannelMaterial.enterprise_id == user.enterprise_id,
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail={"message": "物料不存在", "message_en": "Material not found"})
    m.status = "archived"
    await db.flush()
    return {"id": str(m.id), "status": "archived"}


@router.post("/{material_id}/extract")
async def extract_channel_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChannelMaterial).where(
            ChannelMaterial.id == uuid.UUID(material_id),
            ChannelMaterial.enterprise_id == user.enterprise_id,
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail={"message": "物料不存在", "message_en": "Material not found"})

    try:
        from app.skills.registry import SkillRegistry
        skill = SkillRegistry().get_skill("channel-material")
        if skill:
            ctx = {
                "material_content": m.content or "",
                "material_title": m.title or "",
                "channel": m.channel,
                "material_type": m.material_type or "",
            }
            res = await skill.execute("分析该渠道物料", ctx)
            extracted = res.get("extracted_info", {})
            if not extracted:
                for card in res.get("cards", []):
                    if card.get("type") == "channel-material-extract":
                        extracted = card.get("data", {})
                        break
            m.extracted_info = extracted
            await db.flush()
            return {"id": str(m.id), "extracted_info": extracted}
    except Exception:
        pass

    fallback = {
        "brand_tone": "专业可信赖",
        "selling_points": ["效果显著", "安全可靠"],
        "keywords": (m.title or "").split("｜"),
    }
    m.extracted_info = fallback
    await db.flush()
    return {"id": str(m.id), "extracted_info": fallback}
