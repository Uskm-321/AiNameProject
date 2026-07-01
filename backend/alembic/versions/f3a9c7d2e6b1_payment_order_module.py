"""payment order module

Revision ID: f3a9c7d2e6b1
Revises: c2b8f4a6d9e1
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c7d2e6b1"
down_revision: Union[str, Sequence[str], None] = "c2b8f4a6d9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("out_trade_no", sa.String(length=64), nullable=False),
        sa.Column("trade_no", sa.String(length=128), nullable=True),
        sa.Column("package_id", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_key.id"], name=op.f("fk_payment_order_api_key_id_api_key")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_payment_order_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_order")),
        sa.UniqueConstraint("out_trade_no", name=op.f("uq_payment_order_out_trade_no")),
    )


def downgrade() -> None:
    op.drop_table("payment_order")
