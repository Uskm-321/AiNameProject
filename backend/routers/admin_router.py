from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.admin import AdminActionType
from models.user import User
from repository.user_repo import AdminRepository, UserRepository
from schemas import ResponseOut
from schemas.admin_schemas import (
    AdminActionLogListOut,
    AdminReviewIn,
    ModerationRecordListOut,
    SensitiveWordIn,
    SensitiveWordOut,
)
from schemas.user_schemas import (
    AdminUserListOut,
    AdminUserOut,
    UserBanIn,
    UserBlacklistIn,
    UserSegmentLiteral,
    UserStatusLiteral,
    UserRoleUpdateIn,
    UserSegmentUpdateIn,
)

auth_handler = AuthHandler()
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    user_segment: UserSegmentLiteral | None = None,
    status: UserStatusLiteral | None = None,
    blacklisted: bool | None = None,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = UserRepository(session=session)
    offset = (page - 1) * page_size
    items = await repository.list_users(
        offset=offset,
        limit=page_size,
        keyword=keyword,
        user_segment=user_segment,
        status=status,
        blacklisted=blacklisted,
    )
    total = await repository.count_users(
        keyword=keyword,
        user_segment=user_segment,
        status=status,
        blacklisted=blacklisted,
    )
    return AdminUserListOut(total=total or 0, items=items)


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user_profile(
    user_id: int,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = UserRepository(session=session)
    user = await repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
async def update_user_role(
    user_id: int,
    data: UserRoleUpdateIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.update_user_flags(user_id, role=data.role)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.ROLE_CHANGE.value,
        detail=f"role={data.role}",
        target_user_id=user_id,
    )
    return user


@router.patch("/users/{user_id}/segment", response_model=AdminUserOut)
async def update_user_segment(
    user_id: int,
    data: UserSegmentUpdateIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.update_user_flags(user_id, user_segment=data.user_segment)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.SEGMENT_CHANGE.value,
        detail=f"user_segment={data.user_segment}",
        target_user_id=user_id,
    )
    return user


@router.post("/users/{user_id}/ban", response_model=AdminUserOut)
async def ban_user(
    user_id: int,
    data: UserBanIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.set_ban(user_id, ban_reason=data.reason, banned_until=data.banned_until)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.BAN.value,
        detail=f"reason={data.reason or ''}; banned_until={data.banned_until or ''}",
        target_user_id=user_id,
    )
    return user


@router.post("/users/{user_id}/unban", response_model=AdminUserOut)
async def unban_user(
    user_id: int,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.unset_ban(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.UNBAN.value,
        target_user_id=user_id,
    )
    return user


@router.post("/users/{user_id}/blacklist", response_model=AdminUserOut)
async def add_blacklist(
    user_id: int,
    data: UserBlacklistIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.add_blacklist(user_id, reason=data.reason)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.BLACKLIST.value,
        detail=f"reason={data.reason or ''}",
        target_user_id=user_id,
    )
    return user


@router.delete("/users/{user_id}/blacklist", response_model=AdminUserOut)
async def remove_blacklist(
    user_id: int,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    user = await user_repository.remove_blacklist(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.UNBLACKLIST.value,
        target_user_id=user_id,
    )
    return user


@router.get("/sensitive-words", response_model=list[SensitiveWordOut])
async def list_sensitive_words(
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    return await repository.list_sensitive_words()


@router.post("/sensitive-words", response_model=SensitiveWordOut)
async def upsert_sensitive_word(
    data: SensitiveWordIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    rule = await repository.create_sensitive_word(
        word=data.word,
        reason=data.reason,
        severity=data.severity,
        created_by=current_admin.id,
    )
    await repository.create_action_log(
        current_admin.id,
        AdminActionType.SENSITIVE_WORD_UPSERT.value,
        detail=f"word={data.word}; severity={data.severity}; reason={data.reason or ''}",
    )
    return rule


@router.delete("/sensitive-words/{word}", response_model=ResponseOut)
async def disable_sensitive_word(
    word: str,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    rule = await repository.disable_sensitive_word(word)
    if not rule:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    await repository.create_action_log(
        current_admin.id,
        AdminActionType.SENSITIVE_WORD_DISABLE.value,
        detail=f"word={word}",
    )
    return ResponseOut()


@router.delete("/sensitive-words/{word}/remove", response_model=ResponseOut)
async def delete_sensitive_word(
    word: str,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    rule = await repository.delete_sensitive_word(word)
    if not rule:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    await repository.create_action_log(
        current_admin.id,
        AdminActionType.SENSITIVE_WORD_DELETE.value,
        detail=f"word={word}",
    )
    return ResponseOut()


@router.get("/moderation-records", response_model=ModerationRecordListOut)
async def list_moderation_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    offset = (page - 1) * page_size
    items = await repository.list_moderation_records(offset=offset, limit=page_size)
    total = await repository.count_moderation_records()
    return ModerationRecordListOut(total=total or 0, items=items)


@router.post("/moderation-records/{record_id}/review", response_model=ResponseOut)
async def review_moderation_record(
    record_id: int,
    data: AdminReviewIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    record = await repository.mark_moderation_reviewed(record_id, current_admin.id, note=data.note)
    if not record:
        raise HTTPException(status_code=404, detail="巡查记录不存在")
    await repository.create_action_log(
        current_admin.id,
        AdminActionType.MODERATION_REVIEW.value,
        detail=f"record_id={record_id}; note={data.note or ''}",
    )
    return ResponseOut()


@router.get("/action-logs", response_model=AdminActionLogListOut)
async def list_action_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session=session)
    offset = (page - 1) * page_size
    items = await repository.list_actions(offset=offset, limit=page_size)
    total = await repository.count_actions()
    return AdminActionLogListOut(total=total or 0, items=items)
