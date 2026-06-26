from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


RawPasswordStr = Annotated[str, Field(..., min_length=6, max_length=8)]
UserNameStr = Annotated[str, Field(min_length=4, max_length=8)]
UserRoleLiteral = Literal["USER", "ADMIN"]
UserSegmentLiteral = Literal["B", "C"]
UserStatusLiteral = Literal["ACTIVE", "BANNED"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: RawPasswordStr
    username: UserNameStr
    confirm_password: RawPasswordStr
    code: Annotated[str, Field(..., min_length=4, max_length=4)]

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
    role: UserRoleLiteral = "USER"
    user_segment: UserSegmentLiteral = "C"
    status: UserStatusLiteral = "ACTIVE"
    blacklisted: bool = False


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


class AdminUserListOut(BaseModel):
    total: int
    items: list[AdminUserOut]


class UserRoleUpdateIn(BaseModel):
    role: UserRoleLiteral


class UserSegmentUpdateIn(BaseModel):
    user_segment: UserSegmentLiteral


class UserBanIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
    banned_until: datetime | None = None


class UserBlacklistIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
