from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128))
    subscription_type: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    subscription_end: Mapped[datetime | None] = mapped_column(DateTime)
    onboarding_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_exam: Mapped[str | None] = mapped_column(String(8))
    selected_subjects: Mapped[list[str] | None] = mapped_column(JSON)
    referral_code: Mapped[str | None] = mapped_column(String(16), index=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger)
    daily_ai_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_ai_reset_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
