from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.user import User
from repository.api_key_repo import APIKeyRepository
from schemas import ResponseOut
from schemas.api_key_schemas import (
    APIKeyCreateIn,
    APIKeyCreateOut,
    APIKeyActionIn,
    APIKeyOut,
    APIKeyStatsOut,
    APIKeyUsageListOut,
    APIKeyUsageOut,
)


auth_handler = AuthHandler()
router = APIRouter(prefix="/api-key", tags=["api-key"])


def _key_out(api_key) -> APIKeyOut:
    masked = api_key.key if len(api_key.key) <= 12 else f"{api_key.key[:7]}...{api_key.key[-4:]}"
    return APIKeyOut(
        id=api_key.id,
        name=api_key.name,
        key_masked=masked,
        status=api_key.status,
        total_quota=api_key.total_quota,
        used_today=api_key.used_today,
        total_used=api_key.total_used,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
    )


@router.post("/create", response_model=APIKeyCreateOut)
async def create_api_key(
    data: APIKeyCreateIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    api_key = await repository.create_key(current_user.id, data.name)
    return APIKeyCreateOut(
        id=api_key.id,
        key=api_key.key,
        name=api_key.name,
        status=api_key.status,
        total_quota=api_key.total_quota,
        used_today=api_key.used_today,
        total_used=api_key.total_used,
        created_at=api_key.created_at,
    )


@router.get("/list", response_model=list[APIKeyOut])
async def list_api_keys(
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    return [_key_out(item) for item in await repository.list_keys(current_user.id)]


@router.post("/disable", response_model=ResponseOut)
async def disable_api_key(
    data: APIKeyActionIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    api_key = await repository.disable_key(current_user.id, data.key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return ResponseOut()


@router.post("/enable", response_model=ResponseOut)
async def enable_api_key(
    data: APIKeyActionIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    api_key = await repository.enable_key(current_user.id, data.key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在或无法启用")
    return ResponseOut()


@router.post("/delete", response_model=ResponseOut)
async def delete_api_key(
    data: APIKeyActionIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    api_key = await repository.delete_key(current_user.id, data.key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return ResponseOut()


@router.get("/stats", response_model=APIKeyStatsOut)
async def api_key_stats(
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    return await repository.stats(current_user.id)


@router.get("/usage", response_model=APIKeyUsageListOut)
async def api_key_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = APIKeyRepository(session=session)
    total, items = await repository.list_usage(
        current_user.id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return APIKeyUsageListOut(
        total=total,
        items=[
            APIKeyUsageOut(
                id=item.id,
                api_key_id=item.api_key_id,
                path=item.path,
                cost=item.cost,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ],
    )
