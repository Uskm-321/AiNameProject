"""api key module

Revision ID: b7a4c2d9e1f0
Revises: 9f3d0e4c1a7d
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7a4c2d9e1f0"
down_revision: Union[str, Sequence[str], None] = "9f3d0e4c1a7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_quota", sa.Integer(), nullable=False),
        sa.Column("used_today", sa.Integer(), nullable=False),
        sa.Column("total_used", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_api_key_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_key")),
        sa.UniqueConstraint("key", name=op.f("uq_api_key_key")),
    )
    op.create_table(
        "api_key_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_key.id"], name=op.f("fk_api_key_usage_api_key_id_api_key")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_api_key_usage_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_key_usage")),
    )


def downgrade() -> None:
    op.drop_table("api_key_usage")
    op.drop_table("api_key")
