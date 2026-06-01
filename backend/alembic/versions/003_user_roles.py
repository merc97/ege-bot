"""Add role and parent-student linking to users

Revision ID: 003
Revises: 002
Create Date: 2026-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="student"))
    op.add_column("users", sa.Column("linked_student_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("users", sa.Column("parent_linked_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_linked_student_id", "users", ["linked_student_id"])


def downgrade() -> None:
    op.drop_index("ix_users_linked_student_id", "users")
    op.drop_column("users", "parent_linked_at")
    op.drop_column("users", "linked_student_id")
    op.drop_column("users", "role")
