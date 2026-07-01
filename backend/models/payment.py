from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class PaymentStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CLOSED = "closed"
    FAILED = "failed"


class PaymentOrder(Base):
    __tablename__ = "payment_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_key.id"), nullable=False)
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trade_no: Mapped[str | None] = mapped_column(String(128))
    package_id: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quota: Mapped[int] = mapped_column(Integer, nullable=False)
    qr_code: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.CREATED.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
