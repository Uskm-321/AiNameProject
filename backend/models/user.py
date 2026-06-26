from datetime import datetime
from enum import Enum

from pwdlib import PasswordHash
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


password_hash = PasswordHash.recommended()


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserSegment(str, Enum):
    B = "B"
    C = "C"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BANNED = "BANNED"


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
        return self.role == UserRole.ADMIN.value

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value and not self.blacklisted


class EmailCode(Base):
    __tablename__ = "email_code"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
