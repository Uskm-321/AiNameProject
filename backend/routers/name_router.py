import json
import traceback
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS

from core.auth import AuthHandler
from core.moderation import ModerationService
from core.workflow import feedback_names, get_names_v2
from dependencies import get_session
from models.user import User, UserStatus
from repository.api_key_repo import APIKeyRepository
from repository.user_repo import UserRepository
from schemas.name import FeedbackIn, NameIn, NameOut, NameWithThreadOut

auth_handler = AuthHandler()
router = APIRouter(prefix="/name", tags=["name"])
optional_bearer = HTTPBearer(auto_error=False)


@dataclass
class GenerateIdentity:
    user: User
    api_key_id: int | None = None


def _extract_names(name_result):
    if isinstance(name_result, dict):
        names = name_result.get("names", [])
        return names.get("names", []) if isinstance(names, dict) else names
    return []


async def generate_auth_dependency(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    auth: HTTPAuthorizationCredentials | None = Security(optional_bearer),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)

    if x_api_key:
        api_key_repository = APIKeyRepository(session=session)
        api_key = await api_key_repository.get_active_key(x_api_key)
        if not api_key:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="API Key 无效或已禁用")
        user = await user_repository.get_by_id(api_key.user_id)
        if not user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="用户不存在")
        user = await user_repository.clear_expired_ban(user)
        if user.status == UserStatus.BANNED.value and (not user.banned_until or user.banned_until > datetime.now()):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="用户已封禁")
        if user.blacklisted:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="用户已进入黑名单")
        return GenerateIdentity(user=user, api_key_id=api_key.id)

    if auth:
        user_id = int(auth_handler.decode_access_token(auth.credentials))
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="用户不存在")
        user = await user_repository.clear_expired_ban(user)
        if user.status == UserStatus.BANNED.value and (not user.banned_until or user.banned_until > datetime.now()):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="用户已封禁")
        if user.blacklisted:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="用户已进入黑名单")
        return GenerateIdentity(user=user)

    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="请登录或提供 X-API-Key")


@router.post("/get_names", response_model=NameOut)
async def get_names(
    name_info: NameIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        moderation = ModerationService(session=session)
        request_text = json.dumps(name_info.model_dump(), ensure_ascii=False)
        await moderation.ensure_request_allowed(current_user.id, "name.get_names.input", request_text)
        name_result = await get_names_v2(name_info, current_user.id)
        names_list = _extract_names(name_result)
        await moderation.ensure_names_allowed(current_user.id, "name.get_names.output", request_text, names_list)
        return NameOut(names=names_list)
    except HTTPException:
        raise
    except Exception as e:
        print(f"/get_names error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成名字失败: {str(e)}")


@router.post("/npc", response_model=NameWithThreadOut)
@router.post("/novel-character", response_model=NameWithThreadOut)
@router.post("/place", response_model=NameWithThreadOut)
@router.post("/generate", response_model=NameWithThreadOut)
async def take_names_first_time(
    name_info: NameIn,
    request: Request,
    identity: GenerateIdentity = Depends(generate_auth_dependency),
    session: AsyncSession = Depends(get_session),
):
    usage_id = None
    request_succeeded = False
    api_key_repository = APIKeyRepository(session=session)
    try:
        current_user = identity.user
        endpoint_category = {
            "/name/npc": "NPC",
            "/name/novel-character": "小说角色",
            "/name/place": "地名",
        }.get(request.url.path)
        if endpoint_category:
            name_info = name_info.model_copy(update={"category": endpoint_category})
        if identity.api_key_id is not None:
            key_for_quota = await api_key_repository.get_active_key(request.headers.get("X-API-Key", ""))
            if not key_for_quota:
                raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="API Key 无效或已禁用")
            api_key, quota_error, usage_id = await api_key_repository.consume_quota(
                key_for_quota,
                request.url.path,
            )
            if quota_error == "quota_exceeded":
                raise HTTPException(status_code=HTTP_429_TOO_MANY_REQUESTS, detail="API Key 今日调用额度已用完")
            if quota_error:
                raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="API Key 无效或已禁用")

        moderation = ModerationService(session=session)
        request_text = json.dumps(name_info.model_dump(), ensure_ascii=False)
        await moderation.ensure_request_allowed(current_user.id, "name.generate.input", request_text)
        name_result = await get_names_v2(name_info, current_user.id)
        final_names = _extract_names(name_result)
        await moderation.ensure_names_allowed(current_user.id, "name.generate.output", request_text, final_names)
        request_succeeded = True
        return NameWithThreadOut(thread_id=name_result["thread_id"], names=final_names)
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"数据格式异常，缺少字段: {e}")
    except Exception as e:
        print(f"/generate error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if usage_id is not None:
            await api_key_repository.mark_usage_status(
                usage_id,
                "success" if request_succeeded else "failed",
            )


@router.post("/feedback", response_model=NameWithThreadOut)
async def take_names_feedback(
    data: FeedbackIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        moderation = ModerationService(session=session)
        request_text = json.dumps(data.model_dump(), ensure_ascii=False)
        await moderation.ensure_request_allowed(current_user.id, "name.feedback.input", request_text)
        result = await feedback_names(data, current_user.id)
        final_names = _extract_names(result)
        await moderation.ensure_names_allowed(current_user.id, "name.feedback.output", request_text, final_names)
        return NameWithThreadOut(thread_id=result["thread_id"], names=final_names)
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"反馈数据格式异常: {e}")
    except Exception as e:
        print(f"/feedback error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
