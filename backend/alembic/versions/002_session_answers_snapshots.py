"""Add question/answer snapshots to session_answers

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_answers", sa.Column("question_text", sa.Text(), nullable=True))
    op.add_column("session_answers", sa.Column("correct_answer_snapshot", sa.String(512), nullable=True))
    op.add_column("session_answers", sa.Column("subject", sa.String(32), nullable=True))
    op.add_column("session_answers", sa.Column("task_number", sa.Integer(), nullable=True))
    op.add_column("session_answers", sa.Column("shown_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_answers", "shown_at")
    op.drop_column("session_answers", "task_number")
    op.drop_column("session_answers", "subject")
    op.drop_column("session_answers", "correct_answer_snapshot")
    op.drop_column("session_answers", "question_text")
