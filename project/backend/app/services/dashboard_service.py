import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.script import Script, ScriptUsage
from app.models.simulation import SimulationSession
from app.models.training import TrainingRecord
from app.models.user import User


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self, enterprise_id: str) -> dict:
        eid = uuid.UUID(enterprise_id)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_scripts = await self._count(
            select(func.count(Script.id)).where(Script.enterprise_id == eid)
        )
        published_scripts = await self._count(
            select(func.count(Script.id)).where(
                Script.enterprise_id == eid, Script.status == "published"
            )
        )
        total_usage = await self._count(
            select(func.count(ScriptUsage.id)).where(ScriptUsage.enterprise_id == eid)
        )
        today_usage = await self._count(
            select(func.count(ScriptUsage.id)).where(
                ScriptUsage.enterprise_id == eid,
                ScriptUsage.created_at >= today_start,
            )
        )

        avg_conv_result = await self.db.execute(
            select(func.avg(Script.conversion_rate)).where(
                Script.enterprise_id == eid, Script.status == "published"
            )
        )
        avg_conversion = avg_conv_result.scalar() or 0.0

        active_users = await self._count(
            select(func.count(func.distinct(ScriptUsage.user_id))).where(
                ScriptUsage.enterprise_id == eid,
                ScriptUsage.created_at >= today_start,
            )
        )

        total_training = await self._count(
            select(func.count(TrainingRecord.id)).where(TrainingRecord.enterprise_id == eid)
        )
        correct_training = await self._count(
            select(func.count(TrainingRecord.id)).where(
                TrainingRecord.enterprise_id == eid,
                TrainingRecord.is_correct.is_(True),
            )
        )
        training_rate = correct_training / total_training if total_training > 0 else 0.0

        avg_sim_score = 0.0

        return {
            "total_scripts": total_scripts,
            "published_scripts": published_scripts,
            "today_usage_count": today_usage,
            "total_usage_count": total_usage,
            "avg_conversion_rate": round(avg_conversion, 4),
            "active_users_today": active_users,
            "training_completion_rate": round(training_rate, 4),
            "avg_simulation_score": round(avg_sim_score, 1),
        }

    async def get_script_ranking(self, enterprise_id: str, limit: int = 10) -> dict:
        eid = uuid.UUID(enterprise_id)

        by_usage_result = await self.db.execute(
            select(Script)
            .where(Script.enterprise_id == eid, Script.status == "published")
            .order_by(Script.usage_count.desc())
            .limit(limit)
        )
        by_usage = by_usage_result.scalars().all()

        by_conv_result = await self.db.execute(
            select(Script)
            .where(Script.enterprise_id == eid, Script.status == "published")
            .order_by(Script.conversion_rate.desc())
            .limit(limit)
        )
        by_conversion = by_conv_result.scalars().all()

        def _to_item(s: Script) -> dict:
            return {
                "script_id": str(s.id),
                "title": s.title,
                "category": s.category,
                "usage_count": s.usage_count,
                "conversion_rate": s.conversion_rate,
                "user_rating": s.user_rating,
            }

        return {
            "by_usage": [_to_item(s) for s in by_usage],
            "by_conversion": [_to_item(s) for s in by_conversion],
        }

    async def get_team_stats(self, enterprise_id: str) -> dict:
        eid = uuid.UUID(enterprise_id)

        users_result = await self.db.execute(
            select(User).where(User.enterprise_id == eid, User.is_active.is_(True))
        )
        users = users_result.scalars().all()

        members = []
        for user in users:
            usage_count = await self._count(
                select(func.count(ScriptUsage.id)).where(ScriptUsage.user_id == user.id)
            )

            total_q = await self._count(
                select(func.count(TrainingRecord.id)).where(TrainingRecord.user_id == user.id)
            )
            correct_q = await self._count(
                select(func.count(TrainingRecord.id)).where(
                    TrainingRecord.user_id == user.id,
                    TrainingRecord.is_correct.is_(True),
                )
            )

            sim_count = await self._count(
                select(func.count(SimulationSession.id)).where(
                    SimulationSession.user_id == user.id,
                    SimulationSession.status == "completed",
                )
            )

            members.append({
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role,
                "scripts_used": usage_count,
                "training_accuracy": round(correct_q / total_q, 4) if total_q > 0 else 0.0,
                "training_completed": total_q,
                "simulation_avg_score": 0.0,
                "simulation_count": sim_count,
            })

        return {
            "members": members,
            "total_members": len(members),
        }

    async def get_trends(self, enterprise_id: str, days: int = 7) -> dict:
        eid = uuid.UUID(enterprise_id)
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        date_expr_usage = func.date(ScriptUsage.created_at)
        usage_result = await self.db.execute(
            select(
                date_expr_usage.label("date"),
                func.count(ScriptUsage.id).label("value"),
            )
            .where(ScriptUsage.enterprise_id == eid, ScriptUsage.created_at >= start)
            .group_by(date_expr_usage)
            .order_by(date_expr_usage)
        )
        usage_trend = [{"date": str(r[0]), "value": r[1]} for r in usage_result.all()]

        date_expr_script = func.date(Script.created_at)
        script_result = await self.db.execute(
            select(
                date_expr_script.label("date"),
                func.count(Script.id).label("value"),
            )
            .where(Script.enterprise_id == eid, Script.created_at >= start)
            .group_by(date_expr_script)
            .order_by(date_expr_script)
        )
        new_scripts_trend = [{"date": str(r[0]), "value": r[1]} for r in script_result.all()]

        date_expr_train = func.date(TrainingRecord.created_at)
        training_result = await self.db.execute(
            select(
                date_expr_train.label("date"),
                func.count(TrainingRecord.id).label("value"),
            )
            .where(TrainingRecord.enterprise_id == eid, TrainingRecord.created_at >= start)
            .group_by(date_expr_train)
            .order_by(date_expr_train)
        )
        training_trend = [{"date": str(r[0]), "value": r[1]} for r in training_result.all()]

        return {
            "usage_trend": usage_trend,
            "new_scripts_trend": new_scripts_trend,
            "training_trend": training_trend,
            "period": f"{days}d",
        }

    async def _count(self, stmt) -> int:
        result = await self.db.execute(stmt)
        return result.scalar() or 0
