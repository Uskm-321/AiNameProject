import json
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.community import CommunityPoll, CommunityPollOption, CommunityPollVote
from models.user import User
from schemas.community_schemas import CommunityPollCreateIn


class CommunityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_poll(self, user_id: int, data: CommunityPollCreateIn):
        async with self.session.begin():
            poll = CommunityPoll(
                user_id=user_id,
                naming_type=data.naming_type,
                ai_analysis=data.ai_analysis or "",
            )
            self.session.add(poll)
            await self.session.flush()

            for item in data.candidate_names:
                self.session.add(
                    CommunityPollOption(
                        poll_id=poll.id,
                        name=item.name,
                        reference=item.reference,
                        moral=item.moral,
                        style_reason=item.style_reason,
                        score=item.score,
                        domains_json=json.dumps([domain.model_dump() for domain in item.domains], ensure_ascii=False),
                    )
                )
            return poll

    async def list_polls(self, user_id: int, *, offset: int = 0, limit: int = 20, include_all: bool = False):
        async with self.session.begin():
            stmt = select(CommunityPoll, User.username).join(User, User.id == CommunityPoll.user_id)
            count_stmt = select(func.count(CommunityPoll.id))

            if not include_all:
                visible_filter = or_(CommunityPoll.hidden.is_(False), CommunityPoll.user_id == user_id)
                stmt = stmt.where(visible_filter)
                count_stmt = count_stmt.where(visible_filter)

            stmt = stmt.order_by(CommunityPoll.created_at.desc(), CommunityPoll.id.desc()).offset(offset).limit(limit)
            rows = (await self.session.execute(stmt)).all()
            total = await self.session.scalar(count_stmt)
            return total or 0, rows

    async def get_poll(self, poll_id: int):
        async with self.session.begin():
            return await self.session.scalar(select(CommunityPoll).where(CommunityPoll.id == poll_id))

    async def get_options(self, poll_id: int):
        result = await self.session.scalars(
            select(CommunityPollOption).where(CommunityPollOption.poll_id == poll_id).order_by(CommunityPollOption.id.asc())
        )
        return list(result)

    async def get_user_vote(self, poll_id: int, user_id: int):
        return await self.session.scalar(
            select(CommunityPollVote).where(
                CommunityPollVote.poll_id == poll_id,
                CommunityPollVote.user_id == user_id,
            )
        )

    async def vote(self, poll_id: int, option_id: int, user_id: int):
        async with self.session.begin():
            poll = await self.session.scalar(select(CommunityPoll).where(CommunityPoll.id == poll_id))
            if not poll or poll.hidden:
                return None

            option = await self.session.scalar(
                select(CommunityPollOption).where(
                    CommunityPollOption.id == option_id,
                    CommunityPollOption.poll_id == poll_id,
                )
            )
            if not option:
                return None

            vote = await self.session.scalar(
                select(CommunityPollVote).where(
                    CommunityPollVote.poll_id == poll_id,
                    CommunityPollVote.user_id == user_id,
                )
            )
            if vote and vote.option_id == option_id:
                return vote

            if vote:
                old_option = await self.session.scalar(select(CommunityPollOption).where(CommunityPollOption.id == vote.option_id))
                if old_option and old_option.votes_count > 0:
                    old_option.votes_count -= 1
                vote.option_id = option_id
            else:
                vote = CommunityPollVote(poll_id=poll_id, option_id=option_id, user_id=user_id)
                self.session.add(vote)

            option.votes_count += 1
            return vote

    async def hide_poll(self, poll_id: int, admin_user_id: int, reason: str):
        async with self.session.begin():
            poll = await self.session.scalar(select(CommunityPoll).where(CommunityPoll.id == poll_id))
            if not poll:
                return None
            poll.hidden = True
            poll.hidden_reason = reason
            poll.hidden_by = admin_user_id
            poll.hidden_at = datetime.now()
            return poll

    async def unhide_poll(self, poll_id: int):
        async with self.session.begin():
            poll = await self.session.scalar(select(CommunityPoll).where(CommunityPoll.id == poll_id))
            if not poll:
                return None
            poll.hidden = False
            poll.hidden_reason = None
            poll.hidden_by = None
            poll.hidden_at = None
            return poll
