from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentPackageOut(BaseModel):
    id: str
    name: str
    amount: Decimal
    quota: int


class PaymentCreateIn(BaseModel):
    package_id: str = Field(..., min_length=1, max_length=50)
    api_key_id: int


class PaymentCreateOut(BaseModel):
    id: int
    out_trade_no: str
    pay_url: str
    pay_form_url: str
    qr_code: str | None = None
    qr_image_url: str | None = None
    amount: Decimal
    quota: int
    subject: str
    status: str
    expires_at: datetime


class PaymentOrderOut(BaseModel):
    id: int
    out_trade_no: str
    trade_no: str | None = None
    package_id: str
    api_key_id: int
    subject: str
    amount: Decimal
    quota: int
    qr_code: str | None = None
    qr_image_url: str | None = None
    status: str
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None = None


class PaymentSyncOut(BaseModel):
    order: PaymentOrderOut
    alipay_status: str | None = None
    message: str
