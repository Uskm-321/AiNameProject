import random
import string
from datetime import datetime
from typing import Annotated

from aiosmtplib import SMTPException, SMTPResponseException
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from core.redisconfig import get_redis_client
from dependencies import get_mail, get_session
from repository.user_repo import UserRepository
from schemas import ResponseOut
from schemas.user_schemas import LoginIn, LoginOut, RegisterIn, UserCreateSchema
from models.user import User, UserStatus

router = APIRouter(prefix="/auth", tags=["auth"])
auth_handler = AuthHandler()


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
        await redis_client.set(email, code, ex=300)
        return ResponseOut()
    except (SMTPResponseException, SMTPException) as error_str:
        if "-1" in str(error_str) and r"\x00" in str(error_str):
            await redis_client.set(email, code, ex=300)
            return ResponseOut()
        print(error_str)
        return ResponseOut(result="failure")


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

    email_code = await redis_client.get(userinfo.email)
    if not email_code or email_code != userinfo.code:
        raise HTTPException(400, detail="验证码错误或已过期")

    try:
        user_schema = UserCreateSchema(
            email=str(userinfo.email),
            password=str(userinfo.password),
            username=str(userinfo.username),
        )
        await user_repository.create(user_schema)
        await redis_client.delete(userinfo.email)
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

    token = auth_handler.encode_login_token(user.id)
    return {
        "token": token["access_token"],
        "user": user,
    }
