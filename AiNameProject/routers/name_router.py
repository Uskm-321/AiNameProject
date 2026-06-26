import json
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from core.moderation import ModerationService
from core.workflow import feedback_names, get_names_v2
from dependencies import get_session
from models.user import User
from schemas.name import FeedbackIn, NameIn, NameOut, NameWithThreadOut

auth_handler = AuthHandler()
router = APIRouter(prefix="/name", tags=["name"])


def _extract_names(name_result):
    if isinstance(name_result, dict):
        names = name_result.get("names", [])
        return names.get("names", []) if isinstance(names, dict) else names
    return []


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


@router.post("/generate", response_model=NameWithThreadOut)
async def take_names_first_time(
    name_info: NameIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        moderation = ModerationService(session=session)
        request_text = json.dumps(name_info.model_dump(), ensure_ascii=False)
        await moderation.ensure_request_allowed(current_user.id, "name.generate.input", request_text)
        name_result = await get_names_v2(name_info, current_user.id)
        final_names = _extract_names(name_result)
        await moderation.ensure_names_allowed(current_user.id, "name.generate.output", request_text, final_names)
        return NameWithThreadOut(thread_id=name_result["thread_id"], names=final_names)
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"数据格式异常，缺少字段: {e}")
    except Exception as e:
        print(f"/generate error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
