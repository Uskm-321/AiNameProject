"""payment order qr code

Revision ID: a6d2f3c9b8e4
Revises: f3a9c7d2e6b1
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6d2f3c9b8e4"
down_revision: Union[str, Sequence[str], None] = "f3a9c7d2e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payment_order", sa.Column("qr_code", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_order", "qr_code")
