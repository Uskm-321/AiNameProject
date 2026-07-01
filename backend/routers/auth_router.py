import random
import string
from datetime import datetime
from time import time
from typing import Annotated

from aiosmtplib import SMTPException, SMTPResponseException
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from core.redisconfig import get_redis_client
from dependencies import get_mail, get_session
from repository.invitation_repo import InvitationRepository
from repository.user_repo import UserRepository
from schemas import ResponseOut
from schemas.user_schemas import LoginIn, LoginOut, RegisterIn, UserCreateSchema
from models.user import User, UserStatus

router = APIRouter(prefix="/auth", tags=["auth"])
auth_handler = AuthHandler()
_email_code_cache: dict[str, tuple[str, float]] = {}


async def _save_email_code(redis_client: Redis, email: str, code: str):
    try:
        await redis_client.set(email, code, ex=300)
    except RedisError as error:
        _email_code_cache[email] = (code, time() + 300)
        print(f"Redis unavailable, verification code stored in memory for {email}: {error}")


async def _get_email_code(redis_client: Redis, email: str):
    try:
        code = await redis_client.get(email)
        if code:
            return code
    except RedisError as error:
        print(f"Redis unavailable, reading verification code from memory for {email}: {error}")

    cached = _email_code_cache.get(email)
    if not cached:
        return None
    code, expires_at = cached
    if expires_at < time():
        _email_code_cache.pop(email, None)
        return None
    return code


async def _delete_email_code(redis_client: Redis, email: str):
    _email_code_cache.pop(email, None)
    try:
        await redis_client.delete(email)
    except RedisError as error:
        print(f"Redis unavailable, skipped deleting verification code for {email}: {error}")


@router.get("/code", response_model=ResponseOut)
async def get_email_code(
    email: Annotated[EmailStr, Query(...)],
    mail: FastMail = Depends(get_mail),
    session: AsyncSession = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client),
):
    source = string.digits * 4
    code = "".join(random.sample(source, 4))
    message = MessageSchema(
        subject="【ainame app】注册验证码",
        recipients=[email],
        body=f"您的验证码是：{code}，五分钟内有效!",
        subtype=MessageType.plain,
    )
    try:
        await mail.send_message(message)
        await _save_email_code(redis_client, str(email), code)
        return ResponseOut()
    except (SMTPResponseException, SMTPException) as error_str:
        if "-1" in str(error_str) and r"\x00" in str(error_str):
            await _save_email_code(redis_client, str(email), code)
            return ResponseOut()
        await _save_email_code(redis_client, str(email), code)
        print(f"Email verification code for {email}: {code}")
        print(error_str)
        raise HTTPException(status_code=503, detail="邮件发送失败，请检查邮箱配置；开发调试验证码已打印在后端终端")
    except Exception as error:
        await _save_email_code(redis_client, str(email), code)
        print(f"Email verification code for {email}: {code}")
        print(error)
        raise HTTPException(status_code=503, detail="验证码发送失败，请查看后端终端错误信息")


@router.post("/register", response_model=ResponseOut)
async def register(
    userinfo: RegisterIn,
    session: AsyncSession = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client),
):
    user_repository = UserRepository(session=session)
    email_exist = await user_repository.email_is_exist(email=str(userinfo.email))
    if email_exist:
        raise HTTPException(400, detail="该邮箱已注册")

    email_code = await _get_email_code(redis_client, str(userinfo.email))
    if not email_code or email_code != userinfo.code:
        raise HTTPException(400, detail="验证码错误或已过期")

    try:
        user_schema = UserCreateSchema(
            email=str(userinfo.email),
            password=str(userinfo.password),
            username=str(userinfo.username),
        )
        invitation_repository = InvitationRepository(session=session)
        await invitation_repository.create_user(user_schema, userinfo.invite_code)
        await _delete_email_code(redis_client, str(userinfo.email))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return ResponseOut()


@router.post("/login", response_model=LoginOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    user_repository = UserRepository(session=session)
    user: User | None = await user_repository.get_by_email(str(data.email))
    if not user:
        raise HTTPException(status_code=400, detail="该用户不存在")
    if not user.check_password(data.password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    if user.status == UserStatus.BANNED.value and (not user.banned_until or user.banned_until > datetime.now()):
        raise HTTPException(status_code=403, detail="用户已封禁")
    if user.blacklisted:
        raise HTTPException(status_code=403, detail="用户已进入黑名单")
    if not user.invite_code:
        invitation_repository = InvitationRepository(session=session)
        user, _, _ = await invitation_repository.summary(user.id)

    token = auth_handler.encode_login_token(user.id)
    return {
        "token": token["access_token"],
        "user": user,
    }
