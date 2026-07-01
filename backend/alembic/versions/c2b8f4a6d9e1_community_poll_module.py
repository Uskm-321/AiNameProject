"""community poll module

Revision ID: c2b8f4a6d9e1
Revises: e9d6a2b5c3f8
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2b8f4a6d9e1"
down_revision: Union[str, Sequence[str], None] = "e9d6a2b5c3f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_poll",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("naming_type", sa.String(length=50), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hidden_reason", sa.String(length=255), nullable=True),
        sa.Column("hidden_by", sa.Integer(), nullable=True),
        sa.Column("hidden_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["hidden_by"], ["user.id"], name=op.f("fk_community_poll_hidden_by_user")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_poll_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_poll")),
    )
    op.create_table(
        "community_poll_option",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("moral", sa.Text(), nullable=True),
        sa.Column("style_reason", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("domains_json", sa.Text(), nullable=True),
        sa.Column("votes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["community_poll.id"], name=op.f("fk_community_poll_option_poll_id_community_poll")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_poll_option")),
    )
    op.create_table(
        "community_poll_vote",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["community_poll_option.id"], name=op.f("fk_community_poll_vote_option_id_community_poll_option")),
        sa.ForeignKeyConstraint(["poll_id"], ["community_poll.id"], name=op.f("fk_community_poll_vote_poll_id_community_poll")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_community_poll_vote_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_poll_vote")),
        sa.UniqueConstraint("poll_id", "user_id", name="uq_community_poll_vote_poll_user"),
    )


def downgrade() -> None:
    op.drop_table("community_poll_vote")
    op.drop_table("community_poll_option")
    op.drop_table("community_poll")
