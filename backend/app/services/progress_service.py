from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.progress import UserProgress
from app.models.session import TestSession
from app.models.user import User
from app.schemas.session import ProgressOut, ProgressSubject


class ProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, telegram_id: int) -> ProgressOut | None:
        user_result = await self.db.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return None

        progress_result = await self.db.execute(
            select(
                UserProgress.subject,
                func.sum(UserProgress.total_attempts).label("total"),
                func.sum(UserProgress.correct_attempts).label("correct"),
            )
            .where(UserProgress.user_id == user.id)
            .group_by(UserProgress.subject)
        )
        rows = progress_result.all()

        sessions_count = await self.db.execute(
            select(func.count(TestSession.id)).where(
                TestSession.user_id == user.id,
                TestSession.status == "finished",
            )
        )
        total_sessions = sessions_count.scalar_one()

        subjects = []
        for row in rows:
            accuracy = round(row.correct / row.total, 2) if row.total > 0 else 0.0
            weak_tasks_result = await self.db.execute(
                select(UserProgress.task_number)
                .where(
                    UserProgress.user_id == user.id,
                    UserProgress.subject == row.subject,
                    UserProgress.total_attempts >= 3,
                    UserProgress.correct_attempts * 1.0 / UserProgress.total_attempts < 0.5,
                    UserProgress.task_number.is_not(None),
                )
                .order_by(UserProgress.correct_attempts * 1.0 / UserProgress.total_attempts)
                .limit(5)
            )
            weak_tasks = [r[0] for r in weak_tasks_result.all()]
            subjects.append(ProgressSubject(
                subject=row.subject,
                total_attempts=row.total,
                correct_attempts=row.correct,
                accuracy=accuracy,
                weak_tasks=weak_tasks,
            ))

        return ProgressOut(
            telegram_id=telegram_id,
            subjects=subjects,
            total_sessions=total_sessions,
            streak_days=0,
        )
