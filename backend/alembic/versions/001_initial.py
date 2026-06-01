"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64)),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("last_name", sa.String(128)),
        sa.Column("subscription_type", sa.String(16), nullable=False, server_default="free"),
        sa.Column("subscription_end", sa.DateTime()),
        sa.Column("onboarding_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("selected_exam", sa.String(8)),
        sa.Column("selected_subjects", JSONB),
        sa.Column("referral_code", sa.String(16)),
        sa.Column("referred_by", sa.BigInteger()),
        sa.Column("daily_ai_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_ai_reset_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_referral_code", "users", ["referral_code"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("exam_type", sa.String(8), nullable=False),
        sa.Column("topic", sa.String(128)),
        sa.Column("task_number", sa.Integer()),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", JSONB),
        sa.Column("correct_answer", sa.String(512), nullable=False),
        sa.Column("hint", sa.Text()),
        sa.Column("source_url", sa.String(256)),
        sa.Column("source_id", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tasks_subject_exam", "tasks", ["subject", "exam_type", "is_active"])
    op.create_index("ix_tasks_source_id", "tasks", ["source_id"])

    op.create_table(
        "test_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("exam_type", sa.String(8), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False, server_default="practice"),
        sa.Column("topic", sa.String(128)),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_index("ix_sessions_user_id", "test_sessions", ["user_id"])

    op.create_table(
        "session_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.BigInteger(), sa.ForeignKey("test_sessions.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("user_answer", sa.Text()),
        sa.Column("is_correct", sa.Boolean()),
        sa.Column("ai_explanation", sa.Text()),
        sa.Column("time_spent", sa.Integer()),
        sa.Column("answered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_answers_session_id", "session_answers", ["session_id"])

    op.create_table(
        "user_progress",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("task_number", sa.Integer()),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practiced_at", sa.DateTime()),
    )
    op.create_index("ix_progress_user_id", "user_progress", ["user_id"])
    op.create_unique_constraint(
        "uq_progress_user_subject_task",
        "user_progress",
        ["user_id", "subject", "task_number"],
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("payment_id", sa.String(128)),
        sa.Column("amount", sa.Integer()),
        sa.Column("currency", sa.String(8), server_default="RUB"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_payment_id", "subscriptions", ["payment_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("user_progress")
    op.drop_table("session_answers")
    op.drop_table("test_sessions")
    op.drop_table("tasks")
    op.drop_table("users")
