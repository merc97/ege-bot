from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    telegram_id: int
    subject: str
    exam_type: str
    mode: str = "practice"


class AnswerSubmit(BaseModel):
    task_id: int
    user_answer: str
    time_spent: int | None = None
    want_ai: bool = True


class AnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    hint: str | None = None
    ai_explanation: str | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    exam_type: str
    mode: str
    total_questions: int
    correct_answers: int
    status: str
    started_at: datetime
    finished_at: datetime | None


class ProgressSubject(BaseModel):
    subject: str
    total_attempts: int
    correct_attempts: int
    accuracy: float
    weak_tasks: list[int]


class ProgressOut(BaseModel):
    telegram_id: int
    subjects: list[ProgressSubject]
    total_sessions: int
    streak_days: int
