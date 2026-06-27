from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.admin import AdminActionType
from models.user import APIKey, APIKeyStatus, APIKeyUsage, User, UserRole
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
    AdminUserCreateIn,
    AdminManagedUserOut,
    AdminUserAPIKeyOut,
    AdminUserDetailOut,
    AdminUserListOut,
    AdminUserOut,
    AdminUsersOverviewOut,
    UserBanIn,
    UserBlacklistIn,
    UserSegmentLiteral,
    UserStatusLiteral,
    UserRoleUpdateIn,
    UserSegmentUpdateIn,
)

auth_handler = AuthHandler()
router = APIRouter(prefix="/admin", tags=["admin"])
SUPER_ADMIN_ROLES = {UserRole.SUPER_ADMIN.value, "SUPER_ADMIN"}


def _managed_user(user: User, today_usage: int = 0) -> AdminManagedUserOut:
    return AdminManagedUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        user_segment=user.user_segment,
        status=user.status,
        blacklisted=user.blacklisted,
        ban_reason=user.ban_reason,
        banned_until=user.banned_until,
        blacklist_reason=user.blacklist_reason,
        blacklisted_at=user.blacklisted_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        today_usage=today_usage,
    )


def _ensure_can_manage_target(current_admin: User, target_user: User) -> None:
    if current_admin.id == target_user.id:
        raise HTTPException(status_code=403, detail="不能操作自己的账号")
    target_role = str(target_user.role).lower()
    if target_role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="不能操作超级管理员")
    if current_admin.role not in SUPER_ADMIN_ROLES and target_role != UserRole.USER.value:
        raise HTTPException(status_code=403, detail="普通管理员只能管理普通用户")


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
    start_today = datetime.combine(datetime.now().date(), time.min)
    async with session.begin():
        usage_rows = (
            await session.execute(
                select(APIKeyUsage.user_id, func.coalesce(func.sum(APIKeyUsage.cost), 0))
                .where(APIKeyUsage.created_at >= start_today)
                .group_by(APIKeyUsage.user_id)
            )
        ).all()
    usage_by_user = {user_id: int(used or 0) for user_id, used in usage_rows}
    return AdminUserListOut(
        total=total or 0,
        items=[_managed_user(user, usage_by_user.get(user.id, 0)) for user in items],
    )


@router.get("/users/overview", response_model=AdminUsersOverviewOut)
async def users_overview(
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    start_today = datetime.combine(datetime.now().date(), time.min)
    async with session.begin():
        total_users = await session.scalar(select(func.count(User.id)))
        active_users_today = await session.scalar(
            select(func.count(func.distinct(APIKeyUsage.user_id))).where(
                APIKeyUsage.created_at >= start_today
            )
        )
        total_usage = await session.scalar(select(func.coalesce(func.sum(APIKeyUsage.cost), 0)))
    return AdminUsersOverviewOut(
        total_users=total_users or 0,
        active_users_today=active_users_today or 0,
        total_usage=total_usage or 0,
    )


@router.post("/users", response_model=AdminUserOut)
async def create_user(
    data: AdminUserCreateIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以创建账号")

    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    if await user_repository.get_by_email(data.email):
        raise HTTPException(status_code=400, detail="邮箱已存在")
    if await user_repository.get_by_username(data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = await user_repository.create_admin_user(
        email=str(data.email),
        username=data.username,
        password=data.password,
        role=data.role,
    )
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.CREATE_USER.value,
        detail=f"email={data.email}; username={data.username}; role={data.role}",
        target_user_id=user.id,
    )
    return user


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
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以修改用户角色")
    if current_admin.id == user_id:
        raise HTTPException(status_code=403, detail="不能修改自己的角色")

    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    target_user = await user_repository.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.role in SUPER_ADMIN_ROLES and target_user.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=400, detail="系统只能有 1 个超级管理员，不能新增超级管理员")
    if target_user.role in SUPER_ADMIN_ROLES and data.role not in SUPER_ADMIN_ROLES:
        super_admin_count = await user_repository.count_super_admins()
        if (super_admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留 1 个超级管理员")

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
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以修改用户画像")
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
    target_user = await user_repository.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    _ensure_can_manage_target(current_admin, target_user)
    user = await user_repository.set_ban(user_id, ban_reason=data.reason, banned_until=data.banned_until)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.BAN.value,
        detail=(
            f"reason={data.reason or ''}; banned_until={data.banned_until or ''}; "
            "active_api_keys=disabled"
        ),
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
    target_user = await user_repository.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    _ensure_can_manage_target(current_admin, target_user)
    user = await user_repository.unset_ban(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.UNBAN.value,
        target_user_id=user_id,
    )
    return user


@router.get("/users/{user_id}/detail", response_model=AdminUserDetailOut)
async def get_user_detail(
    user_id: int,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = UserRepository(session=session)
    user = await repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    start_today = datetime.combine(datetime.now().date(), time.min)
    async with session.begin():
        today_usage = await session.scalar(
            select(func.coalesce(func.sum(APIKeyUsage.cost), 0)).where(
                APIKeyUsage.user_id == user_id,
                APIKeyUsage.created_at >= start_today,
            )
        )
        api_keys = list(
            await session.scalars(
                select(APIKey)
                .where(APIKey.user_id == user_id, APIKey.status != APIKeyStatus.DELETED.value)
                .order_by(APIKey.id.desc())
            )
        )
    today = datetime.now().date()
    return AdminUserDetailOut(
        user=_managed_user(user, int(today_usage or 0)),
        api_keys=[
            AdminUserAPIKeyOut(
                id=item.id,
                name=item.name,
                key_masked=item.key if len(item.key) <= 12 else f"{item.key[:7]}...{item.key[-4:]}",
                status=item.status,
                total_quota=item.total_quota,
                used_today=(
                    item.used_today
                    if item.last_used_at and item.last_used_at.date() == today
                    else 0
                ),
                total_used=item.total_used,
                last_used_at=item.last_used_at,
                created_at=item.created_at,
            )
            for item in api_keys
        ],
    )


@router.delete("/users/{user_id}", response_model=ResponseOut)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以删除用户")
    if current_admin.id == user_id:
        raise HTTPException(status_code=403, detail="不能删除自己")

    user_repository = UserRepository(session=session)
    admin_repository = AdminRepository(session=session)
    target_user = await user_repository.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target_user.role in SUPER_ADMIN_ROLES:
        super_admin_count = await user_repository.count_super_admins()
        if (super_admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留 1 个超级管理员")

    await user_repository.delete_user(user_id)
    await admin_repository.create_action_log(
        current_admin.id,
        AdminActionType.DELETE_USER.value,
        detail=f"delete_user={user_id}",
    )
    return ResponseOut()


@router.post("/users/{user_id}/blacklist", response_model=AdminUserOut)
async def add_blacklist(
    user_id: int,
    data: UserBlacklistIn,
    current_admin: User = Depends(auth_handler.auth_admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以拉黑用户")
    if current_admin.id == user_id:
        raise HTTPException(status_code=403, detail="不能拉黑自己")
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
    if current_admin.role not in SUPER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="只有超级管理员可以移出黑名单")
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
        created_by=current_admin.id,
    )
    await repository.create_action_log(
        current_admin.id,
        AdminActionType.SENSITIVE_WORD_UPSERT.value,
        detail=f"word={data.word}; reason={data.reason or ''}",
    )
    return rule


@router.delete("/sensitive-words/{word}", response_model=ResponseOut)
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
