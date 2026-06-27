from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.auth import AuthHandler
from core.invite_link import build_invite_register_link
from dependencies import get_session
from models.user import User
from repository.invitation_repo import InvitationRepository
from schemas.invitation_schemas import CreditRewardOut, InvitationSummaryOut


router = APIRouter(prefix="/invitation", tags=["invitation"])
auth_handler = AuthHandler()


@router.get("/me", response_model=InvitationSummaryOut)
async def invitation_summary(
    request: Request,
    current_user: User = Depends(auth_handler.auth_user_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = InvitationRepository(session)
    user, invite_count, rewards = await repository.summary(current_user.id)
    invite_link = build_invite_register_link(str(request.base_url), user.invite_code)
    return InvitationSummaryOut(
        invite_code=user.invite_code,
        invite_link=invite_link,
        invite_count=invite_count,
        credits=user.credits,
        rewards=[
            CreditRewardOut(
                id=item.id,
                amount=item.amount,
                reason=item.reason,
                related_user_id=item.related_user_id,
                created_at=item.created_at,
            )
            for item in rewards
        ],
    )
