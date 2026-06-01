from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.session import TestSession, SessionAnswer
from app.models.task import Task
from app.models.progress import UserProgress
from app.models.user import User
from app.schemas.session import AnswerResult
from app.services.ai_service import AIService
from app.services.user_service import UserService


def _normalize(answer: str) -> str:
    return answer.strip().lower().replace(",", ".").replace(" ", "")


class SessionService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis
        self.ai = AIService(redis)

    async def create(self, user_id: int, subject: str, exam_type: str, mode: str = "practice") -> TestSession:
        session = TestSession(user_id=user_id, subject=subject, exam_type=exam_type, mode=mode)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def submit_answer(
        self,
        session_id: int,
        task_id: int,
        user_answer: str,
        time_spent: int | None,
        want_ai: bool,
    ) -> AnswerResult:
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        is_correct = _normalize(user_answer) == _normalize(task.correct_answer)

        ai_explanation: str | None = None
        if not is_correct and want_ai:
            session = await self.db.get(TestSession, session_id)
            user = await self.db.get(User, session.user_id) if session else None
            svc = UserService(self.db)
            if user and await svc.can_use_ai(user):
                ai_explanation = await self.ai.get_explanation(
                    task_id=task.id,
                    subject=task.subject,
                    task_number=task.task_number,
                    question_text=task.question_text,
                    correct_answer=task.correct_answer,
                    user_answer=user_answer,
                )
                if ai_explanation:
                    await svc.increment_ai_usage(user.id)

        self.db.add(SessionAnswer(
            session_id=session_id,
            task_id=task_id,
            subject=task.subject,
            task_number=task.task_number,
            question_text=task.question_text,
            correct_answer_snapshot=task.correct_answer,
            user_answer=user_answer,
            is_correct=is_correct,
            ai_explanation=ai_explanation,
            time_spent=time_spent,
            shown_at=datetime.utcnow(),
        ))

        await self.db.execute(
            update(TestSession)
            .where(TestSession.id == session_id)
            .values(
                total_questions=TestSession.total_questions + 1,
                correct_answers=TestSession.correct_answers + (1 if is_correct else 0),
            )
        )
        await self._upsert_progress(session_id, task, is_correct)
        await self.db.commit()

        return AnswerResult(
            is_correct=is_correct,
            correct_answer=task.correct_answer,
            hint=task.hint,
            ai_explanation=ai_explanation,
        )

    async def _upsert_progress(self, session_id: int, task: Task, is_correct: bool) -> None:
        session = await self.db.get(TestSession, session_id)
        if not session:
            return
        result = await self.db.execute(
            select(UserProgress).where(
                UserProgress.user_id == session.user_id,
                UserProgress.subject == task.subject,
                UserProgress.task_number == task.task_number,
            )
        )
        prog = result.scalar_one_or_none()
        if prog:
            prog.total_attempts += 1
            if is_correct:
                prog.correct_attempts += 1
            prog.last_practiced_at = datetime.utcnow()
        else:
            self.db.add(UserProgress(
                user_id=session.user_id,
                subject=task.subject,
                task_number=task.task_number,
                total_attempts=1,
                correct_attempts=1 if is_correct else 0,
                last_practiced_at=datetime.utcnow(),
            ))

    async def finish(self, session_id: int) -> TestSession:
        session = await self.db.get(TestSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.status = "finished"
        session.finished_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session
