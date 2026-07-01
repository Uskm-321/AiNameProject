import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.user import CreditReward, Invitation, User
from schemas.user_schemas import UserCreateSchema


class InvitationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _new_invite_code(self) -> str:
        while True:
            code = secrets.token_urlsafe(6)
            exists = await self.session.scalar(select(User.id).where(User.invite_code == code))
            if not exists:
                return code

    async def create_user(self, user_schema: UserCreateSchema, invite_code: str | None = None) -> User:
        async with self.session.begin():
            inviter = None
            normalized_code = (invite_code or "").strip()
            if normalized_code:
                inviter = await self.session.scalar(
                    select(User).where(User.invite_code == normalized_code)
                )
                if not inviter:
                    raise ValueError("邀请码无效")

            user = User(
                **user_schema.model_dump(),
                invite_code=await self._new_invite_code(),
                invited_by_user_id=inviter.id if inviter else None,
                credits=5 if inviter else 0,
            )
            self.session.add(user)
            await self.session.flush()

            if inviter:
                inviter.credits += 10
                self.session.add(
                    Invitation(
                        inviter_id=inviter.id,
                        invitee_id=user.id,
                        invite_code=normalized_code,
                    )
                )
                self.session.add_all(
                    [
                        CreditReward(
                            user_id=inviter.id,
                            amount=10,
                            reason="INVITER_REWARD",
                            related_user_id=user.id,
                        ),
                        CreditReward(
                            user_id=user.id,
                            amount=5,
                            reason="INVITEE_REWARD",
                            related_user_id=inviter.id,
                        ),
                    ]
                )
            return user

    async def summary(self, user_id: int):
        async with self.session.begin():
            user = await self.session.scalar(select(User).where(User.id == user_id))
            if user and not user.invite_code:
                user.invite_code = await self._new_invite_code()
            invite_count = await self.session.scalar(
                select(func.count(Invitation.id)).where(Invitation.inviter_id == user_id)
            )
            rewards = list(
                await self.session.scalars(
                    select(CreditReward)
                    .where(CreditReward.user_id == user_id)
                    .order_by(CreditReward.id.desc())
                )
            )
            return user, invite_count or 0, rewards
