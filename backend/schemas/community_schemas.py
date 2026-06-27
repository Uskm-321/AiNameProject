from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from schemas.agent import DomainSchema, NameSchema


class CommunityPollCreateIn(BaseModel):
    naming_type: Annotated[str, Field(..., min_length=1, max_length=50)]
    candidate_names: Annotated[list[NameSchema], Field(..., min_length=1, max_length=10)]
    ai_analysis: str | None = Field(default="", max_length=2000)


class CommunityVoteIn(BaseModel):
    option_id: int


class CommunityHideIn(BaseModel):
    reason: Annotated[str, Field(..., min_length=1, max_length=255)]


class CommunityPollOptionOut(BaseModel):
    id: int
    name: str
    reference: str = ""
    moral: str = ""
    style_reason: str = ""
    score: int = 0
    domains: list[DomainSchema] = Field(default_factory=list)
    votes_count: int = 0


class CommunityPollOut(BaseModel):
    id: int
    user_id: int
    username: str
    naming_type: str
    ai_analysis: str = ""
    hidden: bool = False
    hidden_reason: str | None = None
    created_at: datetime
    options: list[CommunityPollOptionOut]
    my_vote_option_id: int | None = None


class CommunityPollListOut(BaseModel):
    total: int
    items: list[CommunityPollOut]
