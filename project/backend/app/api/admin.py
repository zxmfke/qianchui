"""Super-admin API: system overview, enterprise CRUD, account CRUD, data query."""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.exceptions import PARAM_ERROR, PERMISSION_DENIED
from app.models.channel_material import ChannelMaterial
from app.models.conversation import Conversation, Message
from app.models.diagnosis import DiagnosisReport
from app.models.enterprise import Enterprise
from app.models.memory import PainPoint, Product, ServiceItem
from app.models.script import Script
from app.models.simulation import SimulationSession
from app.models.training import TrainingRecord
from app.models.user import User
from app.schemas.admin import (
    AdminDataQuery,
    AdminDataQueryResponse,
    DailyStats,
    EnterpriseCreate,
    EnterpriseDetail,
    EnterpriseListItem,
    EnterpriseStats,
    EnterpriseUpdate,
    SystemOverview,
    SystemTrend,
    UserCreate,
    UserListItem,
    UserUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/admin", tags=["admin"])

SUPER_ADMIN = require_role("super_admin")


# ── System Overview ──────────────────────────────────────────────────


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    async def count(model):
        r = await db.execute(select(func.count()).select_from(model))
        return r.scalar() or 0

    active_ent = await db.execute(
        select(func.count()).select_from(Enterprise).where(Enterprise.is_active.is_(True))
    )
    active_usr = await db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )

    return SystemOverview(
        total_enterprises=await count(Enterprise),
        active_enterprises=active_ent.scalar() or 0,
        total_users=await count(User),
        active_users=active_usr.scalar() or 0,
        total_scripts=await count(Script),
        total_conversations=await count(Conversation),
        total_messages=await count(Message),
        total_training_records=await count(TrainingRecord),
        total_simulations=await count(SimulationSession),
        total_diagnosis_reports=await count(DiagnosisReport),
        total_channel_materials=await count(ChannelMaterial),
    )


@router.get("/trends", response_model=SystemTrend)
async def get_system_trends(
    days: int = Query(30, ge=1, le=90),
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    daily: dict[str, DailyStats] = {}

    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        daily[d] = DailyStats(date=d, new_enterprises=0, new_users=0, new_scripts=0, new_conversations=0)

    for model, field_name in [
        (Enterprise, "new_enterprises"),
        (User, "new_users"),
        (Script, "new_scripts"),
        (Conversation, "new_conversations"),
    ]:
        stmt = (
            select(func.date(model.created_at).label("d"), func.count().label("c"))
            .where(model.created_at >= since)
            .group_by(func.date(model.created_at))
        )
        rows = await db.execute(stmt)
        for row in rows:
            d_str = str(row.d)
            if d_str in daily:
                setattr(daily[d_str], field_name, row.c)

    return SystemTrend(daily_stats=list(daily.values()))


# ── Enterprise CRUD ──────────────────────────────────────────────────


@router.get("/enterprises", response_model=PaginatedResponse[EnterpriseListItem])
async def list_enterprises(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=200),
    is_active: bool | None = None,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    base = select(Enterprise)
    count_q = select(func.count()).select_from(Enterprise)

    if search:
        base = base.where(Enterprise.name.ilike(f"%{search}%"))
        count_q = count_q.where(Enterprise.name.ilike(f"%{search}%"))
    if is_active is not None:
        base = base.where(Enterprise.is_active.is_(is_active))
        count_q = count_q.where(Enterprise.is_active.is_(is_active))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(Enterprise.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = []
    for ent in rows:
        u_count = (await db.execute(
            select(func.count()).select_from(User).where(User.enterprise_id == ent.id)
        )).scalar() or 0
        s_count = (await db.execute(
            select(func.count()).select_from(Script).where(Script.enterprise_id == ent.id)
        )).scalar() or 0
        c_count = (await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.enterprise_id == ent.id)
        )).scalar() or 0
        items.append(EnterpriseListItem(
            id=ent.id, name=ent.name, industry=ent.industry, is_active=ent.is_active,
            user_count=u_count, script_count=s_count, conversation_count=c_count,
            created_at=ent.created_at,
        ))

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/enterprises/{enterprise_id}", response_model=EnterpriseDetail)
async def get_enterprise_detail(
    enterprise_id: uuid.UUID,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    ent = (await db.execute(
        select(Enterprise).where(Enterprise.id == enterprise_id)
        .options(selectinload(Enterprise.users))
    )).scalar_one_or_none()
    if not ent:
        raise PARAM_ERROR("企业不存在", "Enterprise not found")

    async def cnt(model):
        r = await db.execute(
            select(func.count()).select_from(model).where(model.enterprise_id == enterprise_id)
        )
        return r.scalar() or 0

    stats = EnterpriseStats(
        user_count=len(ent.users),
        script_count=await cnt(Script),
        conversation_count=await cnt(Conversation),
        training_count=await cnt(TrainingRecord),
        simulation_count=await cnt(SimulationSession),
        diagnosis_count=await cnt(DiagnosisReport),
        channel_material_count=await cnt(ChannelMaterial),
        pain_point_count=await cnt(PainPoint),
        product_count=await cnt(Product),
        service_count=await cnt(ServiceItem),
    )

    users = [
        UserListItem(
            id=u.id, email=u.email, username=u.username, role=u.role,
            is_active=u.is_active, enterprise_id=u.enterprise_id,
            enterprise_name=ent.name, last_login_at=u.last_login_at,
            created_at=u.created_at, updated_at=u.updated_at,
        )
        for u in ent.users
    ]

    return EnterpriseDetail(
        id=ent.id, name=ent.name, industry=ent.industry, config=ent.config,
        is_active=ent.is_active, created_at=ent.created_at, updated_at=ent.updated_at,
        users=users, stats=stats,
    )


@router.post("/enterprises", response_model=EnterpriseListItem, status_code=201)
async def create_enterprise(
    body: EnterpriseCreate,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    ent = Enterprise(name=body.name, industry=body.industry, is_active=body.is_active)
    db.add(ent)
    await db.flush()
    return EnterpriseListItem(
        id=ent.id, name=ent.name, industry=ent.industry, is_active=ent.is_active,
        user_count=0, script_count=0, conversation_count=0, created_at=ent.created_at,
    )


@router.put("/enterprises/{enterprise_id}", response_model=EnterpriseListItem)
async def update_enterprise(
    enterprise_id: uuid.UUID,
    body: EnterpriseUpdate,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    ent = (await db.execute(
        select(Enterprise).where(Enterprise.id == enterprise_id)
    )).scalar_one_or_none()
    if not ent:
        raise PARAM_ERROR("企业不存在", "Enterprise not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(ent, field, val)
    await db.flush()

    u_count = (await db.execute(
        select(func.count()).select_from(User).where(User.enterprise_id == ent.id)
    )).scalar() or 0
    s_count = (await db.execute(
        select(func.count()).select_from(Script).where(Script.enterprise_id == ent.id)
    )).scalar() or 0
    c_count = (await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.enterprise_id == ent.id)
    )).scalar() or 0

    return EnterpriseListItem(
        id=ent.id, name=ent.name, industry=ent.industry, is_active=ent.is_active,
        user_count=u_count, script_count=s_count, conversation_count=c_count,
        created_at=ent.created_at,
    )


@router.delete("/enterprises/{enterprise_id}", status_code=204)
async def delete_enterprise(
    enterprise_id: uuid.UUID,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    ent = (await db.execute(
        select(Enterprise).where(Enterprise.id == enterprise_id)
    )).scalar_one_or_none()
    if not ent:
        raise PARAM_ERROR("企业不存在", "Enterprise not found")
    await db.delete(ent)


# ── Account CRUD ─────────────────────────────────────────────────────


@router.get("/users", response_model=PaginatedResponse[UserListItem])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=200),
    enterprise_id: uuid.UUID | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    base = select(User).options(selectinload(User.enterprise))
    count_q = select(func.count()).select_from(User)

    if search:
        like = f"%{search}%"
        base = base.where((User.username.ilike(like)) | (User.email.ilike(like)))
        count_q = count_q.where((User.username.ilike(like)) | (User.email.ilike(like)))
    if enterprise_id:
        base = base.where(User.enterprise_id == enterprise_id)
        count_q = count_q.where(User.enterprise_id == enterprise_id)
    if role:
        base = base.where(User.role == role)
        count_q = count_q.where(User.role == role)
    if is_active is not None:
        base = base.where(User.is_active.is_(is_active))
        count_q = count_q.where(User.is_active.is_(is_active))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [
        UserListItem(
            id=u.id, email=u.email, username=u.username, role=u.role,
            is_active=u.is_active, enterprise_id=u.enterprise_id,
            enterprise_name=u.enterprise.name if u.enterprise else None,
            last_login_at=u.last_login_at,
            created_at=u.created_at, updated_at=u.updated_at,
        )
        for u in rows
    ]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post("/users", response_model=UserListItem, status_code=201)
async def create_user(
    body: UserCreate,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    ent = (await db.execute(
        select(Enterprise).where(Enterprise.id == body.enterprise_id)
    )).scalar_one_or_none()
    if not ent:
        raise PARAM_ERROR("所属企业不存在", "Enterprise not found")

    existing = (await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )).scalar_one_or_none()
    if existing:
        raise PARAM_ERROR("邮箱或用户名已被注册", "Email or username already taken")

    hashed = AuthService.hash_password(body.password)
    user = User(
        email=body.email, username=body.username, hashed_password=hashed,
        role=body.role, enterprise_id=body.enterprise_id, is_active=body.is_active,
    )
    db.add(user)
    await db.flush()

    return UserListItem(
        id=user.id, email=user.email, username=user.username, role=user.role,
        is_active=user.is_active, enterprise_id=user.enterprise_id,
        enterprise_name=ent.name, last_login_at=None,
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.put("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    target = (await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.enterprise))
    )).scalar_one_or_none()
    if not target:
        raise PARAM_ERROR("用户不存在", "User not found")

    ent_name = target.enterprise.name if target.enterprise else None

    updates = body.model_dump(exclude_unset=True)
    if "password" in updates:
        updates["hashed_password"] = AuthService.hash_password(updates.pop("password"))

    changing_enterprise = "enterprise_id" in updates and updates["enterprise_id"] != target.enterprise_id
    for field, val in updates.items():
        setattr(target, field, val)
    await db.flush()
    await db.refresh(target)

    if changing_enterprise:
        ent = (await db.execute(
            select(Enterprise).where(Enterprise.id == target.enterprise_id)
        )).scalar_one_or_none()
        ent_name = ent.name if ent else None

    return UserListItem(
        id=target.id, email=target.email, username=target.username, role=target.role,
        is_active=target.is_active, enterprise_id=target.enterprise_id,
        enterprise_name=ent_name, last_login_at=target.last_login_at,
        created_at=target.created_at, updated_at=target.updated_at,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    cur_user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    if user_id == cur_user.id:
        raise PERMISSION_DENIED("不能删除自己的账号")
    target = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if not target:
        raise PARAM_ERROR("用户不存在", "User not found")
    await db.delete(target)


# ── Admin Data Query (conversational) ────────────────────────────────


@router.post("/query", response_model=AdminDataQueryResponse)
async def admin_data_query(
    body: AdminDataQuery,
    _user: User = Depends(SUPER_ADMIN),
    db: AsyncSession = Depends(get_db),
):
    """Parse natural-language admin questions into SQL queries and return results."""
    question = body.question.lower()
    today = date.today()
    yesterday = today - timedelta(days=1)

    result_data: dict = {}
    answer_parts: list[str] = []

    if any(kw in question for kw in ["企业", "company", "enterprise"]):
        if any(kw in question for kw in ["昨天", "yesterday"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Enterprise)
                .where(func.date(Enterprise.created_at) == yesterday)
            )).scalar() or 0
            answer_parts.append(f"昨天（{yesterday}）新增企业 {cnt} 家")
            result_data["yesterday_new_enterprises"] = cnt
        elif any(kw in question for kw in ["今天", "today"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Enterprise)
                .where(func.date(Enterprise.created_at) == today)
            )).scalar() or 0
            answer_parts.append(f"今天（{today}）新增企业 {cnt} 家")
            result_data["today_new_enterprises"] = cnt
        elif any(kw in question for kw in ["总", "total", "一共", "多少"]):
            total = (await db.execute(
                select(func.count()).select_from(Enterprise)
            )).scalar() or 0
            active = (await db.execute(
                select(func.count()).select_from(Enterprise)
                .where(Enterprise.is_active.is_(True))
            )).scalar() or 0
            answer_parts.append(f"目前共有 {total} 家企业，其中活跃 {active} 家")
            result_data["total_enterprises"] = total
            result_data["active_enterprises"] = active

    if any(kw in question for kw in ["用户", "账号", "user", "account"]):
        if any(kw in question for kw in ["昨天", "yesterday"]):
            cnt = (await db.execute(
                select(func.count()).select_from(User)
                .where(func.date(User.created_at) == yesterday)
            )).scalar() or 0
            answer_parts.append(f"昨天（{yesterday}）新增用户 {cnt} 个")
            result_data["yesterday_new_users"] = cnt
        elif any(kw in question for kw in ["今天", "today"]):
            cnt = (await db.execute(
                select(func.count()).select_from(User)
                .where(func.date(User.created_at) == today)
            )).scalar() or 0
            answer_parts.append(f"今天（{today}）新增用户 {cnt} 个")
            result_data["today_new_users"] = cnt
        elif any(kw in question for kw in ["总", "total", "一共", "多少"]):
            total = (await db.execute(
                select(func.count()).select_from(User)
            )).scalar() or 0
            active = (await db.execute(
                select(func.count()).select_from(User)
                .where(User.is_active.is_(True))
            )).scalar() or 0
            answer_parts.append(f"目前共有 {total} 个用户，其中活跃 {active} 个")
            result_data["total_users"] = total
            result_data["active_users"] = active

    if any(kw in question for kw in ["话术", "script"]):
        if any(kw in question for kw in ["昨天", "yesterday"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Script)
                .where(func.date(Script.created_at) == yesterday)
            )).scalar() or 0
            answer_parts.append(f"昨天（{yesterday}）新增话术 {cnt} 条")
            result_data["yesterday_new_scripts"] = cnt
        elif any(kw in question for kw in ["今天", "today"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Script)
                .where(func.date(Script.created_at) == today)
            )).scalar() or 0
            answer_parts.append(f"今天（{today}）新增话术 {cnt} 条")
            result_data["today_new_scripts"] = cnt
        elif any(kw in question for kw in ["总", "total", "一共", "多少"]):
            total = (await db.execute(
                select(func.count()).select_from(Script)
            )).scalar() or 0
            answer_parts.append(f"目前共有 {total} 条话术")
            result_data["total_scripts"] = total

    if any(kw in question for kw in ["对话", "conversation"]):
        if any(kw in question for kw in ["昨天", "yesterday"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Conversation)
                .where(func.date(Conversation.created_at) == yesterday)
            )).scalar() or 0
            answer_parts.append(f"昨天（{yesterday}）新增对话 {cnt} 条")
            result_data["yesterday_new_conversations"] = cnt
        elif any(kw in question for kw in ["今天", "today"]):
            cnt = (await db.execute(
                select(func.count()).select_from(Conversation)
                .where(func.date(Conversation.created_at) == today)
            )).scalar() or 0
            answer_parts.append(f"今天（{today}）新增对话 {cnt} 条")
            result_data["today_new_conversations"] = cnt

    if any(kw in question for kw in ["概况", "总览", "overview", "全局"]):
        total_ent = (await db.execute(select(func.count()).select_from(Enterprise))).scalar() or 0
        total_usr = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
        total_scr = (await db.execute(select(func.count()).select_from(Script))).scalar() or 0
        total_conv = (await db.execute(select(func.count()).select_from(Conversation))).scalar() or 0
        answer_parts.append(
            f"系统概况：企业 {total_ent} 家，用户 {total_usr} 个，"
            f"话术 {total_scr} 条，对话 {total_conv} 条"
        )
        result_data.update(dict(
            total_enterprises=total_ent, total_users=total_usr,
            total_scripts=total_scr, total_conversations=total_conv,
        ))

    if not answer_parts:
        answer_parts.append(
            "抱歉，我暂时无法理解这个问题。你可以问我关于企业数量、用户数量、话术数量、对话数量等数据。\n"
            "示例：\n• 昨天新增多少企业？\n• 目前一共有多少话术？\n• 系统总览"
        )

    return AdminDataQueryResponse(
        answer="\n".join(answer_parts),
        data=result_data if result_data else None,
    )
