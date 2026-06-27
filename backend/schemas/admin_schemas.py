from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


ModerationDecisionLiteral = Literal["PASS", "BLOCK"]
ReviewStatusLiteral = Literal["AUTO_PASS", "AUTO_BLOCK", "PENDING", "REVIEWED"]


class SensitiveWordIn(BaseModel):
    word: Annotated[str, Field(..., min_length=1, max_length=128)]
    reason: str | None = Field(default=None, max_length=255)


class SensitiveWordOut(SensitiveWordIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ModerationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source: str
    input_text: str
    output_text: str | None = None
    matched_words: str | None = None
    decision: ModerationDecisionLiteral
    review_status: ReviewStatusLiteral
    review_note: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ModerationRecordListOut(BaseModel):
    total: int
    items: list[ModerationRecordOut]


class AdminActionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_user_id: int
    target_user_id: int | None = None
    action: str
    detail: str | None = None
    created_at: datetime


class AdminActionLogListOut(BaseModel):
    total: int
    items: list[AdminActionLogOut]


class AdminReviewIn(BaseModel):
    note: str | None = Field(default=None, max_length=255)
