"""drop sensitive word severity

Revision ID: f4c8a1d2e3b9
Revises: e9d6a2b5c3f8
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c8a1d2e3b9"
down_revision: Union[str, Sequence[str], None] = "e9d6a2b5c3f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("sensitive_word_rule")}
    if "severity" in columns:
        op.drop_column("sensitive_word_rule", "severity")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("sensitive_word_rule")}
    if "severity" not in columns:
        op.add_column(
            "sensitive_word_rule",
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="BLOCK"),
        )
