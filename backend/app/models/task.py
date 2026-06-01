from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_subject_exam", "subject", "exam_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(8), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(128))
    task_number: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(String(512), nullable=False)
    hint: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(256))
    source_id: Mapped[str | None] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
