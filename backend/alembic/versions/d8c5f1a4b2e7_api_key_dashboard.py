"""api key dashboard fields

Revision ID: d8c5f1a4b2e7
Revises: b7a4c2d9e1f0
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8c5f1a4b2e7"
down_revision: Union[str, Sequence[str], None] = "b7a4c2d9e1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_key_usage",
        sa.Column("status", sa.String(length=20), server_default="success", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("api_key_usage", "status")
