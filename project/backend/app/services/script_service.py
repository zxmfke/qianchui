import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.memory import PainPoint, Product, ServiceItem
from app.models.script import Script, ScriptUsage, script_pain_points, script_products, script_services


class ScriptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_scripts(
        self,
        enterprise_id: str,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
        difficulty: int | None = None,
    ) -> tuple[list[Script], int]:
        eid = uuid.UUID(enterprise_id)
        query = select(Script).where(Script.enterprise_id == eid)

        if search:
            query = query.where(
                Script.title.ilike(f"%{search}%") | Script.content.ilike(f"%{search}%")
            )
        if category:
            query = query.where(Script.category == category)
        if status:
            query = query.where(Script.status == status)
        if difficulty:
            query = query.where(Script.difficulty == difficulty)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Script.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        scripts = list(result.scalars().all())

        return scripts, total

    async def create_script(
        self,
        enterprise_id: str,
        user_id: str,
        title: str,
        content: str,
        category: str | None = None,
        tags: list[str] | None = None,
        psychology_layer: str | None = None,
        strategy_layer: str | None = None,
        variants: list[str] | None = None,
        difficulty: int = 1,
        target_role: str = "all",
        pain_point_ids: list[uuid.UUID] | None = None,
        product_ids: list[uuid.UUID] | None = None,
        service_ids: list[uuid.UUID] | None = None,
    ) -> Script:
        script = Script(
            enterprise_id=uuid.UUID(enterprise_id),
            title=title,
            category=category,
            tags=tags or [],
            psychology_layer=psychology_layer,
            strategy_layer=strategy_layer,
            content=content,
            variants=variants or [],
            difficulty=difficulty,
            target_role=target_role,
            created_by=uuid.UUID(user_id),
        )
        self.db.add(script)
        await self.db.flush()

        if pain_point_ids:
            await self._link_pain_points(script.id, pain_point_ids)
        if product_ids:
            await self._link_products(script.id, product_ids)
        if service_ids:
            await self._link_services(script.id, service_ids)

        await self.db.flush()
        return script

    async def get_script(self, script_id: str, enterprise_id: str) -> Script | None:
        result = await self.db.execute(
            select(Script).where(
                Script.id == uuid.UUID(script_id),
                Script.enterprise_id == uuid.UUID(enterprise_id),
            )
        )
        return result.scalar_one_or_none()

    async def update_script(
        self,
        script_id: str,
        enterprise_id: str,
        **kwargs,
    ) -> Script | None:
        script = await self.get_script(script_id, enterprise_id)
        if not script:
            return None

        pain_point_ids = kwargs.pop("pain_point_ids", None)
        product_ids = kwargs.pop("product_ids", None)
        service_ids = kwargs.pop("service_ids", None)

        for key, value in kwargs.items():
            if value is not None and hasattr(script, key):
                setattr(script, key, value)

        if pain_point_ids is not None:
            await self._unlink_all(script.id, script_pain_points)
            await self._link_pain_points(script.id, pain_point_ids)
        if product_ids is not None:
            await self._unlink_all(script.id, script_products)
            await self._link_products(script.id, product_ids)
        if service_ids is not None:
            await self._unlink_all(script.id, script_services)
            await self._link_services(script.id, service_ids)

        script.version += 1
        await self.db.flush()
        await self.db.refresh(script)
        return script

    async def delete_script(self, script_id: str, enterprise_id: str) -> bool:
        script = await self.get_script(script_id, enterprise_id)
        if not script:
            return False
        await self.db.delete(script)
        await self.db.flush()
        return True

    async def record_usage(
        self,
        script_id: str,
        user_id: str,
        enterprise_id: str,
        context: dict | None = None,
    ) -> ScriptUsage:
        usage = ScriptUsage(
            script_id=uuid.UUID(script_id),
            user_id=uuid.UUID(user_id),
            enterprise_id=uuid.UUID(enterprise_id),
            context=context or {},
        )
        self.db.add(usage)

        script = await self.get_script(script_id, enterprise_id)
        if script:
            script.usage_count += 1

        await self.db.flush()
        return usage

    async def get_categories(self, enterprise_id: str) -> list[dict]:
        eid = uuid.UUID(enterprise_id)
        result = await self.db.execute(
            select(Script.category, func.count(Script.id).label("count"))
            .where(Script.enterprise_id == eid, Script.category.isnot(None))
            .group_by(Script.category)
            .order_by(func.count(Script.id).desc())
        )
        rows = result.all()
        return [{"name": row[0], "count": row[1]} for row in rows]

    async def _link_pain_points(self, script_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
        for pid in ids:
            await self.db.execute(
                script_pain_points.insert().values(script_id=script_id, pain_point_id=pid)
            )

    async def _link_products(self, script_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
        for pid in ids:
            await self.db.execute(
                script_products.insert().values(script_id=script_id, product_id=pid)
            )

    async def _link_services(self, script_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
        for sid in ids:
            await self.db.execute(
                script_services.insert().values(script_id=script_id, service_id=sid)
            )

    async def _unlink_all(self, script_id: uuid.UUID, table) -> None:
        await self.db.execute(
            table.delete().where(table.c.script_id == script_id)
        )
