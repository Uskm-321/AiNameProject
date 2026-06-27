from datetime import datetime
from enum import Enum
import secrets

from pwdlib import PasswordHash
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


password_hash = PasswordHash.recommended()


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserSegment(str, Enum):
    B = "B"
    C = "C"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BANNED = "BANNED"


class APIKeyStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    _password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.USER.value, nullable=False)
    user_segment: Mapped[str] = mapped_column(String(10), default=UserSegment.C.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value, nullable=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255))
    banned_until: Mapped[datetime | None] = mapped_column(DateTime)
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blacklist_reason: Mapped[str | None] = mapped_column(String(255))
    blacklisted_at: Mapped[datetime | None] = mapped_column(DateTime)
    invite_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        default=lambda: secrets.token_urlsafe(6),
        nullable=False,
    )
    invited_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __init__(self, *args, **kwargs):
        password = kwargs.pop("password", None)
        super().__init__(*args, **kwargs)
        if password:
            self.password = password

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = password_hash.hash(password)

    def check_password(self, password):
        return password_hash.verify(password, self._password)

    @property
    def is_admin(self) -> bool:
        return self.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "ADMIN", "SUPER_ADMIN"}

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value and not self.blacklisted


class EmailCode(Base):
    __tablename__ = "email_code"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class APIKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=APIKeyStatus.ACTIVE.value, nullable=False)
    total_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class APIKeyUsage(Base):
    __tablename__ = "api_key_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_key.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    cost: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class Invitation(Base):
    __tablename__ = "invitation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    invitee_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class CreditReward(Base):
    __tablename__ = "credit_reward"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    related_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
