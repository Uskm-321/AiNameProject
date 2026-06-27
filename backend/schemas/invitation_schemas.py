from datetime import datetime

from pydantic import BaseModel


class CreditRewardOut(BaseModel):
    id: int
    amount: int
    reason: str
    related_user_id: int | None = None
    created_at: datetime


class InvitationSummaryOut(BaseModel):
    invite_code: str
    invite_link: str
    invite_count: int
    credits: int
    rewards: list[CreditRewardOut]
