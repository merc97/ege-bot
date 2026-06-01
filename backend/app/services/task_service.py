from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.task import Task
from app.models.session import SessionAnswer, TestSession
from app.models.progress import UserProgress
from app.schemas.task import TaskImport


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self.db.get(Task, task_id)

    async def get_next(self, user_id: int, subject: str, exam_type: str, session_id: int) -> Task | None:
        answered_subq = select(SessionAnswer.task_id).where(SessionAnswer.session_id == session_id)

        # Prioritize tasks user got wrong in past (weak spots)
        weak_subq = (
            select(UserProgress.task_number)
            .where(
                UserProgress.user_id == user_id,
                UserProgress.subject == subject,
                UserProgress.total_attempts > 0,
                UserProgress.correct_attempts * 1.0 / UserProgress.total_attempts < 0.5,
            )
        )

        stmt = (
            select(Task)
            .where(
                Task.subject == subject,
                Task.exam_type == exam_type,
                Task.is_active.is_(True),
                Task.id.not_in(answered_subq),
                Task.task_number.in_(weak_subq),
            )
            .order_by(func.random())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            stmt = (
                select(Task)
                .where(
                    Task.subject == subject,
                    Task.exam_type == exam_type,
                    Task.is_active.is_(True),
                    Task.id.not_in(answered_subq),
                )
                .order_by(func.random())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            task = result.scalar_one_or_none()

        return task

    async def import_tasks(self, items: list[TaskImport]) -> int:
        count = 0
        for item in items:
            if item.source_id:
                exists = await self.db.execute(
                    select(Task.id).where(Task.source_id == item.source_id)
                )
                if exists.scalar_one_or_none():
                    continue
            self.db.add(Task(**item.model_dump()))
            count += 1
        await self.db.commit()
        return count

    async def count(self, subject: str | None = None, exam_type: str | None = None) -> int:
        stmt = select(func.count(Task.id)).where(Task.is_active.is_(True))
        if subject:
            stmt = stmt.where(Task.subject == subject)
        if exam_type:
            stmt = stmt.where(Task.exam_type == exam_type)
        result = await self.db.execute(stmt)
        return result.scalar_one()
