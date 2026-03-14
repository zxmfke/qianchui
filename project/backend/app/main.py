import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    ab_test, admin, annotation, auth, channel_material, conversations, dashboard,
    diagnosis, flywheel, llm_proxy, memory, optimization, scripts, simulation,
    skills, training,
)
from app.config import get_settings
from app.exceptions import BizError
from app.logging_config import setup_logging
from app.middleware import RequestLoggerMiddleware
from app.providers.factory import ModelProviderFactory
from app.skills.data_insight import DataInsightSkill
from app.skills.memory_query import MemoryQuerySkill
from app.skills.registry import SkillRegistry
from app.skills.script_annotate import ScriptAnnotateSkill
from app.skills.script_diagnose import ScriptDiagnoseSkill
from app.skills.script_optimize import ScriptOptimizeSkill
from app.skills.script_recommend import ScriptRecommendSkill
from app.skills.script_simulate import ScriptSimulateSkill
from app.skills.script_train import ScriptTrainSkill
from app.skills.channel_material import ChannelMaterialSkill
from app.skills.flywheel_sense import FlywheelSenseSkill
from app.skills.flywheel_cascade import FlywheelCascadeSkill
from app.skills.flywheel_insight import FlywheelInsightSkill

_settings = get_settings()
setup_logging(
    log_level=_settings.LOG_LEVEL,
    log_format=_settings.LOG_FORMAT,
    log_file=_settings.LOG_FILE,
)
logger = logging.getLogger(__name__)


def register_skills() -> None:
    settings = get_settings()
    provider = ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
        http_proxy=settings.LLM_HTTP_PROXY,
    )

    registry = SkillRegistry()
    registry.register(ScriptRecommendSkill(provider))
    registry.register(ScriptDiagnoseSkill(provider))
    registry.register(ScriptTrainSkill(provider))
    registry.register(ScriptSimulateSkill(provider))
    registry.register(DataInsightSkill(provider))
    registry.register(MemoryQuerySkill(provider))
    registry.register(ScriptOptimizeSkill(provider))
    registry.register(ScriptAnnotateSkill(provider))
    registry.register(ChannelMaterialSkill(provider))
    registry.register(FlywheelSenseSkill(provider))
    registry.register(FlywheelCascadeSkill(provider))
    registry.register(FlywheelInsightSkill(provider))


async def ensure_super_admin() -> None:
    """Ensure superadmin account exists with correct password."""
    from app.database import async_session_factory
    from app.models.enterprise import Enterprise
    from app.models.user import User
    from passlib.context import CryptContext
    from sqlalchemy import select

    _SA_USERNAME = "superadmin"
    _SA_PASSWORD = "kst@2026"
    _SA_EMAIL = "superadmin@qianchui.com"

    pwd_ctx = CryptContext(schemes=["bcrypt"])

    async with async_session_factory() as session:
        existing = (await session.execute(
            select(User).where(User.username == _SA_USERNAME)
        )).scalar_one_or_none()

        if existing:
            if not pwd_ctx.verify(_SA_PASSWORD, existing.hashed_password):
                existing.hashed_password = pwd_ctx.hash(_SA_PASSWORD)
                await session.commit()
                logger.info("Super admin password reset to default")
            return

        ent = (await session.execute(
            select(Enterprise).where(Enterprise.name == "千锤平台")
        )).scalar_one_or_none()
        if not ent:
            ent = Enterprise(name="千锤平台", industry="平台运营", is_active=True)
            session.add(ent)
            await session.flush()

        user = User(
            enterprise_id=ent.id, email=_SA_EMAIL,
            username=_SA_USERNAME, hashed_password=pwd_ctx.hash(_SA_PASSWORD),
            role="super_admin", is_active=True,
        )
        session.add(user)
        await session.commit()
        logger.info("Default super_admin created: %s / %s", _SA_USERNAME, _SA_PASSWORD)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.database import engine
    from app.models.base import Base
    from app.services.data_simulator import run_simulator
    from app.observability import init_langfuse, flush as flush_langfuse

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_super_admin()
    register_skills()
    init_langfuse()

    logger.info("Application startup complete")

    simulator_task = asyncio.create_task(run_simulator())
    yield
    simulator_task.cancel()
    flush_langfuse()


app = FastAPI(
    title="千锤·营销话术AI操作系统",
    description="AI Native 营销话术管理平台 — 话术资产可沉淀、可复用、可进化",
    version="1.1.0",
    lifespan=lifespan,
)


# ── Unified error handlers ──────────────────────────────────────────


@app.exception_handler(BizError)
async def biz_error_handler(_request: Request, exc: BizError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "message_en": exc.message_en},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    fields = []
    for err in exc.errors():
        loc = ".".join(str(l) for l in err.get("loc", []) if l != "body")
        fields.append(f"{loc}: {err.get('msg', '')}")
    return JSONResponse(
        status_code=422,
        content={"code": 42200, "message": "参数验证错误", "message_en": "Validation error", "details": fields},
    )


@app.exception_handler(Exception)
async def global_error_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 50000, "message": "服务器内部错误", "message_en": "Internal server error"},
    )


# ── Middleware ───────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(scripts.router)
app.include_router(conversations.router)
app.include_router(dashboard.router)
app.include_router(training.router)
app.include_router(simulation.router)
app.include_router(diagnosis.router)
app.include_router(memory.router)
app.include_router(optimization.router)
app.include_router(annotation.router)
app.include_router(ab_test.router)
app.include_router(channel_material.router)
app.include_router(flywheel.router)
app.include_router(skills.router)
app.include_router(llm_proxy.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "千锤·营销话术AI操作系统"}
