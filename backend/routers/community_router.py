import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.community import CommunityPoll
from models.user import User
from repository.community_repo import CommunityRepository
from schemas import ResponseOut
from schemas.community_schemas import (
    CommunityPollCreateIn,
    CommunityPollListOut,
    CommunityPollOptionOut,
    CommunityPollOut,
    CommunityVoteIn,
)

auth_handler = AuthHandler()
router = APIRouter(prefix="/community", tags=["community"])


def _parse_domains(raw: str | None):
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


async def _build_poll_out(
    repository: CommunityRepository,
    poll: CommunityPoll,
    username: str,
    current_user: User,
):
    options = await repository.get_options(poll.id)
    vote = await repository.get_user_vote(poll.id, current_user.id)
    return CommunityPollOut(
        id=poll.id,
        user_id=poll.user_id,
        username=username,
        naming_type=poll.naming_type,
        ai_analysis=poll.ai_analysis or "",
        hidden=poll.hidden,
        hidden_reason=poll.hidden_reason if poll.user_id == current_user.id else None,
        created_at=poll.created_at,
        my_vote_option_id=vote.option_id if vote else None,
        options=[
            CommunityPollOptionOut(
                id=option.id,
                name=option.name,
                reference=option.reference or "",
                moral=option.moral or "",
                style_reason=option.style_reason or "",
                score=option.score,
                domains=_parse_domains(option.domains_json),
                votes_count=option.votes_count,
            )
            for option in options
        ],
    )


@router.post("/polls", response_model=CommunityPollOut)
async def create_poll(
    data: CommunityPollCreateIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = CommunityRepository(session=session)
    poll = await repository.create_poll(current_user.id, data)
    return await _build_poll_out(repository, poll, current_user.username, current_user)


@router.get("/polls", response_model=CommunityPollListOut)
async def list_polls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = CommunityRepository(session=session)
    offset = (page - 1) * page_size
    total, rows = await repository.list_polls(current_user.id, offset=offset, limit=page_size)
    items = [
        await _build_poll_out(repository, poll, username, current_user)
        for poll, username in rows
    ]
    return CommunityPollListOut(total=total, items=items)


@router.post("/polls/{poll_id}/vote", response_model=ResponseOut)
async def vote_poll(
    poll_id: int,
    data: CommunityVoteIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = CommunityRepository(session=session)
    vote = await repository.vote(poll_id, data.option_id, current_user.id)
    if not vote:
        raise HTTPException(status_code=404, detail="投票不存在或已被隐藏")
    return ResponseOut()


@router.delete("/polls/{poll_id}", response_model=ResponseOut)
async def delete_poll(
    poll_id: int,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = CommunityRepository(session=session)
    poll = await repository.get_poll(poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="投票不存在")
    if poll.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只能删除自己发布的投票")
    await repository.delete_poll(poll_id)
    return ResponseOut()
