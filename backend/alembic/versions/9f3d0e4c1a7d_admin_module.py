"""admin module

Revision ID: 9f3d0e4c1a7d
Revises: 50731e824950
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3d0e4c1a7d"
down_revision: Union[str, Sequence[str], None] = "50731e824950"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"))
    op.add_column("user", sa.Column("user_segment", sa.String(length=10), nullable=False, server_default="C"))
    op.add_column("user", sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"))
    op.add_column("user", sa.Column("ban_reason", sa.String(length=255), nullable=True))
    op.add_column("user", sa.Column("banned_until", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("blacklisted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user", sa.Column("blacklist_reason", sa.String(length=255), nullable=True))
    op.add_column("user", sa.Column("blacklisted_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("user", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    op.create_table(
        "sensitive_word_rule",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("word", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], name=op.f("fk_sensitive_word_rule_created_by_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sensitive_word_rule")),
        sa.UniqueConstraint("word", name=op.f("uq_sensitive_word_rule_word")),
    )
    op.create_table(
        "moderation_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("matched_words", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("review_note", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"], name=op.f("fk_moderation_record_reviewed_by_user")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_moderation_record_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_record")),
    )
    op.create_table(
        "admin_action_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["user.id"], name=op.f("fk_admin_action_log_admin_user_id_user")),
        sa.ForeignKeyConstraint(["target_user_id"], ["user.id"], name=op.f("fk_admin_action_log_target_user_id_user")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_action_log")),
    )


def downgrade() -> None:
    op.drop_table("admin_action_log")
    op.drop_table("moderation_record")
    op.drop_table("sensitive_word_rule")
    op.drop_column("user", "updated_at")
    op.drop_column("user", "created_at")
    op.drop_column("user", "blacklisted_at")
    op.drop_column("user", "blacklist_reason")
    op.drop_column("user", "blacklisted")
    op.drop_column("user", "banned_until")
    op.drop_column("user", "ban_reason")
    op.drop_column("user", "status")
    op.drop_column("user", "user_segment")
    op.drop_column("user", "role")
