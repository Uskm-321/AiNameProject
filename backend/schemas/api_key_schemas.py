from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class APIKeyCreateIn(BaseModel):
    name: Annotated[str, Field(..., min_length=1, max_length=100)]


class APIKeyCreateOut(BaseModel):
    id: int
    key: str
    name: str
    status: str
    total_quota: int
    used_today: int
    total_used: int
    created_at: datetime


class APIKeyOut(BaseModel):
    id: int
    name: str
    key_masked: str
    status: str
    total_quota: int
    used_today: int
    total_used: int
    last_used_at: datetime | None = None
    created_at: datetime


class APIKeyActionIn(BaseModel):
    key_id: int


class APIKeyDailyUsageOut(BaseModel):
    date: str
    used: int


class APIKeyEndpointUsageOut(BaseModel):
    name: str
    used: int


class APIKeyStatsOut(BaseModel):
    total_keys: int
    used_today: int
    remaining_today: int
    total_used: int
    recent_7_days: list[APIKeyDailyUsageOut]
    endpoint_distribution: list[APIKeyEndpointUsageOut]


class APIKeyUsageOut(BaseModel):
    id: int
    api_key_id: int
    path: str
    cost: int
    status: str
    created_at: datetime


class APIKeyUsageListOut(BaseModel):
    total: int
    items: list[APIKeyUsageOut]
