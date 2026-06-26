from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class ModerationDecision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"


class ReviewStatus(str, Enum):
    AUTO_PASS = "AUTO_PASS"
    AUTO_BLOCK = "AUTO_BLOCK"
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"


class SensitiveWordSeverity(str, Enum):
    BLOCK = "BLOCK"
    WARN = "WARN"


class AdminActionType(str, Enum):
    BAN = "BAN"
    UNBAN = "UNBAN"
    BLACKLIST = "BLACKLIST"
    UNBLACKLIST = "UNBLACKLIST"
    ROLE_CHANGE = "ROLE_CHANGE"
    SEGMENT_CHANGE = "SEGMENT_CHANGE"
    SENSITIVE_WORD_UPSERT = "SENSITIVE_WORD_UPSERT"
    SENSITIVE_WORD_DISABLE = "SENSITIVE_WORD_DISABLE"
    MODERATION_REVIEW = "MODERATION_REVIEW"


class SensitiveWordRule(Base):
    __tablename__ = "sensitive_word_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20), default=SensitiveWordSeverity.BLOCK.value, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class ModerationRecord(Base):
    __tablename__ = "moderation_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text)
    matched_words: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default=ReviewStatus.PENDING.value, nullable=False)
    review_note: Mapped[str | None] = mapped_column(String(255))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class AdminActionLog(Base):
    __tablename__ = "admin_action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
