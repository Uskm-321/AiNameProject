from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class CommunityPoll(Base):
    __tablename__ = "community_poll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    naming_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_reason: Mapped[str | None] = mapped_column(String(255))
    hidden_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class CommunityPollOption(Base):
    __tablename__ = "community_poll_option"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("community_poll.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    reference: Mapped[str | None] = mapped_column(Text)
    moral: Mapped[str | None] = mapped_column(Text)
    style_reason: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    domains_json: Mapped[str | None] = mapped_column(Text)
    votes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CommunityPollVote(Base):
    __tablename__ = "community_poll_vote"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_community_poll_vote_poll_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("community_poll.id"), nullable=False)
    option_id: Mapped[int] = mapped_column(ForeignKey("community_poll_option.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
