from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


RawPasswordStr = Annotated[str, Field(..., min_length=6, max_length=8)]
UserNameStr = Annotated[str, Field(min_length=4, max_length=8)]
UserRoleLiteral = Literal["user", "admin", "super_admin", "USER", "ADMIN", "SUPER_ADMIN"]
UserSegmentLiteral = Literal["B", "C"]
UserStatusLiteral = Literal["ACTIVE", "BANNED"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: RawPasswordStr
    username: UserNameStr
    confirm_password: RawPasswordStr
    code: Annotated[str, Field(..., min_length=4, max_length=4)]
    invite_code: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def password_is_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords don't match")
        return self


class UserCreateSchema(BaseModel):
    email: EmailStr
    password: RawPasswordStr
    username: UserNameStr


class LoginIn(BaseModel):
    email: EmailStr
    password: RawPasswordStr


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: UserRoleLiteral = "user"
    user_segment: UserSegmentLiteral = "C"
    status: UserStatusLiteral = "ACTIVE"
    blacklisted: bool = False
    invite_code: str = ""
    credits: int = 0


class LoginOut(BaseModel):
    token: str
    user: UserSchema


class AdminUserOut(UserSchema):
    ban_reason: str | None = None
    banned_until: datetime | None = None
    blacklist_reason: str | None = None
    blacklisted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminManagedUserOut(AdminUserOut):
    today_usage: int = 0


class AdminUserListOut(BaseModel):
    total: int
    items: list[AdminManagedUserOut]


class AdminUserAPIKeyOut(BaseModel):
    id: int
    name: str
    key_masked: str
    status: str
    total_quota: int
    used_today: int
    total_used: int
    last_used_at: datetime | None = None
    created_at: datetime


class AdminUserDetailOut(BaseModel):
    user: AdminManagedUserOut
    api_keys: list[AdminUserAPIKeyOut]


class AdminUsersOverviewOut(BaseModel):
    total_users: int
    active_users_today: int
    total_usage: int


class AdminUserCreateIn(BaseModel):
    email: EmailStr
    password: RawPasswordStr
    username: Annotated[str, Field(..., min_length=3, max_length=8)]
    role: Literal["USER", "ADMIN"] = "USER"


class UserRoleUpdateIn(BaseModel):
    role: Literal["USER", "ADMIN"]


class UserSegmentUpdateIn(BaseModel):
    user_segment: UserSegmentLiteral


class UserBanIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
    banned_until: datetime | None = None


class UserBlacklistIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
