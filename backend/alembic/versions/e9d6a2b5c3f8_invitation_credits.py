"""invitation credits

Revision ID: e9d6a2b5c3f8
Revises: d8c5f1a4b2e7
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9d6a2b5c3f8"
down_revision: Union[str, Sequence[str], None] = "d8c5f1a4b2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("invite_code", sa.String(length=32), nullable=True))
    op.add_column("user", sa.Column("invited_by_user_id", sa.Integer(), nullable=True))
    op.add_column(
        "user",
        sa.Column("credits", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        op.f("fk_user_invited_by_user_id_user"),
        "user",
        "user",
        ["invited_by_user_id"],
        ["id"],
    )
    op.create_unique_constraint(op.f("uq_user_invite_code"), "user", ["invite_code"])
    op.create_table(
        "invitation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("inviter_id", sa.Integer(), nullable=False),
        sa.Column("invitee_id", sa.Integer(), nullable=False),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invitee_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["inviter_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invitee_id"),
    )
    op.create_table(
        "credit_reward",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("related_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["related_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("credit_reward")
    op.drop_table("invitation")
    op.drop_constraint(op.f("uq_user_invite_code"), "user", type_="unique")
    op.drop_constraint(op.f("fk_user_invited_by_user_id_user"), "user", type_="foreignkey")
    op.drop_column("user", "credits")
    op.drop_column("user", "invited_by_user_id")
    op.drop_column("user", "invite_code")
